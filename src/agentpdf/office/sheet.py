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
CREATE_EVIDENCE_WORKBOOK_TOOL_NAME = "sheet.create.evidence_workbook"
VALIDATE_WORKBOOK_TOOL_NAME = "sheet.validate.workbook"
VALIDATE_FORMULAS_TOOL_NAME = "sheet.validation.formulas"
READ_WORKBOOK_TOOL_NAME = "sheet.read.workbook"
PROFILE_DATA_TOOL_NAME = "sheet.profile.data"
CELL_REF_RE = re.compile(r"^([A-Z]+)([0-9]+)$", re.IGNORECASE)
FORMULA_CELL_REF_RE = re.compile(r"(?<![A-Z0-9_])\$?[A-Z]{1,3}\$?[0-9]+(?::\$?[A-Z]{1,3}\$?[0-9]+)?", re.IGNORECASE)
EXTERNAL_FORMULA_REF_RE = re.compile(r"\[([^\]]+)\]([^'!]+)")
VOLATILE_FORMULA_RE = re.compile(r"\b(NOW|TODAY|RAND|RANDBETWEEN|OFFSET|INDIRECT)\s*\(", re.IGNORECASE)
FORMULA_ERROR_VALUES = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}
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
        next_recommended_tools=[
            "sheet.extract.tables",
            "sheet.profile.data",
            "sheet.validation.formulas",
            "office.context.build_packet",
        ],
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
        next_recommended_tools=[
            "sheet.create.evidence_workbook",
            "sheet.write.workbook",
            "office.workflow.extract_to_sheet",
            "office.context.build_packet",
        ],
    )


def write_sheet_workbook(data: dict[str, Any] | list[dict[str, Any]], output_path: str | Path) -> ToolResult:
    return _write_sheet_workbook(data, output_path, tool_name=WRITE_WORKBOOK_TOOL_NAME)


def create_evidence_workbook(data: dict[str, Any] | list[dict[str, Any]], output_path: str | Path) -> ToolResult:
    return _write_sheet_workbook(data, output_path, tool_name=CREATE_EVIDENCE_WORKBOOK_TOOL_NAME)


