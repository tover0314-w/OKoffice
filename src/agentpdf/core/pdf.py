from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.page_ranges import parse_page_range
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path
from agentpdf.validation.pdf import validate_pdf

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def inspect_pdf(path: str | Path) -> dict[str, Any]:
    resolved = resolve_input_path(path)
    if resolved.suffix.lower() != ".pdf":
        raise AgentPDFException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(resolved)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {resolved}") from exc

    if reader.is_encrypted:
        return {
            "path": str(resolved),
            "encrypted": True,
            "page_count": None,
            "metadata": {},
            "pages": [],
        }

    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        mediabox = page.mediabox
        pages.append(
            {
                "page_number": index,
                "width": float(mediabox.width),
                "height": float(mediabox.height),
                "rotation": int(page.get("/Rotate", 0) or 0),
            }
        )

    metadata = {
        key.lstrip("/"): str(value)
        for key, value in (reader.metadata or {}).items()
        if value is not None
    }
    return {
        "path": str(resolved),
        "encrypted": False,
        "page_count": len(reader.pages),
        "metadata": metadata,
        "pages": pages,
    }


def merge_pdfs(input_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    tool = "pdf.organize.merge"
    writer = PdfWriter()
    total_pages = 0
    for input_path in input_paths:
        resolved = resolve_input_path(input_path)
        reader = _reader_for_operation(resolved)
        for page in reader.pages:
            writer.add_page(page)
            total_pages += 1

    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)

    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=total_pages)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        usage={"input_count": len(input_paths), "page_count": total_pages},
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def split_pdf(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    tool = "pdf.organize.split"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    writer = PdfWriter()
    for page_index in selected_pages:
        writer.add_page(reader.pages[page_index])

    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)

    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(selected_pages))
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "selected_pages": [page + 1 for page in selected_pages],
        },
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def extract_pages_pdf(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    return _write_selected_pages(
        tool="pdf.organize.extract_pages",
        input_path=input_path,
        selected_pages_spec=pages,
        output_path=output_path,
    )


def remove_pages_pdf(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    tool = "pdf.organize.remove_pages"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    removed_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    selected_pages = [index for index in range(len(reader.pages)) if index not in removed_pages]
    if not selected_pages:
        raise AgentPDFException("invalid_page_range", "Removing those pages would create an empty PDF.")
    return _write_pages_by_index(
        tool=tool,
        resolved=resolved,
        reader=reader,
        selected_pages=selected_pages,
        output_path=output_path,
        usage={"input": str(resolved), "removed_pages": [page + 1 for page in sorted(removed_pages)]},
    )


def rotate_pages_pdf(
    input_path: str | Path,
    pages: str,
    degrees: int,
    output_path: str | Path,
) -> ToolResult:
    tool = "pdf.organize.rotate_pages"
    if degrees % 90 != 0:
        raise AgentPDFException(
            "invalid_page_range",
            "Rotation degrees must be a multiple of 90.",
            details={"degrees": degrees},
        )
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index in selected_pages:
            page.rotate(degrees)
        writer.add_page(page)

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
        usage={
            "input": str(resolved),
            "rotated_pages": [page + 1 for page in sorted(selected_pages)],
            "degrees": degrees,
        },
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def image_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    tool = "pdf.convert.image_to_pdf"
    if not image_paths:
        raise AgentPDFException("file_not_found", "At least one input image is required.")

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - reportlab depends on Pillow in normal installs
        raise AgentPDFException("dependency_missing", "Image to PDF requires Pillow.") from exc

    resolved_images = []
    for image_path in image_paths:
        resolved = resolve_input_path(image_path)
        if resolved.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            raise AgentPDFException(
                "unsupported_file_type",
                f"Unsupported image format: {resolved.suffix}",
                details={"supported_suffixes": sorted(SUPPORTED_IMAGE_SUFFIXES)},
            )
        resolved_images.append(resolved)

    output = resolve_output_path(output_path)
    document = canvas.Canvas(str(output))
    for image_path in resolved_images:
        with Image.open(image_path) as raw_image:
            image = raw_image.convert("RGB")
            width, height = image.size
            document.setPageSize((width, height))
            document.drawImage(ImageReader(image), 0, 0, width=width, height=height)
            document.showPage()
    document.save()

    return _result_for_created_pdf(
        tool=tool,
        output=output,
        usage={"input_images": [str(path) for path in resolved_images], "image_count": len(resolved_images)},
        next_tools=["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def add_text_watermark_pdf(
    input_path: str | Path,
    text: str,
    output_path: str | Path,
    pages: str = "all",
    font_size: int = 48,
    opacity: float = 0.18,
    angle: int = 45,
) -> ToolResult:
    tool = "pdf.edit.watermark"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    writer = PdfWriter(clone_from=resolved)

    for index, page in enumerate(writer.pages):
        if index in selected_pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay = _watermark_overlay_page(
                text=text,
                width=width,
                height=height,
                font_size=font_size,
                opacity=opacity,
                angle=angle,
            )
            page.merge_page(overlay)

    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "text": text,
            "pages": [page + 1 for page in sorted(selected_pages)],
            "font_size": font_size,
            "opacity": opacity,
            "angle": angle,
        },
    )


def add_page_numbers_pdf(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
    template: str = "{page}",
    font_size: int = 10,
) -> ToolResult:
    tool = "pdf.edit.page_numbers"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    total = len(reader.pages)
    writer = PdfWriter(clone_from=resolved)

    for index, page in enumerate(writer.pages):
        if index in selected_pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            label = template.format(page=index + 1, total=total)
            page.merge_page(_page_number_overlay_page(label, width, height, font_size=font_size))

    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=total,
        usage={
            "input": str(resolved),
            "pages": [page + 1 for page in sorted(selected_pages)],
            "template": template,
            "font_size": font_size,
        },
    )


