from __future__ import annotations

import json
import os
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from reportlab.lib import colors as rl_colors
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from okoffice.artifacts.store import build_artifact
from okoffice.core.page_ranges import parse_page_range
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path
from okoffice.validation.pdf import validate_pdf

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
CJK_FONT_PATH_ENV = "AGENTPDF_CJK_FONT_PATH"
CJK_CID_FONT = "STSong-Light"
CJK_FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf"),
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
)
_REGISTERED_CJK_FONTS: tuple[str, str] | None = None
BUILTIN_STYLE_PACKS: dict[str, dict[str, Any]] = {
    "plain_report": {
        "style_id": "plain_report",
        "name": "Plain Report",
        "description": "Readable default report styling for local PDF creation.",
        "page": {
            "size": "letter",
            "orientation": "portrait",
            "margins": {"top": 54, "right": 54, "bottom": 54, "left": 54},
        },
        "typography": {
            "heading_font": "system-sans",
            "body_font": "system-sans",
            "base_size": 10,
        },
        "colors": {"primary": "#111827", "accent": "#2563eb", "text": "#111827"},
        "components": ["section_header", "bullet_list", "table"],
    },
    "business_report_modern": {
        "style_id": "business_report_modern",
        "name": "Business Report Modern",
        "description": "Clean board-report style with section hierarchy and muted blue accents.",
        "page": {
            "size": "A4",
            "orientation": "portrait",
            "margins": {"top": 56, "right": 56, "bottom": 56, "left": 56},
        },
        "typography": {
            "heading_font": "system-sans",
            "body_font": "system-sans",
            "base_size": 10,
        },
        "colors": {"primary": "#1f3a5f", "accent": "#6b8fb3", "text": "#111827"},
        "components": ["cover", "toc", "section_header", "metric_card", "table", "callout"],
    },
    "academic_paper_basic": {
        "style_id": "academic_paper_basic",
        "name": "Academic Paper Basic",
        "description": "Conservative serif layout for papers and research notes.",
        "page": {
            "size": "letter",
            "orientation": "portrait",
            "margins": {"top": 60, "right": 60, "bottom": 60, "left": 60},
        },
        "typography": {"heading_font": "serif", "body_font": "serif", "base_size": 10},
        "colors": {"primary": "#111827", "accent": "#374151", "text": "#111827"},
        "components": ["section_header", "table", "appendix"],
    },
    "resume_modern": {
        "style_id": "resume_modern",
        "name": "Resume Modern",
        "description": "Compact resume layout with strong section headers.",
        "page": {
            "size": "letter",
            "orientation": "portrait",
            "margins": {"top": 42, "right": 48, "bottom": 42, "left": 48},
        },
        "typography": {
            "heading_font": "system-sans",
            "body_font": "system-sans",
            "base_size": 9,
        },
        "colors": {"primary": "#0f766e", "accent": "#475569", "text": "#0f172a"},
        "components": ["section_header", "bullet_list"],
    },
    "invoice_clean": {
        "style_id": "invoice_clean",
        "name": "Invoice Clean",
        "description": "Simple invoice/report layout with restrained green accents.",
        "page": {
            "size": "letter",
            "orientation": "portrait",
            "margins": {"top": 48, "right": 54, "bottom": 48, "left": 54},
        },
        "typography": {
            "heading_font": "system-sans",
            "body_font": "system-sans",
            "base_size": 10,
        },
        "colors": {"primary": "#166534", "accent": "#94a3b8", "text": "#111827"},
        "components": ["table", "section_header"],
    },
    "paper_ink": {
        "style_id": "paper_ink",
        "name": "Paper Ink",
        "description": "Polished document template style for agent-created briefs and worksheets.",
        "page": {
            "size": "A4",
            "orientation": "portrait",
            "margins": {"top": 50, "right": 54, "bottom": 54, "left": 54},
        },
        "typography": {
            "heading_font": "system-sans",
            "body_font": "system-sans",
            "base_size": 10,
        },
        "colors": {"primary": "#20314f", "accent": "#2f7d6d", "text": "#1f2937"},
        "components": ["cover", "section_header", "callout", "worksheet_prompt", "checklist"],
    },
}


def inspect_pdf(path: str | Path) -> dict[str, Any]:
    resolved = resolve_input_path(path)
    if resolved.suffix.lower() != ".pdf":
        raise OKofficeException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(resolved)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {resolved}") from exc

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


def inspect_pdf_pages(path: str | Path, pages: str = "all") -> dict[str, Any]:
    resolved = resolve_input_path(path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    page_results: list[dict[str, Any]] = []
    warnings: list[str] = []

    for page_index in selected_pages:
        page = reader.pages[page_index]
        try:
            text = page.extract_text() or ""
            text_error = None
        except Exception as exc:
            text = ""
            text_error = str(exc)
            warnings.append(f"Text extraction failed on page {page_index + 1}.")

        mediabox = page.mediabox
        page_payload: dict[str, Any] = {
            "page_number": page_index + 1,
            "width": float(mediabox.width),
            "height": float(mediabox.height),
            "rotation": int(page.get("/Rotate", 0) or 0),
            "has_text_layer": bool(text.strip()),
            "text_char_count": len(text),
            "image_count": _count_page_images(page),
        }
        if text_error:
            page_payload["text_error"] = text_error
        page_results.append(page_payload)

    return {
        "input": str(resolved),
        "page_count": len(reader.pages),
        "page_range": pages,
        "selected_pages": [page + 1 for page in selected_pages],
        "pages": page_results,
        "warnings": warnings,
    }


def page_info_pdf(path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.metadata.page_info"
    info = inspect_pdf_pages(path, pages=pages)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=list(info.get("warnings", [])),
        usage=info,
        next_recommended_tools=["pdf.inspect.pages", "pdf.validation.render_check"],
    )


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
        raise OKofficeException("invalid_page_range", "Removing those pages would create an empty PDF.")
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
        raise OKofficeException(
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


def reorder_pages_pdf(input_path: str | Path, order: str, output_path: str | Path) -> ToolResult:
    tool = "pdf.organize.reorder_pages"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(order, total_pages=len(reader.pages))
    expected_pages = set(range(len(reader.pages)))
    if set(selected_pages) != expected_pages or len(selected_pages) != len(reader.pages):
        raise OKofficeException(
            "invalid_page_range",
            "Reorder must include every page exactly once.",
            details={
                "page_count": len(reader.pages),
                "selected_pages": [page + 1 for page in selected_pages],
            },
        )
    return _write_pages_by_index(
        tool=tool,
        resolved=resolved,
        reader=reader,
        selected_pages=selected_pages,
        output_path=output_path,
        usage={"input": str(resolved), "order": [page + 1 for page in selected_pages]},
    )


def insert_blank_pages_pdf(
    input_path: str | Path,
    after_page: int,
    count: int,
    output_path: str | Path,
) -> ToolResult:
    tool = "pdf.organize.insert_blank_pages"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    total_pages = len(reader.pages)
    if after_page < 0 or after_page > total_pages:
        raise OKofficeException(
            "invalid_page_range",
            f"after_page must be between 0 and {total_pages}.",
            details={"after_page": after_page, "page_count": total_pages},
        )
    if count < 1:
        raise OKofficeException(
            "invalid_page_range",
            "Blank page count must be at least 1.",
            details={"count": count},
        )

    size_page = reader.pages[after_page - 1] if after_page > 0 else reader.pages[0]
    width = float(size_page.mediabox.width)
    height = float(size_page.mediabox.height)
    writer = PdfWriter()
    if after_page == 0:
        _add_blank_pages(writer, count=count, width=width, height=height)
    for index, page in enumerate(reader.pages, start=1):
        writer.add_page(page)
        if index == after_page:
            _add_blank_pages(writer, count=count, width=width, height=height)

    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=total_pages + count,
        usage={
            "input": str(resolved),
            "after_page": after_page,
            "blank_page_count": count,
            "page_size": {"width": width, "height": height},
        },
    )


def n_up_pdf(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
    per_sheet: int = 2,
) -> ToolResult:
    tool = "pdf.organize.n_up"
    if per_sheet not in {2, 4}:
        raise OKofficeException(
            "invalid_input",
            "n-up per_sheet must be 2 or 4 in the local OSS implementation.",
            details={"per_sheet": per_sheet},
        )
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    if not selected_pages:
        raise OKofficeException("invalid_page_range", "n-up requires at least one source page.")

    first_page = reader.pages[selected_pages[0]]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)
    columns, rows = (2, 1) if per_sheet == 2 else (2, 2)
    writer = PdfWriter()
    for chunk_start in range(0, len(selected_pages), per_sheet):
        sheet = writer.add_blank_page(width=width, height=height)
        for slot, page_index in enumerate(selected_pages[chunk_start : chunk_start + per_sheet]):
            _merge_page_into_n_up_slot(
                sheet,
                reader.pages[page_index],
                slot=slot,
                columns=columns,
                rows=rows,
                output_width=width,
                output_height=height,
            )

    output_pages = (len(selected_pages) + per_sheet - 1) // per_sheet
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=output_pages,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "source_pages": [page + 1 for page in selected_pages],
            "per_sheet": per_sheet,
            "layout": {"columns": columns, "rows": rows},
            "output_pages": output_pages,
            "page_size": {"width": width, "height": height},
        },
        next_recommended_tools=["pdf.validation.render_check", "pdf.validation.page_count_check"],
    )


