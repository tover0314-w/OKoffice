import json
import re
from pathlib import Path

from agentpdf.tools.registry import IMPLEMENTED_TOOLS, get_tool, load_tool_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_registry_loads_complete_public_manifest() -> None:
    manifest = load_tool_manifest()

    assert len(manifest.tools) >= 100
    assert get_tool("agent.setup.claude_code").implemented is True
    assert get_tool("pdf.inspect.document").name == "pdf.inspect.document"
    assert get_tool("pdf.inspect.pages").implemented is True
    assert get_tool("pdf.organize.merge").implemented is True
    assert get_tool("pdf.organize.split").implemented is True
    assert get_tool("pdf.organize.extract_pages").implemented is True
    assert get_tool("pdf.organize.remove_pages").implemented is True
    assert get_tool("pdf.organize.rotate_pages").implemented is True
    assert get_tool("pdf.organize.reorder_pages").implemented is True
    assert get_tool("pdf.organize.insert_blank_pages").implemented is True
    assert get_tool("pdf.optimize.compress").implemented is True
    assert get_tool("pdf.optimize.repair").implemented is True
    assert get_tool("pdf.convert.pdf_to_images").implemented is True
    assert get_tool("pdf.convert.extract_images").implemented is True
    assert get_tool("pdf.convert.pdf_to_text").implemented is True
    assert get_tool("pdf.convert.pdf_to_json").implemented is True
    assert get_tool("pdf.convert.pdf_to_markdown").implemented is True
    assert get_tool("pdf.convert.image_to_pdf").implemented is True
    assert get_tool("pdf.convert.text_to_pdf").implemented is True
    assert get_tool("pdf.convert.markdown_to_pdf").implemented is True
    assert get_tool("pdf.edit.watermark").implemented is True
    assert get_tool("pdf.edit.page_numbers").implemented is True
    assert get_tool("pdf.metadata.read").implemented is True
    assert get_tool("pdf.metadata.update").implemented is True
    assert get_tool("pdf.metadata.remove").implemented is True
    assert get_tool("pdf.validation.validate_output").implemented is True
    assert get_tool("pdf.validation.render_check").implemented is True
    assert get_tool("pdf.validation.blank_page_check").implemented is True
    assert get_tool("pdf.ai.create.from_prompt").implemented is True
    assert get_tool("pdf.ai.create.template_preview").implemented is True
    assert get_tool("pdf.ai.create.templates").implemented is True
    assert get_tool("pdf.ai.create.template_packs").implemented is True
    assert get_tool("pdf.ai.create.validate_template_pack").implemented is True
    assert get_tool("pdf.ai.create.from_template_pack").implemented is True
    assert get_tool("pdf.ai.rag.cite_answer").implemented is True
    assert get_tool("pdf.ai.rag.chat").implemented is True
    assert get_tool("pdf.ai.rag.export_report").implemented is True
    assert get_tool("pdf.ai.rag.highlight_sources").implemented is True
    assert get_tool("pdf.workflow.plan").implemented is True
    assert get_tool("pdf.workflow.run").implemented is True
    assert get_tool("pdf.workflow.report").implemented is True
    assert get_tool("pdf.context.build_packet").implemented is True
    assert get_tool("pdf.compose.from_context").implemented is True
    assert get_tool("pdf.target.profiles").implemented is True
    assert get_tool("pdf.target.validate_profile").implemented is True
    assert get_tool("pdf.evidence.coverage_report").implemented is True
    assert get_tool("pdf.artifacts.export_bundle").implemented is True
    assert get_tool("pdf.patch.plan").implemented is True
    assert get_tool("pdf.patch.preview").implemented is True
    assert get_tool("pdf.patch.apply").implemented is True
    assert get_tool("pdf.patch.verify").implemented is True


