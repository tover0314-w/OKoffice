import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from PIL import Image
from pypdf import PdfReader
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.context.packet import build_context_packet
from agentpdf.core.pdf import inspect_pdf_pages
from agentpdf.creation.agent import (
    create_pdf_from_template_pack,
    create_pdf_with_agent,
    list_template_packs,
    plan_template_pack_creation,
    validate_template_pack,
)
from agentpdf.evidence.coverage import create_coverage_report
from agentpdf.mcp.server import (
    pdf_ai_create_agent,
    pdf_ai_create_from_template_pack,
    pdf_ai_create_plan_template_pack,
    pdf_ai_create_template_packs,
    pdf_ai_create_validate_template_pack,
    pdf_patch_plan,
)
from agentpdf.patch.transaction import (
    apply_patch_transaction,
    plan_patch_transaction,
    preview_patch_transaction,
    verify_patch_transaction,
)
from agentpdf.tools.runner import run_patch_apply, run_patch_plan, run_patch_preview, run_patch_verify


runner = CliRunner()


def _example_pack() -> dict[str, object]:
    return {
        "pack_id": "local_agent_documents",
        "name": "Local Agent Documents",
        "version": "0.1.0",
        "description": "Reusable local templates for agent-generated PDFs.",
        "license": "Apache-2.0",
        "templates": [
            {
                "template_id": "board_audit",
                "name": "Board Audit Packet",
                "description": "A technical audit report for leadership review.",
                "base_template": "business_report",
                "target_profile": "technical_audit",
                "default_style_pack": "business_report_modern",
                "fields": {
                    "required": ["title", "sections"],
                    "optional": ["audience", "checklist"],
                },
                "layout_slots": ["cover", "executive_summary", "findings", "evidence"],
                "supported_block_types": ["section", "code", "table", "slide"],
                "color_schemes": {
                    "executive_blue": {
                        "primary": "#1f3a5f",
                        "accent": "#f59e0b",
                        "text": "#111827",
                    }
                },
                "sample_data": {
                    "title": "AgentPDF Board Audit",
                    "audience": "engineering leadership",
                    "sections": [
                        {
                            "heading": "Executive Summary",
                            "body": "Template packs let agents create validated PDFs locally.",
                        },
                        {
                            "heading": "Evidence",
                            "body": "Each output records template, color scheme, and validation details.",
                        },
                    ],
                    "checklist": ["Validate renderability", "Attach evidence coverage"],
                },
            }
        ],
    }


def test_template_pack_catalog_lists_agent_ready_templates() -> None:
    result = list_template_packs()

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.template_packs"
    catalog = result.usage["template_pack_catalog"]
    assert catalog["pack_count"] >= 1
    starter = catalog["packs"]["local_agent_starter"]
    assert starter["cloud_required"] is False
    assert "board_audit" in starter["template_ids"]
    assert "executive_blue" in starter["color_scheme_ids"]
    assert "pdf.ai.create.from_template_pack" in result.next_recommended_tools


def test_template_pack_catalog_includes_kami_like_local_templates() -> None:
    result = list_template_packs()

    starter = result.usage["template_pack_catalog"]["packs"]["local_agent_starter"]
    template_ids = set(starter["template_ids"])

    assert {
        "board_audit",
        "research_brief_packet",
        "evidence_packet",
        "agent_resume",
        "client_invoice",
        "project_proposal",
        "lesson_worksheet",
        "media_review_deck",
    }.issubset(template_ids)
    assert starter["template_count"] >= 8
    assert "resume_ink" in starter["color_scheme_ids"]
    assert "invoice_gold" in starter["color_scheme_ids"]
    assert "proposal_violet" in starter["color_scheme_ids"]


def test_template_pack_planner_selects_specialized_templates_by_target_profile(tmp_path: Path) -> None:
    research = plan_template_pack_creation(
        "local_agent_starter",
        target_profile="research_brief",
        planned_output_path=tmp_path / "research.pdf",
    )
    evidence = plan_template_pack_creation(
        "local_agent_starter",
        target_profile="evidence_packet_pdf",
        planned_output_path=tmp_path / "evidence.pdf",
    )
    resume = plan_template_pack_creation(
        "local_agent_starter",
        target_profile="resume_pdf",
        planned_output_path=tmp_path / "resume.pdf",
    )

    assert research.usage["template_pack_plan"]["selected_template_id"] == "research_brief_packet"
    assert evidence.usage["template_pack_plan"]["selected_template_id"] == "evidence_packet"
    assert resume.usage["template_pack_plan"]["selected_template_id"] == "agent_resume"
    assert resume.usage["template_pack_plan"]["target_profile_known"] is True