def booklet_pdf(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.organize.booklet"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    if not selected_pages:
        raise OKofficeException("invalid_page_range", "Booklet imposition requires at least one page.")

    padded: list[int | None] = list(selected_pages)
    while len(padded) % 4 != 0:
        padded.append(None)
    signature_order: list[int | None] = []
    left = 0
    right = len(padded) - 1
    while left < right:
        signature_order.extend([padded[right], padded[left], padded[left + 1], padded[right - 1]])
        left += 2
        right -= 2

    first_page = reader.pages[selected_pages[0]]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)
    writer = PdfWriter()
    for chunk_start in range(0, len(signature_order), 2):
        sheet = writer.add_blank_page(width=width, height=height)
        for slot, page_index in enumerate(signature_order[chunk_start : chunk_start + 2]):
            if page_index is None:
                continue
            _merge_page_into_n_up_slot(
                sheet,
                reader.pages[page_index],
                slot=slot,
                columns=2,
                rows=1,
                output_width=width,
                output_height=height,
            )

    output_pages = len(signature_order) // 2
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=output_pages,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "source_pages": [page + 1 for page in selected_pages],
            "padded_page_count": len(padded),
            "signature_order": [page + 1 if page is not None else None for page in signature_order],
            "output_pages": output_pages,
            "layout": {"columns": 2, "rows": 1},
            "page_size": {"width": width, "height": height},
        },
        next_recommended_tools=["pdf.validation.render_check", "pdf.validation.page_count_check"],
    )


def compress_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.optimize.compress"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    writer = PdfWriter()
    compressed_streams = 0
    for page in reader.pages:
        writer.add_page(page)
        writer_page = writer.pages[-1]
        compress = getattr(writer_page, "compress_content_streams", None)
        if callable(compress):
            compress()
            compressed_streams += 1
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))

    output = resolve_output_path(output_path)
    with output.open("wb") as handle:
        writer.write(handle)

    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=len(reader.pages))
    original_size = resolved.stat().st_size
    output_size = artifact.size_bytes
    bytes_saved = original_size - output_size
    warnings = [] if bytes_saved > 0 else ["Output is not smaller; source may already be compressed."]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=warnings,
        usage={
            "input": str(resolved),
            "original_size_bytes": original_size,
            "output_size_bytes": output_size,
            "bytes_saved": bytes_saved,
            "compression_ratio": output_size / original_size if original_size else None,
            "compressed_content_streams": compressed_streams,
        },
        next_recommended_tools=["pdf.validation.validate_output", "pdf.validation.render_check"],
    )


def repair_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.optimize.repair"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    writer = _writer_from_reader_pages(reader)
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "repair_strategy": "pypdf_read_rewrite",
            "page_count": len(reader.pages),
        },
    )


def remove_unused_objects_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.optimize.remove_unused_objects"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    writer = _writer_from_reader_pages(reader)
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))

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
            "rewrite_strategy": "pypdf_reachable_page_tree",
            "page_count": len(reader.pages),
            "original_size_bytes": resolved.stat().st_size,
            "output_size_bytes": artifact.size_bytes,
            "estimated_original_object_count": _estimate_pdf_object_count(reader),
            "note": "The local implementation rewrites the reachable page tree; it does not run qpdf object-stream optimization.",
        },
        next_recommended_tools=["pdf.optimize.compress", "pdf.validation.render_check"],
    )


def validate_pdfa_pdf(input_path: str | Path) -> ToolResult:
    tool = "pdf.optimize.validate_pdfa"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    raw = resolved.read_bytes()
    lower_raw = raw.lower()
    has_pdfa_marker = b"pdfaid:part" in lower_raw or b"pdfaid:conformance" in lower_raw
    output_intents = reader.trailer.get("/Root", {}).get("/OutputIntents")
    has_output_intent = bool(output_intents)
    fonts = _collect_font_records(reader, list(range(len(reader.pages))))
    unembedded_fonts = [font for font in fonts if not font["embedded"]]
    profile = _detect_pdfa_profile(raw)
    checks = [
        ValidationCheck(
            name="pdfa_metadata_marker",
            status="passed" if has_pdfa_marker else "warning",
            details={"profile": profile},
            message=None if has_pdfa_marker else "No PDF/A XMP identification marker was found.",
        ),
        ValidationCheck(
            name="pdfa_output_intent",
            status="passed" if has_output_intent else "warning",
            details={"output_intent_count": len(output_intents) if output_intents else 0},
            message=None if has_output_intent else "No PDF/A output intent was found.",
        ),
        ValidationCheck(
            name="pdfa_font_embedding_heuristic",
            status="passed" if not unembedded_fonts else "warning",
            details={
                "font_count": len(fonts),
                "unembedded_fonts": [font["base_font"] for font in unembedded_fonts],
            },
            message=None if not unembedded_fonts else "Some fonts appear unembedded.",
        ),
    ]
    compliant = all(check.status == "passed" for check in checks)
    validation = ValidationReport(
        status="passed" if compliant else "warning",
        checks=checks,
        page_count=len(reader.pages),
        warnings=[] if compliant else ["Local PDF/A validation is heuristic; use veraPDF for certification."],
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        validation=validation,
        warnings=validation.warnings,
        usage={
            "input": str(resolved),
            "pdfa_compliant": compliant,
            "profile": profile,
            "page_count": len(reader.pages),
            "font_count": len(fonts),
            "unembedded_font_count": len(unembedded_fonts),
            "validator": "okoffice_local_pdfa_heuristic",
        },
        next_recommended_tools=["pdf.optimize.to_pdfa", "pdf.convert.extract_fonts"],
    )


def image_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    tool = "pdf.convert.image_to_pdf"
    if not image_paths:
        raise OKofficeException("file_not_found", "At least one input image is required.")

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - reportlab depends on Pillow in normal installs
        raise OKofficeException("dependency_missing", "Image to PDF requires Pillow.") from exc

    resolved_images = []
    for image_path in image_paths:
        resolved = resolve_input_path(image_path)
        if resolved.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            raise OKofficeException(
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


def extract_fonts_pdf(input_path: str | Path, pages: str = "all") -> ToolResult:
    tool = "pdf.convert.extract_fonts"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    fonts = _collect_font_records(reader, selected_pages)
    warnings = []
    if not fonts:
        warnings.append("No page fonts were found in selected pages.")
    if any(not font["embedded"] for font in fonts):
        warnings.append("Some fonts appear to be referenced by base name rather than embedded.")
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "selected_pages": [page + 1 for page in selected_pages],
            "font_count": len(fonts),
            "fonts": fonts,
        },
        next_recommended_tools=["pdf.optimize.validate_pdfa", "pdf.optimize.subset_fonts"],
    )


