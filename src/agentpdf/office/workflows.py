from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.deck import create_deck_from_outline
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.sheet import extract_sheet_tables, profile_sheet_data
from agentpdf.office.word import extract_word_tables
from agentpdf.office.xlsx import write_xlsx
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_output_path


EXTRACT_TO_SHEET_TOOL_NAME = "office.workflow.extract_to_sheet"
SHEET_TO_DECK_TOOL_NAME = "office.workflow.sheet_to_deck"
TOOL_NAME = EXTRACT_TO_SHEET_TOOL_NAME
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


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
            "office.workflow.sheet_to_deck",
            "office.context.build_packet",
        ],
    )


def sheet_to_deck(
    workbook_path: str | Path,
    output_path: str | Path,
    *,
    title: str | None = None,
    max_rows_per_sheet: int = 100,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except AgentPDFException as exc:
        return _failed(exc.to_error(), tool=SHEET_TO_DECK_TOOL_NAME)

    profile_result = profile_sheet_data(workbook_path, max_rows_per_sheet=max_rows_per_sheet)
    if profile_result.status == "failed":
        return _failed(
            profile_result.error
            or AgentPDFError(code="unsupported_file_type", message="Workbook profile failed before deck creation."),
            tool=SHEET_TO_DECK_TOOL_NAME,
        )

    profile_usage = profile_result.usage
    summary = profile_usage.get("summary", {}) if isinstance(profile_usage.get("summary"), dict) else {}
    profiles = profile_usage.get("profiles", []) if isinstance(profile_usage.get("profiles"), list) else []
    data_row_count = int(summary.get("data_row_count", 0))
    profiled_profiles = [profile for profile in profiles if isinstance(profile, dict) and int(profile.get("data_row_count", 0)) > 0]
    if data_row_count <= 0 or not profiled_profiles:
        return _failed(
            AgentPDFError(
                code="unsafe_input_rejected",
                message="office.workflow.sheet_to_deck requires at least one profiled workbook data row.",
                details={"workbook_path": str(workbook_path), "profiled_sheet_count": len(profiled_profiles)},
            ),
            tool=SHEET_TO_DECK_TOOL_NAME,
        )

    outline = _sheet_profile_outline(
        workbook_path=workbook_path,
        title=title,
        profile_summary=summary,
        profiles=profiled_profiles,
        warnings=profile_result.warnings,
    )
    deck_result = create_deck_from_outline(outline, output)
    if deck_result.status == "failed":
        return _failed(
            deck_result.error or AgentPDFError(code="artifact_validation_failed", message="Deck creation failed."),
            tool=SHEET_TO_DECK_TOOL_NAME,
        )

    artifact = build_artifact(output, SHEET_TO_DECK_TOOL_NAME)
    deck_summary = deck_result.usage.get("summary", {}) if isinstance(deck_result.usage.get("summary"), dict) else {}
    warnings = [*profile_result.warnings, *deck_result.warnings]
    checks = [
        ValidationCheck(
            name="workbook_profiled",
            status="passed",
            details={
                "workbook_path": str(workbook_path),
                "profiled_sheet_count": summary.get("profiled_sheet_count", 0),
                "data_row_count": data_row_count,
                "source_coverage": summary.get("source_coverage", {}),
            },
        ),
        ValidationCheck(
            name="deck_outline_created",
            status="passed",
            details={
                "slide_count": len(outline["slides"]),
                "style": outline["style"],
                "source": outline["source"],
            },
        ),
        ValidationCheck(
            name="pptx_written",
            status="passed",
            details={"path": output.as_posix(), "mime_type": PPTX_MIME_TYPE},
        ),
        ValidationCheck(
            name="deck_validated",
            status=deck_result.validation.status if deck_result.validation is not None else "warning",
            details={
                "slide_count": deck_summary.get("slide_count", len(outline["slides"])),
                "text_run_count": deck_summary.get("text_run_count", 0),
            },
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=SHEET_TO_DECK_TOOL_NAME,
        artifacts=[artifact],
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "workbook_path": str(workbook_path),
                "deck_path": output.as_posix(),
                "slide_count": deck_summary.get("slide_count", len(outline["slides"])),
                "profiled_sheet_count": summary.get("profiled_sheet_count", len(profiled_profiles)),
                "column_count": summary.get("column_count", 0),
                "data_row_count": data_row_count,
                "missing_cell_count": summary.get("missing_cell_count", 0),
                "formula_cell_count": summary.get("formula_cell_count", 0),
                "source_coverage": summary.get("source_coverage", {}),
            },
            "workbook_profile": {
                "summary": summary,
                "profiles": profiled_profiles,
            },
            "outline": outline,
            "deck": {
                "path": output.as_posix(),
                "format": "pptx",
                "artifact_id": artifact.artifact_id,
            },
        },
        next_recommended_tools=[
            "deck.inspect.presentation",
            "deck.validate.presentation",
            "office.workflow.board_pack",
            "office.context.build_packet",
        ],
    )


