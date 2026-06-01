import json
import asyncio
from pathlib import Path

from agentpdf.mcp.server import (
    create_mcp_server,
    pdf_extract_text,
    pdf_extract_pages,
    pdf_inspect_document,
    pdf_merge,
    pdf_metadata_read,
    pdf_render_pages,
)


def test_mcp_server_exposes_local_pdf_tools() -> None:
    server = create_mcp_server()
    tool_names = {tool.name for tool in asyncio.run(server.list_tools())}

    assert "pdf_inspect_document" in tool_names
    assert "pdf_merge" in tool_names
    assert "pdf_split" in tool_names
    assert "pdf_extract_pages" in tool_names
    assert "pdf_remove_pages" in tool_names
    assert "pdf_rotate_pages" in tool_names
    assert "pdf_render_pages" in tool_names
    assert "pdf_extract_text" in tool_names
    assert "pdf_metadata_read" in tool_names
    assert "pdf_metadata_update" in tool_names
    assert "pdf_metadata_remove" in tool_names
    assert "agentpdf_tool_manifest" in tool_names


def test_mcp_inspect_returns_same_tool_result_contract(simple_pdf: Path) -> None:
    payload = json.loads(pdf_inspect_document(str(simple_pdf)))

    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.inspect.document"
    assert payload["usage"]["page_count"] == 1


def test_mcp_merge_returns_artifact(simple_pdf: Path, two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "merged.pdf"

    payload = json.loads(pdf_merge([str(simple_pdf), str(two_page_pdf)], str(output)))

    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["page_count"] == 3


def test_mcp_render_pages_returns_image_artifact(simple_pdf: Path, tmp_path: Path) -> None:
    payload = json.loads(pdf_render_pages(str(simple_pdf), pages="1", image_format="png", out_dir=str(tmp_path)))

    assert payload["status"] == "succeeded"
    assert payload["artifacts"][0]["mime_type"] == "image/png"


def test_mcp_extract_pages_returns_artifact(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "extract.pdf"

    payload = json.loads(pdf_extract_pages(str(two_page_pdf), pages="1", output_path=str(output)))

    assert payload["status"] == "succeeded"
    assert payload["tool"] == "pdf.organize.extract_pages"


def test_mcp_text_and_metadata_tools(text_pdf: Path, metadata_pdf: Path) -> None:
    text = json.loads(pdf_extract_text(str(text_pdf), pages="1"))
    metadata = json.loads(pdf_metadata_read(str(metadata_pdf)))

    assert text["tool"] == "pdf.convert.pdf_to_text"
    assert "AgentPDF local text layer" in text["usage"]["text"]
    assert metadata["usage"]["metadata"]["Title"] == "Original Title"
