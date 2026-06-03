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
    assert get_tool("pdf.optimize.subset_fonts").implemented is True
    assert get_tool("pdf.optimize.to_pdfa").implemented is True
    assert get_tool("pdf.convert.pdf_to_images").implemented is True
    assert get_tool("pdf.convert.extract_images").implemented is True
    assert get_tool("pdf.convert.pdf_to_text").implemented is True
    assert get_tool("pdf.convert.pdf_to_json").implemented is True
    assert get_tool("pdf.convert.pdf_to_markdown").implemented is True
    assert get_tool("pdf.convert.pdf_to_html").implemented is True
    assert get_tool("pdf.convert.pdf_to_docx").implemented is True
    assert get_tool("pdf.convert.pdf_to_pptx").implemented is True
    assert get_tool("pdf.convert.pdf_to_xlsx").implemented is True
    assert get_tool("pdf.convert.image_to_pdf").implemented is True
    assert get_tool("pdf.convert.html_to_pdf").implemented is True
    assert get_tool("pdf.render.html_package").implemented is True
    assert get_tool("pdf.convert.url_to_pdf").implemented is True
    assert get_tool("pdf.convert.docx_to_pdf").implemented is True
    assert get_tool("pdf.convert.pptx_to_pdf").implemented is True
    assert get_tool("pdf.convert.xlsx_to_pdf").implemented is True
    assert get_tool("pdf.convert.text_to_pdf").implemented is True
    assert get_tool("pdf.convert.markdown_to_pdf").implemented is True
    assert get_tool("pdf.context.image_analyze").implemented is True
    assert get_tool("pdf.edit.watermark").implemented is True
    assert get_tool("pdf.edit.page_numbers").implemented is True
    assert get_tool("pdf.metadata.read").implemented is True
    assert get_tool("pdf.metadata.update").implemented is True
    assert get_tool("pdf.metadata.remove").implemented is True
    assert get_tool("pdf.validation.validate_output").implemented is True
    assert get_tool("pdf.validation.render_check").implemented is True
    assert get_tool("pdf.validation.blank_page_check").implemented is True
    assert get_tool("pdf.forms.import_data").implemented is True
    assert get_tool("pdf.forms.create").implemented is True
    assert get_tool("pdf.forms.validate").implemented is True
    assert get_tool("pdf.security.protect").implemented is True
    assert get_tool("pdf.security.decrypt_authorized").implemented is True
    assert get_tool("pdf.security.malware_scan").implemented is True
    assert get_tool("pdf.ocr_scan.ocr").implemented is True
    assert get_tool("pdf.ocr_scan.searchable_pdf").implemented is True
    assert get_tool("pdf.ocr_scan.scan_to_pdf").implemented is True
    assert get_tool("pdf.compare.semantic_diff").implemented is True
    assert get_tool("pdf.compare.version_report").implemented is True
    assert get_tool("pdf.ai.parse.figures").implemented is True
    assert get_tool("pdf.ai.parse.formulas").implemented is True
    assert get_tool("pdf.ai.parse.charts").implemented is True
    assert get_tool("pdf.ai.parse.references").implemented is True
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
    assert get_tool("pdf.authoring.plan").implemented is True
    assert get_tool("pdf.storyboard.plan").implemented is True
    assert get_tool("pdf.pages.write").implemented is True
    assert get_tool("pdf.create.html_package").implemented is True
    assert get_tool("pdf.qa.visual_report").implemented is True
    assert get_tool("pdf.workflow.research_deck").implemented is True
    assert get_tool("pdf.context.build_packet").implemented is True
    assert get_tool("pdf.compose.from_context").implemented is True
    assert get_tool("pdf.target.profiles").implemented is True
    assert get_tool("pdf.target.validate_profile").implemented is True
    assert get_tool("pdf.evidence.map_sources").implemented is True
    assert get_tool("pdf.evidence.cite_claims").implemented is True
    assert get_tool("pdf.evidence.coverage_report").implemented is True
    assert get_tool("pdf.artifacts.export_bundle").implemented is True
    assert get_tool("pdf.patch.plan").implemented is True
    assert get_tool("pdf.patch.preview").implemented is True
    assert get_tool("pdf.patch.apply").implemented is True
    assert get_tool("pdf.patch.verify").implemented is True