def add_shape_pdf(
    input_path: str | Path,
    output_path: str | Path,
    shape: str,
    page: int,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: str = "#2563eb",
    fill_color: str | None = None,
    line_width: float = 1.5,
    opacity: float = 1.0,
) -> ToolResult:
    tool = "pdf.edit.add_shape"
    normalized_shape = shape.lower().strip()
    if normalized_shape not in {"rectangle", "line", "circle", "ellipse"}:
        raise OKofficeException(
            "invalid_input",
            "shape must be one of rectangle, line, circle, or ellipse.",
            details={"shape": shape},
        )
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    page_index = _validate_one_based_page(page, len(reader.pages))
    writer = PdfWriter(clone_from=resolved)
    target_page = writer.pages[page_index]
    overlay = _shape_overlay_page(
        shape=normalized_shape,
        page_width=float(target_page.mediabox.width),
        page_height=float(target_page.mediabox.height),
        x=float(x),
        y=float(y),
        width=float(width),
        height=float(height),
        stroke_color=stroke_color,
        fill_color=fill_color,
        line_width=float(line_width),
        opacity=float(opacity),
    )
    target_page.merge_page(overlay)
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "page": page,
            "shape": normalized_shape,
            "bbox": [float(x), float(y), float(x) + float(width), float(y) + float(height)],
            "stroke_color": stroke_color,
            "fill_color": fill_color,
            "line_width": float(line_width),
            "opacity": max(0.0, min(float(opacity), 1.0)),
        },
    )


def underline_pdf(
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    bbox: list[float] | tuple[float, float, float, float],
    color: str = "#2563eb",
    line_width: float = 1.0,
) -> ToolResult:
    return _mark_bbox_line_pdf(
        tool="pdf.edit.underline",
        input_path=input_path,
        output_path=output_path,
        page=page,
        bbox=bbox,
        color=color,
        line_width=line_width,
        line_position="underline",
    )


def strikeout_pdf(
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    bbox: list[float] | tuple[float, float, float, float],
    color: str = "#dc2626",
    line_width: float = 1.0,
) -> ToolResult:
    return _mark_bbox_line_pdf(
        tool="pdf.edit.strikeout",
        input_path=input_path,
        output_path=output_path,
        page=page,
        bbox=bbox,
        color=color,
        line_width=line_width,
        line_position="middle",
    )


def freehand_draw_pdf(
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    points: list[list[float]] | list[tuple[float, float]],
    stroke_color: str = "#2563eb",
    line_width: float = 1.5,
    opacity: float = 1.0,
) -> ToolResult:
    tool = "pdf.edit.freehand_draw"
    normalized_points = _normalize_points(points)
    if len(normalized_points) < 2:
        raise OKofficeException("invalid_input", "freehand drawing requires at least two points.")
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    page_index = _validate_one_based_page(page, len(reader.pages))
    writer = PdfWriter(clone_from=resolved)
    target_page = writer.pages[page_index]
    overlay = _freehand_overlay_page(
        page_width=float(target_page.mediabox.width),
        page_height=float(target_page.mediabox.height),
        points=normalized_points,
        stroke_color=stroke_color,
        line_width=float(line_width),
        opacity=float(opacity),
    )
    target_page.merge_page(overlay)
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "page": page,
            "point_count": len(normalized_points),
            "points": normalized_points,
            "stroke_color": stroke_color,
            "line_width": float(line_width),
            "opacity": max(0.0, min(float(opacity), 1.0)),
        },
    )


def resize_pages_pdf(
    input_path: str | Path,
    output_path: str | Path,
    width: float,
    height: float,
    pages: str = "all",
) -> ToolResult:
    tool = "pdf.edit.resize_pages"
    if width <= 0 or height <= 0:
        raise OKofficeException("invalid_input", "width and height must be positive.")
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    writer = PdfWriter()
    scale_records = []
    for index, source_page in enumerate(reader.pages):
        if index not in selected_pages:
            writer.add_page(source_page)
            continue
        source_width = float(source_page.mediabox.width)
        source_height = float(source_page.mediabox.height)
        scale = min(float(width) / source_width, float(height) / source_height)
        tx = (float(width) - source_width * scale) / 2
        ty = (float(height) - source_height * scale) / 2
        resized = writer.add_blank_page(width=float(width), height=float(height))
        resized.merge_transformed_page(deepcopy(source_page), Transformation().scale(scale).translate(tx, ty))
        scale_records.append({"page": index + 1, "scale": scale, "translate": [tx, ty]})
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "page_range": pages,
            "resized_pages": [page + 1 for page in sorted(selected_pages)],
            "target_size": {"width": float(width), "height": float(height)},
            "placements": scale_records,
        },
    )


def add_margin_pdf(
    input_path: str | Path,
    output_path: str | Path,
    margin: float = 0,
    pages: str = "all",
    top: float | None = None,
    right: float | None = None,
    bottom: float | None = None,
    left: float | None = None,
) -> ToolResult:
    tool = "pdf.edit.add_margin"
    margins = {
        "top": float(margin if top is None else top),
        "right": float(margin if right is None else right),
        "bottom": float(margin if bottom is None else bottom),
        "left": float(margin if left is None else left),
    }
    if any(value < 0 for value in margins.values()):
        raise OKofficeException("invalid_input", "Margins must be zero or positive.")
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    writer = PdfWriter()
    page_sizes = []
    for index, source_page in enumerate(reader.pages):
        if index not in selected_pages:
            writer.add_page(source_page)
            continue
        source_width = float(source_page.mediabox.width)
        source_height = float(source_page.mediabox.height)
        new_width = source_width + margins["left"] + margins["right"]
        new_height = source_height + margins["top"] + margins["bottom"]
        target = writer.add_blank_page(width=new_width, height=new_height)
        target.merge_transformed_page(
            deepcopy(source_page),
            Transformation().translate(margins["left"], margins["bottom"]),
        )
        page_sizes.append(
            {
                "page": index + 1,
                "source_size": {"width": source_width, "height": source_height},
                "output_size": {"width": new_width, "height": new_height},
            }
        )
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "page_range": pages,
            "margins": margins,
            "pages": page_sizes,
        },
    )


def add_underlay_pdf(
    input_path: str | Path,
    output_path: str | Path,
    text: str,
    pages: str = "all",
    font_size: int = 72,
    opacity: float = 0.12,
    angle: int = 45,
    color: str = "#64748b",
) -> ToolResult:
    tool = "pdf.edit.underlay"
    if not text:
        raise OKofficeException("invalid_input", "underlay text must not be empty.")
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = set(parse_page_range(pages, total_pages=len(reader.pages)))
    writer = PdfWriter()
    for index, source_page in enumerate(reader.pages):
        if index not in selected_pages:
            writer.add_page(source_page)
            continue
        width = float(source_page.mediabox.width)
        height = float(source_page.mediabox.height)
        underlay = _text_mark_overlay_page(
            text=text,
            width=width,
            height=height,
            font_size=font_size,
            opacity=opacity,
            angle=angle,
            color=color,
        )
        underlay.merge_page(deepcopy(source_page))
        writer.add_page(underlay)
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "page_range": pages,
            "pages": [page + 1 for page in sorted(selected_pages)],
            "text": text,
            "font_size": font_size,
            "opacity": max(0.0, min(float(opacity), 1.0)),
            "angle": angle,
            "color": color,
        },
        next_recommended_tools=["pdf.validation.render_check", "pdf.inspect.pages"],
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


