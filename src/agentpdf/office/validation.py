from __future__ import annotations

import re
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path


FORMULA_ERROR_VALUES = {"#DIV/0!", "#N/A", "#NAME?", "#NULL!", "#NUM!", "#REF!", "#VALUE!", "#SPILL!", "#CALC!"}
TOOL_NAME = "sheet.validation.formulas"
PACKAGE_TOOL_NAME = "office.validation.package"
OOXML_PRIMARY_MEMBERS = {
    "word/document.xml": "ooxml_docx",
    "xl/workbook.xml": "ooxml_xlsx",
    "ppt/presentation.xml": "ooxml_pptx",
}
OOXML_EXTENSIONS = {
    ".docx": "ooxml_docx",
    ".docm": "ooxml_docx",
    ".xlsx": "ooxml_xlsx",
    ".xlsm": "ooxml_xlsx",
    ".pptx": "ooxml_pptx",
    ".pptm": "ooxml_pptx",
}
MACRO_EXTENSIONS = {".docm", ".xlsm", ".pptm"}
MAX_XML_SCAN_BYTES = 1_000_000


def validate_sheet_formulas(path: str | Path) -> ToolResult:
    inspected = inspect_sheet_workbook(path)
    if inspected.status != "succeeded":
        return _failed(inspected.error or AgentPDFError(code="output_validation_failed", message="Workbook inspect failed."))

    usage = inspected.usage
    formulas = list(usage.get("formulas") or [])
    issues = _formula_issues(formulas)
    warnings = _warnings(usage, issues)
    validation = _validation_report(usage, issues, warnings)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        validation=validation,
        warnings=warnings,
        usage={
            "summary": _summary(usage, issues),
            "issues": issues,
            "formula_evaluation": {
                "status": "structural_only",
                "evaluated": False,
                "worker_configured": False,
                "reason": "Local OSS validation does not calculate workbook formulas.",
            },
            "bindings": {
                "table_count": usage.get("summary", {}).get("table_count", 0),
                "chart_count": usage.get("summary", {}).get("chart_count", 0),
                "named_range_count": usage.get("summary", {}).get("named_range_count", 0),
                "tables": usage.get("tables", []),
                "charts": usage.get("charts", []),
                "named_ranges": usage.get("named_ranges", []),
                "data_model": usage.get("data_model", {"field_count": 0, "fields": []}),
                "chart_plan": usage.get("chart_plan", {"chart_plan_count": 0, "charts": []}),
            },
            "package": usage.get("package", {}),
        },
        next_recommended_tools=["sheet.inspect.workbook", "office.context.build_packet", "office.workflow.sheet_to_deck"],
    )


def validate_office_package(path: str | Path) -> ToolResult:
    try:
        resolved = resolve_input_path(path)
    except AgentPDFException as exc:
        return _failed_package(exc.to_error())

    suffix = resolved.suffix.lower()
    if suffix == ".pdf" or _starts_with_pdf_header(resolved):
        return _validate_pdf_package(resolved)
    if suffix not in OOXML_EXTENSIONS:
        return _failed_package(
            AgentPDFError(
                code="unsupported_file_type",
                message=f"Unsupported Office package type for validation: {suffix or '<none>'}",
                details={"path": resolved.as_posix()},
            )
        )
    if not zipfile.is_zipfile(resolved):
        return _failed_package(
            AgentPDFError(
                code="unsupported_file_type",
                message=f"{resolved.name} has an Office extension but is not a readable OOXML ZIP package.",
                details={"path": resolved.as_posix(), "extension": suffix},
            )
        )

    with zipfile.ZipFile(resolved) as archive:
        names = archive.namelist()
        normalized_names = [name.replace("\\", "/") for name in names]
        normalized_name_set = set(normalized_names)
        unsafe_members = [name for name in names if _is_unsafe_zip_entry(name)]
        content_types_present = "[Content_Types].xml" in normalized_name_set
        package_type = _detect_ooxml_package_type(normalized_name_set, suffix)
        macro_enabled = suffix in MACRO_EXTENSIONS or _has_macro_markers(archive, names)
        has_external_relationships = _has_external_relationships(archive, names)

    warnings = _package_warnings(macro_enabled, has_external_relationships)
    failed = bool(unsafe_members) or not content_types_present
    summary = {
        "package_type": package_type,
        "member_count": len(names),
        "unsafe_member_count": len(unsafe_members),
        "warning_count": len(warnings),
    }
    usage = {
        "summary": summary,
        "package": {
            "path": resolved.as_posix(),
            "package_type": package_type,
            "content_types_present": content_types_present,
            "macro_enabled": macro_enabled,
            "has_external_relationships": has_external_relationships,
            "mutates_inputs": False,
        },
        "unsafe_members": unsafe_members,
    }
    validation = _package_validation_report(
        summary=summary,
        content_types_present=content_types_present,
        unsafe_members=unsafe_members,
        macro_enabled=macro_enabled,
        has_external_relationships=has_external_relationships,
        warnings=warnings,
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed" if failed else "succeeded",
        tool=PACKAGE_TOOL_NAME,
        validation=validation,
        warnings=warnings,
        usage=usage,
        error=(
            AgentPDFError(
                code="unsafe_input_rejected",
                message="Office package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_members},
            )
            if unsafe_members
            else AgentPDFError(
                code="output_validation_failed",
                message="OOXML package is missing [Content_Types].xml.",
                details={"path": resolved.as_posix()},
            )
            if failed
            else None
        ),
        next_recommended_tools=["office.inspect.file", "office.context.build_packet"] if not failed else [],
    )