def _sheet_profile_outline(
    *,
    workbook_path: str | Path,
    title: str | None,
    profile_summary: dict[str, Any],
    profiles: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    deck_title = (title or "").strip() or f"{Path(workbook_path).stem} Review"
    source_coverage = profile_summary.get("source_coverage", {})
    coverage_status = source_coverage.get("status", "unknown") if isinstance(source_coverage, dict) else "unknown"
    slides: list[dict[str, Any]] = [
        {
            "title": deck_title,
            "subtitle": "Generated from an OKoffice workbook profile",
            "bullets": [
                f"{profile_summary.get('profiled_sheet_count', len(profiles))} profiled sheet(s)",
                f"{profile_summary.get('data_row_count', 0)} data rows across {profile_summary.get('column_count', 0)} columns",
                f"Source coverage: {coverage_status}",
            ],
            "notes": f"Source workbook: {workbook_path}",
        },
        {
            "title": "Executive Summary",
            "bullets": [
                f"Workbook rows profiled: {profile_summary.get('data_row_count', 0)}",
                f"Formula cells detected: {profile_summary.get('formula_cell_count', 0)}",
                f"Missing cells detected: {profile_summary.get('missing_cell_count', 0)}",
                f"Source refs: {coverage_status}",
            ],
        },
    ]
    for profile in profiles[:8]:
        slides.append(_profile_slide(profile, coverage_status=coverage_status))

    validation_bullets = [
        f"Source coverage: {coverage_status}",
        f"Source ref rows: {profile_summary.get('source_ref_row_count', 0)}",
        f"Missing cells: {profile_summary.get('missing_cell_count', 0)}",
        f"Formula cells: {profile_summary.get('formula_cell_count', 0)}",
    ]
    if warnings:
        validation_bullets.append(f"Warnings: {len(warnings)}")
    slides.append(
        {
            "title": "Validation & Source Map",
            "bullets": validation_bullets,
            "notes": "Run deck.inspect.presentation and office.workflow.board_pack before delivery.",
        }
    )
    return {
        "title": deck_title,
        "style": "executive",
        "source": {
            "type": "workbook_profile",
            "workbook_path": str(workbook_path),
            "profile_tool": "sheet.profile.data",
        },
        "slides": slides,
    }


def _profile_slide(profile: dict[str, Any], *, coverage_status: str) -> dict[str, Any]:
    sheet_name = str(profile.get("sheet_name") or "Workbook Sheet")
    headers = [str(header) for header in profile.get("headers", []) if str(header).strip()]
    columns = profile.get("columns", []) if isinstance(profile.get("columns"), list) else []
    numeric_columns = _columns_by_semantic_type(columns, "number")
    text_columns = _columns_by_semantic_type(columns, "text")
    bullets = [
        f"{profile.get('data_row_count', 0)} data rows across {len(headers)} columns",
        f"Key columns: {_join_limited(headers, fallback='none detected')}",
        f"Numeric columns: {_join_limited(numeric_columns, fallback='none detected')}",
        f"Text columns: {_join_limited(text_columns, fallback='none detected')}",
        f"Missing cells: {profile.get('missing_cell_count', 0)}; formula cells: {profile.get('formula_cell_count', 0)}",
        f"Source coverage: {coverage_status}",
    ]
    return {
        "title": f"{sheet_name} Snapshot",
        "bullets": bullets,
        "notes": f"Source workbook sheet: {sheet_name}",
    }


def _columns_by_semantic_type(columns: list[Any], semantic_type: str) -> list[str]:
    names: list[str] = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        if column.get("semantic_type") == semantic_type:
            names.append(str(column.get("header") or f"column_{column.get('column_index', '')}").strip())
    return [name for name in names if name]


def _join_limited(values: list[str], *, fallback: str, limit: int = 5) -> str:
    cleaned = [value for value in values if value][:limit]
    if not cleaned:
        return fallback
    suffix = "" if len(values) <= limit else f" (+{len(values) - limit} more)"
    return ", ".join(cleaned) + suffix


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


def _failed(error: AgentPDFError, *, tool: str = TOOL_NAME) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
