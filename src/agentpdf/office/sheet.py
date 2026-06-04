from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.ooxml import SHEET_NS, count_members, read_xml, sorted_members, zip_names
from agentpdf.office.xlsx import write_xlsx
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_output_path


INSPECT_TOOL_NAME = "sheet.inspect.workbook"
EXTRACT_TABLES_TOOL_NAME = "sheet.extract.tables"
WRITE_WORKBOOK_TOOL_NAME = "sheet.write.workbook"
VALIDATE_WORKBOOK_TOOL_NAME = "sheet.validate.workbook"
READ_WORKBOOK_TOOL_NAME = "sheet.read.workbook"
CELL_REF_RE = re.compile(r"^([A-Z]+)([0-9]+)$", re.IGNORECASE)
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def inspect_sheet_workbook(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            INSPECT_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet inspect failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            INSPECT_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.inspect.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    sheets = _sheet_summaries(source_path, worksheet_members, sheet_names)
    formula_count = sum(int(sheet["formula_count"]) for sheet in sheets)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=INSPECT_TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="workbook_xml_present", status="passed"),
            ],
        ),
        usage={
            "workbook": {
                "path": source_path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
                "sheet_count": len(sheets),
            },
            "sheets": sheets,
            "formulas": {"formula_count": formula_count},
            "tables": {"table_count": count_members(names, prefix="xl/tables/")},
            "charts": {"chart_count": count_members(names, prefix="xl/charts/")},
            "links": {"external_link_count": count_members(names, prefix="xl/externalLinks/")},
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=["sheet.extract.tables", "sheet.profile.data", "office.context.build_packet"],
    )


def extract_sheet_tables(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet table extraction failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.extract.tables requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))
    tables = _extract_worksheet_tables(source_path, worksheet_members, sheet_names, shared_strings)
    row_count = sum(len(table["rows"]) for table in tables)
    cell_count = sum(len(row["cells"]) for table in tables for row in table["rows"])

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=EXTRACT_TABLES_TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="workbook_xml_present", status="passed"),
                ValidationCheck(
                    name="tables_extracted",
                    status="passed",
                    details={"table_count": len(tables), "row_count": row_count, "cell_count": cell_count},
                ),
            ],
        ),
        usage={
            "workbook": {
                "path": source_path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
                "sheet_count": len(worksheet_members),
            },
            "summary": {"table_count": len(tables), "row_count": row_count, "cell_count": cell_count},
            "tables": tables,
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=["sheet.write.workbook", "office.workflow.extract_to_sheet", "office.context.build_packet"],
    )


def write_sheet_workbook(data: dict[str, Any] | list[dict[str, Any]], output_path: str | Path) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except AgentPDFException as exc:
        return _failed(WRITE_WORKBOOK_TOOL_NAME, exc.to_error())

    records = _write_records(data)
    if not records:
        return _failed(
            WRITE_WORKBOOK_TOOL_NAME,
            AgentPDFError(
                code="unsafe_input_rejected",
                message="sheet.write.workbook requires at least one record or table row.",
            ),
        )

    max_columns = max(len(record["values"]) for record in records)
    source_ref_count = sum(len(record["source_refs"]) for record in records)
    workbook_rows = [_workbook_headers(max_columns)]
    source_rows = [
        [
            "record_index",
            "source_path",
            "source_format",
            "table_id",
            "source_sheet",
            "source_row_index",
            "source_refs_json",
        ]
    ]
    for record_index, record in enumerate(records, start=1):
        values = list(record["values"])
        workbook_rows.append(
            [
                record["source_path"],
                record["source_format"],
                record["table_id"],
                record["source_sheet"],
                record["source_row_index"],
                *values,
                *([""] * (max_columns - len(values))),
            ]
        )
        source_rows.append(
            [
                record_index,
                record["source_path"],
                record["source_format"],
                record["table_id"],
                record["source_sheet"],
                record["source_row_index"],
                json.dumps(record["source_refs"], ensure_ascii=False, sort_keys=True),
            ]
        )

    write_xlsx(output, [("Workbook", workbook_rows), ("SourceRefs", source_rows)])
    artifact = build_artifact(output, WRITE_WORKBOOK_TOOL_NAME)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=WRITE_WORKBOOK_TOOL_NAME,
        artifacts=[artifact],
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="records_normalized",
                    status="passed",
                    details={
                        "record_count": len(records),
                        "column_count": max_columns,
                        "source_ref_count": source_ref_count,
                    },
                ),
                ValidationCheck(
                    name="workbook_written",
                    status="passed",
                    details={"path": output.as_posix(), "mime_type": XLSX_MIME_TYPE},
                ),
            ],
        ),
        usage={
            "summary": {
                "record_count": len(records),
                "column_count": max_columns,
                "source_ref_count": source_ref_count,
            },
            "workbook": {
                "path": output.as_posix(),
                "format": "xlsx",
                "sheets": ["Workbook", "SourceRefs"],
                "artifact_id": artifact.artifact_id,
            },
            "records": records,
        },
        next_recommended_tools=[
            "sheet.inspect.workbook",
            "sheet.validate.workbook",
            "office.context.build_packet",
            "office.workflow.source_to_deck",
        ],
    )