def test_authoring_tools_are_in_registry() -> None:
    manifest_path = REPO_ROOT / "schemas" / "tool-manifest.full.json"
    raw_tools = {
        tool["name"]: tool for tool in json.loads(manifest_path.read_text(encoding="utf-8"))["tools"]
    }
    expected_interfaces = {"cli", "mcp", "rest", "sdk"}
    implemented_tools = {
        "pdf.authoring.plan": "authoring",
        "pdf.storyboard.plan": "authoring",
        "pdf.pages.write": "authoring",
        "pdf.create.html_package": "authoring",
        "pdf.render.html_package": "render",
        "pdf.qa.visual_report": "validation",
        "pdf.workflow.createpdf": "workflow",
        "pdf.workflow.research_deck": "workflow",
        "pdf.research.plan": "research",
        "pdf.research.source_cards": "research",
        "pdf.research.evidence_cards": "research",
        "pdf.design.tokens": "authoring",
        "pdf.pages.revise": "authoring",
    }
    planned_tools = {
        "pdf.insights.synthesize": ("insights", True),
    }

    for name, category in implemented_tools.items():
        tool = get_tool(name)
        raw_tool = raw_tools[name]

        assert tool.status == "beta"
        assert tool.category == category
        assert set(tool.interfaces) == expected_interfaces
        assert tool.implemented is True
        assert raw_tool["implemented"] is True
        assert raw_tool["oss_default"] is True
        assert raw_tool["requires_model"] is False

    for name, (category, requires_model) in planned_tools.items():
        tool = get_tool(name)
        raw_tool = raw_tools[name]

        assert tool.status == "planned"
        assert tool.category == category
        assert set(tool.interfaces) == expected_interfaces
        assert tool.implemented is False
        assert raw_tool["implemented"] is False
        assert raw_tool["oss_default"] is False
        assert raw_tool["requires_model"] is requires_model


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


