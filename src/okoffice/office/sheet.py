from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree


from okoffice.artifacts.store import build_artifact
from okoffice.office.inspect import inspect_office_file
from okoffice.office.ooxml import SHEET_NS, count_members, read_xml, sorted_members, zip_names
from okoffice.office.shared import dedupe_strings, failed_result, job_id, validation_report_status
from okoffice.office.xlsx import write_xlsx
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_output_path


INSPECT_TOOL_NAME = "sheet.inspect.workbook"
EXTRACT_TABLES_TOOL_NAME = "sheet.extract.tables"
WRITE_WORKBOOK_TOOL_NAME = "sheet.write.workbook"
CREATE_EVIDENCE_WORKBOOK_TOOL_NAME = "sheet.create.evidence_workbook"
VALIDATE_WORKBOOK_TOOL_NAME = "sheet.validate.workbook"
VALIDATE_FORMULAS_TOOL_NAME = "sheet.validation.formulas"
VALIDATE_MODEL_CHECKS_TOOL_NAME = "sheet.validation.model_checks"
VALIDATE_EXTERNAL_LINKS_TOOL_NAME = "sheet.validation.external_links"
READ_WORKBOOK_TOOL_NAME = "sheet.read.workbook"
PROFILE_DATA_TOOL_NAME = "sheet.profile.data"
CELL_REF_RE = re.compile(r"^([A-Z]+)([0-9]+)$", re.IGNORECASE)
FORMULA_CELL_REF_RE = re.compile(r"(?<![A-Z0-9_])\$?[A-Z]{1,3}\$?[0-9]+(?::\$?[A-Z]{1,3}\$?[0-9]+)?", re.IGNORECASE)
EXTERNAL_FORMULA_REF_RE = re.compile(r"\[([^\]]+)\]([^'!]+)")
VOLATILE_FORMULA_RE = re.compile(r"\b(NOW|TODAY|RAND|RANDBETWEEN|OFFSET|INDIRECT)\s*\(", re.IGNORECASE)
FORMULA_ERROR_VALUES = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}
XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
RICH_SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE_R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"
CORE_NS = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"