def _shape_overlay_page(
    shape: str,
    page_width: float,
    page_height: float,
    x: float,
    y: float,
    width: float,
    height: float,
    stroke_color: str,
    fill_color: str | None,
    line_width: float,
    opacity: float,
) -> Any:
    buffer = BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    overlay.saveState()
    _apply_canvas_alpha(overlay, opacity)
    overlay.setStrokeColor(_hex_color(stroke_color))
    overlay.setLineWidth(max(line_width, 0.1))
    if fill_color:
        overlay.setFillColor(_hex_color(fill_color))
    else:
        overlay.setFillColor(rl_colors.transparent)
    if shape == "rectangle":
        overlay.rect(x, y, width, height, fill=1 if fill_color else 0, stroke=1)
    elif shape == "line":
        overlay.line(x, y, x + width, y + height)
    elif shape == "circle":
        radius = min(abs(width), abs(height)) / 2
        overlay.circle(x + width / 2, y + height / 2, radius, fill=1 if fill_color else 0, stroke=1)
    else:
        overlay.ellipse(x, y, x + width, y + height, fill=1 if fill_color else 0, stroke=1)
    overlay.restoreState()
    overlay.showPage()
    overlay.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _bbox_line_overlay_page(
    page_width: float,
    page_height: float,
    bbox: list[float],
    color: str,
    line_width: float,
    line_position: str,
) -> Any:
    x0, y0, x1, y1 = bbox
    y = y0 if line_position == "underline" else y0 + (y1 - y0) * 0.55
    buffer = BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    overlay.setStrokeColor(_hex_color(color))
    overlay.setLineWidth(max(line_width, 0.1))
    overlay.line(x0, y, x1, y)
    overlay.showPage()
    overlay.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _freehand_overlay_page(
    page_width: float,
    page_height: float,
    points: list[list[float]],
    stroke_color: str,
    line_width: float,
    opacity: float,
) -> Any:
    buffer = BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    overlay.saveState()
    _apply_canvas_alpha(overlay, opacity)
    overlay.setStrokeColor(_hex_color(stroke_color))
    overlay.setLineWidth(max(line_width, 0.1))
    path = overlay.beginPath()
    path.moveTo(points[0][0], points[0][1])
    for x, y in points[1:]:
        path.lineTo(x, y)
    overlay.drawPath(path, stroke=1, fill=0)
    overlay.restoreState()
    overlay.showPage()
    overlay.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _text_mark_overlay_page(
    text: str,
    width: float,
    height: float,
    font_size: int,
    opacity: float,
    angle: int,
    color: str,
) -> Any:
    buffer = BytesIO()
    overlay = canvas.Canvas(buffer, pagesize=(width, height))
    overlay.saveState()
    _apply_canvas_alpha(overlay, opacity)
    overlay.setFillColor(_hex_color(color))
    overlay.setFont("Helvetica-Bold", font_size)
    overlay.translate(width / 2, height / 2)
    overlay.rotate(angle)
    overlay.drawCentredString(0, 0, text)
    overlay.restoreState()
    overlay.showPage()
    overlay.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _mark_bbox_line_pdf(
    tool: str,
    input_path: str | Path,
    output_path: str | Path,
    page: int,
    bbox: list[float] | tuple[float, float, float, float],
    color: str,
    line_width: float,
    line_position: str,
) -> ToolResult:
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    page_index = _validate_one_based_page(page, len(reader.pages))
    normalized_bbox = _normalize_bbox(bbox)
    writer = PdfWriter(clone_from=resolved)
    target_page = writer.pages[page_index]
    overlay = _bbox_line_overlay_page(
        page_width=float(target_page.mediabox.width),
        page_height=float(target_page.mediabox.height),
        bbox=normalized_bbox,
        color=color,
        line_width=float(line_width),
        line_position=line_position,
    )
    target_page.merge_page(overlay)
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "page": page,
            "bbox": normalized_bbox,
            "color": color,
            "line_width": float(line_width),
        },
    )


def _apply_canvas_alpha(document: canvas.Canvas, opacity: float) -> None:
    if hasattr(document, "setFillAlpha"):
        bounded = max(0.0, min(float(opacity), 1.0))
        document.setFillAlpha(bounded)
        document.setStrokeAlpha(bounded)


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


def _add_blank_pages(writer: PdfWriter, count: int, width: float, height: float) -> None:
    for _ in range(count):
        writer.add_blank_page(width=width, height=height)