def test_validate_template_pack_reports_agent_contract(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "template-pack.validation.json"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")

    result = validate_template_pack(pack_path, output_path=output_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.validate_template_pack"
    report = result.usage["template_pack_validation"]
    assert report["is_valid"] is True
    assert report["pack_id"] == "local_agent_documents"
    assert report["template_count"] == 1
    assert report["templates"][0]["template_id"] == "board_audit"
    assert report["templates"][0]["agent_ready"] is True
    assert report["templates"][0]["supported_block_types"] == ["section", "code", "table", "slide"]
    assert output_path.exists()


def test_validate_template_pack_rejects_unknown_supported_block_type(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = ["section", "unknown_widget"]
    pack_path = tmp_path / "template-pack.json"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")

    result = validate_template_pack(pack_path)

    report = result.usage["template_pack_validation"]
    assert result.status == "failed"
    assert report["is_valid"] is False
    assert "unsupported block type" in report["templates"][0]["errors"][0]


def test_template_pack_planner_selects_template_from_context_and_profile(tmp_path: Path) -> None:
    image_path = tmp_path / "diagram.png"
    Image.new("RGB", (80, 48), color=(31, 58, 95)).save(image_path)
    packet_path = tmp_path / "planner-context.packet.json"
    planned_pdf = tmp_path / "planned-board-audit.pdf"
    plan_path = tmp_path / "template-pack.plan.json"
    build_context_packet(
        [
            {
                "context_item_id": "ctx_brief",
                "text": "Create a technical audit PDF for leadership.",
                "label": "Planner Brief",
            },
            {
                "context_item_id": "ctx_code",
                "path": "src/agentpdf/creation/agent.py",
                "label": "Creation Agent Code",
            },
            {
                "context_item_id": "ctx_metrics",
                "table": {
                    "columns": ["metric", "value"],
                    "rows": [["coverage", "1.0"], ["routes", "8"]],
                },
                "label": "Planner Metrics",
            },
            {"context_item_id": "ctx_image", "path": str(image_path), "label": "Planner Diagram"},
            {
                "context_item_id": "ctx_link",
                "uri": "https://example.com/template-planning",
                "label": "Planner Reference",
            },
        ],
        output_path=packet_path,
        title="Planner Context",
    )

    result = plan_template_pack_creation(
        "examples/template-packs/local-agent-starter.json",
        target_profile="technical_audit",
        context_packet_path=packet_path,
        planned_output_path=planned_pdf,
        output_path=plan_path,
    )

    plan = result.usage["template_pack_plan"]
    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_schema = json.loads(Path("schemas/template-pack-plan.schema.json").read_text(encoding="utf-8"))
    candidates = plan["candidates"]

    assert list(Draft202012Validator(plan_schema).iter_errors(plan)) == []
    assert result.tool == "pdf.ai.create.plan_template_pack"
    assert result.status == "succeeded"
    assert plan["selected_template_id"] == "board_audit"
    assert plan["selected_color_scheme"] == "executive_blue"
    assert plan["selected_style_pack"] == "business_report_modern"
    assert plan["target_profile"] == "technical_audit"
    assert plan["context_block_type_counts"] == {
        "section": 1,
        "code": 1,
        "table": 1,
        "image": 1,
        "citation": 1,
    }
    assert candidates[0]["template_id"] == "board_audit"
    assert candidates[0]["target_profile_match"] is True
    assert candidates[0]["matched_block_types"] == ["citation", "code", "image", "section", "table"]
    assert candidates[0]["unsupported_context_block_types"] == []
    assert candidates[0]["score"] > candidates[1]["score"]
    assert plan["create_payload"] == {
        "template_pack_path": "examples/template-packs/local-agent-starter.json",
        "template_id": "board_audit",
        "color_scheme": "executive_blue",
        "context_packet_path": str(packet_path),
        "output_path": str(planned_pdf),
    }
    assert plan["preview_payload"] == {
        "template": "business_report",
        "output_path": str(planned_pdf.with_suffix(".preview.pdf")),
        "style_pack": "business_report_modern",
    }
    assert saved_plan == plan
    assert "pdf.ai.create.from_template_pack" in result.next_recommended_tools


def test_template_pack_create_agent_runs_plan_create_and_validation_chain(tmp_path: Path) -> None:
    image_path = tmp_path / "agent-diagram.png"
    Image.new("RGB", (96, 64), color=(15, 118, 110)).save(image_path)
    packet_path = tmp_path / "create-agent-context.packet.json"
    output_path = tmp_path / "create-agent-board-audit.pdf"
    plan_path = tmp_path / "create-agent.plan.json"
    coverage_path = tmp_path / "create-agent.coverage.json"
    context_classification_path = output_path.with_suffix(".context-classification.json")
    context_report_pdf_path = tmp_path / "create-agent.context-report.pdf"
    context_report_json_path = tmp_path / "create-agent.context-report.json"
    bundle_path = tmp_path / "create-agent.agentpdf-bundle.zip"
    build_context_packet(
        [
            {"context_item_id": "ctx_brief", "text": "Create a technical audit PDF.", "label": "Brief"},
            {"context_item_id": "ctx_code", "path": "src/agentpdf/creation/agent.py", "label": "Code"},
            {
                "context_item_id": "ctx_metrics",
                "table": {"columns": ["metric", "value"], "rows": [["coverage", "1.0"]]},
                "label": "Metrics",
            },
            {"context_item_id": "ctx_image", "path": str(image_path), "label": "Diagram"},
            {"context_item_id": "ctx_link", "uri": "https://example.com/create-agent", "label": "Reference"},
        ],
        output_path=packet_path,
        title="Create Agent Context",
    )

    result = create_pdf_with_agent(
        "examples/template-packs/local-agent-starter.json",
        target_profile="technical_audit",
        context_packet_path=packet_path,
        output_path=output_path,
        plan_output_path=plan_path,
        coverage_output_path=coverage_path,
        context_report_output_path=context_report_pdf_path,
        context_report_json_output_path=context_report_json_path,
        bundle_output_path=bundle_path,
    )

    run = result.usage["create_agent_run"]
    run_schema = json.loads(Path("schemas/create-agent-run.schema.json").read_text(encoding="utf-8"))

    assert list(Draft202012Validator(run_schema).iter_errors(run)) == []
    assert result.tool == "pdf.ai.create.agent"
    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output_path.exists()
    assert output_path.with_suffix(".composition.json").exists()
    assert plan_path.exists()
    assert coverage_path.exists()
    assert context_classification_path.exists()
    assert context_report_pdf_path.exists()
    assert context_report_json_path.exists()
    assert bundle_path.exists()
    assert run["status"] == "succeeded"
    assert run["selected_template_id"] == "board_audit"
    assert run["selected_color_scheme"] == "executive_blue"
    assert run["step_order"] == [
        "pdf.ai.create.plan_template_pack",
        "pdf.context.classify",
        "pdf.evidence.context_packet_report",
        "pdf.ai.create.from_template_pack",
        "pdf.validation.render_check",
        "pdf.validation.blank_page_check",
        "pdf.evidence.coverage_report",
        "pdf.artifacts.export_bundle",
        "pdf.artifacts.verify_bundle",
    ]
    assert run["output_pdf_path"] == str(output_path.resolve())
    assert run["composition_path"] == str(output_path.with_suffix(".composition.json").resolve())
    assert run["template_layer_manifest_path"] == str(output_path.with_suffix(".layers.json").resolve())
    assert run["template_layer_manifest"]["template_id"] == "board_audit"
    assert run["template_layer_manifest"]["layer_count"] == len(run["create_result"]["usage"]["composition_ir"]["blocks"])
    assert run["plan_path"] == str(plan_path.resolve())
    assert run["coverage_path"] == str(coverage_path.resolve())
    assert run["context_classification_path"] == str(context_classification_path.resolve())
    assert run["context_report_path"] == str(context_report_pdf_path.resolve())
    assert run["context_report_json_path"] == str(context_report_json_path.resolve())
    assert run["bundle_path"] == str(bundle_path.resolve())
    assert run["context_classification"]["tool"] == "pdf.context.classify"
    assert run["context_classification"]["usage"]["classification_count"] == 5
    assert run["context_classification"]["usage"]["type_counts"] == {
        "code": 1,
        "data": 1,
        "image": 1,
        "text": 1,
        "web_link": 1,
    }
    assert "Web links are not fetched by local classification." in run["context_classification"]["warnings"]
    assert run["context_packet_report"]["tool"] == "pdf.evidence.context_packet_report"
    assert run["context_packet_report"]["validation"]["status"] == "passed"
    assert run["context_packet_report"]["usage"]["source_ref_count"] == 5
    assert run["bundle_export"]["tool"] == "pdf.artifacts.export_bundle"
    assert run["bundle_verification"]["validation"]["status"] == "passed"
    assert run["bundle_export"]["usage"]["file_count"] >= 7
    assert run["render_check"]["validation"]["status"] == "passed"
    assert run["blank_page_check"]["usage"]["blank_pages"] == []
    assert run["coverage_report"]["usage"]["coverage"]["coverage_ratio"] == 1.0
    assert run["validation_summary"]["context_classification"] == "succeeded"
    assert run["validation_summary"]["context_packet_report"] == "passed"
    assert run["validation_summary"]["bundle_verification"] == "passed"
    assert run["slot_routing_plan"]["warning_route_count"] == 0
    bundle_entries = run["bundle_export"]["usage"]["bundle_entries"]
    assert "artifacts/create-agent-board-audit.context-classification.json" in bundle_entries
    assert "artifacts/create-agent.context-report.pdf" in bundle_entries
    assert "artifacts/create-agent.context-report.json" in bundle_entries
    assert "artifacts/create-agent.coverage.json" in bundle_entries
    assert "pdf.patch.plan" in result.next_recommended_tools
    assert "pdf.artifacts.export_bundle" in result.next_recommended_tools


def test_create_pdf_from_template_pack_writes_validated_pdf(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit.pdf"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.from_template_pack"
    assert result.artifacts[0].mime_type == "application/pdf"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["pack_id"] == "local_agent_documents"
    assert result.usage["template_id"] == "board_audit"
    assert result.usage["base_template"] == "business_report"
    assert result.usage["color_scheme"] == "executive_blue"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_path).pages)
    assert "AgentPDF Board Audit" in text
    assert "Template packs let agents create validated PDFs locally" in text


def test_create_pdf_from_template_pack_writes_composition_and_coverage(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit.pdf"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
    )

    composition_path = output_path.with_suffix(".composition.json")
    layer_path = output_path.with_suffix(".layers.json")
    assert composition_path.exists()
    assert layer_path.exists()
    assert [artifact.mime_type for artifact in result.artifacts] == [
        "application/pdf",
        "application/json",
        "application/json",
    ]
    assert result.artifacts[1].path == composition_path.resolve()
    assert result.artifacts[2].path == layer_path.resolve()
    assert result.usage["composition_path"] == composition_path.as_posix()
    assert result.usage["template_layer_manifest_path"] == layer_path.as_posix()
    assert result.usage["composition_ir"]["target_profile_id"] == "technical_audit"
    assert result.usage["template_layer_manifest"]["composition_id"] == result.usage["composition_ir"][
        "composition_id"
    ]
    assert result.usage["composition_ir"]["blocks"][0]["source_refs"] == [
        "tpl://local_agent_documents/board_audit/sample_data"
    ]
    assert result.usage["source_map"][0]["source_ref"] == "tpl://local_agent_documents/board_audit/sample_data"
    assert result.usage["evidence_coverage"]["coverage_ratio"] == 1.0

    coverage = create_coverage_report(composition_path, output_path=tmp_path / "coverage.json")

    assert coverage.status == "succeeded"
    assert coverage.usage["coverage"]["coverage_ratio"] == 1.0
    assert coverage.usage["uncovered_blocks"] == []
    assert coverage.usage["source_refs"] == ["tpl://local_agent_documents/board_audit/sample_data"]


def test_template_pack_renders_agent_blocks_into_slots_and_source_map(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-blocks.pdf"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    data = {
        "title": "Agent Block Audit",
        "blocks": [
            {
                "block_id": "blk_agent_code",
                "type": "code",
                "title": "Risky Function",
                "target_slot": "evidence",
                "language": "python",
                "code": "def risky_total(items):\n    return sum(items)\n",
                "source_refs": ["ctx_code"],
            },
            {
                "block_id": "blk_agent_table",
                "type": "table",
                "title": "Runtime Metrics",
                "target_slot": "findings",
                "columns": ["metric", "value"],
                "rows": [["latency_ms", "42"], ["error_rate", "0.01"]],
                "source_refs": ["ctx_metrics"],
            },
            {
                "block_id": "blk_agent_slide",
                "type": "slide",
                "title": "Decision Slide",
                "target_slot": "recommendations",
                "body": ["Keep local validation before sharing."],
                "source_refs": ["ctx_decision"],
            },
        ],
    }

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )

    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_path).pages)
    blocks = {block["block_id"]: block for block in result.usage["composition_ir"]["blocks"]}
    source_map = result.usage["source_map"]
    covered_refs = set(result.usage["evidence_coverage"]["covered_source_refs"])

    assert "Risky Function" in text
    assert "risky_total" in text
    assert "Runtime Metrics" in text
    assert "latency_ms" in text
    assert "Decision Slide" in text
    assert blocks["blk_agent_code"]["type"] == "code"
    assert blocks["blk_agent_code"]["target_slot"] == "evidence"
    assert blocks["blk_agent_code"]["source_refs"] == ["ctx_code"]
    assert blocks["blk_agent_table"]["type"] == "table"
    assert blocks["blk_agent_slide"]["type"] == "slide"
    assert {
        (entry["block_id"], entry["source_ref"], entry["target_slot"])
        for entry in source_map
    } >= {
        ("blk_agent_code", "ctx_code", "evidence"),
        ("blk_agent_table", "ctx_metrics", "findings"),
        ("blk_agent_slide", "ctx_decision", "recommendations"),
    }
    source_kinds = {entry["source_ref"]: entry["source_kind"] for entry in source_map}
    assert source_kinds["ctx_code"] == "agent_context"
    assert source_kinds["ctx_metrics"] == "agent_context"
    assert source_kinds["ctx_decision"] == "agent_context"
    assert {"ctx_code", "ctx_metrics", "ctx_decision"} <= covered_refs