def read_sheet_workbook(path: str | Path, max_rows_per_sheet: int = 100) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            READ_WORKBOOK_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet read failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            READ_WORKBOOK_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.read.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return _failed(
            READ_WORKBOOK_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.read.workbook requires xl/workbook.xml in the XLSX package.",
                details={"path": source_path.as_posix()},
            ),
        )

    row_limit = max(0, int(max_rows_per_sheet))
    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))
    sheets = _read_sheet_payloads(source_path, worksheet_members, sheet_names, shared_strings, row_limit)
    source_refs = _source_refs_summary(sheets)
    summary = {
        "sheet_count": len(sheets),
        "row_count": sum(int(sheet["row_count"]) for sheet in sheets),
        "returned_row_count": sum(int(sheet["returned_row_count"]) for sheet in sheets),
        "cell_count": sum(int(sheet["cell_count"]) for sheet in sheets),
        "returned_cell_count": sum(int(sheet["returned_cell_count"]) for sheet in sheets),
        "formula_count": sum(int(sheet["formula_count"]) for sheet in sheets),
        "source_refs_sheet_present": source_refs["present"],
        "source_ref_row_count": source_refs["row_count"],
        "max_rows_per_sheet": row_limit,
        "truncated": any(bool(sheet["truncated"]) for sheet in sheets),
    }
    warnings = list(preflight.warnings)
    if summary["truncated"]:
        warnings.append(f"Workbook rows were truncated to max_rows_per_sheet={row_limit}.")
    checks = [
        ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
        ValidationCheck(name="workbook_xml_present", status="passed", details={"member": "xl/workbook.xml"}),
        ValidationCheck(
            name="worksheets_read",
            status="passed",
            details={
                "sheet_count": summary["sheet_count"],
                "returned_row_count": summary["returned_row_count"],
                "returned_cell_count": summary["returned_cell_count"],
            },
        ),
        _validation_check(
            "row_limit_applied",
            condition=not summary["truncated"],
            failed_status="warning",
            passed_details={
                "max_rows_per_sheet": row_limit,
                "truncated": summary["truncated"],
            },
            failed_message="Workbook rows were truncated for bounded agent output.",
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=READ_WORKBOOK_TOOL_NAME,
        validation=ValidationReport(
            status=_validation_report_status(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "workbook": {
                "path": source_path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
            },
            "summary": summary,
            "sheets": sheets,
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.profile.data",
            "sheet.validate.workbook",
            "office.context.build_packet",
            "office.workflow.source_to_deck",
        ],
    )


def validate_sheet_workbook(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            VALIDATE_WORKBOOK_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            VALIDATE_WORKBOOK_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.validate.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return _failed(
            VALIDATE_WORKBOOK_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.validate.workbook requires xl/workbook.xml in the XLSX package.",
                details={"path": source_path.as_posix()},
            ),
        )

    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))
    sheets = _validation_sheet_summaries(source_path, worksheet_members, sheet_names, shared_strings)
    source_refs = _source_refs_summary(sheets)
    summary = {
        "sheet_count": len(sheets),
        "nonempty_sheet_count": sum(1 for sheet in sheets if int(sheet["nonempty_cell_count"]) > 0),
        "blank_sheet_count": sum(1 for sheet in sheets if sheet["is_blank"]),
        "formula_count": sum(int(sheet["formula_count"]) for sheet in sheets),
        "table_count": count_members(names, prefix="xl/tables/"),
        "chart_count": count_members(names, prefix="xl/charts/"),
        "external_link_count": count_members(names, prefix="xl/externalLinks/"),
        "source_refs_sheet_present": source_refs["present"],
        "source_ref_row_count": source_refs["row_count"],
        "macro_enabled": bool(preflight.usage["safety"].get("macro_enabled", False)),
        "has_external_relationships": bool(preflight.usage["safety"].get("has_external_relationships", False)),
    }
    warnings = list(preflight.warnings)
    checks = [
        ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
        ValidationCheck(
            name="workbook_xml_present",
            status="passed",
            details={"member": "xl/workbook.xml"},
        ),
        _validation_check(
            "sheet_count_nonzero",
            condition=summary["sheet_count"] > 0,
            failed_status="failed",
            passed_details={"sheet_count": summary["sheet_count"]},
            failed_message="Workbook has no worksheets.",
        ),
        _validation_check(
            "nonempty_workbook",
            condition=summary["nonempty_sheet_count"] > 0,
            failed_status="failed",
            passed_details={"nonempty_sheet_count": summary["nonempty_sheet_count"]},
            failed_message="Workbook contains no non-empty sheets.",
        ),
        _validation_check(
            "blank_sheets_absent",
            condition=summary["blank_sheet_count"] == 0,
            failed_status="warning",
            passed_details={"blank_sheet_count": summary["blank_sheet_count"]},
            failed_message="Workbook contains blank sheets.",
        ),
        _validation_check(
            "external_links_absent",
            condition=summary["external_link_count"] == 0,
            failed_status="warning",
            passed_details={"external_link_count": summary["external_link_count"]},
            failed_message="External workbook links detected.",
        ),
        _validation_check(
            "source_refs_sheet_present",
            condition=bool(source_refs["present"]),
            failed_status="warning",
            passed_details=source_refs,
            failed_message="SourceRefs sheet is missing; provenance may be incomplete.",
        ),
        _validation_check(
            "macros_absent",
            condition=not summary["macro_enabled"],
            failed_status="warning",
            passed_details={"macro_enabled": summary["macro_enabled"]},
            failed_message="Macro-enabled workbook markers detected; macros are not executed.",
        ),
        _validation_check(
            "external_relationships_absent",
            condition=not summary["has_external_relationships"],
            failed_status="warning",
            passed_details={"has_external_relationships": summary["has_external_relationships"]},
            failed_message="External Office relationship targets were detected.",
        ),
    ]
    if summary["blank_sheet_count"]:
        blank_names = [str(sheet["name"]) for sheet in sheets if sheet["is_blank"]]
        warnings.append(f"Workbook contains blank sheets: {', '.join(blank_names)}.")
    if summary["external_link_count"]:
        warnings.append(f"External workbook links detected: {summary['external_link_count']}.")
    if not source_refs["present"]:
        warnings.append("SourceRefs sheet is missing; provenance may be incomplete.")
    if summary["macro_enabled"]:
        warnings.append("Macro-enabled workbook markers were detected; macros are not executed.")
    if summary["has_external_relationships"]:
        warnings.append("External Office relationship targets were detected.")

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=VALIDATE_WORKBOOK_TOOL_NAME,
        validation=ValidationReport(
            status=_validation_report_status(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "workbook": {
                "path": source_path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
            },
            "summary": summary,
            "sheets": sheets,
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.extract.tables",
            "office.context.build_packet",
            "office.workflow.source_to_deck",
        ],
    )


