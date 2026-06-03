from __future__ import annotations

import csv
import shutil
import subprocess
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageFilter
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult
from agentpdf.security.paths import resolve_input_path, resolve_output_path
from agentpdf.validation.pdf import validate_pdf

OCR_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def scan_to_pdf(image_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    tool = "pdf.ocr_scan.scan_to_pdf"
    if not image_paths:
        raise AgentPDFException("unsafe_input_rejected", "At least one scan image is required.")
    images = [resolve_input_path(path) for path in image_paths]
    output = resolve_output_path(output_path)
    document = canvas.Canvas(str(output))
    page_count = 0
    for image_path in images:
        with Image.open(image_path) as image:
            width, height = image.size
            document.setPageSize((width, height))
            document.drawImage(ImageReader(image), 0, 0, width=width, height=height)
            document.showPage()
            page_count += 1
    document.save()
    artifact = build_artifact(output, source_tool=tool)
    validation = validate_pdf(output, expected_pages=page_count)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=validation.warnings or [],
        usage={
            "inputs": [str(path) for path in images],
            "output": str(output),
            "page_count": page_count,
            "ocr_mode": "image_only_pdf",
        },
        next_recommended_tools=["pdf.ocr_scan.multilingual_ocr", "pdf.validation.render_check"],
    )


def ocr_pdf(
    input_path: str | Path,
    pages: str = "all",
    languages: list[str] | None = None,
    dpi: int = 200,
    engine: str = "tesseract",
    psm: int = 6,
) -> ToolResult:
    tool = "pdf.ocr_scan.ocr"
    source = resolve_input_path(input_path)
    requested_languages = _normalize_languages(languages)
    if source.suffix.lower() == ".pdf":
        page_inputs = _ocr_pdf_page_inputs(source, pages=pages, dpi=dpi)
        input_kind = "pdf"
    elif source.suffix.lower() in OCR_IMAGE_SUFFIXES:
        page_inputs = [_ocr_image_page_input(source)]
        input_kind = "image"
    else:
        raise AgentPDFException(
            "unsupported_file_type",
            "OCR input must be a PDF or local image file.",
            details={"path": str(source), "suffix": source.suffix},
        )

    try:
        pages_usage = []
        all_regions = []
        with tempfile.TemporaryDirectory(prefix="agentpdf-ocr-") as temp_dir:
            temp_root = Path(temp_dir)
            for page_input in page_inputs:
                image_path = page_input.get("image_path")
                cleanup_path = None
                if image_path is None:
                    cleanup_path = temp_root / f"page-{page_input['page_number']:04d}.png"
                    _render_pdf_page_to_image(
                        source,
                        page_index=int(page_input["page_index"]),
                        output_path=cleanup_path,
                        scale=float(page_input["scale"]),
                    )
                    image_path = cleanup_path
                tsv = _run_tesseract_tsv(
                    Path(image_path),
                    languages=requested_languages,
                    engine=engine,
                    psm=psm,
                )
                page_regions = _parse_tesseract_regions(
                    tsv,
                    page_number=int(page_input["page_number"]),
                    page_width=float(page_input["page_width"]),
                    page_height=float(page_input["page_height"]),
                    scale=float(page_input["scale"]),
                    coordinate_space=str(page_input["coordinate_space"]),
                )
                page_text = _regions_to_text(page_regions)
                pages_usage.append(
                    {
                        "page_number": page_input["page_number"],
                        "width": page_input["page_width"],
                        "height": page_input["page_height"],
                        "text": page_text,
                        "region_count": len(page_regions),
                        "regions": page_regions,
                    }
                )
                all_regions.extend(page_regions)
                if cleanup_path is not None and cleanup_path.exists():
                    cleanup_path.unlink()
    except AgentPDFException:
        raise

    text = "\n".join(page["text"] for page in pages_usage if page["text"]).strip()
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        warnings=[] if text else ["No OCR text was detected by the local engine."],
        usage={
            "input": str(source),
            "input_kind": input_kind,
            "selected_pages": [page["page_number"] for page in pages_usage],
            "languages": requested_languages,
            "engine": engine,
            "dpi": dpi,
            "psm": psm,
            "page_count": len(pages_usage),
            "region_count": len(all_regions),
            "text": text,
            "pages": pages_usage,
        },
        next_recommended_tools=[
            "pdf.ocr_scan.searchable_pdf",
            "pdf.ai.parse.lite",
            "pdf.evidence.map_sources",
        ],
    )