def test_raw_manifest_implemented_flags_match_registry() -> None:
    manifest_path = REPO_ROOT / "schemas" / "tool-manifest.full.json"
    manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_implemented_tools = {
        tool["name"] for tool in manifest_json["tools"] if tool.get("implemented") is True
    }

    assert raw_implemented_tools == IMPLEMENTED_TOOLS


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
        "agent.setup.codex",
        "agent.setup.kilo_code",
        "agent.setup.openclaw",
        "pdf.inspect.document",
        "pdf.inspect.pages",
        "pdf.inspect.health",
        "pdf.organize.merge",
        "pdf.organize.split",
        "pdf.organize.extract_pages",
        "pdf.organize.remove_pages",
        "pdf.organize.rotate_pages",
        "pdf.organize.reorder_pages",
        "pdf.organize.insert_blank_pages",
        "pdf.organize.n_up",
        "pdf.organize.booklet",
        "pdf.optimize.compress",
        "pdf.optimize.repair",
        "pdf.optimize.remove_unused_objects",
        "pdf.optimize.subset_fonts",
        "pdf.optimize.to_pdfa",
        "pdf.optimize.validate_pdfa",
        "pdf.convert.pdf_to_images",
        "pdf.convert.extract_images",
        "pdf.convert.extract_fonts",
        "pdf.convert.pdf_to_text",
        "pdf.convert.pdf_to_html",
        "pdf.convert.pdf_to_docx",
        "pdf.convert.pdf_to_pptx",
        "pdf.convert.pdf_to_xlsx",
        "pdf.convert.pdf_to_json",
        "pdf.convert.pdf_to_markdown",
        "pdf.convert.image_to_pdf",
        "pdf.convert.html_to_pdf",
        "pdf.render.html_package",
        "pdf.convert.url_to_pdf",
        "pdf.convert.docx_to_pdf",
        "pdf.convert.pptx_to_pdf",
        "pdf.convert.xlsx_to_pdf",
        "pdf.convert.text_to_pdf",
        "pdf.convert.markdown_to_pdf",
        "pdf.edit.watermark",
        "pdf.edit.page_numbers",
        "pdf.edit.add_shape",
        "pdf.edit.underline",
        "pdf.edit.strikeout",
        "pdf.edit.freehand_draw",
        "pdf.edit.resize_pages",
        "pdf.edit.add_margin",
        "pdf.edit.underlay",
        "pdf.metadata.read",
        "pdf.metadata.update",
        "pdf.metadata.remove",
        "pdf.metadata.page_info",
        "pdf.metadata.update_outline",
        "pdf.validation.validate_output",
        "pdf.validation.page_count_check",
        "pdf.validation.render_check",
        "pdf.validation.blank_page_check",
        "pdf.validation.visual_diff",
        "pdf.validation.redaction_check",
        "pdf.forms.import_data",
        "pdf.forms.create",
        "pdf.forms.validate",
        "pdf.ocr_scan.ocr",
        "pdf.ocr_scan.searchable_pdf",
        "pdf.ocr_scan.despeckle",
        "pdf.ocr_scan.remove_existing_ocr",
        "pdf.ocr_scan.scan_to_pdf",
        "pdf.ocr_scan.multilingual_ocr",
        "pdf.security.protect",
        "pdf.security.unlock_authorized",
        "pdf.security.encrypt",
        "pdf.security.decrypt_authorized",
        "pdf.security.sign",
        "pdf.security.verify_signature",
        "pdf.security.remove_metadata",
        "pdf.security.malware_scan",
        "pdf.security.sanitize",
        "pdf.security.redact",
        "pdf.security.verify_redaction",
        "pdf.compare.semantic_diff",
        "pdf.compare.visual_diff",
        "pdf.compare.version_report",
        "pdf.ai.parse.lite",
        "pdf.ai.parse.figures",
        "pdf.ai.parse.formulas",
        "pdf.ai.parse.charts",
        "pdf.ai.parse.references",
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
        "pdf.workflow.createpdf",
        "pdf.authoring.plan",
        "pdf.research.plan",
        "pdf.research.source_cards",
        "pdf.research.evidence_cards",
        "pdf.storyboard.plan",
        "pdf.pages.write",
        "pdf.design.tokens",
        "pdf.pages.revise",
        "pdf.create.html_package",
        "pdf.qa.visual_report",
        "pdf.workflow.research_deck",
        "pdf.context.ingest",
        "pdf.context.packet",
        "pdf.context.build_packet",
        "pdf.context.classify",
        "pdf.context.code_snapshot",
        "pdf.context.data_profile",
        "pdf.context.image_analyze",
        "pdf.compose.plan",
        "pdf.compose.from_context",
        "pdf.compose.render_ir",
        "pdf.compose.add_code_block",
        "pdf.compose.add_figure",
        "pdf.compose.add_table",
        "pdf.compose.add_appendix",
        "pdf.compose.add_citation",
        "pdf.compose.add_media_reference",
        "pdf.compose.add_slide",
        "pdf.target.profiles",
        "pdf.target.select_profile",
        "pdf.target.validate_profile",
        "pdf.artifacts.graph",
        "pdf.artifacts.manifest",
        "pdf.artifacts.source_map",
        "pdf.evidence.map_sources",
        "pdf.evidence.cite_claims",
        "pdf.evidence.coverage_report",
        "pdf.evidence.context_packet_report",
        "pdf.artifacts.export_bundle",
        "pdf.artifacts.verify_bundle",
        "pdf.patch.plan",
        "pdf.patch.preview",
        "pdf.patch.apply",
        "pdf.patch.verify",
    }
