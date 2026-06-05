from __future__ import annotations

import hashlib
import hmac
import json
import math
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path
from okoffice.validation.pdf import validate_pdf


SUSPICIOUS_MARKERS = {
    b"/JavaScript": "javascript_action",
    b"/JS": "javascript_action",
    b"/OpenAction": "open_action",
    b"/Launch": "launch_action",
    b"/EmbeddedFile": "embedded_file",
    b"/RichMedia": "rich_media",
    b"/AA": "additional_action",
}


def protect_pdf(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
    owner_password: str | None = None,
) -> ToolResult:
    return _encrypt_result("pdf.security.protect", input_path, output_path, password, owner_password)


def encrypt_pdf(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
    owner_password: str | None = None,
) -> ToolResult:
    return _encrypt_result("pdf.security.encrypt", input_path, output_path, password, owner_password)


def unlock_authorized_pdf(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> ToolResult:
    return _decrypt_result("pdf.security.unlock_authorized", input_path, output_path, password)


def decrypt_authorized_pdf(
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> ToolResult:
    return _decrypt_result("pdf.security.decrypt_authorized", input_path, output_path, password)


def redact_pdf(
    input_path: str | Path,
    output_path: str | Path,
    regions: list[dict[str, Any]],
    fill_color: str = "#000000",
    render_scale: float = 2.0,
) -> ToolResult:
    tool = "pdf.security.redact"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    normalized_regions = _normalize_redaction_regions(regions, page_count=len(reader.pages))
    output = resolve_output_path(output_path)
    _write_redacted_raster_pdf(
        source,
        output,
        reader=reader,
        regions=normalized_regions,
        fill_color=fill_color,
        render_scale=render_scale,
    )
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    warnings = [
        "Local redaction rasterizes pages into an image-only PDF to remove the original text layer.",
        "Only explicit bbox regions are redacted; automatic sensitive text discovery is not performed.",
    ]
    warnings.extend(validation.warnings or [])
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=warnings,
        usage={
            "input": str(source),
            "output": str(output),
            "redaction_strategy": "local_rasterize_and_mask_regions",
            "redaction_region_count": len(normalized_regions),
            "redaction_pages": sorted({region["page"] for region in normalized_regions}),
            "fill_color": fill_color,
            "render_scale": render_scale,
            "limitations": [
                "Requires caller-supplied page-numbered PDF-coordinate bbox regions.",
                "Raster output preserves visual appearance but removes selectable text and vector structure.",
                "Run pdf.security.verify_redaction with known sensitive terms after redaction.",
            ],
        },
        next_recommended_tools=[
            "pdf.security.verify_redaction",
            "pdf.validation.redaction_check",
            "pdf.validation.visual_diff",
        ],
    )


def verify_redaction_pdf(
    input_path: str | Path,
    search_terms: list[str] | None = None,
) -> ToolResult:
    report, usage, warnings = _redaction_verification_report(input_path, search_terms=search_terms)
    return ToolResult(
        job_id=_job_id(),
        status="failed" if report.status == "failed" else "succeeded",
        tool="pdf.security.verify_redaction",
        validation=report,
        warnings=warnings,
        usage=usage,
        next_recommended_tools=["pdf.validation.redaction_check", "pdf.validation.visual_diff"],
    )


def redaction_check_pdf(
    input_path: str | Path,
    search_terms: list[str] | None = None,
) -> ToolResult:
    report, usage, warnings = _redaction_verification_report(input_path, search_terms=search_terms)
    return ToolResult(
        job_id=_job_id(),
        status="failed" if report.status == "failed" else "succeeded",
        tool="pdf.validation.redaction_check",
        validation=report,
        warnings=warnings,
        usage=usage,
        next_recommended_tools=["pdf.security.verify_redaction", "pdf.validation.visual_diff"],
    )


def inspect_health_pdf(input_path: str | Path) -> ToolResult:
    tool = "pdf.inspect.health"
    source = resolve_input_path(input_path)
    raw = source.read_bytes()
    findings = _security_findings(raw)
    checks: list[ValidationCheck] = [
        ValidationCheck(
            name="pdf_header_present",
            status="passed" if raw.startswith(b"%PDF-") else "failed",
            details={"header": raw[:8].decode("latin-1", errors="replace")},
            message=None if raw.startswith(b"%PDF-") else "File does not start with a PDF header.",
        ),
        ValidationCheck(
            name="xref_trailer_present",
            status="passed" if b"startxref" in raw and b"%%EOF" in raw else "warning",
            details={"has_startxref": b"startxref" in raw, "has_eof": b"%%EOF" in raw},
            message=None if b"startxref" in raw and b"%%EOF" in raw else "PDF trailer markers are incomplete.",
        ),
        ValidationCheck(
            name="static_pdf_risk_markers",
            status="passed" if not findings else "warning",
            details={"findings": findings},
            message="Suspicious PDF action markers found." if findings else None,
        ),
    ]
    usage: dict[str, Any] = {
        "input": str(source),
        "size_bytes": source.stat().st_size,
        "scanner": "okoffice_pdf_health_static_v1",
        "findings": findings,
        "suspicious_count": len(findings),
    }

    try:
        reader = PdfReader(source)
    except Exception as exc:
        checks.append(
            ValidationCheck(
                name="parseable_pdf",
                status="failed",
                message=str(exc),
            )
        )
        report = ValidationReport(status="failed", checks=checks, warnings=["PDF parsing failed."])
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=tool,
            validation=report,
            warnings=report.warnings,
            usage={**usage, "parseable": False},
            next_recommended_tools=["pdf.optimize.repair"],
        )

    usage["parseable"] = True
    usage["encrypted"] = reader.is_encrypted
    checks.append(ValidationCheck(name="parseable_pdf", status="passed", details={"encrypted": reader.is_encrypted}))
    if reader.is_encrypted:
        checks.append(
            ValidationCheck(
                name="encrypted_pdf",
                status="warning",
                details={"encrypted": True},
                message="Encrypted PDFs require authorized decryption for deeper health checks.",
            )
        )
        usage["page_count"] = None
        usage["metadata_keys"] = []
    else:
        page_sizes = _page_size_facts(reader)
        huge_pages = [page for page in page_sizes if page["width"] > 14400 or page["height"] > 14400]
        metadata_keys = sorted(str(key).lstrip("/") for key in (reader.metadata or {}).keys())
        checks.append(
            ValidationCheck(
                name="page_count_nonzero",
                status="passed" if len(reader.pages) > 0 else "failed",
                details={"page_count": len(reader.pages)},
            )
        )
        checks.append(
            ValidationCheck(
                name="page_geometry_reasonable",
                status="passed" if not huge_pages else "warning",
                details={"huge_pages": huge_pages},
                message="Very large page dimensions detected." if huge_pages else None,
            )
        )
        usage["page_count"] = len(reader.pages)
        usage["page_sizes"] = page_sizes
        usage["metadata_keys"] = metadata_keys
        usage["metadata_key_count"] = len(metadata_keys)

    warnings = _health_warnings(checks)
    report = ValidationReport(status=_validation_status(checks), checks=checks, warnings=warnings)
    return ToolResult(
        job_id=_job_id(),
        status="failed" if report.status == "failed" else "succeeded",
        tool=tool,
        validation=report,
        warnings=warnings,
        usage=usage,
        next_recommended_tools=(
            ["pdf.security.sanitize", "pdf.security.malware_scan"]
            if findings
            else ["pdf.inspect.document", "pdf.validation.render_check"]
        ),
    )