def _sheet_names(workbook_root: object | None) -> list[str]:
    if workbook_root is None:
        return []
    return [
        str(sheet.get("name") or f"Sheet {index}")
        for index, sheet in enumerate(workbook_root.findall(".//main:sheet", SHEET_NS), start=1)
    ]


def _sheet_summaries(path: Path, worksheet_members: list[str], sheet_names: list[str]) -> list[dict[str, object]]:
    summaries = []
    for index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        dimension = ""
        formula_count = 0
        if worksheet_root is not None:
            dimension_element = worksheet_root.find(".//main:dimension", SHEET_NS)
            dimension = str(dimension_element.get("ref") or "") if dimension_element is not None else ""
            formula_count = len(worksheet_root.findall(".//main:f", SHEET_NS))
        summaries.append(
            {
                "name": sheet_names[index - 1] if index <= len(sheet_names) else f"Sheet {index}",
                "sheet_index": index,
                "member": member,
                "dimension": dimension,
                "formula_count": formula_count,
            }
        )
    return summaries


def _validation_sheet_summaries(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
) -> list[dict[str, object]]:
    summaries = []
    for index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        sheet_name = sheet_names[index - 1] if index <= len(sheet_names) else f"Sheet {index}"
        dimension = ""
        formula_count = 0
        rows: list[dict[str, object]] = []
        if worksheet_root is not None:
            dimension_element = worksheet_root.find(".//main:dimension", SHEET_NS)
            dimension = str(dimension_element.get("ref") or "") if dimension_element is not None else ""
            formula_count = len(worksheet_root.findall(".//main:f", SHEET_NS))
            rows = _worksheet_rows(path, worksheet_root, sheet_name, index, shared_strings)
        nonempty_cell_count = sum(len(row["cells"]) for row in rows if isinstance(row.get("cells"), list))
        summaries.append(
            {
                "name": sheet_name,
                "sheet_index": index,
                "member": member,
                "dimension": dimension,
                "row_count": len(rows),
                "nonempty_cell_count": nonempty_cell_count,
                "formula_count": formula_count,
                "is_blank": nonempty_cell_count == 0 and formula_count == 0,
            }
        )
    return summaries