def inspect_sheet_workbook(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return failed_result(
            INSPECT_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet inspect failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            INSPECT_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.inspect.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    try:
        usage, warnings = _rich_inspect_sheet_workbook(source_path, preflight)
    except OKofficeException as exc:
        return failed_result(INSPECT_TOOL_NAME, exc.to_error())
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        return failed_result(
            INSPECT_TOOL_NAME,
            OKofficeError(
                code="output_validation_failed",
                message=f"Unable to inspect workbook package structure: {exc}",
                details={"path": source_path.as_posix()},
            ),
        )

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=INSPECT_TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="workbook_xml_present", status="passed", details={"member": "xl/workbook.xml"}),
                ValidationCheck(name="structure_extracted", status="passed", details=usage["summary"]),
                ValidationCheck(
                    name="formula_evaluation_explicit",
                    status="passed",
                    details=usage["formula_evaluation"],
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage=usage,
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
        return failed_result(
            EXTRACT_TABLES_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet table extraction failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            EXTRACT_TABLES_TOOL_NAME,
            OKofficeError(
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
        job_id=job_id(),
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
    except OKofficeException as exc:
        return failed_result(tool_name, exc.to_error())

    records = _write_records(data)
    if not records:
        return failed_result(
            tool_name,
            OKofficeError(
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
        job_id=job_id(),
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
        return failed_result(
            READ_WORKBOOK_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet read failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            READ_WORKBOOK_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.read.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return failed_result(
            READ_WORKBOOK_TOOL_NAME,
            OKofficeError(
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
        job_id=job_id(),
        status="succeeded",
        tool=READ_WORKBOOK_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
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
        return failed_result(
            PROFILE_DATA_TOOL_NAME,
            read_result.error or OKofficeError(code="unsupported_file_type", message="Sheet profile failed."),
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
        job_id=job_id(),
        status="succeeded",
        tool=PROFILE_DATA_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
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
        return failed_result(
            VALIDATE_WORKBOOK_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            VALIDATE_WORKBOOK_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.validate.workbook requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return failed_result(
            VALIDATE_WORKBOOK_TOOL_NAME,
            OKofficeError(
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
        job_id=job_id(),
        status="succeeded",
        tool=VALIDATE_WORKBOOK_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
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
        return failed_result(
            VALIDATE_FORMULAS_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet formula validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            VALIDATE_FORMULAS_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.validation.formulas requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return failed_result(
            VALIDATE_FORMULAS_TOOL_NAME,
            OKofficeError(
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
        job_id=job_id(),
        status="succeeded",
        tool=VALIDATE_FORMULAS_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
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


def validate_sheet_model_checks(path: str | Path) -> ToolResult:
    """Perform structural model checks on workbook formulas."""
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return failed_result(
            VALIDATE_MODEL_CHECKS_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet model-check validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            VALIDATE_MODEL_CHECKS_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.validation.model_checks requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    workbook_root = read_xml(source_path, "xl/workbook.xml")
    if workbook_root is None:
        return failed_result(
            VALIDATE_MODEL_CHECKS_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.validation.model_checks requires xl/workbook.xml in the XLSX package.",
                details={"path": source_path.as_posix()},
            ),
        )

    sheet_names = _sheet_names(workbook_root)
    worksheet_members = sorted_members(names, prefix="xl/worksheets/sheet")
    shared_strings = _shared_strings(read_xml(source_path, "xl/sharedStrings.xml"))
    formulas = _formula_payloads(source_path, worksheet_members, sheet_names, shared_strings)

    # Build a set of (sheet_name, cell_ref) for all non-empty input cells.
    input_cells = _input_cell_set(source_path, worksheet_members, sheet_names, shared_strings)

    # Circular reference candidates: formula references its own cell.
    circular_refs = _detect_circular_refs(formulas)

    # Empty input cells: formula references a cell that has no value.
    empty_inputs = _detect_empty_inputs(formulas, input_cells)

    # Balance check: SUM formulas where the range might not cover all needed rows.
    balance_issues = _detect_balance_issues(formulas, source_path, worksheet_members, sheet_names, shared_strings)

    summary = {
        "sheet_count": len(worksheet_members),
        "formula_count": len(formulas),
        "circular_ref_count": len(circular_refs),
        "empty_input_count": len(empty_inputs),
        "balance_issue_count": len(balance_issues),
    }
    warnings = list(preflight.warnings)
    if summary["circular_ref_count"]:
        warnings.append(f"Circular reference candidates detected: {summary['circular_ref_count']}.")
    if summary["empty_input_count"]:
        warnings.append(f"Formulas referencing empty input cells detected: {summary['empty_input_count']}.")
    if summary["balance_issue_count"]:
        warnings.append(f"Potential SUM range balance issues detected: {summary['balance_issue_count']}.")

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
            "circular_refs_absent",
            condition=summary["circular_ref_count"] == 0,
            failed_status="warning",
            passed_details={"circular_ref_count": summary["circular_ref_count"]},
            failed_message="Circular reference candidates were detected.",
        ),
        _validation_check(
            "empty_inputs_absent",
            condition=summary["empty_input_count"] == 0,
            failed_status="warning",
            passed_details={"empty_input_count": summary["empty_input_count"]},
            failed_message="Formulas referencing empty input cells were detected.",
        ),
        _validation_check(
            "balance_issues_absent",
            condition=summary["balance_issue_count"] == 0,
            failed_status="warning",
            passed_details={"balance_issue_count": summary["balance_issue_count"]},
            failed_message="Potential SUM range balance issues were detected.",
        ),
    ]

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=VALIDATE_MODEL_CHECKS_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
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
            "model_checks": {
                "circular_refs": circular_refs,
                "empty_inputs": empty_inputs,
                "balance_issues": balance_issues,
            },
            "engine": {"evaluation": "structural_only", "recalculated": False},
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.validation.formulas",
            "sheet.validate.workbook",
            "sheet.profile.data",
            "office.context.build_packet",
        ],
    )


def validate_sheet_external_links(path: str | Path) -> ToolResult:
    """Audit external link targets in an XLSX workbook package."""
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return failed_result(
            VALIDATE_EXTERNAL_LINKS_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Sheet external-link validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "xlsx":
        return failed_result(
            VALIDATE_EXTERNAL_LINKS_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="sheet.validation.external_links requires an XLSX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    try:
        external_links = _extract_external_links(source_path)
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        return failed_result(
            VALIDATE_EXTERNAL_LINKS_TOOL_NAME,
            OKofficeError(
                code="output_validation_failed",
                message=f"Unable to read external relationships from workbook package: {exc}",
                details={"path": source_path.as_posix()},
            ),
        )

    summary = {
        "external_link_count": len(external_links),
    }
    warnings = list(preflight.warnings)
    if summary["external_link_count"]:
        warnings.append(f"External link targets detected: {summary['external_link_count']}.")

    checks = [
        ValidationCheck(name="format_is_xlsx", status="passed", details=preflight.usage["format"]),
        ValidationCheck(
            name="external_links_scanned",
            status="passed",
            details={"external_link_count": summary["external_link_count"]},
        ),
        _validation_check(
            "external_links_absent",
            condition=summary["external_link_count"] == 0,
            failed_status="warning",
            passed_details={"external_link_count": summary["external_link_count"]},
            failed_message="External link targets were detected in the workbook package.",
        ),
    ]

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=VALIDATE_EXTERNAL_LINKS_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
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
            "external_links": external_links,
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.validation.formulas",
            "sheet.validation.model_checks",
            "sheet.validate.workbook",
            "office.context.build_packet",
        ],
    )


class _CountedList(list[dict[str, Any]]):
    def __init__(self, items: list[dict[str, Any]], **metrics: int) -> None:
        super().__init__(items)
        self._metrics = metrics

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            if item in self._metrics:
                return self._metrics[item]
            raise KeyError(item)
        return super().__getitem__(item)

    def get(self, key: str, default: Any = None) -> Any:
        return self._metrics.get(key, default)


def _rich_inspect_sheet_workbook(path: Path, preflight: ToolResult) -> tuple[dict[str, Any], list[str]]:
    names = {name.replace("\\", "/") for name in zip_names(path)}
    unsafe_entries = [name for name in names if _rich_unsafe_zip_entry(name)]
    if unsafe_entries:
        raise OKofficeException(
            "unsafe_input_rejected",
            "Workbook package contains unsafe ZIP entry names.",
            details={"unsafe_package_entries": unsafe_entries},
        )
    workbook_root = read_xml(path, "xl/workbook.xml")
    if workbook_root is None:
        raise OKofficeException(
            "unsupported_file_type",
            "Workbook package is missing xl/workbook.xml.",
            details={"path": path.as_posix()},
        )

    with zipfile.ZipFile(path) as archive:
        workbook_rels = _rich_read_relationships(archive, "xl/_rels/workbook.xml.rels", "xl/workbook.xml", names)
        shared_strings = _shared_strings(read_xml(path, "xl/sharedStrings.xml"))
        external_relationships = _rich_external_relationships(archive, names)
        sheets, formulas, tables, comments, charts, rows_by_sheet = _rich_read_sheets(
            archive,
            path,
            workbook_root,
            workbook_rels,
            names,
            shared_strings,
        )
        named_ranges = _rich_named_ranges(workbook_root)
        metadata = _rich_core_metadata(archive, names)

    data_model = _rich_data_model(rows_by_sheet.get("DataModel", []))
    chart_plan = _rich_chart_plan(rows_by_sheet.get("Charts", []))
    charts.extend(_rich_planned_charts(chart_plan))
    hidden_sheet_count = sum(1 for sheet in sheets if bool(sheet["hidden"]))
    safety = dict(preflight.usage.get("safety", {}))
    package = {
        "path": path.as_posix(),
        "package_type": preflight.usage["format"]["package_type"],
        "zip_entry_count": len(names),
        "macro_enabled": bool(safety.get("macro_enabled", False)),
        "has_external_relationships": bool(safety.get("has_external_relationships", False))
        or bool(external_relationships),
        "external_relationships": external_relationships,
        "unsafe_package_entries": unsafe_entries,
    }
    summary = {
        "sheet_count": len(sheets),
        "visible_sheet_count": len(sheets) - hidden_sheet_count,
        "hidden_sheet_count": hidden_sheet_count,
        "table_count": len(tables),
        "formula_count": len(formulas),
        "chart_count": len(charts),
        "data_model_count": int(data_model["field_count"]),
        "chart_plan_count": int(chart_plan["chart_plan_count"]),
        "named_range_count": len(named_ranges),
        "comment_count": len(comments),
        "external_link_count": len(external_relationships) or count_members(names, prefix="xl/externalLinks/"),
    }
    warnings = dedupe_strings(
        [
            *preflight.warnings,
            *(["Macro-enabled workbook package markers were detected; macros are not executed."] if package["macro_enabled"] else []),
            *(["External workbook relationship targets were detected."] if package["has_external_relationships"] else []),
            *(["Hidden workbook sheets were detected."] if hidden_sheet_count else []),
        ]
    )
    return (
        {
            "file": preflight.usage["file"],
            "workbook": {
                "path": path.as_posix(),
                "format": "xlsx",
                "package_type": preflight.usage["format"]["package_type"],
                "sheet_count": len(sheets),
            },
            "summary": summary,
            "metadata": metadata,
            "package": package,
            "sheets": sheets,
            "formulas": _CountedList(formulas, formula_count=len(formulas)),
            "tables": _CountedList(tables, table_count=len(tables)),
            "charts": _CountedList(charts, chart_count=len(charts)),
            "links": {"external_link_count": summary["external_link_count"]},
            "data_model": data_model,
            "chart_plan": chart_plan,
            "comments": comments,
            "named_ranges": named_ranges,
            "formula_evaluation": {
                "status": "structural_only",
                "evaluated": False,
                "reason": "Local OSS workbook inspect does not calculate formulas.",
            },
            "safety": safety,
        },
        warnings,
    )


def _rich_read_sheets(
    archive: zipfile.ZipFile,
    path: Path,
    workbook_root: ElementTree.Element,
    workbook_rels: dict[str, dict[str, str]],
    names: set[str],
    shared_strings: list[str],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, list[list[str]]],
]:
    sheets: list[dict[str, Any]] = []
    formulas: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    rows_by_sheet: dict[str, list[list[str]]] = {}

    for index, sheet in enumerate(workbook_root.findall(f"{RICH_SHEET_NS}sheets/{RICH_SHEET_NS}sheet"), start=1):
        sheet_name = str(sheet.attrib.get("name") or f"Sheet{index}")
        rel_id = sheet.attrib.get(f"{OFFICE_R_NS}id")
        state = str(sheet.attrib.get("state") or "visible")
        part = workbook_rels.get(str(rel_id), {}).get("target") if rel_id else None
        if not part:
            guessed_part = f"xl/worksheets/sheet{index}.xml"
            if guessed_part in names:
                part = guessed_part
        sheet_info: dict[str, Any] = {
            "name": sheet_name,
            "sheet_index": index,
            "sheet_id": sheet.attrib.get("sheetId"),
            "state": state,
            "hidden": state in {"hidden", "veryHidden"},
            "member": part,
            "part": part,
            "dimension": "",
            "used_range": None,
            "row_count": 0,
            "formula_count": 0,
            "table_count": 0,
            "chart_count": 0,
            "comment_count": 0,
            "locator": _rich_locator(sheet=sheet_name),
        }
        if part and part in names:
            sheet_root = ElementTree.fromstring(archive.read(part))
            rows_by_sheet[sheet_name] = _rich_worksheet_rows(sheet_root, shared_strings)
            dimension = _rich_dimension(sheet_root)
            sheet_info["dimension"] = dimension
            sheet_info["used_range"] = dimension or None
            sheet_info["row_count"] = len(sheet_root.findall(f"{RICH_SHEET_NS}sheetData/{RICH_SHEET_NS}row"))
            sheet_rels = _rich_read_relationships(archive, _rich_rels_part_for(part), part, names)
            sheet_formulas = _rich_formulas(sheet_root, sheet_name, shared_strings)
            sheet_tables = _rich_tables(archive, sheet_name, sheet_rels, names)
            sheet_comments = _rich_comments(archive, sheet_name, sheet_rels, names)
            sheet_charts = _rich_charts(archive, sheet_name, sheet_rels, names)
            formulas.extend(sheet_formulas)
            tables.extend(sheet_tables)
            comments.extend(sheet_comments)
            charts.extend(sheet_charts)
            sheet_info["formula_count"] = len(sheet_formulas)
            sheet_info["table_count"] = len(sheet_tables)
            sheet_info["chart_count"] = len(sheet_charts)
            sheet_info["comment_count"] = len(sheet_comments)
        sheets.append(sheet_info)
    tables.extend(_rich_orphan_tables(archive, names, tables))
    charts.extend(_rich_orphan_charts(names, charts))
    return sheets, formulas, tables, comments, charts, rows_by_sheet


def _rich_dimension(sheet_root: ElementTree.Element) -> str:
    dimension = sheet_root.find(f"{RICH_SHEET_NS}dimension")
    return str(dimension.attrib.get("ref") or "") if dimension is not None else ""


def _rich_formulas(
    sheet_root: ElementTree.Element,
    sheet_name: str,
    shared_strings: list[str],
) -> list[dict[str, Any]]:
    formulas: list[dict[str, Any]] = []
    for cell in sheet_root.findall(f".//{RICH_SHEET_NS}c"):
        formula_node = cell.find(f"{RICH_SHEET_NS}f")
        if formula_node is None or not formula_node.text:
            continue
        cell_ref = str(cell.attrib.get("r") or "")
        formula = formula_node.text
        cached_value = _cell_value(cell, shared_strings)
        formulas.append(
            {
                "sheet": sheet_name,
                "sheet_name": sheet_name,
                "cell": cell_ref,
                "cell_ref": cell_ref,
                "formula": formula,
                "cached_value": cached_value if cached_value != "" else None,
                "has_external_reference": "[" in formula,
                "locator": _rich_locator(sheet=sheet_name, cell=cell_ref, formula=formula),
            }
        )
    return formulas


def _rich_tables(
    archive: zipfile.ZipFile,
    sheet_name: str,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/table") or relationship["target"] not in names:
            continue
        root = ElementTree.fromstring(archive.read(relationship["target"]))
        name = root.attrib.get("displayName") or root.attrib.get("name") or root.attrib.get("id")
        table_range = root.attrib.get("ref")
        tables.append(
            {
                "sheet": sheet_name,
                "name": name,
                "range": table_range,
                "part": relationship["target"],
                "member": relationship["target"],
                "column_count": len(root.findall(f"{RICH_SHEET_NS}tableColumns/{RICH_SHEET_NS}tableColumn")),
                "locator": _rich_locator(sheet=sheet_name, range=table_range, table=name),
            }
        )
    return tables


def _rich_orphan_tables(
    archive: zipfile.ZipFile,
    names: set[str],
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    referenced_parts = {str(table.get("part") or "") for table in tables}
    orphans: list[dict[str, Any]] = []
    for part in sorted(name for name in names if name.startswith("xl/tables/") and name.endswith(".xml")):
        if part in referenced_parts:
            continue
        root = ElementTree.fromstring(archive.read(part))
        name = str(root.attrib.get("displayName") or root.attrib.get("name") or PurePosixPath(part).stem)
        range_ref = str(root.attrib.get("ref") or "")
        orphans.append(
            {
                "name": name,
                "display_name": name,
                "sheet_name": None,
                "range": range_ref,
                "range_ref": range_ref,
                "part": part,
                "member": part,
                "column_count": len(root.findall(f"{RICH_SHEET_NS}tableColumns/{RICH_SHEET_NS}tableColumn")),
                "locator": _rich_locator(table=name, range_ref=range_ref),
            }
        )
    return orphans


def _rich_comments(
    archive: zipfile.ZipFile,
    sheet_name: str,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/comments") or relationship["target"] not in names:
            continue
        root = ElementTree.fromstring(archive.read(relationship["target"]))
        authors = [author.text or "" for author in root.findall(f"{RICH_SHEET_NS}authors/{RICH_SHEET_NS}author")]
        for comment in root.findall(f"{RICH_SHEET_NS}commentList/{RICH_SHEET_NS}comment"):
            author_index = int(comment.attrib.get("authorId", "0"))
            cell_ref = str(comment.attrib.get("ref") or "")
            comments.append(
                {
                    "sheet": sheet_name,
                    "cell": cell_ref,
                    "author": authors[author_index] if author_index < len(authors) else None,
                    "text": _rich_text_content(comment),
                    "locator": _rich_locator(sheet=sheet_name, cell=cell_ref),
                }
            )
    return comments


def _rich_charts(
    archive: zipfile.ZipFile,
    sheet_name: str,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/drawing") or relationship["target"] not in names:
            continue
        drawing_rels = _rich_read_relationships(
            archive,
            _rich_rels_part_for(relationship["target"]),
            relationship["target"],
            names,
        )
        for drawing_relationship in drawing_rels.values():
            if not drawing_relationship["type"].endswith("/chart"):
                continue
            chart_id = PurePosixPath(drawing_relationship["target"]).stem
            charts.append(
                {
                    "sheet": sheet_name,
                    "chart_id": chart_id,
                    "part": drawing_relationship["target"],
                    "locator": _rich_locator(sheet=sheet_name, chart=chart_id),
                }
            )
    return charts


def _rich_orphan_charts(names: set[str], charts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    referenced_parts = {str(chart.get("part") or "") for chart in charts}
    orphans: list[dict[str, Any]] = []
    for part in sorted(name for name in names if name.startswith("xl/charts/") and name.endswith(".xml")):
        if part in referenced_parts:
            continue
        chart_id = PurePosixPath(part).stem
        orphans.append(
            {
                "chart_id": chart_id,
                "title": chart_id,
                "sheet_name": None,
                "part": part,
                "member": part,
                "locator": _rich_locator(chart=chart_id),
            }
        )
    return orphans


def _rich_worksheet_rows(sheet_root: ElementTree.Element, shared_strings: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in sheet_root.findall(f"{RICH_SHEET_NS}sheetData/{RICH_SHEET_NS}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{RICH_SHEET_NS}c"):
            cell_ref = str(cell.attrib.get("r") or "")
            column = _column_number(re.match(r"([A-Z]+)", cell_ref, re.IGNORECASE).group(1)) if re.match(r"([A-Z]+)", cell_ref, re.IGNORECASE) else 0
            if column:
                cells[column] = _cell_value(cell, shared_strings)
        if cells:
            rows.append([cells.get(index, "") for index in range(1, max(cells) + 1)])
    return rows


def _rich_data_model(rows: list[list[str]]) -> dict[str, Any]:
    fields = _rich_table_dicts(rows)
    return {"field_count": len(fields), "fields": fields}


def _rich_chart_plan(rows: list[list[str]]) -> dict[str, Any]:
    charts = _rich_table_dicts(rows)
    return {"chart_plan_count": len(charts), "charts": charts}


def _rich_planned_charts(chart_plan: dict[str, Any]) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    for chart in chart_plan.get("charts", []):
        if not isinstance(chart, dict):
            continue
        chart_id = str(chart.get("chart_id") or "")
        if not chart_id:
            continue
        source_sheet = str(chart.get("source_sheet") or "Evidence")
        charts.append(
            {
                "sheet": source_sheet,
                "chart_id": chart_id,
                "chart_type": chart.get("chart_type"),
                "title": chart.get("title"),
                "source_range": chart.get("source_range"),
                "planned": True,
                "locator": _rich_locator(sheet=source_sheet, chart=chart_id),
            }
        )
    return charts


def _rich_table_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [header.strip() for header in rows[0]]
    records: list[dict[str, str]] = []
    for row in rows[1:]:
        records.append({header: row[index] if index < len(row) else "" for index, header in enumerate(headers) if header})
    return records


def _rich_named_ranges(workbook_root: ElementTree.Element) -> list[dict[str, Any]]:
    named_ranges: list[dict[str, Any]] = []
    for defined_name in workbook_root.findall(f"{RICH_SHEET_NS}definedNames/{RICH_SHEET_NS}definedName"):
        named_ranges.append(
            {
                "name": defined_name.attrib.get("name"),
                "refers_to": defined_name.text or "",
                "scope": defined_name.attrib.get("localSheetId"),
            }
        )
    return named_ranges


def _rich_core_metadata(archive: zipfile.ZipFile, names: set[str]) -> dict[str, Any]:
    if "docProps/core.xml" not in names:
        return {}
    root = ElementTree.fromstring(archive.read("docProps/core.xml"))
    return {
        "title": _rich_first_text(root, f"{DC_NS}title"),
        "creator": _rich_first_text(root, f"{DC_NS}creator"),
        "last_modified_by": _rich_first_text(root, f"{CORE_NS}lastModifiedBy"),
    }


def _rich_read_relationships(
    archive: zipfile.ZipFile,
    rels_part: str,
    source_part: str,
    names: set[str],
) -> dict[str, dict[str, str]]:
    if rels_part not in names:
        return {}
    root = ElementTree.fromstring(archive.read(rels_part))
    relationships: dict[str, dict[str, str]] = {}
    for relationship in root.findall(f"{REL_NS}Relationship"):
        rel_id = str(relationship.attrib.get("Id") or "")
        target = str(relationship.attrib.get("Target") or "")
        relationships[rel_id] = {
            "id": rel_id,
            "type": str(relationship.attrib.get("Type") or ""),
            "target": _rich_resolve_target(source_part, target),
            "target_mode": str(relationship.attrib.get("TargetMode") or ""),
        }
    return relationships


def _rich_external_relationships(archive: zipfile.ZipFile, names: set[str]) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    for name in sorted(names):
        if not name.endswith(".rels"):
            continue
        root = ElementTree.fromstring(archive.read(name))
        for relationship in root.findall(f"{REL_NS}Relationship"):
            if relationship.attrib.get("TargetMode") == "External":
                relationships.append(
                    {
                        "relationship_part": name,
                        "type": str(relationship.attrib.get("Type") or ""),
                        "target": str(relationship.attrib.get("Target") or ""),
                    }
                )
    return relationships


def _rich_rels_part_for(part: str) -> str:
    path = PurePosixPath(part)
    return str(path.parent / "_rels" / f"{path.name}.rels")


def _rich_resolve_target(source_part: str, target: str) -> str:
    if "://" in target:
        return target
    if target.startswith("/"):
        return target.lstrip("/")
    path = PurePosixPath(source_part).parent / target
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        else:
            parts.append(part)
    return "/".join(parts)


def _rich_text_content(element: ElementTree.Element) -> str:
    return "".join(node.text or "" for node in element.iter() if node.tag == f"{RICH_SHEET_NS}t").strip()


def _rich_first_text(root: ElementTree.Element, tag: str) -> str | None:
    node = root.find(tag)
    return node.text if node is not None else None


def _rich_locator(**kwargs: Any) -> dict[str, Any]:
    locator = {"kind": "sheet"}
    locator.update({key: value for key, value in kwargs.items() if value not in {None, ""}})
    return locator


def _rich_unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts or normalized.startswith("/") or normalized.startswith("../") or ":" in parts[0]:
        return True
    return any(part in {"", ".", ".."} for part in parts)


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


# ---------------------------------------------------------------------------
# Model-check helpers (circular refs, empty inputs, balance issues)
# ---------------------------------------------------------------------------

def _input_cell_set(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
) -> set[tuple[str, str]]:
    """Build a set of (sheet_name, CELL_REF) for all non-empty input cells."""
    populated: set[tuple[str, str]] = set()
    for sheet_index, member in enumerate(worksheet_members, start=1):
        worksheet_root = read_xml(path, member)
        if worksheet_root is None:
            continue
        sheet_name = sheet_names[sheet_index - 1] if sheet_index <= len(sheet_names) else f"Sheet {sheet_index}"
        for cell in worksheet_root.findall(".//main:c", SHEET_NS):
            cell_ref = str(cell.get("r") or "").upper()
            value = _cell_value(cell, shared_strings)
            if value != "":
                populated.add((sheet_name.upper(), cell_ref))
    return populated


def _detect_circular_refs(formulas: list[dict[str, object]]) -> list[dict[str, object]]:
    """Detect formulas that reference their own cell."""
    circular_refs: list[dict[str, object]] = []
    for formula in formulas:
        sheet_name = str(formula.get("sheet_name", ""))
        cell_ref = str(formula.get("cell_ref", ""))
        formula_text = str(formula.get("formula", ""))
        if not cell_ref or not formula_text:
            continue
        normalized_cell = cell_ref.replace("$", "").upper()
        precedents = _formula_precedents(formula_text)
        for precedent in precedents:
            if ":" in precedent:
                # Range reference -- skip for circular detection (too complex for structural check).
                continue
            if precedent == normalized_cell:
                circular_refs.append(
                    {
                        "sheet_name": sheet_name,
                        "cell_ref": cell_ref,
                        "formula": formula_text,
                        "self_reference": normalized_cell,
                    }
                )
                break
    return circular_refs


def _detect_empty_inputs(
    formulas: list[dict[str, object]],
    input_cells: set[tuple[str, str]],
) -> list[dict[str, object]]:
    """Detect formula cells that reference empty input cells."""
    empty_inputs: list[dict[str, object]] = []
    for formula in formulas:
        sheet_name = str(formula.get("sheet_name", ""))
        formula_text = str(formula.get("formula", ""))
        if not formula_text:
            continue
        sheet_key = sheet_name.upper()
        precedents = _formula_precedents(formula_text)
        for precedent in precedents:
            if ":" in precedent:
                continue
            if (sheet_key, precedent) not in input_cells:
                empty_inputs.append(
                    {
                        "sheet_name": sheet_name,
                        "cell_ref": str(formula.get("cell_ref", "")),
                        "formula": formula_text,
                        "missing_cell": precedent,
                    }
                )
    return empty_inputs


_SUM_RANGE_RE = re.compile(
    r"SUM\s*\(\s*([A-Z]{1,3}\d+)\s*:\s*([A-Z]{1,3}\d+)\s*\)",
    re.IGNORECASE,
)


def _detect_balance_issues(
    formulas: list[dict[str, object]],
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
) -> list[dict[str, object]]:
    """Detect SUM formulas where the range might not cover all needed rows."""
    balance_issues: list[dict[str, object]] = []
    for formula in formulas:
        formula_text = str(formula.get("formula", ""))
        if not formula_text:
            continue
        for match in _SUM_RANGE_RE.finditer(formula_text):
            start_ref = match.group(1).upper()
            end_ref = match.group(2).upper()
            start_parsed = _parse_cell_ref(start_ref)
            end_parsed = _parse_cell_ref(end_ref)
            if start_parsed is None or end_parsed is None:
                continue
            start_row, start_col = start_parsed
            end_row, end_col = end_parsed
            if start_col != end_col:
                # Multi-column range -- not a simple column balance check.
                continue
            # Check if there is data in the column below the end row.
            sheet_name = str(formula.get("sheet_name", ""))
            column_letter = _column_letters(start_col)
            has_data_below = _has_data_below_row(
                path, worksheet_members, sheet_names, shared_strings,
                sheet_name, column_letter, end_row,
            )
            if has_data_below:
                balance_issues.append(
                    {
                        "sheet_name": sheet_name,
                        "cell_ref": str(formula.get("cell_ref", "")),
                        "formula": formula_text,
                        "sum_range": f"{start_ref}:{end_ref}",
                        "potential_gap": True,
                    }
                )
    return balance_issues


def _has_data_below_row(
    path: Path,
    worksheet_members: list[str],
    sheet_names: list[str],
    shared_strings: list[str],
    sheet_name: str,
    column_letter: str,
    end_row: int,
) -> bool:
    """Check if there is non-empty data in the given column below the specified row."""
    target_col = _column_number(column_letter)
    for sheet_index, member in enumerate(worksheet_members, start=1):
        current_name = sheet_names[sheet_index - 1] if sheet_index <= len(sheet_names) else f"Sheet {sheet_index}"
        if current_name != sheet_name:
            continue
        worksheet_root = read_xml(path, member)
        if worksheet_root is None:
            continue
        for cell in worksheet_root.findall(".//main:c", SHEET_NS):
            cell_ref = str(cell.get("r") or "")
            parsed = _parse_cell_ref(cell_ref)
            if parsed is None:
                continue
            cell_row, cell_col = parsed
            if cell_col == target_col and cell_row > end_row:
                value = _cell_value(cell, shared_strings)
                if value != "":
                    formula_node = cell.find(f"./main:f", SHEET_NS)
                    # Only flag input cells, not other SUM formulas.
                    if formula_node is None:
                        return True
    return False


# ---------------------------------------------------------------------------
# External-link helpers
# ---------------------------------------------------------------------------

def _extract_external_links(source_path: Path) -> list[dict[str, str]]:
    """Extract external relationship targets from the XLSX package."""
    links: list[dict[str, str]] = []
    names = {name.replace("\\", "/") for name in zip_names(source_path)}
    with zipfile.ZipFile(source_path) as archive:
        for name in sorted(names):
            if not name.endswith(".rels"):
                continue
            root = ElementTree.fromstring(archive.read(name))
            for relationship in root.findall(f"{REL_NS}Relationship"):
                if relationship.attrib.get("TargetMode") == "External":
                    links.append(
                        {
                            "relationship_part": name,
                            "type": str(relationship.attrib.get("Type") or ""),
                            "target": str(relationship.attrib.get("Target") or ""),
                        }
                    )
    return links