def _watermark_overlay_page(
    text: str,
    width: float,
    height: float,
    font_size: int,
    opacity: float,
    angle: int,
) -> Any:
    buffer = BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(width, height))
    overlay.saveState()
    if hasattr(overlay, "setFillAlpha"):
        overlay.setFillAlpha(max(0.0, min(opacity, 1.0)))
    overlay.setFillColorRGB(0.35, 0.35, 0.35)
    overlay.setFont("Helvetica-Bold", font_size)
    overlay.translate(width / 2, height / 2)
    overlay.rotate(angle)
    overlay.drawCentredString(0, 0, text)
    overlay.restoreState()
    overlay.showPage()
    overlay.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _page_number_overlay_page(label: str, width: float, height: float, font_size: int) -> Any:
    buffer = BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(width, height))
    overlay.setFillColorRGB(0.15, 0.15, 0.15)
    overlay.setFont("Helvetica", font_size)
    label_width = overlay.stringWidth(label, "Helvetica", font_size)
    overlay.drawString((width - label_width) / 2, 24, label)
    overlay.showPage()
    overlay.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _write_selected_pages(
    tool: str,
    input_path: str | Path,
    selected_pages_spec: str,
    output_path: str | Path,
) -> ToolResult:
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(selected_pages_spec, total_pages=len(reader.pages))
    return _write_pages_by_index(
        tool=tool,
        resolved=resolved,
        reader=reader,
        selected_pages=selected_pages,
        output_path=output_path,
        usage={
            "input": str(resolved),
            "page_range": selected_pages_spec,
            "selected_pages": [page + 1 for page in selected_pages],
        },
    )