def test_template_pack_renders_image_and_citation_blocks_with_evidence(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-visual.pdf"
    image_path = tmp_path / "agent-figure.png"
    Image.new("RGB", (64, 32), color=(31, 58, 95)).save(image_path)
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    data = {
        "title": "Visual Evidence Audit",
        "blocks": [
            {
                "block_id": "blk_agent_image",
                "type": "image",
                "title": "Architecture Figure",
                "target_slot": "evidence",
                "path": str(image_path),
                "caption": "Generated architecture figure used as local visual evidence.",
                "source_refs": ["path://agent-figure.png"],
            },
            {
                "block_id": "blk_agent_citation",
                "type": "citation",
                "title": "Reference Note",
                "target_slot": "recommendations",
                "quote": "Local outputs need evidence and validation.",
                "source": "https://example.com/local-pdf-agents",
                "page": "4",
                "source_refs": ["https://example.com/local-pdf-agents"],
            },
        ],
    }

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )

    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_path).pages)
    blocks = {block["block_id"]: block for block in result.usage["composition_ir"]["blocks"]}
    source_kinds = {entry["source_ref"]: entry["source_kind"] for entry in result.usage["source_map"]}
    page_facts = inspect_pdf_pages(output_path, pages="all")
    image_counts = [page["image_count"] for page in page_facts["pages"]]

    assert "Architecture Figure" in text
    assert "Generated architecture figure used as local visual evidence" in text
    assert "Reference Note" in text
    assert "Local outputs need evidence and validation" in text
    assert max(image_counts) >= 1
    assert blocks["blk_agent_image"]["type"] == "image"
    assert blocks["blk_agent_image"]["data"]["image_evidence"] == {
        "exists": True,
        "width": 64,
        "height": 32,
        "mime_type": "image/png",
    }
    assert blocks["blk_agent_citation"]["type"] == "citation"
    assert source_kinds["path://agent-figure.png"] == "local_file"
    assert source_kinds["https://example.com/local-pdf-agents"] == "web_link"
    assert {
        "path://agent-figure.png",
        "https://example.com/local-pdf-agents",
    } <= set(result.usage["evidence_coverage"]["covered_source_refs"])


def test_template_pack_html_renderer_writes_html_package_and_pdf(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-html.pdf"
    html_output = tmp_path / "board-audit-html.html"
    image_path = tmp_path / "agent-figure.png"
    Image.new("RGB", (64, 32), color=(31, 58, 95)).save(image_path)
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    data = {
        "title": "HTML Template Pack Audit",
        "blocks": [
            {
                "block_id": "blk_agent_image",
                "type": "image",
                "title": "Architecture Figure",
                "target_slot": "evidence",
                "path": str(image_path),
                "caption": "Local visual evidence rendered through the HTML package.",
                "source_refs": ["path://agent-figure.png"],
            }
        ],
    }

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
        renderer="html",
        html_output_path=html_output,
    )

    manifest_path = html_output.with_suffix(".html-manifest.json")
    html_text = html_output.read_text(encoding="utf-8")
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(output_path).pages)

    assert result.status == "succeeded"
    assert result.tool == "pdf.ai.create.from_template_pack"
    assert output_path.exists()
    assert html_output.exists()
    assert manifest_path.exists()
    assert result.usage["renderer"] == "html_package"
    assert result.usage["html_output_path"] == str(html_output.resolve())
    assert result.usage["html_package_manifest_path"] == str(manifest_path.resolve())
    assert result.usage["html_package_manifest"]["asset_count"] == 1
    assert result.usage["html_package_manifest"]["assets"][0]["source_path"] == str(image_path.resolve())
    assert result.usage["html_package_validation"]["status"] == "passed"
    assert any(check.name == "html_package_manifest_valid" for check in result.validation.checks)
    assert any(check.name == "all_assets_resolved" for check in result.validation.checks)
    assert any(str(artifact.path).endswith(".html") for artifact in result.artifacts)
    assert any(str(artifact.path).endswith(".html-manifest.json") for artifact in result.artifacts)
    assert '<img src="./board-audit-html.assets/' in html_text
    assert "HTML Template Pack Audit" in pdf_text
    assert "Architecture Figure" in pdf_text
    assert "Local visual evidence rendered through the HTML package" in pdf_text