def _formula_issues(formulas: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    external_references = [formula for formula in formulas if formula.get("has_external_reference")]
    cached_errors = [formula for formula in formulas if _is_error_value(formula.get("cached_value"))]
    missing_cached_values = [formula for formula in formulas if formula.get("cached_value") in {None, ""}]
    self_references = [formula for formula in formulas if _is_self_reference(formula)]
    return {
        "external_references": external_references,
        "cached_errors": cached_errors,
        "missing_cached_values": missing_cached_values,
        "self_references": self_references,
    }


def _summary(usage: dict[str, Any], issues: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    summary = usage.get("summary", {})
    formula_count = int(summary.get("formula_count", 0))
    return {
        "formula_count": formula_count,
        "external_formula_count": len(issues["external_references"]),
        "cached_error_count": len(issues["cached_errors"]),
        "missing_cached_value_count": len(issues["missing_cached_values"]),
        "self_reference_count": len(issues["self_references"]),
        "named_range_count": int(summary.get("named_range_count", 0)),
        "table_count": int(summary.get("table_count", 0)),
        "chart_count": int(summary.get("chart_count", 0)),
        "data_model_count": int(summary.get("data_model_count", 0)),
        "chart_plan_count": int(summary.get("chart_plan_count", 0)),
        "external_link_count": int(summary.get("external_link_count", 0)),
        "formula_evaluated": False,
    }


def _warnings(usage: dict[str, Any], issues: dict[str, list[dict[str, Any]]]) -> list[str]:
    warnings: list[str] = []
    formula_count = int(usage.get("summary", {}).get("formula_count", 0))
    if formula_count:
        warnings.append("Formula evaluation worker is not configured; validation is structural only.")
    if issues["external_references"]:
        warnings.append(f"External formula references detected: {len(issues['external_references'])}.")
    if issues["cached_errors"]:
        warnings.append(f"Cached formula error values detected: {len(issues['cached_errors'])}.")
    if issues["missing_cached_values"]:
        warnings.append(f"Formulas without cached values detected: {len(issues['missing_cached_values'])}.")
    if issues["self_references"]:
        warnings.append(f"Potential self-referential formulas detected: {len(issues['self_references'])}.")
    package = usage.get("package", {})
    if package.get("macro_enabled"):
        warnings.append("Macro-enabled workbook package markers were detected; macros are not executed.")
    if package.get("has_external_relationships"):
        warnings.append("External workbook relationship targets were detected.")
    return warnings


def _validation_report(
    usage: dict[str, Any],
    issues: dict[str, list[dict[str, Any]]],
    warnings: list[str],
) -> ValidationReport:
    summary = _summary(usage, issues)
    issue_status = "warning" if warnings else "passed"
    return ValidationReport(
        status=issue_status,
        checks=[
            ValidationCheck(name="workbook_inspected", status="passed", details=usage.get("file", {})),
            ValidationCheck(name="formula_inventory", status="passed", details={"formula_count": summary["formula_count"]}),
            ValidationCheck(
                name="external_formula_references",
                status="warning" if issues["external_references"] else "passed",
                details={"count": summary["external_formula_count"]},
            ),
            ValidationCheck(
                name="cached_formula_errors",
                status="warning" if issues["cached_errors"] else "passed",
                details={"count": summary["cached_error_count"]},
            ),
            ValidationCheck(
                name="self_references_structural",
                status="warning" if issues["self_references"] else "passed",
                details={"count": summary["self_reference_count"]},
            ),
            ValidationCheck(
                name="formula_evaluation_worker",
                status="skipped",
                details={"worker_configured": False, "evaluated": False},
                message="Formula value evaluation requires an optional worker.",
            ),
            ValidationCheck(
                name="table_chart_bindings_structural",
                status="passed",
                details={
                    "table_count": summary["table_count"],
                    "chart_count": summary["chart_count"],
                    "named_range_count": summary["named_range_count"],
                    "data_model_count": summary["data_model_count"],
                    "chart_plan_count": summary["chart_plan_count"],
                },
            ),
        ],
        warnings=warnings,
    )


def _validate_pdf_package(path: Path) -> ToolResult:
    inspected = inspect_office_file(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=PACKAGE_TOOL_NAME,
            error=inspected.error,
            warnings=list(inspected.warnings),
        )

    warnings = list(inspected.warnings)
    summary = {
        "package_type": "pdf",
        "member_count": 0,
        "unsafe_member_count": 0,
        "warning_count": len(warnings),
    }
    validation = ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="file_inspected", status="passed", details=inspected.usage.get("file", {})),
            ValidationCheck(
                name="pdf_structural_baseline",
                status="passed",
                message="PDF baseline validation used office.inspect.file facts; no ZIP package checks were run.",
                details=inspected.usage.get("format", {}),
            ),
            ValidationCheck(
                name="zip_checks_not_applicable",
                status="skipped",
                details={"package_type": "pdf"},
            ),
        ],
        warnings=warnings,
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=PACKAGE_TOOL_NAME,
        validation=validation,
        warnings=warnings,
        usage={"summary": summary, "inspect": inspected.usage},
        next_recommended_tools=["pdf.validation.validate_output", "pdf.inspect.health", "office.context.build_packet"],
    )


