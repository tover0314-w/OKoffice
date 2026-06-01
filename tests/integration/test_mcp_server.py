import json
import asyncio
from pathlib import Path

from PIL import Image

from agentpdf.mcp.server import (
    create_mcp_server,
    pdf_add_page_numbers,
    pdf_create_markdown,
    pdf_create_text,
    pdf_extract_text,
    pdf_extract_pages,
    pdf_image_to_pdf,
    pdf_inspect_document,
    pdf_merge,
    pdf_metadata_read,
    pdf_render_pages,
    pdf_validate_output,
    pdf_watermark,
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
    assert "pdf_create_text" in tool_names
    assert "pdf_create_markdown" in tool_names
    assert "pdf_image_to_pdf" in tool_names
    assert "pdf_watermark" in tool_names
    assert "pdf_add_page_numbers" in tool_names
    assert "pdf_validate_output" in tool_names
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


def test_mcp_create_text_and_markdown(tmp_path: Path) -> None:
    text_output = tmp_path / "text.pdf"
    markdown_output = tmp_path / "markdown.pdf"

    text = json.loads(pdf_create_text("MCP created text", str(text_output)))
    markdown = json.loads(pdf_create_markdown("# MCP Report", str(markdown_output)))

    assert text["status"] == "succeeded"
    assert text["tool"] == "pdf.convert.text_to_pdf"
    assert markdown["status"] == "succeeded"
    assert markdown["tool"] == "pdf.convert.markdown_to_pdf"


def test_mcp_image_watermark_page_numbers_and_validate(tmp_path: Path) -> None:
    image = tmp_path / "cover.png"
    image_pdf = tmp_path / "cover.pdf"
    watermarked = tmp_path / "watermarked.pdf"
    numbered = tmp_path / "numbered.pdf"
    Image.new("RGB", (120, 80), color=(120, 40, 80)).save(image)

    image_result = json.loads(pdf_image_to_pdf([str(image)], str(image_pdf)))
    watermark = json.loads(pdf_watermark(str(image_pdf), "CONFIDENTIAL", str(watermarked)))
    page_numbers = json.loads(pdf_add_page_numbers(str(watermarked), str(numbered)))
    validate = json.loads(pdf_validate_output(str(numbered), expected_pages=1))

    assert image_result["tool"] == "pdf.convert.image_to_pdf"
    assert watermark["tool"] == "pdf.edit.watermark"
    assert page_numbers["tool"] == "pdf.edit.page_numbers"
    assert validate["status"] == "succeeded"