def sanitize_pdf(
    input_path: str | Path,
    output_path: str | Path,
    remove_metadata: bool = True,
) -> ToolResult:
    tool = "pdf.security.sanitize"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    before_findings = _security_findings(source.read_bytes())
    writer = PdfWriter()
    removed_page_actions = 0

    for page in reader.pages:
        writer.add_page(page)
        removed_page_actions += _sanitize_page_object(writer.pages[-1])
    if remove_metadata:
        writer.add_metadata({})
    elif reader.metadata:
        writer.add_metadata(dict(reader.metadata))
    removed_catalog_entries = _sanitize_writer_root(writer)

    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)

    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    after_findings = _security_findings(output.read_bytes())
    checks = list(validation.checks)
    checks.append(
        ValidationCheck(
            name="sanitized_static_pdf_risk_markers",
            status="passed" if not after_findings else "failed",
            details={"before_findings": before_findings, "after_findings": after_findings},
            message="Suspicious markers remain after sanitization." if after_findings else None,
        )
    )
    report = ValidationReport(
        status=_validation_status(checks),
        checks=checks,
        page_count=validation.page_count,
        warnings=validation.warnings,
    )
    warnings = list(validation.warnings)
    if after_findings:
        warnings.append("Suspicious PDF markers remain after sanitization.")
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if report.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=report,
        warnings=warnings,
        usage={
            "input": str(source),
            "output": str(output),
            "sanitize_strategy": "local_rewrite_pages_without_catalog_active_content",
            "before_findings": before_findings,
            "after_findings": after_findings,
            "removed_risk_count": max(0, len(before_findings) - len(after_findings)),
            "removed_page_action_count": removed_page_actions,
            "removed_catalog_entry_count": removed_catalog_entries,
            "metadata_removed": remove_metadata,
            "limitations": [
                "Local sanitizer rewrites pages and removes known active-content structures.",
                "It does not execute or emulate PDF JavaScript.",
                "Run pdf.inspect.health after sanitization for independent evidence.",
            ],
        },
        next_recommended_tools=["pdf.inspect.health", "pdf.security.malware_scan", "pdf.validation.render_check"],
    )