def _merge_page_into_n_up_slot(
    sheet: Any,
    source_page: Any,
    slot: int,
    columns: int,
    rows: int,
    output_width: float,
    output_height: float,
) -> None:
    cell_width = output_width / columns
    cell_height = output_height / rows
    source_width = float(source_page.mediabox.width)
    source_height = float(source_page.mediabox.height)
    scale = min(cell_width / source_width, cell_height / source_height)
    scaled_width = source_width * scale
    scaled_height = source_height * scale
    column = slot % columns
    row = slot // columns
    x = column * cell_width + (cell_width - scaled_width) / 2
    y = output_height - ((row + 1) * cell_height) + (cell_height - scaled_height) / 2
    page = deepcopy(source_page)
    transform = Transformation().scale(scale).translate(x, y)
    sheet.merge_transformed_page(page, transform)


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
        raise OKofficeException(
            "dependency_missing",
            "PDF rendering requires the pypdfium2 optional renderer.",
            retry_hint="Install pypdfium2 and retry render.",
        ) from exc

    normalized_format = image_format.lower()
    if normalized_format == "jpg":
        normalized_format = "jpeg"
    if normalized_format not in {"png", "jpeg", "webp"}:
        raise OKofficeException(
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


def extract_images_pdf(
    input_path: str | Path,
    pages: str = "all",
    out_dir: str | Path = "extracted-images",
) -> ToolResult:
    tool = "pdf.convert.extract_images"
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    output_dir = Path(out_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = []
    image_records: list[dict[str, Any]] = []
    warnings: list[str] = []
    for page_index in selected_pages:
        page_number = page_index + 1
        page_images = list(getattr(reader.pages[page_index], "images", []))
        if not page_images:
            warnings.append(f"No embedded images found on page {page_number}.")
            continue
        for image_index, image_file in enumerate(page_images, start=1):
            pil_image = getattr(image_file, "image", None)
            if pil_image is None:
                warnings.append(f"Image {image_index} on page {page_number} could not be decoded.")
                continue
            suffix = _image_suffix(image_file, pil_image)
            output = resolve_output_path(
                output_dir / f"{resolved.stem}-page-{page_number:03d}-image-{image_index:03d}{suffix}"
            )
            pil_image.save(output)
            artifact = build_artifact(output, source_tool=tool)
            artifacts.append(artifact)
            image_records.append(
                {
                    "page_number": page_number,
                    "image_index": image_index,
                    "path": str(output),
                    "artifact_id": artifact.artifact_id,
                    "mime_type": artifact.mime_type,
                    "width": int(pil_image.width),
                    "height": int(pil_image.height),
                    "source_name": str(getattr(image_file, "name", "")),
                }
            )

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={
            "input": str(resolved),
            "page_range": pages,
            "selected_pages": [page + 1 for page in selected_pages],
            "image_count": len(image_records),
            "images": image_records,
            "out_dir": str(output_dir),
        },
        next_recommended_tools=["pdf.inspect.pages", "pdf.ai.parse.lite"],
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


def update_outline_pdf(
    input_path: str | Path,
    outline: list[dict[str, Any]],
    output_path: str | Path,
) -> ToolResult:
    tool = "pdf.metadata.update_outline"
    if not outline:
        raise OKofficeException("invalid_input", "outline must include at least one item.")
    resolved = resolve_input_path(input_path)
    reader = _reader_for_operation(resolved)
    writer = _writer_from_reader_pages(reader)
    if reader.metadata:
        writer.add_metadata(_metadata_to_pdf_dict(_metadata_to_public_dict(reader.metadata)))
    item_count = _add_outline_items(writer, outline, page_count=len(reader.pages))
    return _write_writer_output(
        tool=tool,
        writer=writer,
        output_path=output_path,
        expected_pages=len(reader.pages),
        usage={
            "input": str(resolved),
            "outline_item_count": item_count,
            "outline": outline,
        },
        next_recommended_tools=["pdf.metadata.read", "pdf.validation.render_check"],
    )


def remove_metadata_pdf(
    input_path: str | Path,
    output_path: str | Path,
    tool: str = "pdf.metadata.remove",
) -> ToolResult:
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
    requires_cjk = _requires_cjk_font(text, title)
    _apply_cjk_to_basic_styles(styles, requires_cjk=requires_cjk)
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
        usage={"text_length": len(text), "title": title, "requires_cjk_font": requires_cjk},
        next_tools=["pdf.inspect.document", "pdf.convert.pdf_to_text"],
        source_text=f"{title or ''}\n{text}",
    )


def create_markdown_pdf(
    markdown: str,
    output_path: str | Path,
    title: str | None = None,
    style_pack: str | dict[str, Any] = "plain_report",
) -> ToolResult:
    tool = "pdf.convert.markdown_to_pdf"
    output = resolve_output_path(output_path)
    resolved_style = _resolve_style_pack(style_pack)
    styles = getSampleStyleSheet()
    requires_cjk = _requires_cjk_font(markdown, title)
    _apply_style_pack(styles, resolved_style["pack"], requires_cjk=requires_cjk)
    story = _markdown_to_story(markdown, styles)
    page_size = _style_page_size(resolved_style["pack"])
    margins = _style_margins(resolved_style["pack"])
    _build_pdf_document(
        output,
        story,
        title=title,
        page_size=page_size,
        margins=margins,
    )
    return _result_for_created_pdf(
        tool=tool,
        output=output,
        usage={
            "markdown_length": len(markdown),
            "title": title,
            "style_pack": resolved_style["pack"]["style_id"],
            "style_pack_name": resolved_style["pack"].get("name"),
            "style_pack_source": resolved_style["source"],
            "page": resolved_style["pack"].get("page", {}),
            "colors": resolved_style["pack"].get("colors", {}),
            "components": resolved_style["pack"].get("components", []),
            "requires_cjk_font": requires_cjk,
        },
        next_tools=["pdf.inspect.document", "pdf.convert.pdf_to_text"],
        source_text=f"{title or ''}\n{markdown}",
    )


def create_slide_deck_pdf(
    slides: list[dict[str, Any]],
    output_path: str | Path,
    title: str | None = None,
    style_pack: str | dict[str, Any] = "paper_ink",
) -> ToolResult:
    tool = "pdf.compose.render_slides"
    if not slides:
        raise OKofficeException("invalid_input", "Slide deck must include at least one slide.")
    output = resolve_output_path(output_path)
    resolved_style = _resolve_style_pack(style_pack)
    pack = resolved_style["pack"]
    deck_text = _slide_deck_text(slides, title)
    requires_cjk = _requires_cjk_font(deck_text)
    body_font, heading_font = _canvas_font_pair(requires_cjk=requires_cjk)
    code_font = body_font if requires_cjk else "Courier"
    colors = pack.get("colors", {})
    primary = _hex_color(str(colors.get("primary", "#20314f")))
    accent = _hex_color(str(colors.get("accent", "#2f7d6d")))
    text_color = _hex_color(str(colors.get("text", "#1f2937")))
    page_size = landscape(letter)
    document = canvas.Canvas(str(output), pagesize=page_size)
    document.setTitle(title or "okoffice slide deck")
    width, height = page_size

    for index, slide in enumerate(slides, start=1):
        document.setFillColor(HexColor("#ffffff"))
        document.rect(0, 0, width, height, fill=1, stroke=0)
        document.setFillColor(primary)
        document.setFont(heading_font, 25)
        document.drawString(42, height - 54, str(slide.get("title") or f"Slide {index}"))
        document.setStrokeColor(accent)
        document.setLineWidth(2)
        document.line(42, height - 68, width - 42, height - 68)

        y = height - 96
        subtitle = str(slide.get("subtitle") or "")
        if subtitle:
            document.setFillColor(accent)
            document.setFont(body_font, 12)
            y = _draw_wrapped_lines(document, subtitle, 42, y, width - 84, 15, body_font, 12)
            y -= 8
        body = slide.get("body")
        if isinstance(body, list):
            document.setFillColor(text_color)
            document.setFont(body_font, 13)
            for item in body[:9]:
                y = _draw_wrapped_lines(document, f"- {item}", 52, y, width - 104, 16, body_font, 13)
                y -= 3
        elif isinstance(body, str) and body:
            document.setFillColor(text_color)
            y = _draw_wrapped_lines(document, body, 42, y, width - 84, 16, body_font, 13)

        table = slide.get("table")
        if isinstance(table, dict):
            y = _draw_slide_table(
                document,
                table,
                42,
                y - 8,
                width - 84,
                text_color,
                accent,
                body_font=body_font,
                heading_font=heading_font,
            )

        code = str(slide.get("code") or "")
        if code:
            y = _draw_slide_code(document, code, 42, y - 6, width - 84, font_name=code_font)

        image_path = slide.get("image_path")
        if image_path:
            _draw_slide_image(document, Path(str(image_path)), width - 312, 92, 270, 250)

        refs = ", ".join(str(ref) for ref in slide.get("source_refs", []) if ref)
        document.setFillColor(HexColor("#64748b"))
        document.setFont(body_font, 8)
        document.drawString(42, 28, f"Slide {index} / {len(slides)}")
        if refs:
            document.drawRightString(width - 42, 28, f"Sources: {refs}")
        document.showPage()
    document.save()
    return _result_for_created_pdf(
        tool=tool,
        output=output,
        usage={
            "slide_count": len(slides),
            "title": title,
            "style_pack": pack["style_id"],
            "style_pack_source": resolved_style["source"],
            "requires_cjk_font": requires_cjk,
        },
        next_tools=["pdf.inspect.document", "pdf.validation.render_check"],
        source_text=deck_text,
    )


def _draw_wrapped_lines(
    document: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    line_height: float,
    font_name: str,
    font_size: float,
) -> float:
    document.setFont(font_name, font_size)
    for line in _wrap_canvas_text(str(text), max_width, font_name, font_size):
        document.drawString(x, y, line)
        y -= line_height
    return y


def _wrap_canvas_text(text: str, max_width: float, font_name: str, font_size: float) -> list[str]:
    wrapped: list[str] = []
    for raw_line in text.splitlines() or [""]:
        words = raw_line.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                if current:
                    wrapped.append(current)
                current = word
        wrapped.append(current)
    return wrapped


def _draw_slide_table(
    document: canvas.Canvas,
    table: dict[str, Any],
    x: float,
    y: float,
    width: float,
    text_color: HexColor,
    accent: HexColor,
    body_font: str = "Helvetica",
    heading_font: str = "Helvetica-Bold",
) -> float:
    columns = [str(column) for column in table.get("columns", [])]
    rows = [[str(cell) for cell in row] for row in table.get("rows", [])]
    if not columns:
        return y
    column_width = width / max(len(columns), 1)
    row_height = 24
    document.setFillColor(HexColor("#eef2f7"))
    document.rect(x, y - row_height + 6, width, row_height, fill=1, stroke=0)
    document.setStrokeColor(accent)
    document.setLineWidth(0.7)
    document.setFillColor(text_color)
    document.setFont(heading_font, 10)
    for col_index, column in enumerate(columns):
        document.drawString(x + col_index * column_width + 6, y - 10, column[:28])
    y -= row_height
    document.setFont(body_font, 10)
    for row in rows[:7]:
        document.line(x, y + 4, x + width, y + 4)
        for col_index, cell in enumerate(row[: len(columns)]):
            document.drawString(x + col_index * column_width + 6, y - 10, cell[:28])
        y -= row_height
    return y


def _draw_slide_code(
    document: canvas.Canvas,
    code: str,
    x: float,
    y: float,
    width: float,
    font_name: str = "Courier",
) -> float:
    lines = code.splitlines()[:12]
    line_height = 12
    box_height = max(len(lines), 1) * line_height + 18
    document.setFillColor(HexColor("#f8fafc"))
    document.rect(x, y - box_height + 6, width, box_height, fill=1, stroke=0)
    document.setFillColor(HexColor("#0f172a"))
    document.setFont(font_name, 8.5)
    cursor = y - 10
    for line in lines:
        document.drawString(x + 10, cursor, line[:110])
        cursor -= line_height
    return y - box_height - 6


def _draw_slide_image(document: canvas.Canvas, path: Path, x: float, y: float, max_width: float, max_height: float) -> None:
    if not path.exists():
        document.setFillColor(HexColor("#f8fafc"))
        document.rect(x, y, max_width, max_height, fill=1, stroke=0)
        document.setFillColor(HexColor("#64748b"))
        document.setFont("Helvetica", 9)
        document.drawCentredString(x + max_width / 2, y + max_height / 2, "image unavailable")
        return
    reader = ImageReader(str(path))
    image_width, image_height = reader.getSize()
    scale = min(max_width / image_width, max_height / image_height, 1.0)
    draw_width = image_width * scale
    draw_height = image_height * scale
    document.drawImage(reader, x, y, width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")


def _markdown_to_story(markdown: str, styles: Any) -> list[Any]:
    story: list[Any] = []
    bullet_items: list[ListItem] = []
    lines = markdown.splitlines()

    def flush_bullets() -> None:
        nonlocal bullet_items
        if bullet_items:
            story.append(ListFlowable(bullet_items, bulletType="bullet", leftIndent=18))
            story.append(Spacer(1, 8))
            bullet_items = []

    index = 0
    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()
        if not line:
            flush_bullets()
            index += 1
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
        elif line.startswith("```"):
            flush_bullets()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            story.append(Preformatted(_escape_preformatted("\n".join(code_lines)), styles["Code"]))
            story.append(Spacer(1, 8))
        elif (image := _parse_markdown_image(line)) is not None:
            flush_bullets()
            story.extend(_image_story(image[0], image[1], styles))
        elif _is_markdown_table_start(lines, index):
            flush_bullets()
            table_rows, index = _collect_markdown_table(lines, index)
            story.append(_table_story(table_rows, styles))
            story.append(Spacer(1, 8))
            continue
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
        index += 1
    flush_bullets()
    if not story:
        story.append(Paragraph(" ", styles["BodyText"]))
    return story


def _parse_markdown_image(line: str) -> tuple[str, Path] | None:
    if not line.startswith("![") or "](" not in line or not line.endswith(")"):
        return None
    alt_end = line.find("](")
    alt = line[2:alt_end].strip() or "image"
    raw_path = line[alt_end + 2 : -1].strip()
    if raw_path.startswith("<") and raw_path.endswith(">"):
        raw_path = raw_path[1:-1].strip()
    if not raw_path:
        return None
    return alt, Path(raw_path)


def _image_story(alt: str, path: Path, styles: Any) -> list[Any]:
    if not path.exists():
        return [
            Paragraph(_escape_paragraph(f"Image unavailable: {alt} ({path})"), styles["Code"]),
            Spacer(1, 8),
        ]
    reader = ImageReader(str(path))
    width, height = reader.getSize()
    max_width = 420.0
    max_height = 280.0
    scale = min(max_width / width, max_height / height, 1.0) if width and height else 1.0
    flowables: list[Any] = [
        RLImage(str(path), width=width * scale, height=height * scale),
        Spacer(1, 4),
        Paragraph(_escape_paragraph(alt), styles["Code"]),
        Spacer(1, 8),
    ]
    return flowables


def _is_markdown_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    current = lines[index].strip()
    separator = lines[index + 1].strip()
    return current.startswith("|") and separator.startswith("|") and _is_table_separator_row(separator)


def _collect_markdown_table(lines: list[str], index: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    while index < len(lines) and lines[index].strip().startswith("|"):
        raw = lines[index].strip()
        if not _is_table_separator_row(raw):
            rows.append(_split_table_row(raw))
        index += 1
    return rows, index


def _split_table_row(row: str) -> list[str]:
    normalized = row.strip().strip("|")
    return [cell.strip().replace("\\|", "|") for cell in normalized.split("|")]


def _is_table_separator_row(row: str) -> bool:
    cells = _split_table_row(row)
    return bool(cells) and all(cell and set(cell) <= {"-", ":", " "} for cell in cells)


def _table_story(rows: list[list[str]], styles: Any) -> Table:
    width = max(len(row) for row in rows) if rows else 1
    normalized = [row + [""] * (width - len(row)) for row in rows] or [[""]]
    data = [
        [Paragraph(_escape_paragraph(cell), styles["BodyText"]) for cell in row]
        for row in normalized
    ]
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.35, rl_colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _resolve_style_pack(style_pack: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(style_pack, dict):
        return {"pack": _normalize_style_pack(style_pack), "source": "inline"}

    if style_pack in BUILTIN_STYLE_PACKS:
        return {"pack": dict(BUILTIN_STYLE_PACKS[style_pack]), "source": "builtin"}

    candidate = Path(style_pack)
    if candidate.suffix.lower() == ".json" or candidate.exists():
        resolved = resolve_input_path(candidate)
        try:
            raw = json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise OKofficeException(
                "pdf_parse_failed",
                f"Unable to parse style pack JSON: {resolved}",
            ) from exc
        if not isinstance(raw, dict):
            raise OKofficeException("unsafe_input_rejected", "Style pack JSON must be an object.")
        pack = _normalize_style_pack(raw)
        return {"pack": pack, "source": str(resolved)}

    available = ", ".join(sorted(BUILTIN_STYLE_PACKS))
    raise OKofficeException(
        "unsafe_input_rejected",
        f"Unknown style pack: {style_pack}. Available built-ins: {available}.",
    )


def _normalize_style_pack(raw: dict[str, Any]) -> dict[str, Any]:
    style_id = str(raw.get("style_id") or "").strip()
    name = str(raw.get("name") or style_id or "").strip()
    page = raw.get("page")
    typography = raw.get("typography")
    if not style_id or not name or not isinstance(page, dict) or not isinstance(typography, dict):
        raise OKofficeException(
            "unsafe_input_rejected",
            "Style pack must include style_id, name, page, and typography.",
        )
    normalized = dict(raw)
    normalized["style_id"] = style_id
    normalized["name"] = name
    normalized["page"] = page
    normalized["typography"] = typography
    normalized["colors"] = raw.get("colors") if isinstance(raw.get("colors"), dict) else {}
    normalized["components"] = raw.get("components") if isinstance(raw.get("components"), list) else []
    return normalized


def _apply_style_pack(styles: Any, pack: dict[str, Any], requires_cjk: bool = False) -> None:
    typography = pack.get("typography", {})
    colors = pack.get("colors", {})
    body_font = _font_name(str(typography.get("body_font", "system-sans")), bold=False, requires_cjk=requires_cjk)
    heading_font = _font_name(
        str(typography.get("heading_font", "system-sans")),
        bold=True,
        requires_cjk=requires_cjk,
    )
    base_size = float(typography.get("base_size", 10))
    text_color = _hex_color(str(colors.get("text", "#111827")))
    primary_color = _hex_color(str(colors.get("primary", "#111827")))
    accent_color = _hex_color(str(colors.get("accent", colors.get("primary", "#2563eb"))))

    styles["BodyText"].fontName = body_font
    styles["BodyText"].fontSize = base_size
    styles["BodyText"].leading = base_size * 1.45
    styles["BodyText"].textColor = text_color

    styles["Title"].fontName = heading_font
    styles["Title"].fontSize = base_size * 2.0
    styles["Title"].leading = base_size * 2.35
    styles["Title"].textColor = primary_color
    styles["Title"].spaceAfter = 12

    styles["Heading2"].fontName = heading_font
    styles["Heading2"].fontSize = base_size * 1.35
    styles["Heading2"].leading = base_size * 1.65
    styles["Heading2"].textColor = primary_color

    styles["Heading3"].fontName = heading_font
    styles["Heading3"].fontSize = base_size * 1.12
    styles["Heading3"].leading = base_size * 1.35
    styles["Heading3"].textColor = accent_color

    styles["Code"].fontName = body_font if requires_cjk else "Courier"
    styles["Code"].fontSize = max(base_size * 0.9, 8)
    styles["Code"].leading = max(base_size * 1.25, 10)
    styles["Code"].textColor = text_color


def _apply_cjk_to_basic_styles(styles: Any, requires_cjk: bool) -> None:
    if not requires_cjk:
        return
    body_font, heading_font = _register_cjk_fonts()
    styles["BodyText"].fontName = body_font
    styles["Title"].fontName = heading_font


def _style_page_size(pack: dict[str, Any]) -> tuple[float, float]:
    page = pack.get("page", {})
    size_name = str(page.get("size", "letter")).lower()
    page_size = A4 if size_name == "a4" else letter
    if str(page.get("orientation", "portrait")).lower() == "landscape":
        return landscape(page_size)
    return page_size


def _style_margins(pack: dict[str, Any]) -> dict[str, float]:
    raw = pack.get("page", {}).get("margins", {})
    if not isinstance(raw, dict):
        raw = {}
    return {
        "top": float(raw.get("top", 54)),
        "right": float(raw.get("right", 54)),
        "bottom": float(raw.get("bottom", 54)),
        "left": float(raw.get("left", 54)),
    }


def _font_name(value: str, bold: bool, requires_cjk: bool = False) -> str:
    normalized = value.lower()
    if requires_cjk and normalized not in {"mono", "monospace", "courier"}:
        body_font, heading_font = _register_cjk_fonts()
        return heading_font if bold else body_font
    if normalized in {"serif", "system-serif", "times"}:
        return "Times-Bold" if bold else "Times-Roman"
    if normalized in {"mono", "monospace", "courier"}:
        return "Courier-Bold" if bold else "Courier"
    return "Helvetica-Bold" if bold else "Helvetica"


def _canvas_font_pair(requires_cjk: bool) -> tuple[str, str]:
    if requires_cjk:
        return _register_cjk_fonts()
    return "Helvetica", "Helvetica-Bold"


def _requires_cjk_font(*values: Any) -> bool:
    return any(_contains_cjk(str(value)) for value in values if value is not None)


def _contains_cjk(text: str) -> bool:
    return any(_is_cjk_codepoint(ord(char)) for char in text)


def _is_cjk_codepoint(codepoint: int) -> bool:
    return (
        0x2E80 <= codepoint <= 0x2EFF
        or 0x3000 <= codepoint <= 0x303F
        or 0x3040 <= codepoint <= 0x30FF
        or 0x31F0 <= codepoint <= 0x31FF
        or 0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xAC00 <= codepoint <= 0xD7AF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0xFF00 <= codepoint <= 0xFFEF
        or 0x20000 <= codepoint <= 0x2FA1F
    )


def _register_cjk_fonts() -> tuple[str, str]:
    global _REGISTERED_CJK_FONTS
    if _REGISTERED_CJK_FONTS is not None:
        return _REGISTERED_CJK_FONTS

    for index, font_path in enumerate(_iter_cjk_font_paths()):
        if not font_path.exists():
            continue
        regular_name = f"OKoffice-CJK-{index}"
        bold_name = f"OKoffice-CJK-Bold-{index}"
        try:
            pdfmetrics.registerFont(TTFont(regular_name, str(font_path)))
            pdfmetrics.registerFont(TTFont(bold_name, str(font_path)))
        except Exception:
            continue
        _REGISTERED_CJK_FONTS = (regular_name, bold_name)
        return _REGISTERED_CJK_FONTS

    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CJK_CID_FONT))
    except Exception as exc:
        raise OKofficeException(
            "dependency_missing",
            "Unable to register a CJK-capable PDF font. Set AGENTPDF_CJK_FONT_PATH to a local TTF/TTC font.",
        ) from exc
    _REGISTERED_CJK_FONTS = (CJK_CID_FONT, CJK_CID_FONT)
    return _REGISTERED_CJK_FONTS


def _iter_cjk_font_paths() -> list[Path]:
    paths: list[Path] = []
    env_value = os.environ.get(CJK_FONT_PATH_ENV, "")
    for raw_path in env_value.split(os.pathsep):
        if raw_path.strip():
            paths.append(Path(raw_path.strip()))
    paths.extend(CJK_FONT_CANDIDATES)
    return paths


def _slide_deck_text(slides: list[dict[str, Any]], title: str | None) -> str:
    parts: list[str] = [title or ""]
    for slide in slides:
        parts.append(str(slide.get("title") or ""))
        parts.append(str(slide.get("subtitle") or ""))
        body = slide.get("body")
        if isinstance(body, list):
            parts.extend(str(item) for item in body)
        elif body:
            parts.append(str(body))
        table = slide.get("table")
        if isinstance(table, dict):
            parts.extend(str(column) for column in table.get("columns", []))
            for row in table.get("rows", []):
                if isinstance(row, list):
                    parts.extend(str(cell) for cell in row)
        parts.append(str(slide.get("code") or ""))
    return "\n".join(part for part in parts if part)


def _hex_color(value: str) -> HexColor:
    try:
        return HexColor(value)
    except ValueError:
        return HexColor("#111827")


def _build_pdf_document(
    output: Path,
    story: list[Any],
    title: str | None = None,
    page_size: tuple[float, float] = letter,
    margins: dict[str, float] | None = None,
) -> None:
    resolved_margins = margins or {"top": 54, "right": 54, "bottom": 54, "left": 54}
    document = SimpleDocTemplate(
        str(output),
        pagesize=page_size,
        title=title or "okoffice document",
        leftMargin=resolved_margins["left"],
        rightMargin=resolved_margins["right"],
        topMargin=resolved_margins["top"],
        bottomMargin=resolved_margins["bottom"],
    )
    document.build(story)


def _result_for_created_pdf(
    tool: str,
    output: Path,
    usage: dict[str, Any],
    next_tools: list[str],
    source_text: str | None = None,
) -> ToolResult:
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=artifact.page_count)
    validation = _append_text_glyph_validation(validation, output, source_text)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        usage=usage,
        next_recommended_tools=next_tools,
    )


