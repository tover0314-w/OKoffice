from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.core.pdf import (
    extract_pages_pdf,
    extract_text_pdf,
    inspect_pdf,
    merge_pdfs,
    read_metadata_pdf,
    remove_pages_pdf,
    remove_metadata_pdf,
    render_pdf,
    rotate_pages_pdf,
    split_pdf,
    update_metadata_pdf,
)
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult


def run_inspect(path: str | Path) -> ToolResult:
    tool = "pdf.inspect.document"
    try:
        info = inspect_pdf(path)
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=tool,
            usage=info,
            next_recommended_tools=["pdf.validation.validate_output"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def run_merge(input_paths: list[str | Path], output_path: str | Path) -> ToolResult:
    try:
        return merge_pdfs(input_paths, output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.merge", exc.to_error())


def run_split(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    try:
        return split_pdf(input_path, pages=pages, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.split", exc.to_error())


def run_extract_pages(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    try:
        return extract_pages_pdf(input_path, pages=pages, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.extract_pages", exc.to_error())


def run_remove_pages(input_path: str | Path, pages: str, output_path: str | Path) -> ToolResult:
    try:
        return remove_pages_pdf(input_path, pages=pages, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.remove_pages", exc.to_error())


def run_rotate_pages(
    input_path: str | Path,
    pages: str,
    degrees: int,
    output_path: str | Path,
) -> ToolResult:
    try:
        return rotate_pages_pdf(input_path, pages=pages, degrees=degrees, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.organize.rotate_pages", exc.to_error())


def run_render(
    input_path: str | Path,
    pages: str,
    image_format: str,
    out_dir: str | Path,
) -> ToolResult:
    try:
        return render_pdf(
            input_path=input_path,
            pages=pages,
            image_format=image_format,
            out_dir=out_dir,
        )
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_images", exc.to_error())


def run_extract_text(input_path: str | Path, pages: str = "all") -> ToolResult:
    try:
        return extract_text_pdf(input_path, pages=pages)
    except AgentPDFException as exc:
        return _failed("pdf.convert.pdf_to_text", exc.to_error())


def run_metadata_read(input_path: str | Path) -> ToolResult:
    try:
        return read_metadata_pdf(input_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.read", exc.to_error())


def run_metadata_update(
    input_path: str | Path,
    metadata: dict[str, object],
    output_path: str | Path,
) -> ToolResult:
    try:
        return update_metadata_pdf(input_path, metadata=metadata, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.update", exc.to_error())


def run_metadata_remove(input_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        return remove_metadata_pdf(input_path, output_path=output_path)
    except AgentPDFException as exc:
        return _failed("pdf.metadata.remove", exc.to_error())


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
