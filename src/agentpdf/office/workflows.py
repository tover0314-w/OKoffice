from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.sheet import extract_sheet_tables
from agentpdf.office.word import extract_word_tables
from agentpdf.office.xlsx import write_xlsx
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_output_path


TOOL_NAME = "office.workflow.extract_to_sheet"
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def extract_to_sheet(input_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except AgentPDFException as exc:
        return _failed(exc.to_error())

    records: list[dict[str, Any]] = []
    cell_records: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    warnings: list[str] = []

    for input_path in input_paths:
        source_summary, source_records, source_cells, source_warnings = _extract_source(input_path)
        source_summaries.append(source_summary)
        records.extend(source_records)
        cell_records.extend(source_cells)
        warnings.extend(source_warnings)

    if not records:
        return _failed(
            AgentPDFError(
                code="unsupported_file_type",
                message="No supported Word or Excel tables were extracted for office.workflow.extract_to_sheet.",
                details={"input_count": len(input_paths), "sources": source_summaries},
            )
        )

    _write_evidence_workbook(output, records=records, cell_records=cell_records)
    artifact = build_artifact(output, TOOL_NAME)
    table_count = len({record["table_record_id"] for record in records})
    cell_count = len(cell_records)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        artifacts=[artifact],
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(
                    name="sources_scanned",
                    status="passed",
                    details={"source_count": len(input_paths), "supported_source_count": _supported_count(source_summaries)},
                ),
                ValidationCheck(
                    name="evidence_rows_extracted",
                    status="passed",
                    details={"table_count": table_count, "row_count": len(records), "cell_count": cell_count},
                ),
                ValidationCheck(
                    name="evidence_workbook_written",
                    status="passed",
                    details={"path": output.as_posix(), "mime_type": XLSX_MIME_TYPE},
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "source_count": len(input_paths),
                "supported_source_count": _supported_count(source_summaries),
                "table_count": table_count,
                "row_count": len(records),
                "cell_count": cell_count,
            },
            "evidence_workbook": {
                "path": output.as_posix(),
                "format": "xlsx",
                "sheets": ["Tables", "Cells"],
                "artifact_id": artifact.artifact_id,
            },
            "sources": source_summaries,
            "records": records,
            "cell_records": cell_records,
        },
        next_recommended_tools=[
            "sheet.inspect.workbook",
            "sheet.profile.data",
            "office.workflow.source_to_deck",
            "office.context.build_packet",
        ],
    )