def searchable_pdf(
    input_path: str | Path,
    output_path: str | Path,
    pages: str = "all",
    languages: list[str] | None = None,
    dpi: int = 200,
    engine: str = "tesseract",
    psm: int = 6,
) -> ToolResult:
    tool = "pdf.ocr_scan.searchable_pdf"
    source = resolve_input_path(input_path)
    if source.suffix.lower() != ".pdf":
        raise AgentPDFException(
            "unsupported_file_type",
            "searchable_pdf currently accepts PDF input. Use pdf.ocr_scan.scan_to_pdf for images first.",
        )
    reader = _reader(source)
    ocr_result = ocr_pdf(
        source,
        pages=pages,
        languages=languages,
        dpi=dpi,
        engine=engine,
        psm=psm,
    )
    writer = PdfWriter(clone_from=source)
    for page_usage in ocr_result.usage["pages"]:
        page_index = int(page_usage["page_number"]) - 1
        if not page_usage["regions"]:
            continue
        overlay = _ocr_text_overlay_page(
            page_width=float(reader.pages[page_index].mediabox.width),
            page_height=float(reader.pages[page_index].mediabox.height),
            regions=page_usage["regions"],
        )
        writer.pages[page_index].merge_page(overlay)

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
        warnings=(validation.warnings or []) + list(ocr_result.warnings),
        usage={
            "input": str(source),
            "output": str(output),
            "page_range": pages,
            "languages": ocr_result.usage["languages"],
            "engine": ocr_result.usage["engine"],
            "ocr": {
                "text": ocr_result.usage["text"],
                "page_count": ocr_result.usage["page_count"],
                "region_count": ocr_result.usage["region_count"],
                "selected_pages": ocr_result.usage["selected_pages"],
            },
        },
        next_recommended_tools=["pdf.convert.pdf_to_text", "pdf.validation.render_check"],
    )


def despeckle_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.ocr_scan.despeckle"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    for page in reader.pages:
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
        warnings=[
            "Local despeckle performs a safe PDF rewrite; pixel-level cleanup requires an optional image worker."
        ]
        + (validation.warnings or []),
        usage={
            "input": str(source),
            "output": str(output),
            "page_count": len(reader.pages),
            "despeckle_mode": "safe_pdf_rewrite",
        },
        next_recommended_tools=["pdf.validation.render_check", "pdf.ocr_scan.ocr"],
    )


def remove_existing_ocr_pdf(input_path: str | Path, output_path: str | Path) -> ToolResult:
    tool = "pdf.ocr_scan.remove_existing_ocr"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Producer": "AgentPDF local OCR-layer rewrite"})
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
        warnings=[
            "Local remove_existing_ocr rewrites page objects but does not guarantee removal of all hidden OCR text."
        ]
        + (validation.warnings or []),
        usage={
            "input": str(source),
            "output": str(output),
            "page_count": len(reader.pages),
            "ocr_removal_mode": "best_effort_page_rewrite",
        },
        next_recommended_tools=["pdf.convert.pdf_to_text", "pdf.validation.render_check"],
    )


def multilingual_ocr_pdf(
    input_path: str | Path,
    output_path: str | Path,
    languages: list[str] | None = None,
) -> ToolResult:
    tool = "pdf.ocr_scan.multilingual_ocr"
    source = resolve_input_path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    requested_languages = languages or ["eng"]
    writer.add_metadata(
        {
            "/Producer": "AgentPDF local multilingual OCR placeholder",
            "/AgentPDFOCRLanguages": ",".join(requested_languages),
        }
    )
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
        warnings=[
            "Local multilingual_ocr records requested languages and rewrites the PDF; OCR text creation requires an optional OCR worker."
        ]
        + (validation.warnings or []),
        usage={
            "input": str(source),
            "output": str(output),
            "languages": requested_languages,
            "page_count": len(reader.pages),
            "ocr_mode": "local_worker_placeholder",
        },
        next_recommended_tools=["pdf.convert.pdf_to_text", "pdf.validation.text_layer_check"],
    )


def despeckle_image_file(input_path: str | Path, output_path: str | Path) -> Path:
    source = resolve_input_path(input_path)
    output = resolve_output_path(output_path)
    with Image.open(source) as image:
        image.filter(ImageFilter.MedianFilter(size=3)).save(output)
    return output


def _ocr_pdf_page_inputs(source: Path, pages: str, dpi: int) -> list[dict[str, object]]:
    from agentpdf.core.page_ranges import parse_page_range

    reader = _reader(source)
    selected_pages = parse_page_range(pages, total_pages=len(reader.pages))
    scale = dpi / 72.0
    return [
        {
            "page_index": page_index,
            "page_number": page_index + 1,
            "page_width": float(reader.pages[page_index].mediabox.width),
            "page_height": float(reader.pages[page_index].mediabox.height),
            "scale": scale,
            "coordinate_space": "pdf_points",
            "image_path": None,
        }
        for page_index in selected_pages
    ]


def _ocr_image_page_input(source: Path) -> dict[str, object]:
    with Image.open(source) as image:
        width, height = image.size
    return {
        "page_index": 0,
        "page_number": 1,
        "page_width": width,
        "page_height": height,
        "scale": 1.0,
        "coordinate_space": "image_pixels",
        "image_path": source,
    }