def _read_sheet_payloads(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
    row_limit: int,
) -> list[dict[str, object]]:
    sheets = []
    for index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        sheet_name = sheet_names[index - 1] if index <= len(sheet_names) else f"Sheet {index}"
        dimension = ""
        formula_count = 0
        rows: list[dict[str, object]] = []
        if worksheet_root is not None:
            dimension_element = worksheet_root.find(".//main:dimension", SHEET_NS)
            dimension = str(dimension_element.get("ref") or "") if dimension_element is not None else ""
            formula_count = len(worksheet_root.findall(".//main:f", SHEET_NS))
            rows = _worksheet_rows(path, worksheet_root, sheet_name, index, shared_strings)
        returned_rows = rows[:row_limit]
        sheets.append(
            {
                "name": sheet_name,
                "sheet_index": index,
                "member": member,
                "dimension": dimension,
                "row_count": len(rows),
                "returned_row_count": len(returned_rows),
                "cell_count": sum(len(row["cells"]) for row in rows if isinstance(row.get("cells"), list)),
                "returned_cell_count": sum(
                    len(row["cells"]) for row in returned_rows if isinstance(row.get("cells"), list)
                ),
                "formula_count": formula_count,
                "truncated": len(returned_rows) < len(rows),
                "rows": returned_rows,
            }
        )
    return sheets


