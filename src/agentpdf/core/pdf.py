from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from pypdf import PdfReader, PdfWriter

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.page_ranges import parse_page_range
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path
from agentpdf.validation.pdf import validate_pdf


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