def sign_pdf(
    input_path: str | Path,
    output_path: str | Path,
    secret: str | None = None,
) -> ToolResult:
    tool = "pdf.security.sign"
    source = resolve_input_path(input_path)
    digest = _sha256(source)
    signature = _signature(digest, secret)
    output = resolve_output_path(output_path)
    payload = {
        "signature_format": "okoffice_detached_sha256_v1",
        "input": str(source),
        "sha256": digest,
        "signature": signature,
        "uses_secret": secret is not None,
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    artifact = build_artifact(output, source_tool=tool)
    artifact.mime_type = "application/json"
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=["Local OSS signing creates a detached integrity manifest, not a PAdES signature."],
        usage=payload,
        next_recommended_tools=["pdf.security.verify_signature"],
    )


def verify_signature_pdf(
    input_path: str | Path,
    signature_path: str | Path,
    secret: str | None = None,
) -> ToolResult:
    tool = "pdf.security.verify_signature"
    source = resolve_input_path(input_path)
    signature_file = resolve_input_path(signature_path)
    payload = json.loads(signature_file.read_text(encoding="utf-8"))
    digest = _sha256(source)
    expected = _signature(digest, secret)
    valid = payload.get("sha256") == digest and payload.get("signature") == expected
    report = ValidationReport(
        status="passed" if valid else "failed",
        checks=[
            ValidationCheck(
                name="detached_signature_match",
                status="passed" if valid else "failed",
                details={"signature_format": payload.get("signature_format")},
            )
        ],
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if valid else "failed",
        tool=tool,
        validation=report,
        warnings=[] if valid else ["Detached signature did not match the current PDF bytes."],
        usage={
            "input": str(source),
            "signature_path": str(signature_file),
            "signature_valid": valid,
            "sha256": digest,
        },
        next_recommended_tools=["pdf.security.malware_scan"],
    )


def malware_scan_pdf(input_path: str | Path) -> ToolResult:
    tool = "pdf.security.malware_scan"
    source = resolve_input_path(input_path)
    raw = source.read_bytes()
    findings = [
        {"marker": marker.decode("latin-1"), "risk": risk}
        for marker, risk in SUSPICIOUS_MARKERS.items()
        if marker in raw
    ]
    report = ValidationReport(
        status="passed" if not findings else "warning",
        checks=[
            ValidationCheck(
                name="static_pdf_risk_markers",
                status="passed" if not findings else "warning",
                details={"findings": findings},
            )
        ],
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        validation=report,
        warnings=["Suspicious PDF action markers found."] if findings else [],
        usage={
            "input": str(source),
            "scanner": "okoffice_static_pdf_marker_scan_v1",
            "suspicious_count": len(findings),
            "findings": findings,
        },
        next_recommended_tools=["pdf.security.sanitize"] if findings else ["pdf.inspect.document"],
    )


