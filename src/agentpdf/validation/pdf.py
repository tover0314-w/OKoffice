from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from agentpdf.core.page_ranges import parse_page_range
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path


def validate_pdf(path: str | Path, expected_pages: int | None = None) -> ValidationReport:
    checks: list[ValidationCheck] = []
    resolved = Path(path)
    if not resolved.exists():
        return ValidationReport(
            status="failed",
            checks=[
                ValidationCheck(
                    name="file_exists",
                    status="failed",
                    message=f"Output file does not exist: {resolved}",
                )
            ],
        )

    try:
        reader = PdfReader(resolved)
        page_count = len(reader.pages)
        checks.append(
            ValidationCheck(
                name="parseable_pdf",
                status="passed",
                details={"path": str(resolved)},
            )
        )
    except Exception as exc:
        return ValidationReport(
            status="failed",
            checks=[
                ValidationCheck(
                    name="parseable_pdf",
                    status="failed",
                    message=str(exc),
                )
            ],
        )

    checks.append(
        ValidationCheck(
            name="page_count_nonzero",
            status="passed" if page_count > 0 else "failed",
            details={"page_count": page_count},
        )
    )
    if expected_pages is not None:
        checks.append(
            ValidationCheck(
                name="expected_page_count",
                status="passed" if page_count == expected_pages else "failed",
                details={"expected": expected_pages, "actual": page_count},
            )
        )

    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ValidationReport(status=status, checks=checks, page_count=page_count)


def render_check_pdf(path: str | Path, pages: str = "all") -> tuple[ValidationReport, dict[str, Any]]:
    """Render selected pages in memory and report whether each page is renderable."""
    resolved = resolve_input_path(path)
    reader = _reader_for_validation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    document = _pdfium_document(resolved)

    checks: list[ValidationCheck] = []
    rendered_pages: list[int] = []
    try:
        for page_index in selected_pages:
            try:
                page = document[page_index]
                bitmap = page.render(scale=0.5)
                image = bitmap.to_pil()
                width, height = image.size
                rendered_pages.append(page_index + 1)
                checks.append(
                    ValidationCheck(
                        name="render_page",
                        status="passed" if width > 0 and height > 0 else "failed",
                        details={
                            "page_number": page_index + 1,
                            "width": width,
                            "height": height,
                            "mode": image.mode,
                        },
                    )
                )
            except Exception as exc:
                checks.append(
                    ValidationCheck(
                        name="render_page",
                        status="failed",
                        details={"page_number": page_index + 1},
                        message=str(exc),
                    )
                )
    finally:
        _close_pdfium_document(document)

    report = ValidationReport(
        status="passed" if all(check.status == "passed" for check in checks) else "failed",
        checks=checks,
        page_count=len(selected_pages),
    )
    usage = {
        "input": str(resolved),
        "page_range": pages,
        "rendered_pages": rendered_pages,
    }
    return report, usage


def blank_page_check_pdf(
    path: str | Path,
    pages: str = "all",
    white_threshold: int = 250,
    max_non_white_ratio: float = 0.001,
) -> tuple[ValidationReport, dict[str, Any]]:
    """Detect visually blank selected pages with text-layer and render-based evidence."""
    resolved = resolve_input_path(path)
    reader = _reader_for_validation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    document = _pdfium_document(resolved)

    checks: list[ValidationCheck] = []
    blank_pages: list[int] = []
    non_blank_pages: list[int] = []
    try:
        for page_index in selected_pages:
            page_number = page_index + 1
            text = reader.pages[page_index].extract_text() or ""
            text_present = bool(text.strip())
            try:
                non_white_ratio = _render_non_white_ratio(
                    document,
                    page_index=page_index,
                    white_threshold=white_threshold,
                )
                is_blank = not text_present and non_white_ratio <= max_non_white_ratio
                if is_blank:
                    blank_pages.append(page_number)
                else:
                    non_blank_pages.append(page_number)
                checks.append(
                    ValidationCheck(
                        name="blank_page",
                        status="warning" if is_blank else "passed",
                        details={
                            "page_number": page_number,
                            "blank": is_blank,
                            "text_present": text_present,
                            "non_white_ratio": non_white_ratio,
                            "white_threshold": white_threshold,
                            "max_non_white_ratio": max_non_white_ratio,
                        },
                        message="Page appears blank." if is_blank else None,
                    )
                )
            except Exception as exc:
                checks.append(
                    ValidationCheck(
                        name="blank_page",
                        status="failed",
                        details={"page_number": page_number, "text_present": text_present},
                        message=str(exc),
                    )
                )
    finally:
        _close_pdfium_document(document)

    warnings = (
        [f"Blank pages detected: {', '.join(str(page) for page in blank_pages)}"]
        if blank_pages
        else []
    )
    report = ValidationReport(
        status=_validation_status(checks),
        checks=checks,
        page_count=len(selected_pages),
        warnings=warnings,
    )
    usage = {
        "input": str(resolved),
        "page_range": pages,
        "blank_pages": blank_pages,
        "non_blank_pages": non_blank_pages,
        "white_threshold": white_threshold,
        "max_non_white_ratio": max_non_white_ratio,
    }
    return report, usage


