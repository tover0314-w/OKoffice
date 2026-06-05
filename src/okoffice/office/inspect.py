from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path


OOXML_PRIMARY_MEMBERS = {
    "word/document.xml": ("docx", "word", "ooxml_docx"),
    "xl/workbook.xml": ("xlsx", "sheet", "ooxml_xlsx"),
    "ppt/presentation.xml": ("pptx", "deck", "ooxml_pptx"),
}
OOXML_EXTENSIONS = {
    ".docx": ("docx", "word", "ooxml_docx"),
    ".docm": ("docx", "word", "ooxml_docx"),
    ".xlsx": ("xlsx", "sheet", "ooxml_xlsx"),
    ".xlsm": ("xlsx", "sheet", "ooxml_xlsx"),
    ".pptx": ("pptx", "deck", "ooxml_pptx"),
    ".pptm": ("pptx", "deck", "ooxml_pptx"),
}
TEXT_FORMATS = {
    ".csv": ("csv", "sheet", "text/csv", "delimited_text"),
    ".tsv": ("tsv", "sheet", "text/tab-separated-values", "delimited_text"),
    ".md": ("markdown", "office", "text/markdown", "markdown"),
    ".markdown": ("markdown", "office", "text/markdown", "markdown"),
    ".html": ("html", "office", "text/html", "html"),
    ".htm": ("html", "office", "text/html", "html"),
    ".txt": ("text", "office", "text/plain", "plain_text"),
}
MIME_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
NEXT_TOOLS = {
    "pdf": ["pdf.inspect.document", "pdf.inspect.health", "office.context.build_packet"],
    "word": ["word.inspect.document", "office.context.build_packet"],
    "sheet": ["sheet.inspect.workbook", "office.context.build_packet"],
    "deck": ["deck.inspect.presentation", "office.context.build_packet"],
    "office": ["office.context.build_packet", "office.extract.schema"],
}


def inspect_office_file(path: str | Path) -> ToolResult:
    tool = "office.inspect.file"
    try:
        resolved = resolve_input_path(path)
        usage, warnings = _inspect_resolved_path(resolved)
        unsafe_entries = list(usage["safety"].get("unsafe_package_entries", []))
        if unsafe_entries:
            raise OKofficeException(
                "unsafe_input_rejected",
                "Office package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_entries},
            )
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=tool,
            validation=_validation_report(resolved, usage, warnings),
            warnings=warnings,
            usage=usage,
            next_recommended_tools=list(usage["recommended_next_tools"]),
        )
    except OKofficeException as exc:
        return _failed(tool, exc.to_error())


def _inspect_resolved_path(path: Path) -> tuple[dict[str, Any], list[str]]:
    file_bytes = path.read_bytes()
    suffix = path.suffix.lower()
    warnings: list[str] = []
    format_info: dict[str, Any]
    safety: dict[str, Any] = {
        "mutates_inputs": False,
        "macro_enabled": False,
        "has_external_relationships": False,
        "unsafe_package_entries": [],
    }

    if file_bytes.startswith(b"%PDF-") or suffix == ".pdf":
        format_info = {
            "detected_format": "pdf",
            "domain": "pdf",
            "mime_type": MIME_TYPES["pdf"],
            "package_type": "pdf",
            "detection_source": ["magic_bytes" if file_bytes.startswith(b"%PDF-") else "extension"],
        }
    elif suffix in OOXML_EXTENSIONS:
        format_info, package_safety, package_warnings = _inspect_ooxml_package(path, suffix)
        safety.update(package_safety)
        warnings.extend(package_warnings)
    elif suffix in TEXT_FORMATS:
        detected_format, domain, mime_type, package_type = TEXT_FORMATS[suffix]
        format_info = {
            "detected_format": detected_format,
            "domain": domain,
            "mime_type": mime_type,
            "package_type": package_type,
            "detection_source": ["extension"],
        }
    else:
        raise OKofficeException(
            "unsupported_file_type",
            f"Unsupported Office artifact type for inspect: {path.suffix or '<none>'}",
            details={"path": path.as_posix()},
        )

    next_tools = _recommended_tools(format_info["domain"])
    return (
        {
            "file": {
                "path": path.as_posix(),
                "name": path.name,
                "extension": suffix,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(file_bytes),
            },
            "format": format_info,
            "safety": safety,
            "recommended_next_tools": next_tools,
        },
        warnings,
    )


def _inspect_ooxml_package(path: Path, suffix: str) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    if not zipfile.is_zipfile(path):
        raise OKofficeException(
            "unsupported_file_type",
            f"{path.name} has an Office extension but is not a readable OOXML ZIP package.",
            details={"path": path.as_posix(), "extension": suffix},
        )
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        normalized_names = {name.replace("\\", "/") for name in names}
        unsafe_entries = [name for name in names if _is_unsafe_zip_entry(name)]
        detected = _detect_ooxml_kind(normalized_names, suffix)
        macro_enabled = suffix.endswith("m") or any(name.lower().endswith("vbaproject.bin") for name in normalized_names)
        has_external_relationships = _has_external_relationships(archive, normalized_names)

    detected_format, domain, package_type = detected
    if macro_enabled:
        warnings.append("Macro-enabled Office package markers were detected; macros are not executed.")
    if has_external_relationships:
        warnings.append("External Office relationship targets were detected.")
    return (
        {
            "detected_format": detected_format,
            "domain": domain,
            "mime_type": MIME_TYPES[detected_format],
            "package_type": package_type,
            "detection_source": ["extension", "zip_package"],
        },
        {
            "mutates_inputs": False,
            "macro_enabled": macro_enabled,
            "has_external_relationships": has_external_relationships,
            "unsafe_package_entries": unsafe_entries,
            "zip_entry_count": len(normalized_names),
        },
        warnings,
    )


def _validation_report(path: Path, usage: dict[str, Any], warnings: list[str]) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(
                name="input_path_safe",
                status="passed",
                message="Input path passed local safety checks.",
            ),
            ValidationCheck(
                name="file_exists",
                status="passed",
                details={"path": path.as_posix()},
            ),
            ValidationCheck(
                name="format_detected",
                status="passed",
                details=usage["format"],
            ),
            ValidationCheck(
                name="package_entries_safe",
                status="passed",
                details={"unsafe_package_entries": usage["safety"].get("unsafe_package_entries", [])},
            ),
        ],
        warnings=warnings,
    )


def _detect_ooxml_kind(names: set[str], suffix: str) -> tuple[str, str, str]:
    for primary_member, detected in OOXML_PRIMARY_MEMBERS.items():
        if primary_member in names:
            return detected
    return OOXML_EXTENSIONS[suffix]


def _has_external_relationships(archive: zipfile.ZipFile, names: set[str]) -> bool:
    for name in sorted(names):
        if not name.endswith(".rels"):
            continue
        info = archive.getinfo(name)
        if info.file_size > 1_000_000:
            continue
        raw = archive.read(name)
        if b'TargetMode="External"' in raw or b"TargetMode='External'" in raw:
            return True
    return False


def _is_unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if not parts or normalized.startswith("/") or normalized.startswith("../") or ":" in parts[0]:
        return True
    return any(part in {"", ".", ".."} for part in parts)


def _recommended_tools(domain: str) -> list[str]:
    return list(NEXT_TOOLS.get(domain, NEXT_TOOLS["office"]))


def _sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _failed(tool: str, error: OKofficeError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