def _encrypt_result(
    tool: str,
    input_path: str | Path,
    output_path: str | Path,
    password: str,
    owner_password: str | None,
) -> ToolResult:
    if not password:
        raise OKofficeException("unsafe_input_rejected", "A non-empty password is required.")
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))
    writer.encrypt(password, owner_password or password)
    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    artifact = build_artifact(output, source_tool=tool)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[artifact],
        warnings=[],
        usage={"input": str(source), "output": str(output), "encrypted": True},
        next_recommended_tools=["pdf.security.permissions", "pdf.security.decrypt_authorized"],
    )


def _decrypt_result(
    tool: str,
    input_path: str | Path,
    output_path: str | Path,
    password: str,
) -> ToolResult:
    source = resolve_input_path(input_path)
    try:
        reader = PdfReader(source)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {source}") from exc
    if not reader.is_encrypted:
        raise OKofficeException("invalid_password", "Input PDF is not encrypted.")
    if reader.decrypt(password) == 0:
        raise OKofficeException("invalid_password", "Password did not unlock the PDF.")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))
    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=validation.warnings or [],
        usage={"input": str(source), "output": str(output), "encrypted": False},
        next_recommended_tools=["pdf.validation.render_check", "pdf.security.malware_scan"],
    )


def _reader(path: Path) -> PdfReader:
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise OKofficeException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require authorized decryption before this operation.",
        )
    return reader


def _security_findings(raw: bytes) -> list[dict[str, Any]]:
    return [
        {"marker": marker.decode("latin-1"), "risk": risk}
        for marker, risk in SUSPICIOUS_MARKERS.items()
        if marker in raw
    ]


def _page_size_facts(reader: PdfReader) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        facts.append(
            {
                "page_number": index,
                "width": float(page.mediabox.width),
                "height": float(page.mediabox.height),
                "rotation": int(page.get("/Rotate", 0) or 0),
            }
        )
    return facts


def _sanitize_writer_root(writer: PdfWriter) -> int:
    root = getattr(writer, "_root_object", {})
    removed = 0
    for key in ("/OpenAction", "/AA", "/Names", "/AcroForm", "/AF", "/EmbeddedFiles", "/JavaScript"):
        removed += _delete_pdf_key(root, key)
    return removed


def _sanitize_page_object(page: Any) -> int:
    removed = 0
    for key in ("/AA", "/A", "/JS", "/OpenAction", "/RichMedia"):
        removed += _delete_pdf_key(page, key)
    annots = page.get("/Annots")
    if not annots:
        return removed

    kept_annotations: list[Any] = []
    try:
        for annotation_ref in annots:
            annotation = annotation_ref.get_object() if hasattr(annotation_ref, "get_object") else annotation_ref
            subtype = str(annotation.get("/Subtype", ""))
            for key in ("/A", "/AA", "/JS", "/RichMedia"):
                removed += _delete_pdf_key(annotation, key)
            if subtype in {"/FileAttachment", "/RichMedia", "/Movie", "/Sound", "/Screen"}:
                removed += 1
                continue
            kept_annotations.append(annotation_ref)
    except Exception:
        return removed

    if kept_annotations:
        page[NameObject("/Annots")] = ArrayObject(kept_annotations)
    else:
        removed += _delete_pdf_key(page, "/Annots")
    return removed


def _delete_pdf_key(obj: Any, key: str) -> int:
    try:
        if key in obj:
            del obj[NameObject(key)]
            return 1
    except Exception:
        try:
            if key in obj:
                del obj[key]
                return 1
        except Exception:
            return 0
    return 0


def _health_warnings(checks: list[ValidationCheck]) -> list[str]:
    warnings: list[str] = []
    if any(check.name == "static_pdf_risk_markers" and check.status == "warning" for check in checks):
        warnings.append("Suspicious PDF action markers found.")
    if any(check.status == "failed" for check in checks):
        warnings.append("PDF health checks failed.")
    return warnings


