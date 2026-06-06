from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


BUNDLE_REPORT_TOOL = "office.bundle.report"
VALIDATE_OUTPUT_TOOL = "office.validate.output"
FORMAT_EXTENSIONS = {".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx", ".pdf": "pdf"}


def report_office_bundle(bundle_path: str | Path) -> ToolResult:
    resolved = Path(bundle_path).resolve()
    if not resolved.exists():
        return failed_result(
            BUNDLE_REPORT_TOOL,
            OKofficeError(code="file_not_found", message=f"Bundle file not found: {resolved.as_posix()}"))
    if not zipfile.is_zipfile(resolved):
        return failed_result(
            BUNDLE_REPORT_TOOL,
            OKofficeError(code="invalid_input", message=f"Bundle is not a readable ZIP file: {resolved.name}"))
    manifest: dict[str, Any] = {}
    artifact_summaries: list[dict[str, Any]] = []
    with zipfile.ZipFile(resolved) as archive:
        names = archive.namelist()
        if "okoffice-bundle-manifest.json" in names:
            try:
                manifest = json.loads(archive.read("okoffice-bundle-manifest.json"))
            except json.JSONDecodeError:
                pass
        artifact_entries = manifest.get("artifacts", []) if isinstance(manifest, dict) else []
        total_size = 0
        formats: set[str] = set()
        for entry in artifact_entries:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("bundle_path") or entry.get("source_path") or "unknown")
            size = int(entry.get("size_bytes") or 0)
            fmt = _format_from_name(name)
            formats.add(fmt)
            total_size += size
            artifact_summaries.append({"name": name, "size": size, "format": fmt})
        if not artifact_summaries:
            for name in names:
                if name in {"okoffice-bundle-manifest.json", "checksums.sha256"}:
                    continue
                info = archive.getinfo(name)
                artifact_summaries.append({"name": name, "size": info.file_size, "format": _format_from_name(name)})
                total_size += info.file_size
    return ToolResult(
        job_id=job_id(), status="succeeded", tool=BUNDLE_REPORT_TOOL,
        validation=ValidationReport(status="passed", checks=[
            ValidationCheck(name="bundle_opened", status="passed", details={"member_count": len(names)}),
            ValidationCheck(name="manifest_parsed", status="passed" if manifest else "warning",
                            details={"manifest_present": bool(manifest)})]),
        usage={
            "summary": {"artifact_count": len(artifact_summaries), "formats": sorted(formats),
                        "total_size_bytes": total_size},
            "artifacts": artifact_summaries, "manifest": manifest},
        next_recommended_tools=["office.bundle.verify", "office.validate.output"])


def validate_office_output(path: str | Path, expected_format: str | None = None) -> ToolResult:
    resolved = Path(path).resolve()
    if not resolved.exists():
        return failed_result(
            VALIDATE_OUTPUT_TOOL,
            OKofficeError(code="file_not_found", message=f"Output file not found: {resolved.as_posix()}"))
    detected = _format_from_name(resolved.name)
    fmt = (expected_format or detected).lower().strip()
    if fmt not in FORMAT_EXTENSIONS.values():
        return failed_result(
            VALIDATE_OUTPUT_TOOL,
            OKofficeError(code="unsupported_format", message=f"Unsupported output format: {fmt}",
                          details={"supported": list(FORMAT_EXTENSIONS.values())}))
    try:
        format_result = _delegate_format_validation(resolved, fmt)
    except OKofficeException as exc:
        return failed_result(VALIDATE_OUTPUT_TOOL, exc.to_error())
    validation = format_result.validation
    check_count = len(validation.checks) if validation else 0
    status = validation.status if validation else "passed"
    return ToolResult(
        job_id=job_id(), status=format_result.status, tool=VALIDATE_OUTPUT_TOOL,
        validation=validation, warnings=list(format_result.warnings), error=format_result.error,
        usage={"summary": {"format": fmt, "validation_status": status, "check_count": check_count},
               "format_validation": format_result.usage, "path": resolved.as_posix()},
        next_recommended_tools=["office.inspect.file", "office.bundle.export"])


def _delegate_format_validation(resolved: Path, fmt: str) -> ToolResult:
    if fmt == "docx":
        from okoffice.office.word_validation import validate_word_document
        return validate_word_document(resolved)
    if fmt == "xlsx":
        from okoffice.office.sheet import validate_sheet_workbook
        return validate_sheet_workbook(resolved)
    if fmt == "pptx":
        from okoffice.office.deck_validation import validate_deck_presentation
        return validate_deck_presentation(resolved)
    return _validate_pdf_basic(resolved)


def _validate_pdf_basic(path: Path) -> ToolResult:
    with path.open("rb") as handle:
        header = handle.read(5)
    is_pdf = header == b"%PDF-"
    file_size = path.stat().st_size
    return ToolResult(
        job_id=job_id(), status="succeeded" if is_pdf else "failed", tool=VALIDATE_OUTPUT_TOOL,
        validation=ValidationReport(
            status="passed" if is_pdf else "failed",
            checks=[ValidationCheck(name="file_exists", status="passed", details={"size_bytes": file_size}),
                    ValidationCheck(name="pdf_header", status="passed" if is_pdf else "failed")]),
        usage={"format": "pdf", "size_bytes": file_size, "header_valid": is_pdf})


def _format_from_name(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return FORMAT_EXTENSIONS.get(suffix, suffix.lstrip(".") or "unknown")