def _append_text_glyph_validation(
    validation: ValidationReport,
    output: Path,
    source_text: str | None,
) -> ValidationReport:
    if not source_text or not _contains_cjk(source_text):
        return validation

    expected_chars = _unique_cjk_chars(source_text, limit=64)
    try:
        reader = PdfReader(output)
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        tofu_count = extracted.count("\u25a0") + extracted.count("\ufffd")
        matched_count = sum(1 for char in expected_chars if char in extracted)
        required_matches = min(3, len(expected_chars))
        passed = tofu_count == 0 and matched_count >= required_matches
        check = ValidationCheck(
            name="text_glyph_coverage",
            status="passed" if passed else "failed",
            details={
                "script": "cjk",
                "expected_unique_chars": len(expected_chars),
                "matched_unique_chars": matched_count,
                "required_matches": required_matches,
                "replacement_glyph_count": tofu_count,
            },
            message=None if passed else "Generated PDF text appears to contain missing CJK glyphs.",
        )
    except Exception as exc:
        check = ValidationCheck(
            name="text_glyph_coverage",
            status="failed",
            details={"script": "cjk"},
            message=str(exc),
        )

    checks = [*validation.checks, check]
    warnings = list(validation.warnings)
    if check.status != "passed":
        warnings.append("Generated PDF may contain missing CJK glyphs.")
    return ValidationReport(
        status=_created_pdf_validation_status(checks),
        checks=checks,
        page_count=validation.page_count,
        warnings=warnings,
    )