def test_template_pack_html_renderer_is_exposed_to_cli_rest_mcp(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    cli_pdf = tmp_path / "cli-board-audit-html.pdf"
    cli_html = tmp_path / "cli-board-audit-html.html"
    api_pdf = tmp_path / "api-board-audit-html.pdf"
    api_html = tmp_path / "api-board-audit-html.html"
    mcp_pdf = tmp_path / "mcp-board-audit-html.pdf"
    mcp_html = tmp_path / "mcp-board-audit-html.html"

    cli_result = runner.invoke(
        app,
        [
            "create",
            "from-template-pack",
            str(pack_path),
            "--template",
            "board_audit",
            "--color-scheme",
            "executive_blue",
            "-o",
            str(cli_pdf),
            "--renderer",
            "html",
            "--html-output",
            str(cli_html),
            "--json",
        ],
    )
    api = TestClient(create_app())
    api_response = api.post(
        "/v1/tools/pdf.ai.create.from_template_pack/run",
        json={
            "template_pack": str(pack_path),
            "template_id": "board_audit",
            "color_scheme": "executive_blue",
            "output_path": str(api_pdf),
            "renderer": "html",
            "html_output_path": str(api_html),
        },
    )
    mcp_payload = json.loads(
        pdf_ai_create_from_template_pack(
            str(pack_path),
            template_id="board_audit",
            output_path=str(mcp_pdf),
            color_scheme="executive_blue",
            renderer="html",
            html_output_path=str(mcp_html),
        )
    )

    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["tool"] == "pdf.ai.create.from_template_pack"
    assert cli_payload["usage"]["renderer"] == "html_package"
    assert cli_pdf.exists()
    assert cli_html.exists()
    assert cli_html.with_suffix(".html-manifest.json").exists()
    assert api_response.status_code == 200
    assert api_response.json()["usage"]["renderer"] == "html_package"
    assert api_pdf.exists()
    assert api_html.exists()
    assert api_html.with_suffix(".html-manifest.json").exists()
    assert mcp_payload["tool"] == "pdf.ai.create.from_template_pack"
    assert mcp_payload["usage"]["renderer"] == "html_package"
    assert mcp_pdf.exists()
    assert mcp_html.exists()
    assert mcp_html.with_suffix(".html-manifest.json").exists()


def test_template_pack_maps_context_packet_to_agent_blocks(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-context.pdf"
    packet_path = tmp_path / "audit.context.json"
    code_path = tmp_path / "risk.py"
    image_path = tmp_path / "architecture.png"
    code_path.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    Image.new("RGB", (80, 40), color=(15, 118, 110)).save(image_path)
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    build_context_packet(
        [
            {
                "context_item_id": "ctx_brief",
                "text": "Create a board audit from supplied context.",
                "role": "brief",
                "label": "Audit Brief",
            },
            {
                "context_item_id": "ctx_code",
                "path": str(code_path),
                "role": "code_evidence",
                "label": "Risk Function",
            },
            {
                "context_item_id": "ctx_metrics",
                "table": {
                    "columns": ["metric", "value"],
                    "rows": [["latency_ms", "42"], ["error_rate", "0.01"]],
                },
                "role": "data_evidence",
                "label": "Runtime Metrics",
            },
            {
                "context_item_id": "ctx_image",
                "path": str(image_path),
                "role": "image_evidence",
                "label": "Architecture Figure",
            },
            {
                "context_item_id": "ctx_link",
                "uri": "https://example.com/local-agent-patterns",
                "role": "citation",
                "label": "Agent Pattern Reference",
            },
        ],
        output_path=packet_path,
        title="Audit Context",
    )

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        context_packet_path=packet_path,
        title="Context Packet Board Audit",
    )

    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_path).pages)
    blocks = {block["block_id"]: block for block in result.usage["composition_ir"]["blocks"]}
    source_kinds = {entry["source_ref"]: entry["source_kind"] for entry in result.usage["source_map"]}
    page_facts = inspect_pdf_pages(output_path, pages="all")

    assert result.usage["context_packet_id"].startswith("ctxpkt_")
    assert result.usage["context_block_count"] == 5
    assert "Risk Function" in text
    assert "risky_total" in text
    assert "Runtime Metrics" in text
    assert "latency_ms" in text
    assert "Architecture Figure" in text
    assert "Agent Pattern Reference" in text
    assert "https://example.com/local-agent-patterns" in text
    assert max(page["image_count"] for page in page_facts["pages"]) >= 1
    assert blocks["blk_ctx_code"]["type"] == "code"
    assert blocks["blk_ctx_metrics"]["type"] == "table"
    assert blocks["blk_ctx_image"]["type"] == "image"
    assert blocks["blk_ctx_link"]["type"] == "citation"
    assert source_kinds["ctx_code"] == "agent_context"
    assert source_kinds["ctx_metrics"] == "agent_context"
    assert source_kinds["ctx_image"] == "agent_context"
    assert source_kinds["ctx_link"] == "agent_context"
    assert {"ctx_brief", "ctx_code", "ctx_metrics", "ctx_image", "ctx_link"} <= set(
        result.usage["evidence_coverage"]["covered_source_refs"]
    )


def test_template_pack_media_context_respects_document_target_profile(tmp_path: Path) -> None:
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    video = tmp_path / "training.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42 local video fixture")
    packet_path = tmp_path / "media.context.json"
    output_path = tmp_path / "board-audit-media.pdf"
    build_context_packet(
        [
            {
                "context_item_id": "ctx_audio",
                "path": str(audio),
                "role": "audio_context",
                "label": "Meeting Audio",
                "transcript": "00:00 Kickoff\n00:12 Decision: keep the local worker boundary explicit.",
                "duration_seconds": 42.5,
                "chapters": [{"start_seconds": 12, "title": "Decision"}],
            },
            {
                "context_item_id": "ctx_video",
                "path": str(video),
                "role": "video_context",
                "label": "Training Video",
                "transcript": "00:00 Dashboard tour\n00:20 Export demo",
                "duration_seconds": 84,
                "keyframes": [{"timestamp_seconds": 20, "label": "Export screen"}],
            },
        ],
        output_path=packet_path,
        title="Media Evidence",
    )

    result = create_pdf_from_template_pack(
        "examples/template-packs/local-agent-starter.json",
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        context_packet_path=packet_path,
    )

    blocks = {block["block_id"]: block for block in result.usage["composition_ir"]["blocks"]}
    routes = {route["block_id"]: route for route in result.usage["slot_routing_plan"]["routes"]}
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_path).pages)

    assert blocks["blk_ctx_audio"]["type"] == "audio_reference"
    assert blocks["blk_ctx_audio"]["target_slot"] == "media_evidence"
    assert blocks["blk_ctx_audio"]["data"]["transcript_excerpt"].startswith("00:00 Kickoff")
    assert blocks["blk_ctx_video"]["type"] == "video_reference"
    assert blocks["blk_ctx_video"]["target_slot"] == "media_evidence"
    assert blocks["blk_ctx_video"]["data"]["keyframe_count"] == 1
    assert routes["blk_ctx_audio"]["target_profile_accepts_block_type"] is True
    assert routes["blk_ctx_audio"]["target_profile_candidate_slots"] == ["media_evidence"]
    assert routes["blk_ctx_video"]["target_profile_accepts_block_type"] is True
    assert result.usage["slot_routing_plan"]["warning_route_count"] == 0
    assert "Meeting Audio" in text
    assert "Decision: keep the local worker boundary explicit" in text
    assert "Training Video" in text
    assert "Dashboard tour" in text