def _extract_source(
    input_path: str | Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    preflight = inspect_office_file(input_path)
    if preflight.status == "failed":
        message = preflight.error.message if preflight.error else f"Unable to inspect source: {input_path}"
        return (
            {"path": str(input_path), "status": "failed", "table_count": 0, "row_count": 0, "cell_count": 0},
            [],
            [],
            [message],
        )

    source_path = str(preflight.usage["file"]["path"])
    source_format = str(preflight.usage["format"]["detected_format"])
    if source_format == "docx":
        result = extract_word_tables(source_path)
    elif source_format == "xlsx":
        result = extract_sheet_tables(source_path)
    else:
        warning = f"office.workflow.extract_to_sheet currently skips {source_format} sources: {source_path}"
        return (
            {
                "path": source_path,
                "format": source_format,
                "status": "skipped",
                "table_count": 0,
                "row_count": 0,
                "cell_count": 0,
                "reason": "unsupported_in_local_extract_to_sheet_v0",
            },
            [],
            [],
            [warning],
        )

    if result.status == "failed":
        message = result.error.message if result.error else f"Unable to extract source tables: {source_path}"
        return (
            {
                "path": source_path,
                "format": source_format,
                "status": "failed",
                "table_count": 0,
                "row_count": 0,
                "cell_count": 0,
            },
            [],
            [],
            [message],
        )

    records, cell_records = _normalize_table_result(source_path, source_format, result.usage["tables"])
    return (
        {
            "path": source_path,
            "format": source_format,
            "status": "extracted",
            "table_count": result.usage["summary"]["table_count"],
            "row_count": len(records),
            "cell_count": len(cell_records),
            "extract_tool": result.tool,
        },
        records,
        cell_records,
        list(result.warnings),
    )


def _normalize_table_result(
    source_path: str,
    source_format: str,
    tables: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = []
    cell_records = []
    for table in tables:
        table_id = str(table["table_id"])
        table_source = table.get("source", {}) if isinstance(table.get("source"), dict) else {}
        sheet_name = str(table_source.get("sheet_name") or "")
        table_record_id = f"{source_format}:{source_path}:{table_id}"
        for row in table.get("rows", []):
            row_index = int(row.get("row_index", 0))
            cells = row.get("cells", []) if isinstance(row.get("cells"), list) else []
            values = [_cell_text(cell) for cell in cells if isinstance(cell, dict)]
            source_refs = [cell.get("source", {}) for cell in cells if isinstance(cell, dict)]
            records.append(
                {
                    "table_record_id": table_record_id,
                    "source_path": source_path,
                    "source_format": source_format,
                    "table_id": table_id,
                    "table_index": int(table.get("table_index", 0)),
                    "source_sheet": sheet_name,
                    "source_row_index": row_index,
                    "values": values,
                    "source_refs": source_refs,
                }
            )
            for fallback_index, cell in enumerate(cells, start=1):
                if not isinstance(cell, dict):
                    continue
                source_ref = cell.get("source", {}) if isinstance(cell.get("source"), dict) else {}
                cell_records.append(
                    {
                        "source_path": source_path,
                        "source_format": source_format,
                        "table_id": table_id,
                        "source_sheet": sheet_name,
                        "source_row_index": row_index,
                        "source_cell_index": int(cell.get("cell_index") or source_ref.get("column_index") or fallback_index),
                        "cell_ref": str(cell.get("cell_ref") or source_ref.get("cell_ref") or ""),
                        "value": _cell_text(cell),
                        "source_ref": source_ref,
                    }
                )
    return records, cell_records


def _cell_text(cell: dict[str, Any]) -> str:
    return str(cell.get("text", cell.get("value", "")))


def _write_evidence_workbook(
    path: Path,
    *,
    records: list[dict[str, Any]],
    cell_records: list[dict[str, Any]],
) -> None:
    max_columns = max((len(record["values"]) for record in records), default=0)
    table_headers = [
        "source_path",
        "source_format",
        "table_id",
        "source_sheet",
        "source_row_index",
        *[f"col_{index}" for index in range(1, max_columns + 1)],
        "source_refs_json",
    ]
    table_rows = [table_headers]
    for record in records:
        values = list(record["values"])
        table_rows.append(
            [
                record["source_path"],
                record["source_format"],
                record["table_id"],
                record["source_sheet"],
                str(record["source_row_index"]),
                *values,
                *([""] * (max_columns - len(values))),
                json.dumps(record["source_refs"], ensure_ascii=False, sort_keys=True),
            ]
        )

    cell_headers = [
        "source_path",
        "source_format",
        "table_id",
        "source_sheet",
        "source_row_index",
        "source_cell_index",
        "cell_ref",
        "value",
        "source_ref_json",
    ]
    cell_rows = [cell_headers]
    for cell in cell_records:
        cell_rows.append(
            [
                cell["source_path"],
                cell["source_format"],
                cell["table_id"],
                cell["source_sheet"],
                str(cell["source_row_index"]),
                str(cell["source_cell_index"]),
                cell["cell_ref"],
                cell["value"],
                json.dumps(cell["source_ref"], ensure_ascii=False, sort_keys=True),
            ]
        )

    write_xlsx(path, [("Tables", table_rows), ("Cells", cell_rows)])


def _supported_count(sources: list[dict[str, Any]]) -> int:
    return sum(1 for source in sources if source.get("status") == "extracted")


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