def _write_sheet_workbook(
    data: dict[str, Any] | list[dict[str, Any]],
    output_path: str | Path,
    *,
    tool_name: str,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except AgentPDFException as exc:
        return _failed(tool_name, exc.to_error())

    records = _write_records(data)
    if not records:
        return _failed(
            tool_name,
            AgentPDFError(
                code="unsafe_input_rejected",
                message=f"{tool_name} requires at least one record or table row.",
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
    artifact = build_artifact(output, tool_name)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool_name,
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
            "deck.compose.plan",
            "office.workflow.sheet_to_deck",
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
            "office.workflow.sheet_to_deck",
        ],
    )


def profile_sheet_data(
    path: str | Path,
    max_rows_per_sheet: int = 100,
    include_source_refs: bool = False,
) -> ToolResult:
    read_result = read_sheet_workbook(path, max_rows_per_sheet=max_rows_per_sheet)
    if read_result.status == "failed":
        return _failed(
            PROFILE_DATA_TOOL_NAME,
            read_result.error or AgentPDFError(code="unsupported_file_type", message="Sheet profile failed."),
        )

    sheets = read_result.usage.get("sheets", [])
    if not isinstance(sheets, list):
        sheets = []
    profiles = [
        _profile_sheet_payload(sheet)
        for sheet in sheets
        if isinstance(sheet, dict) and (include_source_refs or not _is_source_refs_sheet(sheet))
    ]
    source_refs = _source_refs_summary([sheet for sheet in sheets if isinstance(sheet, dict)])
    data_row_count = sum(int(profile["data_row_count"]) for profile in profiles)
    missing_cell_count = sum(int(profile["missing_cell_count"]) for profile in profiles)
    formula_cell_count = sum(int(profile["formula_cell_count"]) for profile in profiles)
    column_count = sum(len(profile["columns"]) for profile in profiles)
    source_coverage = _source_coverage_status(data_row_count, int(source_refs["row_count"]))
    warnings = list(read_result.warnings)
    if missing_cell_count:
        warnings.append(f"Workbook profile found missing cells: {missing_cell_count}.")
    if source_coverage["status"] in {"missing", "partial"}:
        warnings.append(f"Workbook source coverage is {source_coverage['status']}.")

    checks = [
        ValidationCheck(
            name="workbook_read",
            status="passed",
            details={
                "sheet_count": read_result.usage["summary"]["sheet_count"],
                "profiled_sheet_count": len(profiles),
            },
        ),
        _validation_check(
            "missing_cells_absent",
            condition=missing_cell_count == 0,
            failed_status="warning",
            passed_details={"missing_cell_count": missing_cell_count},
            failed_message="Workbook profile contains missing cells.",
        ),
        _validation_check(
            "source_coverage_complete",
            condition=source_coverage["status"] == "complete",
            failed_status="warning",
            passed_details=source_coverage,
            failed_message="Workbook source refs do not cover all profiled data rows.",
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=PROFILE_DATA_TOOL_NAME,
        validation=ValidationReport(
            status=_validation_report_status(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "workbook": read_result.usage["workbook"],
            "summary": {
                "sheet_count": read_result.usage["summary"]["sheet_count"],
                "profiled_sheet_count": len(profiles),
                "column_count": column_count,
                "data_row_count": data_row_count,
                "missing_cell_count": missing_cell_count,
                "formula_cell_count": formula_cell_count,
                "source_refs_sheet_present": source_refs["present"],
                "source_ref_row_count": source_refs["row_count"],
                "source_coverage": source_coverage,
                "max_rows_per_sheet": max(0, int(max_rows_per_sheet)),
                "include_source_refs": include_source_refs,
            },
            "profiles": profiles,
            "safety": read_result.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.create.evidence_workbook",
            "sheet.write.workbook",
            "sheet.validate.workbook",
            "office.context.build_packet",
            "office.workflow.sheet_to_deck",
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
            "sheet.validation.formulas",
            "sheet.extract.tables",
            "office.context.build_packet",
            "office.workflow.sheet_to_deck",
        ],
    )


def validate_sheet_formulas(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(
            VALIDATE_FORMULAS_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Sheet formula validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return _failed(
            VALIDATE_FORMULAS_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.validation.formulas requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return _failed(
            VALIDATE_FORMULAS_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="sheet.validation.formulas requires xl/workbook.xml in the XLSX package.",
                details={"path": source_path.as_posix()},
            ),
        )

    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))
    formulas = _formula_payloads(source_path, worksheet_members, sheet_names, shared_strings)
    summary = {
        "sheet_count": len(worksheet_members),
        "formula_count": len(formulas),
        "formula_error_count": _formula_issue_count(formulas, "formula_error"),
        "broken_ref_count": _formula_issue_count(formulas, "broken_ref"),
        "external_ref_count": _formula_issue_count(formulas, "external_ref"),
        "volatile_formula_count": _formula_issue_count(formulas, "volatile_formula"),
    }
    warnings = list(preflight.warnings)
    if summary["formula_error_count"]:
        warnings.append(f"Formula cached error values detected: {summary['formula_error_count']}.")
    if summary["broken_ref_count"]:
        warnings.append(f"Broken formula references detected: {summary['broken_ref_count']}.")
    if summary["external_ref_count"]:
        warnings.append(f"External formula workbook references detected: {summary['external_ref_count']}.")
    if summary["volatile_formula_count"]:
        warnings.append(f"Volatile formulas detected: {summary['volatile_formula_count']}.")

    checks = [
        ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
        ValidationCheck(name="workbook_xml_present", status="passed", details={"member": "xl/workbook.xml"}),
        ValidationCheck(
            name="formulas_scanned",
            status="passed",
            details={
                "sheet_count": summary["sheet_count"],
                "formula_count": summary["formula_count"],
                "evaluation": "structural_only",
            },
        ),
        _validation_check(
            "formula_errors_absent",
            condition=summary["formula_error_count"] == 0,
            failed_status="warning",
            passed_details={"formula_error_count": summary["formula_error_count"]},
            failed_message="Formula cached error values were detected.",
        ),
        _validation_check(
            "broken_refs_absent",
            condition=summary["broken_ref_count"] == 0,
            failed_status="warning",
            passed_details={"broken_ref_count": summary["broken_ref_count"]},
            failed_message="Broken formula references were detected.",
        ),
        _validation_check(
            "external_formula_refs_absent",
            condition=summary["external_ref_count"] == 0,
            failed_status="warning",
            passed_details={"external_ref_count": summary["external_ref_count"]},
            failed_message="External formula workbook references were detected.",
        ),
        _validation_check(
            "volatile_formulas_absent",
            condition=summary["volatile_formula_count"] == 0,
            failed_status="warning",
            passed_details={"volatile_formula_count": summary["volatile_formula_count"]},
            failed_message="Volatile formulas were detected.",
        ),
    ]

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=VALIDATE_FORMULAS_TOOL_NAME,
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
            "formulas": formulas,
            "engine": {"evaluation": "structural_only", "recalculated": False},
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.validate.workbook",
            "sheet.profile.data",
            "deck.compose.plan",
            "office.workflow.sheet_to_deck",
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
        if _is_source_refs_sheet(sheet):
            return {
                "present": True,
                "sheet_name": sheet["name"],
                "row_count": max(0, int(sheet["row_count"]) - 1),
            }
    return {"present": False, "sheet_name": None, "row_count": 0}


def _is_source_refs_sheet(sheet: dict[str, object]) -> bool:
    normalized_name = str(sheet.get("name", "")).replace(" ", "").replace("_", "").lower()
    return normalized_name == "sourcerefs"


def _formula_payloads(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
) -> list[dict[str, object]]:
    formulas = []
    for sheet_index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        if worksheet_root is None:
            continue
        sheet_name = sheet_names[sheet_index - 1] if sheet_index <= len(sheet_names) else f"Sheet {sheet_index}"
        for row_element in worksheet_root.findall(".//main:sheetData/main:row", SHEET_NS):
            row_index = _row_index(row_element)
            for cell_position, cell_element in enumerate(row_element.findall("./main:c", SHEET_NS), start=1):
                formula = cell_element.find("./main:f", SHEET_NS)
                formula_text = (formula.text or "").strip() if formula is not None else ""
                if not formula_text:
                    continue
                cell_ref = str(cell_element.get("r") or "")
                parsed_ref = _parse_cell_ref(cell_ref)
                if parsed_ref is None:
                    column_index = cell_position
                    resolved_ref = f"{_column_letters(column_index)}{row_index}"
                else:
                    row_index, column_index = parsed_ref
                    resolved_ref = cell_ref.upper()
                cached_value = _cell_value(cell_element, shared_strings)
                data_type = str(cell_element.get("t") or "number")
                external_refs = _external_formula_refs(formula_text)
                volatile_functions = _volatile_formula_functions(formula_text)
                issues = _formula_issues(
                    formula_text=formula_text,
                    cached_value=cached_value,
                    data_type=data_type,
                    external_refs=external_refs,
                    volatile_functions=volatile_functions,
                )
                formulas.append(
                    {
                        "sheet_name": sheet_name,
                        "sheet_index": sheet_index,
                        "member": member,
                        "cell_ref": resolved_ref,
                        "row_index": row_index,
                        "column_index": column_index,
                        "formula": formula_text,
                        "cached_value": cached_value,
                        "data_type": data_type,
                        "precedents": _formula_precedents(formula_text),
                        "external_refs": external_refs,
                        "volatile_functions": volatile_functions,
                        "issues": issues,
                        "source": {
                            "workbook_path": path.as_posix(),
                            "sheet_name": sheet_name,
                            "sheet_index": sheet_index,
                            "cell_ref": resolved_ref,
                            "row_index": row_index,
                            "column_index": column_index,
                        },
                    }
                )
    return formulas


def _formula_issues(
    *,
    formula_text: str,
    cached_value: str,
    data_type: str,
    external_refs: list[str],
    volatile_functions: list[str],
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    normalized_value = cached_value.upper()
    normalized_formula = formula_text.upper()
    if data_type == "e" or normalized_value in FORMULA_ERROR_VALUES:
        issues.append({"kind": "formula_error", "cached_value": cached_value})
    if "#REF!" in normalized_formula:
        issues.append({"kind": "broken_ref", "token": "#REF!"})
    if external_refs:
        issues.append({"kind": "external_ref", "refs": external_refs})
    if volatile_functions:
        issues.append({"kind": "volatile_formula", "functions": volatile_functions})
    return issues


def _formula_precedents(formula_text: str) -> list[str]:
    precedents = []
    for match in FORMULA_CELL_REF_RE.finditer(formula_text):
        ref = match.group(0).replace("$", "").upper()
        if ref not in precedents:
            precedents.append(ref)
    return precedents


def _external_formula_refs(formula_text: str) -> list[str]:
    refs = []
    for workbook, sheet_name in EXTERNAL_FORMULA_REF_RE.findall(formula_text):
        ref = f"[{workbook}]{sheet_name}"
        if ref not in refs:
            refs.append(ref)
    return refs


def _volatile_formula_functions(formula_text: str) -> list[str]:
    functions = []
    for match in VOLATILE_FORMULA_RE.finditer(formula_text):
        name = match.group(1).upper()
        if name not in functions:
            functions.append(name)
    return functions


def _formula_issue_count(formulas: list[dict[str, object]], kind: str) -> int:
    count = 0
    for formula in formulas:
        issues = formula.get("issues", [])
        if isinstance(issues, list) and any(isinstance(issue, dict) and issue.get("kind") == kind for issue in issues):
            count += 1
    return count


def _profile_sheet_payload(sheet: dict[str, object]) -> dict[str, object]:
    rows = sheet.get("rows", [])
    if not isinstance(rows, list) or not rows:
        return {
            "sheet_name": sheet.get("name", ""),
            "sheet_index": sheet.get("sheet_index", 0),
            "header_row_index": None,
            "headers": [],
            "data_row_count": 0,
            "missing_cell_count": 0,
            "formula_cell_count": 0,
            "columns": [],
        }
    header_row = rows[0] if isinstance(rows[0], dict) else {}
    headers = _headers_from_row(header_row)
    data_rows = [row for row in rows[1:] if isinstance(row, dict)]
    columns = [
        _profile_column(column_index=index, header=header, data_rows=data_rows)
        for index, header in enumerate(headers, start=1)
    ]
    return {
        "sheet_name": sheet.get("name", ""),
        "sheet_index": sheet.get("sheet_index", 0),
        "header_row_index": header_row.get("row_index") if isinstance(header_row, dict) else None,
        "headers": headers,
        "data_row_count": len(data_rows),
        "missing_cell_count": sum(int(column["missing_count"]) for column in columns),
        "formula_cell_count": sum(int(column["formula_count"]) for column in columns),
        "columns": columns,
    }


def _headers_from_row(row: dict[str, object]) -> list[str]:
    cells = row.get("cells", [])
    if not isinstance(cells, list):
        return []
    max_column = max(
        (int(cell["column_index"]) for cell in cells if isinstance(cell, dict) and "column_index" in cell),
        default=0,
    )
    values_by_column = {
        int(cell["column_index"]): str(cell.get("value", "")).strip()
        for cell in cells
        if isinstance(cell, dict) and "column_index" in cell
    }
    return [values_by_column.get(index) or f"column_{index}" for index in range(1, max_column + 1)]


def _profile_column(column_index: int, header: str, data_rows: list[dict[str, object]]) -> dict[str, object]:
    missing_count = 0
    nonempty_count = 0
    formula_count = 0
    type_counts: dict[str, int] = {"number": 0, "boolean": 0, "text": 0, "blank": 0}
    examples: list[str] = []
    for row in data_rows:
        cell = _cell_for_column(row, column_index)
        value = str(cell.get("value", "")).strip() if cell is not None else ""
        if cell is not None and cell.get("formula"):
            formula_count += 1
        if value == "":
            missing_count += 1
            type_counts["blank"] += 1
            continue
        nonempty_count += 1
        value_type = _profile_value_type(value)
        type_counts[value_type] += 1
        if len(examples) < 3:
            examples.append(value)
    return {
        "header": header,
        "column_index": column_index,
        "column_ref": _column_letters(column_index),
        "semantic_type": _semantic_type(type_counts),
        "nonempty_count": nonempty_count,
        "missing_count": missing_count,
        "formula_count": formula_count,
        "type_counts": type_counts,
        "examples": examples,
    }


def _cell_for_column(row: dict[str, object], column_index: int) -> dict[str, object] | None:
    cells = row.get("cells", [])
    if not isinstance(cells, list):
        return None
    for cell in cells:
        if isinstance(cell, dict) and int(cell.get("column_index", 0)) == column_index:
            return cell
    return None


def _profile_value_type(value: str) -> str:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return "boolean"
    try:
        float(value.replace(",", ""))
    except ValueError:
        return "text"
    return "number"


def _semantic_type(type_counts: dict[str, int]) -> str:
    candidates = {key: value for key, value in type_counts.items() if key != "blank"}
    if not candidates or max(candidates.values(), default=0) == 0:
        return "blank"
    return max(candidates, key=candidates.get)


def _source_coverage_status(data_row_count: int, source_ref_row_count: int) -> dict[str, object]:
    if data_row_count == 0:
        status = "no_data"
    elif source_ref_row_count >= data_row_count:
        status = "complete"
    elif source_ref_row_count > 0:
        status = "partial"
    else:
        status = "missing"
    ratio = 1.0 if data_row_count == 0 else min(source_ref_row_count, data_row_count) / data_row_count
    return {
        "status": status,
        "data_row_count": data_row_count,
        "source_ref_row_count": source_ref_row_count,
        "coverage_ratio": ratio,
    }


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