def test_template_pack_context_packet_returns_slot_routing_plan(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = [
        "section",
        "code",
        "table",
        "image",
        "slide",
        "citation",
    ]
    pack_path = tmp_path / "template-pack.json"
    packet_path = tmp_path / "routing.context.json"
    output_path = tmp_path / "board-audit-routing.pdf"
    code_path = tmp_path / "risk.py"
    image_path = tmp_path / "architecture.png"
    code_path.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    Image.new("RGB", (80, 40), color=(15, 118, 110)).save(image_path)
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    build_context_packet(
        [
            {"context_item_id": "ctx_brief", "text": "Create an audit.", "label": "Audit Brief"},
            {"context_item_id": "ctx_code", "path": str(code_path), "label": "Risk Function"},
            {
                "context_item_id": "ctx_metrics",
                "table": {"columns": ["metric", "value"], "rows": [["latency_ms", "42"]]},
                "label": "Runtime Metrics",
            },
            {"context_item_id": "ctx_image", "path": str(image_path), "label": "Architecture Figure"},
            {
                "context_item_id": "ctx_link",
                "uri": "https://example.com/local-agent-patterns",
                "label": "Agent Pattern Reference",
            },
        ],
        output_path=packet_path,
        title="Routing Context",
    )

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        context_packet_path=packet_path,
    )

    plan = result.usage["slot_routing_plan"]
    saved_payload = json.loads(output_path.with_suffix(".composition.json").read_text(encoding="utf-8"))
    plan_schema = json.loads(Path("schemas/slot-routing-plan.schema.json").read_text(encoding="utf-8"))
    routes = {route["block_id"]: route for route in plan["routes"]}

    assert list(Draft202012Validator(plan_schema).iter_errors(plan)) == []
    assert plan["slot_routing_plan_id"].startswith("route_")
    assert plan["target_profile_id"] == "technical_audit"
    assert plan["template_id"] == "board_audit"
    assert plan["template_slots"] == ["cover", "executive_summary", "findings", "evidence"]
    assert plan["supported_block_types"] == ["section", "code", "table", "image", "slide", "citation"]
    assert routes["blk_ctx_brief"]["target_slot"] == "executive_summary"
    assert routes["blk_ctx_code"]["target_slot"] == "evidence"
    assert routes["blk_ctx_metrics"]["target_slot"] == "findings"
    assert routes["blk_ctx_image"]["target_slot"] == "evidence"
    assert routes["blk_ctx_link"]["target_slot"] == "recommendations"
    assert routes["blk_ctx_code"]["source_refs"] == ["ctx_code"]
    assert routes["blk_ctx_code"]["source_context_item_id"] == "ctx_code"
    assert routes["blk_ctx_code"]["slot_known"] is True
    assert routes["blk_ctx_code"]["block_type_supported"] is True
    assert routes["blk_ctx_code"]["target_profile_known"] is True
    assert routes["blk_ctx_code"]["target_profile_accepts_block_type"] is True
    assert routes["blk_ctx_code"]["target_profile_candidate_slots"] == ["code_review"]
    assert routes["blk_ctx_metrics"]["target_profile_candidate_slots"] == ["evidence_table"]
    assert routes["blk_ctx_image"]["target_profile_candidate_slots"] == ["visual_evidence"]
    assert routes["blk_ctx_link"]["target_profile_candidate_slots"] == ["evidence_table"]
    assert routes["blk_ctx_code"]["routing_status"] == "accepted"
    assert routes["blk_ctx_code"]["routing_reason"].startswith("Context code item")
    assert plan["warnings"] == []
    assert saved_payload["slot_routing_plan"] == plan
    assert result.usage["composition_ir"]["metadata"]["slot_routing_plan_id"] == plan["slot_routing_plan_id"]


def test_template_pack_writes_kami_like_layer_manifest_for_editable_slots(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = [
        "section",
        "code",
        "table",
        "image",
        "slide",
        "citation",
    ]
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-layers.pdf"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    data = {
        "title": "Editable Board Audit",
        "blocks": [
            {
                "block_id": "blk_agent_note",
                "type": "section",
                "title": "Reviewer Note",
                "target_slot": "findings",
                "body": "This block should be addressable by a future PDF edit agent.",
                "source_refs": ["ctx_note"],
            },
            {
                "block_id": "blk_agent_metrics",
                "type": "table",
                "title": "Metrics",
                "target_slot": "evidence",
                "columns": ["metric", "value"],
                "rows": [["coverage", "1.0"]],
                "source_refs": ["ctx_metrics"],
            },
        ],
    }

    result = create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )

    layer_path = output_path.with_suffix(".layers.json")
    layer_schema = json.loads(Path("schemas/template-layer-manifest.schema.json").read_text(encoding="utf-8"))
    manifest = json.loads(layer_path.read_text(encoding="utf-8"))
    layer_by_block = {layer["block_id"]: layer for layer in manifest["layers"]}

    assert list(Draft202012Validator(layer_schema).iter_errors(manifest)) == []
    assert layer_path.exists()
    assert result.artifacts[-1].path == layer_path.resolve()
    assert result.usage["template_layer_manifest_path"] == layer_path.as_posix()
    assert result.usage["template_layer_manifest"] == manifest
    assert result.usage["composition_ir"]["metadata"]["template_layer_manifest_id"] == manifest[
        "template_layer_manifest_id"
    ]
    assert manifest["template_id"] == "board_audit"
    assert manifest["pack_id"] == "local_agent_documents"
    assert manifest["target_profile_id"] == "technical_audit"
    assert manifest["output_pdf_path"] == str(output_path.resolve())
    assert manifest["layer_count"] == len(result.usage["composition_ir"]["blocks"])
    assert manifest["editable_layer_count"] == manifest["layer_count"]
    assert manifest["layer_types"] == ["section", "table"]
    assert layer_by_block["blk_agent_note"]["target_slot"] == "findings"
    assert layer_by_block["blk_agent_note"]["source_refs"] == ["ctx_note"]
    assert layer_by_block["blk_agent_note"]["anchor"]["anchor_kind"] == "estimated_slot_anchor"
    assert layer_by_block["blk_agent_note"]["anchor"]["page_number"] >= 1
    assert layer_by_block["blk_agent_note"]["anchor"]["bbox"]["coordinate_system"] == "normalized_page"
    assert layer_by_block["blk_agent_note"]["edit_policy"]["editable"] is True
    assert layer_by_block["blk_agent_note"]["edit_policy"]["requires_source_ref"] is True
    assert "replace_block" in layer_by_block["blk_agent_note"]["edit_policy"]["allowed_operations"]
    assert layer_by_block["blk_agent_metrics"]["block_type"] == "table"
    assert layer_by_block["blk_agent_metrics"]["source_kinds"] == ["agent_context"]
    assert manifest["next_recommended_tools"] == [
        "pdf.patch.plan",
        "pdf.evidence.coverage_report",
        "pdf.artifacts.export_bundle",
    ]


def test_template_pack_composition_source_map_is_consumed_by_patch_plan(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit.pdf"
    manifest_path = tmp_path / "board-audit.patch.json"
    patched_path = tmp_path / "board-audit-patched.pdf"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
    )
    composition_path = output_path.with_suffix(".composition.json")
    source_ref = "tpl://local_agent_documents/board_audit/sample_data"

    result = plan_patch_transaction(
        input_path=output_path,
        operations=[
            {
                "op": "append_markdown",
                "title": "Agent Evidence Note",
                "markdown": "## Agent Evidence Note\n\nBoard audit was reviewed against template pack source data.",
                "source_refs": [source_ref],
            }
        ],
        output_path=manifest_path,
        composition_path=composition_path,
        reason="Append an agent evidence note with verified template-pack references.",
    )

    manifest = result.usage["patch_manifest"]
    assert manifest["source_ref_validation"]["status"] == "passed"
    assert manifest["source_ref_validation"]["missing_source_refs"] == []
    assert manifest["source_ref_validation"]["known_source_ref_count"] == 1
    assert manifest["operation_source_map"][0]["operation_id"] == "op_001"
    assert manifest["operation_source_map"][0]["source_refs"] == [source_ref]
    assert manifest["operation_source_map"][0]["matched_sources"][0]["source_ref"] == source_ref
    assert manifest["operation_source_map"][0]["matched_sources"][0]["block_id"] == "blk_tpl_001"
    assert manifest["operations"][0]["source_map_evidence"][0]["source_kind"] == "template_pack"

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["source_ref_validation"] == manifest["source_ref_validation"]
    assert saved["operations"][0]["source_map_evidence"][0]["template_id"] == "board_audit"

    applied = apply_patch_transaction(manifest_path, output_path=patched_path)
    verified = verify_patch_transaction(manifest_path, patched_path)
    patched_text = "\n".join(page.extract_text() or "" for page in PdfReader(patched_path).pages)

    assert applied.status == "succeeded"
    assert verified.status == "succeeded"
    assert verified.usage["verification"]["source_ref_validation_status"] == "passed"
    assert verified.usage["verification"]["matched_source_count"] == 3
    assert "Matched Source Map Evidence" in patched_text
    assert "blk_tpl_001" in patched_text
    assert "executive_summary" in patched_text
    assert "board_audit" in patched_text