def _render_pdf_page_to_image(source: Path, page_index: int, output_path: Path, scale: float) -> None:
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise AgentPDFException(
            "dependency_missing",
            "OCR PDF rendering requires pypdfium2.",
            retry_hint="Install the default AgentPDF dependencies and retry.",
        ) from exc
    document = pdfium.PdfDocument(str(source))
    try:
        page = document[page_index]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        image.save(output_path)
    except Exception as exc:
        raise AgentPDFException("pdf_render_failed", f"Unable to render page {page_index + 1}.") from exc
    finally:
        close = getattr(document, "close", None)
        if callable(close):
            close()


def _run_tesseract_tsv(image_path: Path, languages: list[str], engine: str, psm: int) -> str:
    command = shutil.which(engine)
    if command is None:
        raise AgentPDFException(
            "dependency_missing",
            f"OCR engine not found: {engine}",
            retry_hint=(
                "Install Tesseract OCR and ensure the tesseract executable is on PATH, "
                "or configure a supported local OCR worker."
            ),
            details={"engine": engine},
        )
    language_arg = "+".join(languages)
    completed = subprocess.run(
        [command, str(image_path), "stdout", "-l", language_arg, "--psm", str(psm), "tsv"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise AgentPDFException(
            "pdf_parse_failed",
            "Local OCR engine failed.",
            details={
                "engine": engine,
                "returncode": completed.returncode,
                "stderr": completed.stderr.strip(),
            },
        )
    return completed.stdout


def _parse_tesseract_regions(
    tsv: str,
    page_number: int,
    page_width: float,
    page_height: float,
    scale: float,
    coordinate_space: str,
) -> list[dict[str, object]]:
    regions = []
    reader = csv.DictReader(StringIO(tsv), delimiter="\t")
    for row in reader:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        confidence = _float_or_none(row.get("conf"))
        if confidence is not None and confidence < 0:
            continue
        left = int(float(row.get("left") or 0))
        top = int(float(row.get("top") or 0))
        width = int(float(row.get("width") or 0))
        height = int(float(row.get("height") or 0))
        image_bbox = [left, top, left + width, top + height]
        bbox = (
            _image_bbox_to_pdf_bbox(image_bbox, page_height=page_height, scale=scale)
            if coordinate_space == "pdf_points"
            else image_bbox
        )
        regions.append(
            {
                "page_number": page_number,
                "text": text,
                "bbox": bbox,
                "image_bbox": image_bbox,
                "confidence": confidence,
                "block_number": _int_or_zero(row.get("block_num")),
                "paragraph_number": _int_or_zero(row.get("par_num")),
                "line_number": _int_or_zero(row.get("line_num")),
                "word_number": _int_or_zero(row.get("word_num")),
                "coordinate_space": coordinate_space,
            }
        )
    return regions


def _image_bbox_to_pdf_bbox(image_bbox: list[int], page_height: float, scale: float) -> list[float]:
    left, top, right, bottom = image_bbox
    return [
        round(left / scale, 3),
        round(page_height - (bottom / scale), 3),
        round(right / scale, 3),
        round(page_height - (top / scale), 3),
    ]


def _regions_to_text(regions: list[dict[str, object]]) -> str:
    lines: dict[tuple[int, int, int], list[str]] = {}
    for region in regions:
        key = (
            int(region["block_number"]),
            int(region["paragraph_number"]),
            int(region["line_number"]),
        )
        lines.setdefault(key, []).append(str(region["text"]))
    return "\n".join(" ".join(words) for _, words in sorted(lines.items())).strip()


def _ocr_text_overlay_page(page_width: float, page_height: float, regions: list[dict[str, object]]):
    buffer = BytesIO()
    document = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    document.setFont("Helvetica", 8)
    for region in regions:
        bbox = region["bbox"]
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        x0, y0, x1, y1 = [float(value) for value in bbox]
        font_size = max(min(y1 - y0, 14), 4)
        text = document.beginText(x0, y0)
        text.setFont("Helvetica", font_size)
        if hasattr(text, "setTextRenderMode"):
            text.setTextRenderMode(3)
        text.textOut(str(region["text"]))
        document.drawText(text)
    document.showPage()
    document.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _normalize_languages(languages: list[str] | None) -> list[str]:
    normalized = [str(language).strip() for language in (languages or ["eng"]) if str(language).strip()]
    return normalized or ["eng"]


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_zero(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _reader(path: Path) -> PdfReader:
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise AgentPDFException("pdf_parse_failed", f"Unable to parse PDF: {path}") from exc
    if reader.is_encrypted:
        raise AgentPDFException(
            "encrypted_pdf_requires_password",
            "Encrypted PDFs require authorized decryption before OCR/scan operations.",
        )
    return reader


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