def visual_diff_check_pdf(
    before_path: str | Path,
    after_path: str | Path,
    pages: str = "all",
    max_difference_ratio: float = 0.001,
    render_scale: float = 0.5,
) -> tuple[ValidationReport, dict[str, Any]]:
    """Compare rendered PDF pages and return validation-grade pixel evidence."""
    before = resolve_input_path(before_path)
    after = resolve_input_path(after_path)
    before_reader = _reader_for_validation(before)
    after_reader = _reader_for_validation(after)
    page_count = min(len(before_reader.pages), len(after_reader.pages))
    selected_pages = parse_page_range(pages, total_pages=page_count)
    before_document = _pdfium_document(before)
    after_document = _pdfium_document(after)

    checks: list[ValidationCheck] = []
    changes: list[dict[str, Any]] = []
    try:
        for page_index in selected_pages:
            page_number = page_index + 1
            before_image = _render_page_image(before_document, page_index, render_scale)
            after_image = _render_page_image(after_document, page_index, render_scale)
            size_mismatch = before_image.size != after_image.size
            difference_ratio = (
                1.0
                if size_mismatch
                else _image_difference_ratio(before_image, after_image)
            )
            changed = size_mismatch or difference_ratio > max_difference_ratio
            change = {
                "page_number": page_number,
                "changed": changed,
                "difference_ratio": round(difference_ratio, 6),
                "max_difference_ratio": max_difference_ratio,
                "before_size": list(before_image.size),
                "after_size": list(after_image.size),
                "size_mismatch": size_mismatch,
            }
            changes.append(change)
            checks.append(
                ValidationCheck(
                    name="visual_diff_page",
                    status="warning" if changed else "passed",
                    details=change,
                    message="Rendered page differs." if changed else None,
                )
            )
    finally:
        _close_pdfium_document(before_document)
        _close_pdfium_document(after_document)

    warnings = []
    if len(before_reader.pages) != len(after_reader.pages):
        warnings.append("Input PDFs have different page counts; visual diff used overlapping pages.")
    changed_pages = [change["page_number"] for change in changes if change["changed"]]
    if changed_pages:
        warnings.append(
            "Rendered page differences detected: "
            + ", ".join(str(page) for page in changed_pages)
        )

    report = ValidationReport(
        status=_validation_status(checks),
        checks=checks,
        page_count=len(selected_pages),
        warnings=warnings,
    )
    usage = {
        "before": str(before),
        "after": str(after),
        "page_range": pages,
        "selected_pages": [page + 1 for page in selected_pages],
        "before_page_count": len(before_reader.pages),
        "after_page_count": len(after_reader.pages),
        "changed_page_count": len(changed_pages),
        "changed_pages": changed_pages,
        "changes": changes,
        "max_difference_ratio": max_difference_ratio,
        "render_scale": render_scale,
        "diff_strategy": "local_render_pixel_difference",
        "limitations": [
            "Visual diff uses local rasterized pages and does not explain semantic cause.",
            "Minor antialiasing or renderer differences can appear as pixel changes.",
        ],
    }
    return report, usage


def _reader_for_validation(path: Path) -> PdfReader:
    if path.suffix.lower() != ".pdf":
        raise AgentPDFException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise AgentPDFException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before validation.",
        )
    return reader


def _pdfium_document(path: Path) -> Any:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise AgentPDFException(
            "dependency_missing",
            "Render validation requires the pypdfium2 optional renderer.",
            retry_hint="Install pypdfium2 and retry validation.",
        ) from exc
    return pdfium.PdfDocument(str(path))


def _render_non_white_ratio(document: Any, page_index: int, white_threshold: int) -> float:
    page = document[page_index]
    bitmap = page.render(scale=0.35)
    image = bitmap.to_pil().convert("L")
    histogram = image.histogram()
    total_pixels = image.size[0] * image.size[1]
    if total_pixels == 0:
        return 0.0
    non_white_pixels = sum(count for value, count in enumerate(histogram) if value < white_threshold)
    return non_white_pixels / total_pixels


def _render_page_image(document: Any, page_index: int, scale: float) -> Any:
    page = document[page_index]
    bitmap = page.render(scale=scale)
    return bitmap.to_pil().convert("RGB")


def _image_difference_ratio(before_image: Any, after_image: Any) -> float:
    from PIL import ImageChops

    diff = ImageChops.difference(before_image, after_image).convert("L")
    histogram = diff.histogram()
    total_pixels = diff.size[0] * diff.size[1]
    if total_pixels == 0:
        return 0.0
    changed_pixels = sum(count for value, count in enumerate(histogram) if value > 0)
    return changed_pixels / total_pixels


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