def test_template_pack_layer_manifest_is_consumed_by_patch_plan(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = [
        "section",
        "code",
        "table",
        "image",
        "slide",
        "citation",
    ]
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-layers.pdf"
    manifest_path = tmp_path / "board-audit-layer.patch.json"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    data = {
        "title": "Editable Board Audit",
        "blocks": [
            {
                "block_id": "blk_agent_note",
                "type": "section",
                "title": "Reviewer Note",
                "target_slot": "findings",
                "body": "This block should be addressable by a future PDF edit agent.",
                "source_refs": ["ctx_note"],
            }
        ],
    }
    create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )
    composition_path = output_path.with_suffix(".composition.json")
    layer_path = output_path.with_suffix(".layers.json")

    result = plan_patch_transaction(
        input_path=output_path,
        operations=[
            {
                "op": "append_markdown",
                "title": "Layer-Aware Reviewer Note",
                "markdown": "## Layer-Aware Reviewer Note\n\nThis patch targets a template layer anchor.",
                "source_refs": ["ctx_note"],
                "layer_id": "layer_blk_agent_note",
                "block_id": "blk_agent_note",
                "target_slot": "findings",
            }
        ],
        output_path=manifest_path,
        composition_path=composition_path,
        layer_manifest_path=layer_path,
        reason="Plan an append-only patch against a known template layer.",
    )

    manifest = result.usage["patch_manifest"]
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    patch_schema = json.loads(Path("schemas/patch-manifest.schema.json").read_text(encoding="utf-8"))
    operation = manifest["operations"][0]
    layer_match = manifest["operation_layer_map"][0]["matched_layers"][0]

    assert list(Draft202012Validator(patch_schema).iter_errors(manifest)) == []
    assert manifest["layer_manifest_path"] == str(layer_path.resolve()).replace("\\", "/")
    assert manifest["layer_ref_validation"]["status"] == "passed"
    assert manifest["layer_ref_validation"]["known_layer_count"] >= 1
    assert manifest["layer_ref_validation"]["requested_layer_ids"] == ["layer_blk_agent_note"]
    assert manifest["layer_ref_validation"]["requested_block_ids"] == ["blk_agent_note"]
    assert manifest["layer_ref_validation"]["requested_target_slots"] == ["findings"]
    assert manifest["layer_ref_validation"]["missing_layer_refs"] == []
    assert manifest["operation_layer_map"][0]["operation_id"] == "op_001"
    assert manifest["operation_layer_map"][0]["layer_ids"] == ["layer_blk_agent_note"]
    assert manifest["operation_layer_map"][0]["block_ids"] == ["blk_agent_note"]
    assert manifest["operation_layer_map"][0]["target_slots"] == ["findings"]
    assert manifest["operation_layer_map"][0]["matched_layer_count"] == 1
    assert layer_match["layer_id"] == "layer_blk_agent_note"
    assert layer_match["block_id"] == "blk_agent_note"
    assert layer_match["target_slot"] == "findings"
    assert layer_match["anchor"]["anchor_kind"] == "estimated_slot_anchor"
    assert layer_match["edit_policy"]["editable"] is True
    assert operation["layer_evidence"][0]["source_refs"] == ["ctx_note"]
    assert operation["target_layer_refs"] == {
        "layer_ids": ["layer_blk_agent_note"],
        "block_ids": ["blk_agent_note"],
        "target_slots": ["findings"],
    }
    assert saved["operation_layer_map"] == manifest["operation_layer_map"]

    operations_path = tmp_path / "layer-operations.json"
    operations_path.write_text(
        json.dumps(
            [
                {
                    "op": "append_markdown",
                    "title": "CLI Layer Note",
                    "markdown": "## CLI Layer Note\n\nLayer-aware patch plan through public interfaces.",
                    "source_refs": ["ctx_note"],
                    "layer_id": "layer_blk_agent_note",
                    "block_id": "blk_agent_note",
                    "target_slot": "findings",
                }
            ]
        ),
        encoding="utf-8",
    )
    cli = runner.invoke(
        app,
        [
            "patch",
            "plan",
            str(output_path),
            "--operations",
            str(operations_path),
            "-o",
            str(tmp_path / "cli-layer.patch.json"),
            "--composition",
            str(composition_path),
            "--layers",
            str(layer_path),
            "--json",
        ],
    )
    api = TestClient(create_app()).post(
        "/v1/tools/pdf.patch.plan/run",
        json={
            "input_path": str(output_path),
            "operations": json.loads(operations_path.read_text(encoding="utf-8")),
            "output_path": str(tmp_path / "api-layer.patch.json"),
            "composition_path": str(composition_path),
            "layer_manifest_path": str(layer_path),
        },
    )
    mcp = json.loads(
        pdf_patch_plan(
            str(output_path),
            json.loads(operations_path.read_text(encoding="utf-8")),
            str(tmp_path / "mcp-layer.patch.json"),
            composition_path=str(composition_path),
            layer_manifest_path=str(layer_path),
        )
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["usage"]["patch_manifest"]["layer_ref_validation"]["status"] == "passed"
    assert api.status_code == 200
    assert api.json()["usage"]["patch_manifest"]["operation_layer_map"][0]["matched_layer_count"] == 1
    assert mcp["usage"]["patch_manifest"]["layer_ref_validation"]["requested_block_ids"] == ["blk_agent_note"]


def test_template_pack_layer_patch_regenerates_block_as_append_only_artifact(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = [
        "section",
        "code",
        "table",
        "image",
        "slide",
        "citation",
    ]
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-regenerate.pdf"
    manifest_path = tmp_path / "board-audit-regenerate.patch.json"
    preview_path = tmp_path / "board-audit-regenerate.preview.json"
    patched_path = tmp_path / "board-audit-regenerated.pdf"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    data = {
        "title": "Regeneratable Board Audit",
        "blocks": [
            {
                "block_id": "blk_agent_note",
                "type": "section",
                "title": "Reviewer Note",
                "target_slot": "findings",
                "body": "This original block should remain traceable after regeneration.",
                "source_refs": ["ctx_note"],
            }
        ],
    }
    create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )
    original_page_count = len(PdfReader(output_path).pages)
    composition_path = output_path.with_suffix(".composition.json")
    layer_path = output_path.with_suffix(".layers.json")

    plan = plan_patch_transaction(
        input_path=output_path,
        operations=[
            {
                "op": "regenerate_block",
                "title": "Regenerated Reviewer Note",
                "replacement_markdown": (
                    "## Regenerated Reviewer Note\n\n"
                    "This block was regenerated from agent context while preserving audit evidence."
                ),
                "source_refs": ["ctx_note"],
                "layer_id": "layer_blk_agent_note",
                "block_id": "blk_agent_note",
                "target_slot": "findings",
            }
        ],
        output_path=manifest_path,
        composition_path=composition_path,
        layer_manifest_path=layer_path,
        reason="Regenerate a template block with layer evidence.",
    )
    preview = preview_patch_transaction(manifest_path, output_path=preview_path)
    applied = apply_patch_transaction(manifest_path, output_path=patched_path)
    verified = verify_patch_transaction(manifest_path, patched_path)

    manifest = plan.usage["patch_manifest"]
    patch_schema = json.loads(Path("schemas/patch-manifest.schema.json").read_text(encoding="utf-8"))
    operation = manifest["operations"][0]
    layer_match = manifest["operation_layer_map"][0]["matched_layers"][0]
    patched_text = "\n".join(page.extract_text() or "" for page in PdfReader(patched_path).pages)

    assert list(Draft202012Validator(patch_schema).iter_errors(manifest)) == []
    assert operation["op"] == "regenerate_block"
    assert operation["replacement_markdown"].startswith("## Regenerated Reviewer Note")
    assert operation["target_layer_refs"] == {
        "layer_ids": ["layer_blk_agent_note"],
        "block_ids": ["blk_agent_note"],
        "target_slots": ["findings"],
    }
    assert operation["regeneration_policy"] == {
        "requested_effect": "regenerate_template_block",
        "actual_effect": "append_regenerated_block_appendix",
        "mutates_original_block": False,
        "requires_new_output_path": True,
        "claims_layout_preservation": False,
        "requires_layer_evidence": True,
    }
    assert manifest["layer_ref_validation"]["status"] == "passed"
    assert manifest["operation_layer_map"][0]["matched_layer_count"] == 1
    assert layer_match["layer_id"] == "layer_blk_agent_note"
    assert "regenerate_block" in layer_match["edit_policy"]["allowed_operations"]
    assert preview.usage["operation_summary"][0]["expected_effect"] == (
        "append an audited regenerated block appendix; original template block remains unchanged"
    )
    assert preview.usage["operation_summary"][0]["matched_layer_count"] == 1
    assert preview.usage["will_mutate_input"] is False
    assert applied.status == "succeeded"
    assert applied.usage["input_unchanged"] is True
    assert len(PdfReader(output_path).pages) == original_page_count
    assert len(PdfReader(patched_path).pages) > original_page_count
    assert verified.status == "succeeded"
    assert verified.usage["verification"]["input_unchanged"] is True
    assert verified.usage["verification"]["layer_ref_validation_status"] == "passed"
    assert verified.usage["verification"]["matched_layer_count"] == 1
    assert "Regenerated Reviewer Note" in patched_text
    assert "Regeneration Policy" in patched_text
    assert "Original template block was not mutated" in patched_text
    assert "Matched Template Layer Evidence" in patched_text
    assert "layer_blk_agent_note" in patched_text
    assert "estimated_slot_anchor" in patched_text


def test_template_pack_patch_plan_rejects_layer_operation_not_allowed(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = ["section", "code", "table"]
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-policy.pdf"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    data = {
        "title": "Policy Board Audit",
        "blocks": [
            {
                "block_id": "blk_agent_note",
                "type": "section",
                "title": "Reviewer Note",
                "target_slot": "findings",
                "body": "This layer deliberately disallows regeneration in the edited manifest.",
                "source_refs": ["ctx_note"],
            }
        ],
    }
    create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )
    layer_path = output_path.with_suffix(".layers.json")
    layer_manifest = json.loads(layer_path.read_text(encoding="utf-8"))
    for layer in layer_manifest["layers"]:
        if layer["layer_id"] == "layer_blk_agent_note":
            layer["edit_policy"]["allowed_operations"] = ["append_to_slot", "annotate"]
            break
    layer_path.write_text(json.dumps(layer_manifest, indent=2), encoding="utf-8-sig")

    result = run_patch_plan(
        input_path=output_path,
        operations=[
            {
                "op": "regenerate_block",
                "title": "Regenerated Reviewer Note",
                "replacement_markdown": "## Regenerated Reviewer Note\n\nThis should be rejected.",
                "source_refs": ["ctx_note"],
                "layer_id": "layer_blk_agent_note",
                "block_id": "blk_agent_note",
                "target_slot": "findings",
            }
        ],
        output_path=tmp_path / "policy.patch.json",
        composition_path=output_path.with_suffix(".composition.json"),
        layer_manifest_path=layer_path,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "layer_operation_not_allowed"
    assert result.error.details == {
        "operation_id": "op_001",
        "op": "regenerate_block",
        "layer_id": "layer_blk_agent_note",
        "block_id": "blk_agent_note",
        "target_slot": "findings",
        "editable": True,
        "allowed_operations": ["append_to_slot", "annotate"],
    }


def test_patch_preview_apply_and_verify_reject_tampered_layer_policy(tmp_path: Path) -> None:
    pack = _example_pack()
    pack["templates"][0]["supported_block_types"] = ["section", "code", "table"]
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit-tamper.pdf"
    manifest_path = tmp_path / "board-audit-tamper.patch.json"
    patched_path = tmp_path / "board-audit-tamper-patched.pdf"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    data = {
        "title": "Tamper Board Audit",
        "blocks": [
            {
                "block_id": "blk_agent_note",
                "type": "section",
                "title": "Reviewer Note",
                "target_slot": "findings",
                "body": "This valid patch manifest will be tampered after planning.",
                "source_refs": ["ctx_note"],
            }
        ],
    }
    create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
        data=data,
    )
    plan_patch_transaction(
        input_path=output_path,
        operations=[
            {
                "op": "regenerate_block",
                "title": "Regenerated Reviewer Note",
                "replacement_markdown": "## Regenerated Reviewer Note\n\nThis valid patch will be tampered.",
                "source_refs": ["ctx_note"],
                "layer_id": "layer_blk_agent_note",
                "block_id": "blk_agent_note",
                "target_slot": "findings",
            }
        ],
        output_path=manifest_path,
        composition_path=output_path.with_suffix(".composition.json"),
        layer_manifest_path=output_path.with_suffix(".layers.json"),
    )
    valid_apply = run_patch_apply(manifest_path, output_path=patched_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for operation in manifest["operations"]:
        for layer in operation.get("layer_evidence", []):
            layer["edit_policy"]["allowed_operations"] = ["append_to_slot", "annotate"]
    for operation_layer_map in manifest["operation_layer_map"]:
        for layer in operation_layer_map.get("matched_layers", []):
            layer["edit_policy"]["allowed_operations"] = ["append_to_slot", "annotate"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    preview = run_patch_preview(manifest_path, output_path=tmp_path / "tamper-preview.json")
    apply = run_patch_apply(manifest_path, output_path=tmp_path / "tamper-apply.pdf")
    verify = run_patch_verify(manifest_path, patched_path=patched_path)

    assert valid_apply.status == "succeeded"
    for result in (preview, apply, verify):
        assert result.status == "failed"
        assert result.error is not None
        assert result.error.code == "layer_operation_not_allowed"
        assert result.error.details["operation_id"] == "op_001"
        assert result.error.details["layer_id"] == "layer_blk_agent_note"
        assert result.error.details["allowed_operations"] == ["append_to_slot", "annotate"]


def test_template_pack_patch_plan_rejects_missing_composition_source_refs(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "board-audit.pdf"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    create_pdf_from_template_pack(
        pack_path,
        template_id="board_audit",
        output_path=output_path,
        color_scheme="executive_blue",
    )
    composition_path = output_path.with_suffix(".composition.json")

    result = run_patch_plan(
        input_path=output_path,
        operations=[
            {
                "op": "append_markdown",
                "title": "Unsupported Evidence",
                "markdown": "This source ref is not present in the composition source map.",
                "source_refs": ["tpl://local_agent_documents/board_audit/missing"],
            }
        ],
        output_path=tmp_path / "missing.patch.json",
        composition_path=composition_path,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "source_ref_not_found"
    assert result.error.details["missing_source_refs"] == ["tpl://local_agent_documents/board_audit/missing"]


def test_template_pack_cli_api_and_mcp_are_exposed(tmp_path: Path) -> None:
    pack_path = tmp_path / "template-pack.json"
    output_path = tmp_path / "cli-board-audit.pdf"
    packet_path = tmp_path / "agent-context.packet.json"
    pack_path.write_text(json.dumps(_example_pack()), encoding="utf-8")
    build_context_packet(
        [
            {
                "context_item_id": "ctx_cli_brief",
                "text": "Create this packet from an agent context packet.",
                "label": "CLI Agent Brief",
            }
        ],
        output_path=packet_path,
        title="Interface Context",
    )

    catalog_cli = runner.invoke(app, ["create", "template-packs", "--json"])
    validate_cli = runner.invoke(
        app,
        [
            "create",
            "validate-template-pack",
            str(pack_path),
            "-o",
            str(tmp_path / "cli-validation.json"),
            "--json",
        ],
    )
    plan_cli = runner.invoke(
        app,
        [
            "create",
            "plan-template-pack",
            str(pack_path),
            "--target-profile",
            "technical_audit",
            "--context-packet",
            str(packet_path),
            "--planned-output",
            str(tmp_path / "cli-planned-board-audit.pdf"),
            "-o",
            str(tmp_path / "cli-plan.json"),
            "--json",
        ],
    )
    agent_cli = runner.invoke(
        app,
        [
            "create",
            "agent",
            str(pack_path),
            "--target-profile",
            "technical_audit",
            "--context-packet",
            str(packet_path),
            "-o",
            str(tmp_path / "cli-agent-board-audit.pdf"),
            "--plan-output",
            str(tmp_path / "cli-agent.plan.json"),
            "--coverage-output",
            str(tmp_path / "cli-agent.coverage.json"),
            "--context-classification-output",
            str(tmp_path / "cli-agent.context-classification.json"),
            "--context-report-output",
            str(tmp_path / "cli-agent.context-report.pdf"),
            "--context-report-json-output",
            str(tmp_path / "cli-agent.context-report.json"),
            "--bundle-output",
            str(tmp_path / "cli-agent.agentpdf-bundle.zip"),
            "--json",
        ],
    )
    create_cli = runner.invoke(
        app,
        [
            "create",
            "from-template-pack",
            str(pack_path),
            "--template",
            "board_audit",
            "--color-scheme",
            "executive_blue",
            "--context-packet",
            str(packet_path),
            "-o",
            str(output_path),
            "--json",
        ],
    )

    assert catalog_cli.exit_code == 0
    assert validate_cli.exit_code == 0
    assert plan_cli.exit_code == 0
    assert agent_cli.exit_code == 0
    assert create_cli.exit_code == 0
    assert json.loads(catalog_cli.stdout)["tool"] == "pdf.ai.create.template_packs"
    assert json.loads(validate_cli.stdout)["tool"] == "pdf.ai.create.validate_template_pack"
    plan_payload = json.loads(plan_cli.stdout)
    assert plan_payload["tool"] == "pdf.ai.create.plan_template_pack"
    assert plan_payload["usage"]["template_pack_plan"]["selected_template_id"] == "board_audit"
    agent_payload = json.loads(agent_cli.stdout)
    assert agent_payload["tool"] == "pdf.ai.create.agent"
    assert agent_payload["usage"]["create_agent_run"]["selected_template_id"] == "board_audit"
    assert agent_payload["usage"]["create_agent_run"]["context_classification"]["tool"] == "pdf.context.classify"
    assert agent_payload["usage"]["create_agent_run"]["context_packet_report"]["validation"]["status"] == "passed"
    assert agent_payload["usage"]["create_agent_run"]["bundle_verification"]["validation"]["status"] == "passed"
    assert agent_payload["validation"]["status"] == "passed"
    assert (tmp_path / "cli-agent.context-classification.json").exists()
    assert (tmp_path / "cli-agent.context-report.pdf").exists()
    assert (tmp_path / "cli-agent.context-report.json").exists()
    assert (tmp_path / "cli-agent.agentpdf-bundle.zip").exists()
    create_payload = json.loads(create_cli.stdout)
    assert create_payload["tool"] == "pdf.ai.create.from_template_pack"
    assert create_payload["usage"]["composition_path"].endswith("cli-board-audit.composition.json")
    assert create_payload["usage"]["context_block_count"] == 1
    assert output_path.exists()
    assert output_path.with_suffix(".composition.json").exists()

    api = TestClient(create_app())
    api_catalog = api.post("/v1/tools/pdf.ai.create.template_packs/run", json={})
    api_validate = api.post(
        "/v1/tools/pdf.ai.create.validate_template_pack/run",
        json={"template_pack": str(pack_path)},
    )
    api_plan = api.post(
        "/v1/tools/pdf.ai.create.plan_template_pack/run",
        json={
            "template_pack": str(pack_path),
            "target_profile": "technical_audit",
            "context_packet_path": str(packet_path),
            "planned_output_path": str(tmp_path / "api-planned-board-audit.pdf"),
        },
    )
    api_agent = api.post(
        "/v1/tools/pdf.ai.create.agent/run",
        json={
            "template_pack": str(pack_path),
            "target_profile": "technical_audit",
            "context_packet_path": str(packet_path),
            "output_path": str(tmp_path / "api-agent-board-audit.pdf"),
            "plan_output_path": str(tmp_path / "api-agent.plan.json"),
            "coverage_output_path": str(tmp_path / "api-agent.coverage.json"),
            "context_classification_output_path": str(tmp_path / "api-agent.context-classification.json"),
            "context_report_output_path": str(tmp_path / "api-agent.context-report.pdf"),
            "context_report_json_output_path": str(tmp_path / "api-agent.context-report.json"),
            "bundle_output_path": str(tmp_path / "api-agent.agentpdf-bundle.zip"),
        },
    )
    api_create = api.post(
        "/v1/tools/pdf.ai.create.from_template_pack/run",
        json={
            "template_pack": str(pack_path),
            "template_id": "board_audit",
            "color_scheme": "executive_blue",
            "context_packet_path": str(packet_path),
            "output_path": str(tmp_path / "api-board-audit.pdf"),
        },
    )

    assert api_catalog.status_code == 200
    assert api_validate.status_code == 200
    assert api_plan.status_code == 200
    assert api_agent.status_code == 200
    assert api_create.status_code == 200
    assert api_catalog.json()["tool"] == "pdf.ai.create.template_packs"
    assert api_validate.json()["tool"] == "pdf.ai.create.validate_template_pack"
    assert api_plan.json()["tool"] == "pdf.ai.create.plan_template_pack"
    assert api_plan.json()["usage"]["template_pack_plan"]["create_payload"]["template_id"] == "board_audit"
    assert api_agent.json()["tool"] == "pdf.ai.create.agent"
    assert api_agent.json()["usage"]["create_agent_run"]["selected_template_id"] == "board_audit"
    assert api_agent.json()["usage"]["create_agent_run"]["context_classification"]["tool"] == "pdf.context.classify"
    assert api_agent.json()["usage"]["create_agent_run"]["bundle_verification"]["validation"]["status"] == "passed"
    assert (tmp_path / "api-agent.context-classification.json").exists()
    assert api_create.json()["tool"] == "pdf.ai.create.from_template_pack"
    assert api_create.json()["usage"]["context_block_count"] == 1

    mcp_catalog = json.loads(pdf_ai_create_template_packs())
    mcp_validate = json.loads(pdf_ai_create_validate_template_pack(str(pack_path)))
    mcp_plan = json.loads(
        pdf_ai_create_plan_template_pack(
            str(pack_path),
            target_profile="technical_audit",
            context_packet_path=str(packet_path),
            planned_output_path=str(tmp_path / "mcp-planned-board-audit.pdf"),
        )
    )
    mcp_agent = json.loads(
        pdf_ai_create_agent(
            str(pack_path),
            target_profile="technical_audit",
            context_packet_path=str(packet_path),
            output_path=str(tmp_path / "mcp-agent-board-audit.pdf"),
            plan_output_path=str(tmp_path / "mcp-agent.plan.json"),
            coverage_output_path=str(tmp_path / "mcp-agent.coverage.json"),
            context_classification_output_path=str(tmp_path / "mcp-agent.context-classification.json"),
            context_report_output_path=str(tmp_path / "mcp-agent.context-report.pdf"),
            context_report_json_output_path=str(tmp_path / "mcp-agent.context-report.json"),
            bundle_output_path=str(tmp_path / "mcp-agent.agentpdf-bundle.zip"),
        )
    )
    mcp_create = json.loads(
        pdf_ai_create_from_template_pack(
            str(pack_path),
            template_id="board_audit",
            output_path=str(tmp_path / "mcp-board-audit.pdf"),
            color_scheme="executive_blue",
            context_packet_path=str(packet_path),
        )
    )

    assert mcp_catalog["tool"] == "pdf.ai.create.template_packs"
    assert mcp_validate["tool"] == "pdf.ai.create.validate_template_pack"
    assert mcp_plan["tool"] == "pdf.ai.create.plan_template_pack"
    assert mcp_plan["usage"]["template_pack_plan"]["selected_template_id"] == "board_audit"
    assert mcp_agent["tool"] == "pdf.ai.create.agent"
    assert mcp_agent["usage"]["create_agent_run"]["selected_template_id"] == "board_audit"
    assert mcp_agent["usage"]["create_agent_run"]["context_classification"]["tool"] == "pdf.context.classify"
    assert mcp_agent["usage"]["create_agent_run"]["context_packet_report"]["validation"]["status"] == "passed"
    assert mcp_agent["usage"]["create_agent_run"]["bundle_verification"]["validation"]["status"] == "passed"
    assert (tmp_path / "mcp-agent.context-classification.json").exists()
    assert mcp_create["tool"] == "pdf.ai.create.from_template_pack"
    assert mcp_create["usage"]["context_block_count"] == 1