def _normalize_redaction_regions(
    regions: list[dict[str, Any]],
    page_count: int,
) -> list[dict[str, Any]]:
    if not regions:
        raise OKofficeException(
            "unsafe_input_rejected",
            "At least one explicit redaction region is required.",
        )

    normalized: list[dict[str, Any]] = []
    for index, region in enumerate(regions):
        if not isinstance(region, dict):
            raise OKofficeException(
                "unsafe_input_rejected",
                f"Redaction region {index + 1} must be a JSON object.",
            )
        page = region.get("page")
        bbox = region.get("bbox")
        if not isinstance(page, int) or page < 1 or page > page_count:
            raise OKofficeException(
                "unsafe_input_rejected",
                f"Redaction region {index + 1} has an invalid 1-based page number.",
            )
        if not isinstance(bbox, list | tuple) or len(bbox) != 4:
            raise OKofficeException(
                "unsafe_input_rejected",
                f"Redaction region {index + 1} must include bbox [x0, y0, x1, y1].",
            )
        coordinates = [_finite_float(value, f"region {index + 1} bbox") for value in bbox]
        x0, y0, x1, y1 = coordinates
        if x1 <= x0 or y1 <= y0:
            raise OKofficeException(
                "unsafe_input_rejected",
                f"Redaction region {index + 1} bbox must have positive width and height.",
            )
        normalized.append(
            {
                "page": page,
                "bbox": [x0, y0, x1, y1],
                "label": str(region["label"]) if region.get("label") is not None else None,
            }
        )
    return normalized


