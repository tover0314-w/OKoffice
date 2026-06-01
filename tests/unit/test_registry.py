from agentpdf.tools.registry import IMPLEMENTED_TOOLS, get_tool, load_tool_manifest


def test_registry_loads_complete_public_manifest() -> None:
    manifest = load_tool_manifest()

    assert len(manifest.tools) >= 100
    assert get_tool("pdf.inspect.document").name == "pdf.inspect.document"
    assert get_tool("pdf.organize.merge").implemented is True
    assert get_tool("pdf.organize.split").implemented is True
    assert get_tool("pdf.organize.extract_pages").implemented is True
    assert get_tool("pdf.organize.remove_pages").implemented is True
    assert get_tool("pdf.organize.rotate_pages").implemented is True
    assert get_tool("pdf.convert.pdf_to_images").implemented is True
    assert get_tool("pdf.convert.pdf_to_text").implemented is True
    assert get_tool("pdf.convert.image_to_pdf").implemented is True
    assert get_tool("pdf.convert.text_to_pdf").implemented is True
    assert get_tool("pdf.convert.markdown_to_pdf").implemented is True
    assert get_tool("pdf.edit.watermark").implemented is True
    assert get_tool("pdf.edit.page_numbers").implemented is True
    assert get_tool("pdf.metadata.read").implemented is True
    assert get_tool("pdf.metadata.update").implemented is True
    assert get_tool("pdf.metadata.remove").implemented is True
    assert get_tool("pdf.validation.validate_output").implemented is True


def test_registry_keeps_planned_tools_discoverable() -> None:
    tool = get_tool("pdf.ai.parse.agentic")

    assert tool.status == "cloud_only"
    assert tool.implemented is False


def test_implemented_tools_are_known_names() -> None:
    assert IMPLEMENTED_TOOLS == {
        "pdf.inspect.document",
        "pdf.organize.merge",
        "pdf.organize.split",
        "pdf.organize.extract_pages",
        "pdf.organize.remove_pages",
        "pdf.organize.rotate_pages",
        "pdf.convert.pdf_to_images",
        "pdf.convert.pdf_to_text",
        "pdf.convert.image_to_pdf",
        "pdf.convert.text_to_pdf",
        "pdf.convert.markdown_to_pdf",
        "pdf.edit.watermark",
        "pdf.edit.page_numbers",
        "pdf.metadata.read",
        "pdf.metadata.update",
        "pdf.metadata.remove",
        "pdf.validation.validate_output",
    }
