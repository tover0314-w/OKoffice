from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from agentpdf.tools.registry import load_tool_manifest
from agentpdf.tools.runner import (
    run_extract_pages,
    run_extract_text,
    run_inspect,
    run_metadata_read,
    run_metadata_remove,
    run_metadata_update,
    run_merge,
    run_remove_pages,
    run_render,
    run_rotate_pages,
    run_split,
)


def create_mcp_server() -> FastMCP:
    server = FastMCP(
        "agentpdf",
        instructions=(
            "Local-first PDF tools for agents. Tools return structured AgentPDF "
            "ToolResult JSON and write artifacts to explicit local paths."
        ),
    )
    server.tool(name="agentpdf_tool_manifest")(agentpdf_tool_manifest)
    server.tool(name="pdf_inspect_document")(pdf_inspect_document)
    server.tool(name="pdf_merge")(pdf_merge)
    server.tool(name="pdf_split")(pdf_split)
    server.tool(name="pdf_extract_pages")(pdf_extract_pages)
    server.tool(name="pdf_remove_pages")(pdf_remove_pages)
    server.tool(name="pdf_rotate_pages")(pdf_rotate_pages)
    server.tool(name="pdf_render_pages")(pdf_render_pages)
    server.tool(name="pdf_extract_text")(pdf_extract_text)
    server.tool(name="pdf_metadata_read")(pdf_metadata_read)
    server.tool(name="pdf_metadata_update")(pdf_metadata_update)
    server.tool(name="pdf_metadata_remove")(pdf_metadata_remove)
    return server


def agentpdf_tool_manifest() -> str:
    """Return the complete AgentPDF tool manifest with implementation statuses."""
    return load_tool_manifest().model_dump_json()


def pdf_inspect_document(path: str) -> str:
    """Inspect a local PDF document."""
    return run_inspect(path).model_dump_json()


def pdf_merge(input_paths: list[str], output_path: str) -> str:
    """Merge local PDF files into a new output PDF."""
    return run_merge(input_paths, output_path).model_dump_json()


def pdf_split(input_path: str, pages: str, output_path: str) -> str:
    """Extract selected pages from a local PDF into a new output PDF."""
    return run_split(input_path, pages=pages, output_path=output_path).model_dump_json()


def pdf_extract_pages(input_path: str, pages: str, output_path: str) -> str:
    """Extract selected pages from a local PDF into a new output PDF."""
    return run_extract_pages(input_path, pages=pages, output_path=output_path).model_dump_json()


def pdf_remove_pages(input_path: str, pages: str, output_path: str) -> str:
    """Remove selected pages from a local PDF and write a new output PDF."""
    return run_remove_pages(input_path, pages=pages, output_path=output_path).model_dump_json()


def pdf_rotate_pages(input_path: str, pages: str, degrees: int, output_path: str) -> str:
    """Rotate selected pages from a local PDF and write a new output PDF."""
    return run_rotate_pages(
        input_path,
        pages=pages,
        degrees=degrees,
        output_path=output_path,
    ).model_dump_json()


def pdf_render_pages(
    input_path: str,
    pages: str,
    image_format: Literal["png", "jpeg", "jpg", "webp"] = "png",
    out_dir: str = "renders",
) -> str:
    """Render selected local PDF pages to image artifacts."""
    return run_render(
        input_path,
        pages=pages,
        image_format=image_format,
        out_dir=out_dir,
    ).model_dump_json()


def pdf_extract_text(input_path: str, pages: str = "all") -> str:
    """Extract text from selected local PDF pages."""
    return run_extract_text(input_path, pages=pages).model_dump_json()


def pdf_metadata_read(input_path: str) -> str:
    """Read local PDF document metadata."""
    return run_metadata_read(input_path).model_dump_json()


def pdf_metadata_update(input_path: str, metadata: dict[str, object], output_path: str) -> str:
    """Update local PDF metadata and write a new PDF."""
    return run_metadata_update(input_path, metadata=metadata, output_path=output_path).model_dump_json()


def pdf_metadata_remove(input_path: str, output_path: str) -> str:
    """Remove local PDF metadata and write a new PDF."""
    return run_metadata_remove(input_path, output_path=output_path).model_dump_json()


def run_mcp_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    create_mcp_server().run(transport=transport)
