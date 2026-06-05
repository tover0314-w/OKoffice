from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from uuid import uuid4

from PIL import Image

from okoffice.ocr_scan.local import OCR_IMAGE_SUFFIXES, ocr_pdf
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_input_path


def analyze_image(
    input_path: str | Path,
    languages: list[str] | None = None,
    run_ocr: bool = True,
    engine: str = "tesseract",
    psm: int = 6,
) -> ToolResult:
    tool = "pdf.context.image_analyze"
    source = resolve_input_path(input_path)
    if source.suffix.lower() not in OCR_IMAGE_SUFFIXES:
        raise OKofficeException(
            "unsupported_file_type",
            "Image analysis input must be a local image file.",
            details={"path": str(source), "suffix": source.suffix},
        )

    image = _image_metadata(source)
    warnings: list[str] = []
    ocr = {"status": "skipped", "text": "", "region_count": 0, "regions": [], "pages": []}
    if run_ocr:
        try:
            ocr_result = ocr_pdf(source, languages=languages, engine=engine, psm=psm)
            first_page = ocr_result.usage["pages"][0] if ocr_result.usage["pages"] else {}
            ocr = {
                "status": "succeeded",
                "text": ocr_result.usage["text"],
                "region_count": ocr_result.usage["region_count"],
                "regions": first_page.get("regions", []),
                "pages": ocr_result.usage["pages"],
                "languages": ocr_result.usage["languages"],
                "engine": ocr_result.usage["engine"],
            }
            warnings.extend(ocr_result.warnings)
        except OKofficeException as exc:
            warnings.append(f"OCR unavailable: {exc.message}")
            ocr = {
                "status": "failed",
                "text": "",
                "region_count": 0,
                "regions": [],
                "pages": [],
                "error": exc.to_error().model_dump(mode="json"),
            }

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        warnings=warnings,
        usage={
            "input": str(source),
            "image": image,
            "ocr": ocr,
            "caption": None,
            "objects": [],
            "limitations": [
                "No vision model was used.",
                "Local analysis includes image metadata and optional OCR text regions only.",
            ],
        },
        next_recommended_tools=[
            "pdf.context.ingest",
            "pdf.context.build_packet",
            "pdf.ocr_scan.searchable_pdf",
        ],
    )


def _image_metadata(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
        image_format = image.format
    return {
        "path": str(path),
        "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "width": width,
        "height": height,
        "mode": mode,
        "format": image_format,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