def _source_refs_summary(sheets: list[dict[str, object]]) -> dict[str, object]:
    for sheet in sheets:
        normalized_name = str(sheet["name"]).replace(" ", "").replace("_", "").lower()
        if normalized_name == "sourcerefs":
            return {
                "present": True,
                "sheet_name": sheet["name"],
                "row_count": max(0, int(sheet["row_count"]) - 1),
            }
    return {"present": False, "sheet_name": None, "row_count": 0}


def _validation_check(
    name: str,
    *,
    condition: bool,
    failed_status: str,
    passed_details: dict[str, object],
    failed_message: str,
) -> ValidationCheck:
    if condition:
        return ValidationCheck(name=name, status="passed", details=passed_details)
    return ValidationCheck(name=name, status=failed_status, details=passed_details, message=failed_message)


def _validation_report_status(checks: list[ValidationCheck]) -> str:
    statuses = [check.status for check in checks]
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "passed"


def _write_records(data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: Any = data
    if isinstance(payload, dict) and isinstance(payload.get("usage"), dict):
        payload = payload["usage"]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return [_normalize_write_record(record) for record in payload["records"] if isinstance(record, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("tables"), list):
        return _write_records_from_tables(payload["tables"])
    if isinstance(payload, list):
        return [_normalize_write_record(record) for record in payload if isinstance(record, dict)]
    return []


def _write_records_from_tables(tables: list[Any]) -> list[dict[str, Any]]:
    records = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        table_source = table.get("source", {}) if isinstance(table.get("source"), dict) else {}
        for row in table.get("rows", []):
            if not isinstance(row, dict):
                continue
            cells = row.get("cells", []) if isinstance(row.get("cells"), list) else []
            records.append(
                _normalize_write_record(
                    {
                        "source_path": table_source.get("document_path") or table_source.get("workbook_path") or "",
                        "source_format": "xlsx" if table_source.get("workbook_path") else "docx",
                        "table_id": table.get("table_id", ""),
                        "source_sheet": table_source.get("sheet_name", ""),
                        "source_row_index": row.get("row_index", ""),
                        "values": [_cell_payload_value(cell) for cell in cells if isinstance(cell, dict)],
                        "source_refs": [
                            cell.get("source", {}) for cell in cells if isinstance(cell, dict) and cell.get("source")
                        ],
                    }
                )
            )
    return records


def _normalize_write_record(record: dict[str, Any]) -> dict[str, Any]:
    values = record.get("values", [])
    if not isinstance(values, list):
        values = [values]
    source_refs = record.get("source_refs", [])
    if not isinstance(source_refs, list):
        source_refs = [source_refs]
    return {
        "source_path": str(record.get("source_path", "")),
        "source_format": str(record.get("source_format", "")),
        "table_id": str(record.get("table_id", "")),
        "source_sheet": str(record.get("source_sheet", "")),
        "source_row_index": str(record.get("source_row_index", "")),
        "values": [str(value) for value in values],
        "source_refs": [source_ref for source_ref in source_refs if isinstance(source_ref, dict)],
    }


def _workbook_headers(max_columns: int) -> list[str]:
    return [
        "source_path",
        "source_format",
        "table_id",
        "source_sheet",
        "source_row_index",
        *[f"col_{index}" for index in range(1, max_columns + 1)],
    ]


def _cell_payload_value(cell: dict[str, Any]) -> str:
    return str(cell.get("text", cell.get("value", "")))


def _extract_worksheet_tables(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
) -> list[dict[str, object]]:
    tables = []
    for sheet_index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        if worksheet_root is None:
            continue
        sheet_name = sheet_names[sheet_index - 1] if sheet_index <= len(sheet_names) else f"Sheet {sheet_index}"
        rows = _worksheet_rows(path, worksheet_root, sheet_name, sheet_index, shared_strings)
        if not rows:
            continue
        range_ref = _worksheet_range(worksheet_root, rows)
        tables.append(
            {
                "table_id": f"sheet_{sheet_index}_table_1",
                "table_index": len(tables) + 1,
                "source": {
                    "workbook_path": path.as_posix(),
                    "sheet_name": sheet_name,
                    "sheet_index": sheet_index,
                    "member": member,
                    "range_ref": range_ref,
                },
                "rows": rows,
            }
        )
    return tables


def _worksheet_rows(
    path: Path,
    worksheet_root: ElementTree.Element,
    sheet_name: str,
    sheet_index: int,
    shared_strings: list[str],
) -> list[dict[str, object]]:
    rows = []
    for row_element in worksheet_root.findall(".//main:sheetData/main:row", SHEET_NS):
        row_index = _row_index(row_element)
        cells = []
        for cell_element in row_element.findall("./main:c", SHEET_NS):
            cell_ref = str(cell_element.get("r") or "")
            parsed_ref = _parse_cell_ref(cell_ref)
            if parsed_ref is None:
                column_index = len(cells) + 1
                resolved_ref = f"{_column_letters(column_index)}{row_index}"
            else:
                row_index, column_index = parsed_ref
                resolved_ref = cell_ref.upper()
            value = _cell_value(cell_element, shared_strings)
            if value == "":
                continue
            source = {
                "workbook_path": path.as_posix(),
                "sheet_name": sheet_name,
                "sheet_index": sheet_index,
                "cell_ref": resolved_ref,
                "row_index": row_index,
                "column_index": column_index,
            }
            cell_payload: dict[str, object] = {
                "cell_ref": resolved_ref,
                "row_index": row_index,
                "column_index": column_index,
                "value": value,
                "data_type": str(cell_element.get("t") or "number"),
                "source": source,
            }
            formula = cell_element.find("./main:f", SHEET_NS)
            if formula is not None and formula.text:
                cell_payload["formula"] = formula.text
            cells.append(cell_payload)
        if cells:
            rows.append({"row_index": row_index, "cells": cells})
    return rows


def _worksheet_range(worksheet_root: ElementTree.Element, rows: list[dict[str, object]]) -> str:
    dimension_element = worksheet_root.find(".//main:dimension", SHEET_NS)
    if dimension_element is not None and dimension_element.get("ref"):
        return str(dimension_element.get("ref"))
    row_numbers = [int(row["row_index"]) for row in rows]
    column_numbers = [
        int(cell["column_index"])
        for row in rows
        for cell in row["cells"]
        if isinstance(cell, dict) and "column_index" in cell
    ]
    if not row_numbers or not column_numbers:
        return ""
    return f"{_column_letters(min(column_numbers))}{min(row_numbers)}:{_column_letters(max(column_numbers))}{max(row_numbers)}"


def _shared_strings(root: ElementTree.Element | None) -> list[str]:
    if root is None:
        return []
    values = []
    for item in root.findall(".//main:si", SHEET_NS):
        values.append("".join(node.text or "" for node in item.findall(".//main:t", SHEET_NS)).strip())
    return values


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    data_type = str(cell.get("t") or "")
    if data_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", SHEET_NS)).strip()
    value = cell.find("./main:v", SHEET_NS)
    raw = (value.text or "").strip() if value is not None else ""
    if data_type == "s" and raw.isdigit():
        index = int(raw)
        return shared_strings[index] if index < len(shared_strings) else raw
    return raw


def _row_index(row_element: ElementTree.Element) -> int:
    row_ref = str(row_element.get("r") or "")
    return int(row_ref) if row_ref.isdigit() else 1


def _parse_cell_ref(cell_ref: str) -> tuple[int, int] | None:
    match = CELL_REF_RE.match(cell_ref)
    if match is None:
        return None
    column_letters, row_number = match.groups()
    return int(row_number), _column_number(column_letters)


def _column_number(column_letters: str) -> int:
    number = 0
    for char in column_letters.upper():
        number = number * 26 + (ord(char) - ord("A") + 1)
    return number


def _column_letters(column_number: int) -> str:
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters or "A"


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[error.message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
