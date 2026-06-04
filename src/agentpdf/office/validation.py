from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from agentpdf.office.inspect import inspect_office_file
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path


TOOL_NAME = "office.validation.package"
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


def validate_office_package(path: str | Path) -> ToolResult:
    try:
        resolved = resolve_input_path(path)
    except AgentPDFException as exc:
        return _failed(exc.to_error())

    suffix = resolved.suffix.lower()
    if suffix == ".pdf" or _starts_with_pdf_header(resolved):
        return _validate_pdf_package(resolved)
    if suffix not in OOXML_EXTENSIONS:
        return _failed(
            AgentPDFError(
                code="unsupported_file_type",
                message=f"Unsupported Office package type for validation: {suffix or '<none>'}",
                details={"path": resolved.as_posix()},
            )
        )
    if not zipfile.is_zipfile(resolved):
        return _failed(
            AgentPDFError(
                code="unsupported_file_type",
                message=f"{resolved.name} has an Office extension but is not a readable OOXML ZIP package.",
                details={"path": resolved.as_posix(), "extension": suffix},
            )
        )

    with zipfile.ZipFile(resolved) as archive:
        names = archive.namelist()
        normalized_names = {name.replace("\\", "/") for name in names}
        unsafe_members = [name for name in names if _is_unsafe_zip_entry(name)]
        content_types_present = "[Content_Types].xml" in normalized_names
        package_type = _detect_ooxml_package_type(normalized_names, suffix)
        macro_enabled = suffix in MACRO_EXTENSIONS or _has_macro_markers(archive, names)
        has_external_relationships = _has_external_relationships(archive, names)
        scan_limited_members = _scan_limited_members(archive, names)

    warnings = _package_warnings(macro_enabled, has_external_relationships, scan_limited_members)
    failed = bool(unsafe_members) or not content_types_present
    summary = {
        "package_type": package_type,
        "member_count": len(names),
        "unsafe_member_count": len(unsafe_members),
        "warning_count": len(warnings),
    }
    error = _package_error(resolved, unsafe_members, content_types_present) if failed else None
    return ToolResult(
        job_id=_job_id(),
        status="failed" if failed else "succeeded",
        tool=TOOL_NAME,
        validation=_validation_report(
            summary=summary,
            content_types_present=content_types_present,
            unsafe_members=unsafe_members,
            macro_enabled=macro_enabled,
            has_external_relationships=has_external_relationships,
            scan_limited_members=scan_limited_members,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
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
            "scan_limited_members": scan_limited_members,
        },
        error=error,
        next_recommended_tools=["office.inspect.file", "office.context.build_packet"] if not failed else [],
    )


def _validate_pdf_package(path: Path) -> ToolResult:
    inspected = inspect_office_file(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=TOOL_NAME,
            error=inspected.error,
            warnings=list(inspected.warnings),
        )
    warnings = list(inspected.warnings)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(name="file_inspected", status="passed", details=inspected.usage.get("file", {})),
                ValidationCheck(
                    name="pdf_structural_baseline",
                    status="passed",
                    message="PDF package validation used office.inspect.file facts; ZIP checks do not apply.",
                    details=inspected.usage.get("format", {}),
                ),
                ValidationCheck(name="zip_checks_not_applicable", status="skipped", details={"package_type": "pdf"}),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "package_type": "pdf",
                "member_count": 0,
                "unsafe_member_count": 0,
                "warning_count": len(warnings),
            },
            "inspect": inspected.usage,
        },
        next_recommended_tools=["pdf.inspect.document", "office.context.build_packet"],
    )


def _validation_report(
    *,
    summary: dict[str, Any],
    content_types_present: bool,
    unsafe_members: list[str],
    macro_enabled: bool,
    has_external_relationships: bool,
    scan_limited_members: list[dict[str, Any]],
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
            ValidationCheck(
                name="safety_sensitive_xml_scan",
                status="warning" if scan_limited_members else "passed",
                details={"scan_limited_members": scan_limited_members, "max_scan_bytes": MAX_XML_SCAN_BYTES},
            ),
        ],
        warnings=warnings,
    )


def _package_error(path: Path, unsafe_members: list[str], content_types_present: bool) -> AgentPDFError:
    if unsafe_members:
        return AgentPDFError(
            code="unsafe_input_rejected",
            message="Office package contains unsafe ZIP entry names.",
            details={"unsafe_package_entries": unsafe_members},
        )
    if not content_types_present:
        return AgentPDFError(
            code="output_validation_failed",
            message="OOXML package is missing [Content_Types].xml.",
            details={"path": path.as_posix()},
        )
    return AgentPDFError(code="output_validation_failed", message="Office package validation failed.")


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


def _scan_limited_members(archive: zipfile.ZipFile, names: list[str]) -> list[dict[str, Any]]:
    limited = []
    for name in names:
        normalized = name.replace("\\", "/").lower()
        if not (normalized.endswith(".rels") or normalized == "[content_types].xml"):
            continue
        info = archive.getinfo(name)
        if info.file_size > MAX_XML_SCAN_BYTES:
            limited.append({"name": name, "size_bytes": info.file_size})
    return limited


def _member_contains(archive: zipfile.ZipFile, name: str, needles: tuple[str, ...]) -> bool:
    info = archive.getinfo(name)
    if info.file_size > MAX_XML_SCAN_BYTES:
        return False
    text = archive.read(name).decode("utf-8", errors="ignore")
    return any(needle in text for needle in needles)


def _package_warnings(
    macro_enabled: bool,
    has_external_relationships: bool,
    scan_limited_members: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if macro_enabled:
        warnings.append("Macro-enabled Office package markers were detected; macros are not executed.")
    if has_external_relationships:
        warnings.append("External Office relationship targets were detected.")
    for member in scan_limited_members:
        warnings.append(
            f"Safety-sensitive OOXML member is too large for local safety scan: {member['name']} "
            f"({member['size_bytes']} bytes)."
        )
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


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(job_id=_job_id(), status="failed", tool=TOOL_NAME, error=error, warnings=[error.message])


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