def test_status_matrix_tools_are_discoverable_in_full_manifest() -> None:
    matrix_path = REPO_ROOT / "docs" / "23_FULL_TOOL_STATUS_MATRIX.md"
    matrix_text = matrix_path.read_text(encoding="utf-8")
    total_match = re.search(r"Total tools specified: \*\*(\d+)\*\*", matrix_text)
    matrix_tools = set()
    for line in matrix_text.splitlines():
        match = re.match(r"\| `([^`]+)` \|", line)
        if match:
            matrix_tools.add(match.group(1))

    manifest_tools = {tool.name for tool in load_tool_manifest().tools}
    manifest_path = REPO_ROOT / "schemas" / "tool-manifest.full.json"
    manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert total_match is not None
    assert int(total_match.group(1)) == len(matrix_tools)
    assert manifest_json["tool_count"] == len(manifest_tools)
    assert sorted(matrix_tools - manifest_tools) == []
    assert sorted(manifest_tools - matrix_tools) == []


def test_stable_tools_are_implemented() -> None:
    stable_unimplemented = [
        tool.name for tool in load_tool_manifest().tools if tool.status == "stable" and not tool.implemented
    ]

    assert stable_unimplemented == []


def test_registry_keeps_planned_tools_discoverable() -> None:
    tool = get_tool("pdf.ai.parse.agentic")

    assert tool.status == "cloud_only"
    assert tool.implemented is False


def test_registry_marks_local_create_agent_as_beta() -> None:
    tool = get_tool("pdf.ai.create.from_prompt")
    preview_tool = get_tool("pdf.ai.create.template_preview")
    catalog_tool = get_tool("pdf.ai.create.templates")
    pack_tool = get_tool("pdf.ai.create.template_packs")

    assert tool.status == "beta"
    assert "cli" in tool.interfaces
    assert "mcp" in tool.interfaces
    assert preview_tool.status == "beta"
    assert "rest" in preview_tool.interfaces
    assert catalog_tool.status == "beta"
    assert "rest" in catalog_tool.interfaces
    assert pack_tool.status == "beta"
    assert "mcp" in pack_tool.interfaces


def test_implemented_tools_are_known_names() -> None:
    assert IMPLEMENTED_TOOLS == {
        "agent.setup.claude_code",
        "pdf.inspect.document",
        "pdf.inspect.pages",
        "pdf.organize.merge",
        "pdf.organize.split",
        "pdf.organize.extract_pages",
        "pdf.organize.remove_pages",
        "pdf.organize.rotate_pages",
        "pdf.organize.reorder_pages",
        "pdf.organize.insert_blank_pages",
        "pdf.optimize.compress",
        "pdf.optimize.repair",
        "pdf.convert.pdf_to_images",
        "pdf.convert.extract_images",
        "pdf.convert.pdf_to_text",
        "pdf.convert.pdf_to_json",
        "pdf.convert.pdf_to_markdown",
        "pdf.convert.image_to_pdf",
        "pdf.convert.text_to_pdf",
        "pdf.convert.markdown_to_pdf",
        "pdf.edit.watermark",
        "pdf.edit.page_numbers",
        "pdf.metadata.read",
        "pdf.metadata.update",
        "pdf.metadata.remove",
        "pdf.validation.validate_output",
        "pdf.validation.render_check",
        "pdf.validation.blank_page_check",
        "pdf.ai.parse.lite",
        "pdf.ai.create.from_prompt",
        "pdf.ai.create.template_preview",
        "pdf.ai.create.templates",
        "pdf.ai.create.template_packs",
        "pdf.ai.create.validate_template_pack",
        "pdf.ai.create.plan_template_pack",
        "pdf.ai.create.agent",
        "pdf.ai.create.from_template_pack",
        "pdf.ai.rag.ingest",
        "pdf.ai.rag.query",
        "pdf.ai.rag.search",
        "pdf.ai.rag.cite_answer",
        "pdf.ai.rag.chat",
        "pdf.ai.rag.export_report",
        "pdf.ai.rag.highlight_sources",
        "pdf.workflow.plan",
        "pdf.workflow.run",
        "pdf.workflow.report",
        "pdf.context.build_packet",
        "pdf.compose.from_context",
        "pdf.target.profiles",
        "pdf.target.validate_profile",
        "pdf.evidence.coverage_report",
        "pdf.artifacts.export_bundle",
        "pdf.artifacts.verify_bundle",
        "pdf.patch.plan",
        "pdf.patch.preview",
        "pdf.patch.apply",
        "pdf.patch.verify",
    }