def _write_pages_by_index(
    tool: str,
    resolved: Path,
    reader: PdfReader,
    selected_pages: list[int],
    output_path: str | Path,
    usage: dict[str, Any],
) -> ToolResult:
    writer = PdfWriter()
    for page_index in selected_pages:
        writer.add_page(reader.pages[page_index])

    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)

    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(selected_pages))
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        usage=usage,
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def render_pdf(
    input_path: str | Path,
    pages: str,
    image_format: str,
    out_dir: str | Path,
) -> ToolResult:
    tool = "pdf.convert.pdf_to_images"
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise AgentPDFException(
            "dependency_missing",
            "PDF rendering requires the pypdfium2 optional renderer.",
            retry_hint="Install pypdfium2 and retry render.",
        ) from exc

    normalized_format = image_format.lower()
    if normalized_format == "jpg":
        normalized_format = "jpeg"
    if normalized_format not in {"png", "jpeg", "webp"}:
        raise AgentPDFException(
            "unsupported_file_type",
            f"Unsupported render format: {image_format}",
            details={"supported_formats": ["png", "jpeg", "webp"]},
        )

    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    output_dir = Path(out_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    document = pdfium.PdfDocument(str(resolved))
    artifacts = []
    checks: list[ValidationCheck] = []
    suffix = "jpg" if normalized_format == "jpeg" else normalized_format
    for page_index in selected_pages:
        output = resolve_output_path(
            output_dir / f"{resolved.stem}-page-{page_index + 1:03d}.{suffix}"
        )
        page = document[page_index]
        bitmap = page.render(scale=2)
        image = bitmap.to_pil()
        image.save(output)
        artifact = build_artifact(output, source_tool=tool)
        artifacts.append(artifact)
        checks.append(
            ValidationCheck(
                name="rendered_page",
                status="passed" if artifact.size_bytes > 0 else "failed",
                details={"page": page_index + 1, "path": str(output)},
            )
        )

    validation = ValidationReport(
        status="passed" if all(check.status == "passed" for check in checks) else "failed",
        checks=checks,
        page_count=len(selected_pages),
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=artifacts,
        validation=validation,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "selected_pages": [page + 1 for page in selected_pages],
            "format": normalized_format,
        },
        next_recommended_tools=["pdf.inspect.document"],
    )


def extract_text_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.convert.pdf_to_text"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    page_results: list[dict[str, Any]] = []
    combined: list[str] = []
    warnings: list[str] = []
    for page_index in selected_pages:
        text = reader.pages[page_index].extract_text() or ""
        if not text.strip():
            warnings.append(f"No text extracted from page {page_index + 1}.")
        page_results.append({"page_number": page_index + 1, "text": text})
        combined.append(text)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "pages": page_results,
            "text": "\n".join(combined),
        },
        next_recommended_tools=["pdf.ai.parse.lite", "pdf.ai.rag.ingest"],
    )


def read_metadata_pdf(input_path: str | Path) -> ToolResult:
    tool = "pdf.metadata.read"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        usage={
            "input": str(resolved),
            "metadata": _metadata_to_public_dict(reader.metadata or {}),
            "page_count": len(reader.pages),
        },
        next_recommended_tools=["pdf.metadata.remove", "pdf.security.remove_metadata"],
    )


def update_metadata_pdf(
    input_path: str | Path,
    metadata: dict[str, Any],
    output_path: str | Path,
) -> ToolResult:
    tool = "pdf.metadata.update"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    writer = _writer_from_reader_pages(reader)
    existing = dict(reader.metadata or {})
    existing.update(_metadata_to_pdf_dict(metadata))
    writer.add_metadata({key: str(value) for key, value in existing.items() if value is not None})
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={"input": str(resolved), "metadata": metadata},
    )


def remove_metadata_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.metadata.remove"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    writer = _writer_from_reader_pages(reader)
    writer.add_metadata({})
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={"input": str(resolved), "removed_metadata": True},
    )


def create_text_pdf(text: str, output_path: str | Path, title: str | None = None) -> ToolResult:
    tool = "pdf.convert.text_to_pdf"
    output = resolve_output_path(output_path)
    styles = getSampleStyleSheet()
    story = []
    if title:
        story.append(Paragraph(_escape_paragraph(title), styles["Title"]))
        story.append(Spacer(1, 12))
    for paragraph in _split_paragraphs(text):
        story.append(Paragraph(_escape_paragraph(paragraph), styles["BodyText"]))
        story.append(Spacer(1, 8))
    _build_pdf_document(output, story, title=title)
    return _result_for_created_pdf(
        tool=tool,
        output=output,
        usage={"text_length": len(text), "title": title},
        next_tools=["pdf.inspect.document", "pdf.convert.pdf_to_text"],
    )