def _package_validation_report(
    *,
    summary: dict[str, Any],
    content_types_present: bool,
    unsafe_members: list[str],
    macro_enabled: bool,
    has_external_relationships: bool,
    warnings: list[str],
) -> ValidationReport:
    failed = bool(unsafe_members) or not content_types_present
    return ValidationReport(
        status="failed" if failed else "warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="package_opened", status="passed", details=summary),
            ValidationCheck(
                name="zip_member_names_safe",
                status="failed" if unsafe_members else "passed",
                details={"unsafe_members": unsafe_members, "unsafe_member_count": len(unsafe_members)},
            ),
            ValidationCheck(
                name="content_types_present",
                status="passed" if content_types_present else "failed",
                details={"required_member": "[Content_Types].xml"},
            ),
            ValidationCheck(
                name="macros_not_executed",
                status="warning" if macro_enabled else "passed",
                details={"macro_enabled": macro_enabled, "executed": False},
                message="Macro-enabled package markers were detected; macros were not executed." if macro_enabled else None,
            ),
            ValidationCheck(
                name="external_relationships",
                status="warning" if has_external_relationships else "passed",
                details={"has_external_relationships": has_external_relationships},
            ),
        ],
        warnings=warnings,
    )


def _detect_ooxml_package_type(names: set[str], suffix: str) -> str:
    for primary_member, package_type in OOXML_PRIMARY_MEMBERS.items():
        if primary_member in names:
            return package_type
    return OOXML_EXTENSIONS[suffix]


def _has_macro_markers(archive: zipfile.ZipFile, names: list[str]) -> bool:
    for name in names:
        lower_name = name.lower()
        if lower_name.endswith("vbaproject.bin"):
            return True
        if lower_name == "[content_types].xml" and _member_contains(archive, name, ("macroEnabled", "vbaProject")):
            return True
    return False


def _has_external_relationships(archive: zipfile.ZipFile, names: list[str]) -> bool:
    for name in names:
        if name.endswith(".rels") and _member_contains(archive, name, ('TargetMode="External"', "TargetMode='External'")):
            return True
    return False


def _member_contains(archive: zipfile.ZipFile, name: str, needles: tuple[str, ...]) -> bool:
    info = archive.getinfo(name)
    if info.file_size > MAX_XML_SCAN_BYTES:
        return False
    text = archive.read(name).decode("utf-8", errors="ignore")
    return any(needle in text for needle in needles)


def _package_warnings(macro_enabled: bool, has_external_relationships: bool) -> list[str]:
    warnings: list[str] = []
    if macro_enabled:
        warnings.append("Macro-enabled Office package markers were detected; macros are not executed.")
    if has_external_relationships:
        warnings.append("External Office relationship targets were detected.")
    return warnings


def _is_unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts or normalized.startswith("/") or normalized.startswith("../") or ":" in parts[0]:
        return True
    return any(part in {"", ".", ".."} for part in parts)


def _starts_with_pdf_header(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def _is_error_value(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() in FORMULA_ERROR_VALUES


def _is_self_reference(formula: dict[str, Any]) -> bool:
    cell = str(formula.get("cell") or "")
    expression = str(formula.get("formula") or "")
    if not cell or not expression:
        return False
    pattern = re.compile(rf"(?<![A-Z0-9_]){re.escape(cell)}(?![A-Z0-9_])", re.IGNORECASE)
    return bool(pattern.search(expression))


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _failed_package(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=PACKAGE_TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