def _unique_cjk_chars(text: str, limit: int) -> list[str]:
    chars: list[str] = []
    seen: set[str] = set()
    for char in text:
        if char in seen or not _is_cjk_codepoint(ord(char)):
            continue
        seen.add(char)
        chars.append(char)
        if len(chars) >= limit:
            break
    return chars


def _created_pdf_validation_status(checks: list[ValidationCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    if any(check.status == "skipped" for check in checks):
        return "skipped"
    return "passed"


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


def _escape_preformatted(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    next_recommended_tools: list[str] | None = None,
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
        next_recommended_tools=next_recommended_tools
        or ["pdf.inspect.document", "pdf.validation.validate_output"],
    )


def _add_outline_items(
    writer: PdfWriter,
    outline: list[dict[str, Any]],
    page_count: int,
    parent: Any | None = None,
) -> int:
    count = 0
    for item in outline:
        if not isinstance(item, dict):
            raise OKofficeException("invalid_input", "Each outline item must be an object.")
        title = str(item.get("title") or "").strip()
        if not title:
            raise OKofficeException("invalid_input", "Each outline item must include a title.")
        page_number = int(item.get("page", 1))
        if page_number < 1 or page_number > page_count:
            raise OKofficeException(
                "invalid_page_range",
                f"Outline page must be between 1 and {page_count}.",
                details={"title": title, "page": page_number, "page_count": page_count},
            )
        outline_ref = writer.add_outline_item(title, page_number - 1, parent=parent)
        count += 1
        children = item.get("children")
        if isinstance(children, list):
            count += _add_outline_items(writer, children, page_count=page_count, parent=outline_ref)
    return count


def _validate_one_based_page(page: int, page_count: int) -> int:
    if page < 1 or page > page_count:
        raise OKofficeException(
            "invalid_page_range",
            f"page must be between 1 and {page_count}.",
            details={"page": page, "page_count": page_count},
        )
    return page - 1


def _normalize_bbox(bbox: list[float] | tuple[float, float, float, float]) -> list[float]:
    if len(bbox) != 4:
        raise OKofficeException("invalid_input", "bbox must contain [x0, y0, x1, y1].")
    x0, y0, x1, y1 = [float(value) for value in bbox]
    if x1 <= x0 or y1 <= y0:
        raise OKofficeException("invalid_input", "bbox must have positive width and height.")
    return [x0, y0, x1, y1]


def _normalize_points(points: list[list[float]] | list[tuple[float, float]]) -> list[list[float]]:
    normalized = []
    for point in points:
        if len(point) != 2:
            raise OKofficeException("invalid_input", "Each freehand point must be [x, y].")
        normalized.append([float(point[0]), float(point[1])])
    return normalized


def _estimate_pdf_object_count(reader: PdfReader) -> int | None:
    xref = getattr(reader, "xref", None)
    if not isinstance(xref, dict):
        return None
    count = 0
    for section in xref.values():
        if isinstance(section, dict):
            count += len(section)
    return count or None


def _detect_pdfa_profile(raw: bytes) -> str | None:
    text = raw.decode("latin-1", errors="ignore")
    lowered = text.lower()
    part_marker = "pdfaid:part"
    if part_marker not in lowered:
        return None
    part = _extract_xmlish_value(text, "pdfaid:part")
    conformance = _extract_xmlish_value(text, "pdfaid:conformance")
    if not part:
        return None
    return f"PDF/A-{part}{conformance or ''}"


def _extract_xmlish_value(text: str, tag: str) -> str | None:
    lower = text.lower()
    tag_lower = tag.lower()
    start_tag = f"<{tag_lower}>"
    end_tag = f"</{tag_lower}>"
    start = lower.find(start_tag)
    end = lower.find(end_tag)
    if start >= 0 and end > start:
        return text[start + len(start_tag) : end].strip()
    attr = f"{tag_lower}="
    attr_start = lower.find(attr)
    if attr_start < 0:
        return None
    value_start = attr_start + len(attr)
    quote = text[value_start : value_start + 1]
    if quote not in {"'", '"'}:
        return None
    value_end = text.find(quote, value_start + 1)
    if value_end < 0:
        return None
    return text[value_start + 1 : value_end].strip()


def _collect_font_records(reader: PdfReader, selected_pages: list[int]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str, bool], dict[str, Any]] = {}
    for page_index in selected_pages:
        page = reader.pages[page_index]
        resources = page.get("/Resources") or {}
        try:
            resolved_resources = resources.get_object() if hasattr(resources, "get_object") else resources
            fonts = resolved_resources.get("/Font", {}) or {}
            resolved_fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
        except Exception:
            continue
        for resource_name, raw_font in resolved_fonts.items():
            try:
                font = raw_font.get_object() if hasattr(raw_font, "get_object") else raw_font
                record = _font_record_from_pdf_font(font)
            except Exception:
                continue
            key = (
                record["base_font"],
                record["subtype"],
                record["encoding"],
                bool(record["embedded"]),
            )
            existing = by_key.setdefault(
                key,
                {
                    **record,
                    "resource_names": [],
                    "page_numbers": [],
                },
            )
            resource_name_str = str(resource_name)
            if resource_name_str not in existing["resource_names"]:
                existing["resource_names"].append(resource_name_str)
            page_number = page_index + 1
            if page_number not in existing["page_numbers"]:
                existing["page_numbers"].append(page_number)
    return sorted(by_key.values(), key=lambda item: (item["base_font"], item["subtype"]))


def _font_record_from_pdf_font(font: Any) -> dict[str, Any]:
    subtype = str(font.get("/Subtype", "")).lstrip("/")
    base_font = str(font.get("/BaseFont") or font.get("/Name") or "").lstrip("/")
    encoding = str(font.get("/Encoding", "")).lstrip("/")
    descriptor = font.get("/FontDescriptor")
    if descriptor and hasattr(descriptor, "get_object"):
        descriptor = descriptor.get_object()
    descendant_fonts = font.get("/DescendantFonts")
    if descendant_fonts:
        try:
            descendant = descendant_fonts[0].get_object()
            base_font = str(descendant.get("/BaseFont") or base_font).lstrip("/")
            descendant_descriptor = descendant.get("/FontDescriptor")
            if descendant_descriptor and hasattr(descendant_descriptor, "get_object"):
                descriptor = descendant_descriptor.get_object()
        except Exception:
            pass
    embedded = False
    if descriptor:
        embedded = any(descriptor.get(key) is not None for key in ("/FontFile", "/FontFile2", "/FontFile3"))
    return {
        "base_font": base_font or "unknown",
        "subtype": subtype or "unknown",
        "encoding": encoding or "default",
        "embedded": embedded,
    }


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


def _image_suffix(image_file: Any, pil_image: Any) -> str:
    name = str(getattr(image_file, "name", ""))
    suffix = Path(name).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    image_format = str(getattr(pil_image, "format", "") or "").lower()
    if image_format in {"jpeg", "jpg"}:
        return ".jpg"
    if image_format in {"png", "webp", "bmp", "tif", "tiff"}:
        return f".{image_format}"
    return ".png"


def _count_page_images(page: Any) -> int:
    resources = page.get("/Resources") or {}
    return _count_images_in_resources(resources)


def _count_images_in_resources(resources: Any) -> int:
    try:
        resolved_resources = resources.get_object() if hasattr(resources, "get_object") else resources
        xobjects = resolved_resources.get("/XObject", {}) or {}
        resolved_xobjects = xobjects.get_object() if hasattr(xobjects, "get_object") else xobjects
    except Exception:
        return 0

    image_count = 0
    for raw_object in resolved_xobjects.values():
        try:
            xobject = raw_object.get_object() if hasattr(raw_object, "get_object") else raw_object
            subtype = str(xobject.get("/Subtype", ""))
            if subtype == "/Image":
                image_count += 1
            elif subtype == "/Form":
                nested_resources = xobject.get("/Resources")
                if nested_resources:
                    image_count += _count_images_in_resources(nested_resources)
        except Exception:
            continue
    return image_count


def _reader_for_operation(path: Path) -> PdfReader:
    if path.suffix.lower() != ".pdf":
        raise OKofficeException("unsupported_file_type", "Only PDF files are supported.")
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise OKofficeException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise OKofficeException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require an authorized password before processing.",
        )
    return reader


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