def create_markdown_pdf(
    markdown: str,
    output_path: str | Path,
    title: str | None = None,
    style_pack: str = "plain_report",
) -> ToolResult:
    tool = "pdf.convert.markdown_to_pdf"
    output = resolve_output_path(output_path)
    styles = getSampleStyleSheet()
    story = _markdown_to_story(markdown, styles)
    _build_pdf_document(output, story, title=title)
    return _result_for_created_pdf(
        tool=tool,
        output=output,
        usage={"markdown_length": len(markdown), "title": title, "style_pack": style_pack},
        next_tools=["pdf.inspect.document", "pdf.convert.pdf_to_text"],
    )


def _markdown_to_story(markdown: str, styles: Any) -> list[Any]:
    story: list[Any] = []
    bullet_items: list[ListItem] = []

    def flush_bullets() -> None:
        nonlocal bullet_items
        if bullet_items:
            story.append(ListFlowable(bullet_items, bulletType="bullet", leftIndent=18))
            story.append(Spacer(1, 8))
            bullet_items = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_bullets()
            continue
        if line.startswith("# "):
            flush_bullets()
            story.append(Paragraph(_escape_paragraph(line[2:].strip()), styles["Title"]))
            story.append(Spacer(1, 12))
        elif line.startswith("## "):
            flush_bullets()
            story.append(Paragraph(_escape_paragraph(line[3:].strip()), styles["Heading2"]))
            story.append(Spacer(1, 8))
        elif line.startswith("### "):
            flush_bullets()
            story.append(Paragraph(_escape_paragraph(line[4:].strip()), styles["Heading3"]))
            story.append(Spacer(1, 6))
        elif line.startswith(("- ", "* ")):
            bullet_items.append(
                ListItem(Paragraph(_escape_paragraph(line[2:].strip()), styles["BodyText"]))
            )
        elif line.startswith("|"):
            flush_bullets()
            story.append(Paragraph(_escape_paragraph(line), styles["Code"]))
            story.append(Spacer(1, 4))
        else:
            flush_bullets()
            story.append(Paragraph(_escape_paragraph(line), styles["BodyText"]))
            story.append(Spacer(1, 8))
    flush_bullets()
    if not story:
        story.append(Paragraph(" ", styles["BodyText"]))
    return story


def _build_pdf_document(output: Path, story: list[Any], title: str | None = None) -> None:
    document = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        title=title or "okpdf document",
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    document.build(story)


def _result_for_created_pdf(
    tool: str,
    output: Path,
    usage: dict[str, Any],
    next_tools: list[str],
) -> ToolResult:
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=artifact.page_count)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        usage=usage,
        next_recommended_tools=next_tools,
    )


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return paragraphs or [" "]


def _escape_paragraph(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _writer_from_reader_pages(reader: PdfReader) -> PdfWriter:
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    return writer


def _write_writer_output(
    tool: str,
    writer: PdfWriter,
    output_path: str | Path,
    expected_pages: int,
    usage: dict[str, Any],
) -> ToolResult:
    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=expected_pages)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        usage=usage,
        next_recommended_tools=["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def _metadata_to_public_dict(metadata: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in dict(metadata).items():
        if value is not None:
            result[str(key).lstrip("/")] = str(value)
    return result


def _metadata_to_pdf_dict(metadata: dict[str, Any]) -> dict[str, str]:
    return {
        key if str(key).startswith("/") else f"/{key}": str(value)
        for key, value in metadata.items()
        if value is not None
    }


def _reader_for_operation(path: Path) -> PdfReader:
    if path.suffix.lower() != ".pdf":
        raise AgentPDFException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise AgentPDFException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before processing.",
        )
    return reader


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