def _write_redacted_raster_pdf(
    source: Path,
    output: Path,
    reader: PdfReader,
    regions: list[dict[str, Any]],
    fill_color: str,
    render_scale: float,
) -> None:
    if render_scale <= 0:
        raise OKofficeException("unsafe_input_rejected", "render_scale must be greater than zero.")
    color = _parse_fill_color(fill_color)
    document = _pdfium_document(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf_canvas = canvas.Canvas(str(output))
    try:
        for page_index, page in enumerate(reader.pages):
            page_number = page_index + 1
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            page_left = float(page.mediabox.left)
            page_bottom = float(page.mediabox.bottom)
            image = _render_page_image(document, page_index, render_scale)
            draw = _image_draw(image)
            for region in regions:
                if region["page"] != page_number:
                    continue
                draw.rectangle(
                    _pdf_bbox_to_image_rect(
                        region["bbox"],
                        page_left=page_left,
                        page_bottom=page_bottom,
                        page_width=page_width,
                        page_height=page_height,
                        image_width=image.size[0],
                        image_height=image.size[1],
                    ),
                    fill=color,
                )
            image_buffer = BytesIO()
            image.save(image_buffer, format="PNG")
            image_buffer.seek(0)
            pdf_canvas.setPageSize((page_width, page_height))
            pdf_canvas.drawImage(ImageReader(image_buffer), 0, 0, width=page_width, height=page_height)
            pdf_canvas.showPage()
        pdf_canvas.save()
    finally:
        _close_pdfium_document(document)


def _redaction_verification_report(
    input_path: str | Path,
    search_terms: list[str] | None,
) -> tuple[ValidationReport, dict[str, Any], list[str]]:
    source = resolve_input_path(input_path)
    reader = _reader(source)
    text_by_page = [page.extract_text() or "" for page in reader.pages]
    all_text = "\n".join(text_by_page)
    raw_bytes_lower = source.read_bytes().lower()
    terms = [term for term in (search_terms or []) if term]
    checks: list[ValidationCheck] = []
    leaked_terms: list[str] = []

    if not terms:
        text_layer_empty = not all_text.strip()
        checks.append(
            ValidationCheck(
                name="text_layer_absent_or_empty",
                status="passed" if text_layer_empty else "warning",
                details={"text_layer_char_count": len(all_text)},
                message=None if text_layer_empty else "Extractable text remains; provide search terms for leak checks.",
            )
        )
    for term in terms:
        term_lower = term.lower()
        found_pages = [
            page_number
            for page_number, page_text in enumerate(text_by_page, start=1)
            if term_lower in page_text.lower()
        ]
        encoded = term.encode("utf-8", errors="ignore").lower()
        found_in_bytes = bool(encoded and encoded in raw_bytes_lower)
        if found_pages or found_in_bytes:
            leaked_terms.append(term)
        checks.append(
            ValidationCheck(
                name="redaction_text_term_absent",
                status="failed" if found_pages else "passed",
                details={"term": term, "found_pages": found_pages},
                message="Search term remains in the extractable text layer." if found_pages else None,
            )
        )
        checks.append(
            ValidationCheck(
                name="redaction_bytes_term_absent",
                status="failed" if found_in_bytes else "passed",
                details={"term": term, "found_in_pdf_bytes": found_in_bytes},
                message="Search term remains in raw PDF bytes." if found_in_bytes else None,
            )
        )

    warnings = (
        ["Potential redaction leak detected for supplied search terms."]
        if leaked_terms
        else []
    )
    report = ValidationReport(
        status=_validation_status(checks),
        checks=checks,
        page_count=len(reader.pages),
        warnings=warnings,
    )
    usage = {
        "input": str(source),
        "search_terms": terms,
        "search_term_count": len(terms),
        "text_layer_char_count": len(all_text),
        "leaked_terms": leaked_terms,
        "verification_strategy": "extractable_text_and_raw_pdf_byte_search",
        "limitations": [
            "Checks only supplied terms and extractable text/raw bytes.",
            "Image-only sensitive content requires OCR or visual review.",
        ],
    }
    return report, usage, warnings


def _finite_float(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise OKofficeException("unsafe_input_rejected", f"{label} must contain numbers.") from exc
    if not math.isfinite(number):
        raise OKofficeException("unsafe_input_rejected", f"{label} must contain finite numbers.")
    return number


def _parse_fill_color(value: str) -> tuple[int, int, int]:
    try:
        from PIL import ImageColor
    except ImportError as exc:
        raise OKofficeException(
            "dependency_missing",
            "Local redaction requires Pillow for image masking.",
            retry_hint="Install Pillow and retry redaction.",
        ) from exc
    try:
        rgb = ImageColor.getrgb(value)
    except ValueError as exc:
        raise OKofficeException("unsafe_input_rejected", f"Invalid fill color: {value}") from exc
    if len(rgb) == 4:
        return rgb[:3]
    return rgb


def _image_draw(image: Any) -> Any:
    try:
        from PIL import ImageDraw
    except ImportError as exc:
        raise OKofficeException(
            "dependency_missing",
            "Local redaction requires Pillow for image masking.",
            retry_hint="Install Pillow and retry redaction.",
        ) from exc
    return ImageDraw.Draw(image)


def _pdfium_document(path: Path) -> Any:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OKofficeException(
            "dependency_missing",
            "Local redaction requires the pypdfium2 renderer.",
            retry_hint="Install pypdfium2 and retry redaction.",
        ) from exc
    return pdfium.PdfDocument(str(path))


def _render_page_image(document: Any, page_index: int, scale: float) -> Any:
    page = document[page_index]
    bitmap = page.render(scale=scale)
    return bitmap.to_pil().convert("RGB")


def _pdf_bbox_to_image_rect(
    bbox: list[float],
    *,
    page_left: float,
    page_bottom: float,
    page_width: float,
    page_height: float,
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    page_top = page_bottom + page_height
    left = round(((x0 - page_left) / page_width) * image_width)
    right = round(((x1 - page_left) / page_width) * image_width)
    top = round(((page_top - y1) / page_height) * image_height)
    bottom = round(((page_top - y0) / page_height) * image_height)
    return (
        max(0, min(left, image_width)),
        max(0, min(top, image_height)),
        max(0, min(right, image_width)),
        max(0, min(bottom, image_height)),
    )


def _validation_status(checks: list[ValidationCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"


def _close_pdfium_document(document: Any) -> None:
    close = getattr(document, "close", None)
    if callable(close):
        close()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _signature(digest: str, secret: str | None) -> str:
    if secret is None:
        return digest
    return hmac.new(secret.encode("utf-8"), digest.encode("ascii"), hashlib.sha256).hexdigest()


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
