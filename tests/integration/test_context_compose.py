import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from PIL import Image
from pypdf import PdfReader
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.compose.context import compose_from_context, plan_composition, render_composition_ir
from agentpdf.context.packet import build_context_packet
from agentpdf.context.image import analyze_image
from agentpdf.core.pdf import create_text_pdf, inspect_pdf_pages
from agentpdf.evidence.context_packet_report import create_context_packet_report
from agentpdf.renderers.html_package import write_composition_html_package
import agentpdf.mcp.server as mcp_server
from agentpdf.mcp.server import (
    pdf_compose_from_context,
    pdf_compose_plan,
    pdf_compose_render_ir,
    pdf_context_build_packet,
)


runner = CliRunner()


def test_build_context_packet_normalizes_heterogeneous_context(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    csv = tmp_path / "metrics.csv"
    csv.write_text("metric,value\nlatency_ms,42\nerror_rate,0.01\n", encoding="utf-8")
    image = tmp_path / "screenshot.png"
    Image.new("RGB", (80, 40), color=(40, 80, 120)).save(image)
    source_pdf = tmp_path / "source.pdf"
    create_text_pdf("Source PDF evidence for the audit.", source_pdf)
    packet_path = tmp_path / "context.packet.json"

    result = build_context_packet(
        [
            {
                "text": "Create a technical audit PDF with code, metric, image, and PDF evidence.",
                "role": "brief",
                "label": "User brief",
            },
            {"path": str(code), "role": "code_evidence"},
            {"path": str(csv), "role": "data_evidence"},
            {"path": str(image), "role": "image_evidence"},
            {"path": str(source_pdf), "role": "pdf_evidence"},
        ],
        output_path=packet_path,
        title="Technical Audit Context",
        intent="Create a target PDF artifact with traceable evidence.",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.build_packet"
    assert result.artifacts[0].mime_type == "application/json"
    assert result.usage["item_count"] == 5
    assert result.usage["source_graph"]["node_count"] == 5
    assert result.usage["context_packet"]["title"] == "Technical Audit Context"
    kinds = {item["type"] for item in result.usage["context_packet"]["items"]}
    assert kinds == {"text", "code", "data", "image", "pdf"}
    assert packet_path.exists()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["context_packet_id"].startswith("ctxpkt_")
    assert packet["source_graph"]["nodes"][1]["source_ref"].startswith("ctx_")
    assert packet["items"][1]["metadata"]["line_count"] == 2
    assert packet["items"][2]["content"]["table"]["columns"] == ["metric", "value"]
    assert packet["items"][2]["content"]["table"]["rows"] == [["latency_ms", "42"], ["error_rate", "0.01"]]
    assert packet["items"][3]["metadata"]["width"] == 80
    assert packet["items"][3]["content"]["image"]["path"].endswith("screenshot.png")
    assert packet["items"][4]["metadata"]["page_count"] == 1


def test_context_packet_report_creates_valid_pdf_and_json_audit(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def score(value):\n    return value * 2\n", encoding="utf-8")
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    packet_path = tmp_path / "context.packet.json"
    report_pdf = tmp_path / "context-report.pdf"
    report_json = tmp_path / "context-report.json"

    packet = build_context_packet(
        [
            {"path": str(code), "role": "code_evidence", "label": "Risk Service"},
            {
                "url": "https://okpdf.dev/docs/context",
                "role": "citation",
                "label": "Context Docs",
                "title": "Context Packet Docs",
                "snippet": "Traceable PDF context packets for agents.",
            },
            {
                "path": str(audio),
                "role": "audio_context",
                "label": "Meeting Audio",
                "transcript": "00:00 Keep provenance explicit.",
                "duration_seconds": 12,
            },
        ],
        output_path=packet_path,
        title="Audit Context Packet",
        intent="Create an auditable source packet.",
    ).usage["context_packet"]

    result = create_context_packet_report(
        packet_path,
        output_path=report_pdf,
        report_output_path=report_json,
        title="Audit Context Packet Report",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.evidence.context_packet_report"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert [artifact.mime_type for artifact in result.artifacts] == ["application/pdf", "application/json"]
    assert result.usage["context_packet_id"] == packet["context_packet_id"]
    assert result.usage["source_ref_count"] == 3
    assert result.usage["context_packet_report"]["source_graph"]["node_count"] == 3
    assert "Web links are not fetched by the local report tool." in result.warnings
    assert "Media transcripts are treated as provided evidence." in result.warnings
    report_payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert report_payload["context_packet_id"] == packet["context_packet_id"]
    assert report_payload["items"][0]["evidence_kind"] == "code_evidence"
    assert report_payload["items"][1]["evidence_kind"] == "citation_evidence"
    assert report_payload["items"][2]["evidence_kind"] == "media_evidence"
    assert report_payload["limitations"]["web_fetch"] == "not_performed"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(report_pdf).pages)
    assert "Audit Context Packet Report" in text
    assert "Risk Service" in text
    assert "Context Packet Docs" in text
    assert "Keep provenance explicit" in text
    assert "Source Graph" in text


def test_context_packet_report_cli_rest_and_mcp_are_exposed(tmp_path: Path) -> None:
    packet_path = tmp_path / "context.packet.json"
    cli_pdf = tmp_path / "cli-context-report.pdf"
    cli_json = tmp_path / "cli-context-report.json"
    api_pdf = tmp_path / "api-context-report.pdf"
    mcp_pdf = tmp_path / "mcp-context-report.pdf"
    build_context_packet(
        [{"text": "Create a local provenance report.", "role": "brief", "label": "Brief"}],
        output_path=packet_path,
        title="Interface Context",
    )

    cli_result = runner.invoke(
        app,
        [
            "evidence",
            "context-packet-report",
            str(packet_path),
            "-o",
            str(cli_pdf),
            "--report-output",
            str(cli_json),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.evidence.context_packet_report/run",
        json={"context_packet_path": str(packet_path), "output_path": str(api_pdf)},
    )
    from agentpdf.mcp.server import pdf_evidence_context_packet_report

    mcp_result = json.loads(pdf_evidence_context_packet_report(str(packet_path), str(mcp_pdf)))

    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["tool"] == "pdf.evidence.context_packet_report"
    assert cli_payload["validation"]["status"] == "passed"
    assert cli_pdf.exists()
    assert cli_json.exists()
    assert api_response.status_code == 200
    assert api_response.json()["tool"] == "pdf.evidence.context_packet_report"
    assert api_response.json()["validation"]["status"] == "passed"
    assert mcp_result["tool"] == "pdf.evidence.context_packet_report"
    assert mcp_result["validation"]["status"] == "passed"


def test_build_context_packet_adds_local_image_visual_evidence(tmp_path: Path) -> None:
    image_path = tmp_path / "half-tone.png"
    image = Image.new("RGB", (64, 32), color="white")
    image.paste((0, 0, 0), box=(0, 0, 32, 32))
    image.save(image_path)
    output_pdf = tmp_path / "visual-evidence.pdf"

    packet = build_context_packet(
        [{"path": str(image_path), "role": "image_evidence", "label": "Half Tone"}],
        output_path=tmp_path / "visual.packet.json",
        title="Visual Context",
    ).usage["context_packet"]

    item = packet["items"][0]
    visual = item["metadata"]["visual_evidence"]
    assert visual["width"] == 64
    assert visual["height"] == 32
    assert visual["aspect_ratio"] == 2.0
    assert visual["is_blank"] is False
    assert visual["non_white_ratio"] == 0.5
    assert len(visual["average_color_rgb"]) == 3
    assert len(visual["perceptual_hash"]) == 16
    assert item["content"]["image"]["visual_evidence"]["perceptual_hash"] == visual["perceptual_hash"]
    assert packet["source_graph"]["nodes"][0]["evidence"]["visual_evidence"]["non_white_ratio"] == 0.5
    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []

    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)

    image_block = next(block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "image")
    assert image_block["render_hints"]["visual_evidence"]["is_blank"] is False
    assert image_block["render_hints"]["visual_evidence"]["perceptual_hash"] == visual["perceptual_hash"]
    assert "Visual evidence: non-white ratio 0.5" in result.usage["generated_markdown"]


def test_image_analyze_returns_local_metadata_and_ocr_regions(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image_path)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    result = analyze_image(image_path, languages=["eng"])

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.image_analyze"
    assert result.usage["image"]["width"] == 160
    assert result.usage["image"]["height"] == 80
    assert result.usage["ocr"]["text"] == "Hello OCR"
    assert result.usage["ocr"]["regions"][0]["image_bbox"] == [10, 20, 50, 32]
    assert "No vision model was used." in result.usage["limitations"]


def test_build_context_packet_adds_pdf_page_text_evidence(tmp_path: Path) -> None:
    source_pdf = tmp_path / "source.pdf"
    create_text_pdf(
        "Board packet source.\nRevenue risk appears on page one.\nTrace this PDF evidence.",
        source_pdf,
        title="Board Source",
    )
    output_pdf = tmp_path / "pdf-evidence.pdf"

    packet = build_context_packet(
        [{"path": str(source_pdf), "role": "pdf_evidence", "label": "Board Source PDF"}],
        output_path=tmp_path / "pdf.packet.json",
        title="PDF Evidence Context",
    ).usage["context_packet"]

    item = packet["items"][0]
    pdf_evidence = item["metadata"]["pdf_evidence"]
    assert pdf_evidence["page_count"] == 1
    assert pdf_evidence["has_text_layer"] is True
    assert pdf_evidence["text_char_count"] > 20
    assert pdf_evidence["pages"][0]["page_number"] == 1
    assert pdf_evidence["pages"][0]["bbox"][2] > 0
    assert "Revenue risk appears" in pdf_evidence["pages"][0]["text_preview"]
    assert item["content"]["pdf"]["pdf_evidence"]["pages"][0]["text_preview"] == pdf_evidence["pages"][0]["text_preview"]
    assert packet["source_graph"]["nodes"][0]["evidence"]["pdf_evidence"]["has_text_layer"] is True
    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []

    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)

    pdf_block = next(block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "pdf_reference")
    assert pdf_block["render_hints"]["pdf_evidence"]["has_text_layer"] is True
    assert pdf_block["render_hints"]["pdf_evidence"]["pages"][0]["page_number"] == 1
    assert "### Page 1 Text Evidence" in result.usage["generated_markdown"]
    assert "Revenue risk appears" in result.usage["generated_markdown"]


def test_build_context_packet_adds_web_citation_evidence(tmp_path: Path) -> None:
    output_pdf = tmp_path / "web-citation.pdf"

    packet = build_context_packet(
        [
            {
                "url": "https://OKPDF.dev/docs/context?ref=agent#citation",
                "role": "citation",
                "label": "Context Packet Docs",
                "title": "Context Packet Guide",
                "snippet": "Explains how agents preserve source refs and citation evidence.",
                "author": "OkPDF Team",
                "published_at": "2026-06-02",
            }
        ],
        output_path=tmp_path / "web.packet.json",
        title="Web Citation Context",
    ).usage["context_packet"]

    item = packet["items"][0]
    citation = item["metadata"]["citation_evidence"]
    assert citation["domain"] == "okpdf.dev"
    assert citation["normalized_url"] == "https://okpdf.dev/docs/context?ref=agent#citation"
    assert citation["title"] == "Context Packet Guide"
    assert citation["snippet"].startswith("Explains how agents")
    assert citation["fetch_status"] == "not_fetched"
    assert item["content"]["citation"]["citation_evidence"]["domain"] == "okpdf.dev"
    assert packet["source_graph"]["nodes"][0]["evidence"]["citation_evidence"]["normalized_url"] == citation["normalized_url"]
    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []

    result = compose_from_context(packet, target_profile="research_brief", output_path=output_pdf)

    citation_block = next(block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "citation")
    assert citation_block["render_hints"]["citation_evidence"]["domain"] == "okpdf.dev"
    assert citation_block["render_hints"]["citation_evidence"]["fetch_status"] == "not_fetched"
    assert "Context Packet Guide" in result.usage["generated_markdown"]
    assert "Explains how agents preserve source refs" in result.usage["generated_markdown"]


def test_compose_from_context_creates_pdf_with_source_map_and_coverage(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    csv = tmp_path / "metrics.csv"
    csv.write_text("metric,value\nlatency_ms,42\nerror_rate,0.01\n", encoding="utf-8")
    image = tmp_path / "screenshot.png"
    Image.new("RGB", (80, 40), color=(40, 80, 120)).save(image)
    source_pdf = tmp_path / "source.pdf"
    create_text_pdf("Source PDF evidence for the audit.", source_pdf)
    packet_path = tmp_path / "context.packet.json"
    output_pdf = tmp_path / "technical-audit.pdf"

    packet = build_context_packet(
        [
            {"text": "Create a technical audit PDF with cited evidence.", "role": "brief"},
            {"path": str(code), "role": "code_evidence"},
            {"path": str(csv), "role": "data_evidence"},
            {"path": str(image), "role": "image_evidence"},
            {"path": str(source_pdf), "role": "pdf_evidence"},
        ],
        output_path=packet_path,
        title="Technical Audit Context",
    ).usage["context_packet"]

    result = compose_from_context(
        packet,
        target_profile={
            "profile_id": "technical_audit",
            "title": "AgentPDF Technical Audit",
            "audience": "agent infrastructure maintainers",
            "style_pack": "paper_ink",
            "sections": ["Executive Summary", "Evidence Table", "Code Review", "Source Map"],
            "validation_required": ["render_check", "evidence_coverage_report"],
        },
        output_path=output_pdf,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.compose.from_context"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["target_profile"]["profile_id"] == "technical_audit"
    assert result.usage["composition_ir"]["composition_id"].startswith("cmp_")
    assert result.usage["composition_ir"]["blocks"][0]["source_refs"]
    blocks = {block["block_id"]: block for block in result.usage["composition_ir"]["blocks"]}
    assert blocks["item_ctx_002"]["type"] == "code"
    assert blocks["item_ctx_002"]["render_hints"]["language"] == "python"
    assert blocks["item_ctx_003"]["type"] == "table"
    assert blocks["item_ctx_003"]["render_hints"]["columns"] == ["metric", "value"]
    assert blocks["item_ctx_004"]["type"] == "image"
    assert blocks["item_ctx_004"]["render_hints"]["path"].endswith("screenshot.png")
    assert blocks["item_ctx_005"]["type"] == "pdf_reference"
    assert result.usage["evidence_coverage"]["covered_context_items"] == 5
    assert result.usage["evidence_coverage"]["coverage_ratio"] == 1.0
    assert len(result.usage["source_map"]) >= 5
    assert "![screenshot.png]" in result.usage["generated_markdown"]
    assert any(artifact.mime_type == "application/json" for artifact in result.artifacts)
    page_facts = inspect_pdf_pages(output_pdf, pages="all")
    assert sum(page["image_count"] for page in page_facts["pages"]) >= 1
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "AgentPDF Technical Audit" in text
    assert "risky_total" in text
    assert "latency_ms" in text
    assert "screenshot.png" in text
    assert "Source Map" in text


def test_compose_from_context_html_renderer_writes_html_package_pdf_and_manifest(tmp_path: Path) -> None:
    csv = tmp_path / "metrics.csv"
    csv.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    image = tmp_path / "diagram.png"
    Image.new("RGB", (80, 40), color=(40, 80, 120)).save(image)
    packet = build_context_packet(
        [
            {"text": "Create an HTML-first technical audit.", "role": "brief", "label": "Brief"},
            {"path": str(csv), "role": "data_evidence", "label": "Runtime Metrics"},
            {"path": str(image), "role": "image_evidence", "label": "Architecture Figure"},
        ],
        output_path=tmp_path / "html.context.packet.json",
        title="HTML Context",
    ).usage["context_packet"]
    output_pdf = tmp_path / "html-audit.pdf"
    html_output = tmp_path / "html-audit.html"
    manifest_path = html_output.with_suffix(".html-manifest.json")

    result = compose_from_context(
        packet,
        target_profile="technical_audit",
        output_path=output_pdf,
        renderer="html",
        html_output_path=html_output,
        title="HTML First Audit",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.compose.from_context"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output_pdf.exists()
    assert html_output.exists()
    assert manifest_path.exists()
    assert result.usage["renderer"] == "html_package"
    assert result.usage["html_output_path"] == str(html_output.resolve())
    assert result.usage["html_package_manifest_path"] == str(manifest_path.resolve())
    assert result.usage["html_package_manifest"]["block_count"] == len(result.usage["composition_ir"]["blocks"])
    assert result.usage["html_package_manifest"]["source_ref_count"] == 3
    assert result.usage["html_package_manifest"]["asset_count"] == 1
    assert result.usage["html_package_manifest"]["assets"][0]["source_path"] == str(image.resolve())
    layer_map = result.usage["html_package_manifest"]["layer_map"]
    assert result.usage["html_package_manifest"]["layer_map_count"] == len(result.usage["composition_ir"]["blocks"])
    assert result.usage["html_package_manifest"]["contract"]["layer_id_attribute"] == "data-layer-id"
    assert result.usage["html_package_manifest"]["contract"]["bbox_precision"] == "estimated_dom_not_pdf_glyph_bbox"
    assert {layer["block_id"] for layer in layer_map} == {
        block["block_id"] for block in result.usage["composition_ir"]["blocks"]
    }
    table_layer = next(layer for layer in layer_map if layer["block_type"] == "table")
    assert table_layer["layer_id"].startswith("html_layer_item_ctx_002")
    assert table_layer["source_refs"] == ["ctx_002"]
    assert table_layer["anchor"]["anchor_kind"] == "estimated_dom_anchor"
    assert table_layer["anchor"]["dom_selector"] == f'[data-layer-id="{table_layer["layer_id"]}"]'
    assert table_layer["anchor"]["bbox_precision"] == "estimated_dom_not_pdf_glyph_bbox"
    assert table_layer["anchor"]["dom_bbox_px"]["width"] > 0
    assert len(table_layer["anchor"]["normalized_bbox"]) == 4
    assert result.usage["html_package_validation"]["status"] == "passed"
    assert any(check.name == "html_package_manifest_valid" for check in result.validation.checks)
    assert any(check.name == "all_assets_resolved" for check in result.validation.checks)
    assert any(artifact.mime_type == "text/html" for artifact in result.artifacts)
    assert any(str(artifact.path).endswith(".html-manifest.json") for artifact in result.artifacts)

    html_text = html_output.read_text(encoding="utf-8")
    assert "<body data-agentpdf-document" in html_text
    assert 'data-agentpdf-renderer="html-package-v0"' in html_text
    assert 'data-block-id="summary"' in html_text
    assert 'data-layer-id="html_layer_summary"' in html_text
    assert 'data-source-refs="ctx_001 ctx_002 ctx_003"' in html_text
    assert '<img src="./html-audit.assets/' in html_text
    assert "latency_ms" in html_text
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "HTML First Audit" in pdf_text
    assert "latency_ms" in pdf_text


def test_compose_plan_and_render_ir_create_replayable_pdf(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    csv = tmp_path / "metrics.csv"
    csv.write_text("metric,value\nlatency_ms,42\n", encoding="utf-8")
    packet_path = tmp_path / "context.packet.json"
    plan_path = tmp_path / "technical-audit.plan.json"
    output_pdf = tmp_path / "technical-audit-rendered.pdf"

    packet = build_context_packet(
        [
            {"text": "Create a replayable technical audit.", "role": "brief"},
            {"path": str(code), "role": "code_evidence"},
            {"path": str(csv), "role": "data_evidence"},
        ],
        output_path=packet_path,
        title="Replay Context",
    ).usage["context_packet"]

    plan = plan_composition(
        packet,
        target_profile="technical_audit",
        output_path=plan_path,
        title="Replayable Technical Audit",
    )
    rendered = render_composition_ir(plan_path, output_path=output_pdf)

    assert plan.status == "succeeded"
    assert plan.tool == "pdf.compose.plan"
    assert plan.artifacts[0].source_tool == "pdf.compose.plan"
    assert plan.usage["composition_ir"]["composition_id"].startswith("cmp_")
    assert plan.usage["render_plan"]["renderer"] == "local_markdown_pdf"
    assert "Replayable Technical Audit" in plan.usage["render_plan"]["markdown"]
    assert plan.usage["evidence_coverage"]["coverage_ratio"] == 1.0
    assert plan.next_recommended_tools[0] == "pdf.compose.render_ir"
    saved_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert saved_plan["composition_plan_id"].startswith("cmpplan_")
    assert saved_plan["render_plan"]["markdown"] == plan.usage["render_plan"]["markdown"]

    assert rendered.status == "succeeded"
    assert rendered.tool == "pdf.compose.render_ir"
    assert rendered.validation is not None
    assert rendered.validation.status == "passed"
    assert rendered.artifacts[0].source_tool == "pdf.compose.render_ir"
    assert rendered.usage["composition_id"] == plan.usage["composition_ir"]["composition_id"]
    assert rendered.usage["evidence_coverage"]["coverage_ratio"] == 1.0
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "Replayable Technical Audit" in text
    assert "risky_total" in text
    assert "latency_ms" in text


def test_compose_plan_and_render_ir_are_exposed_to_cli_rest_mcp(tmp_path: Path) -> None:
    packet_path = tmp_path / "context.packet.json"
    cli_plan = tmp_path / "cli.plan.json"
    cli_pdf = tmp_path / "cli-rendered.pdf"
    api_plan = tmp_path / "api.plan.json"
    api_pdf = tmp_path / "api-rendered.pdf"
    mcp_plan_path = tmp_path / "mcp.plan.json"
    mcp_pdf = tmp_path / "mcp-rendered.pdf"
    build_context_packet(
        [{"text": "Create a plan and render it later.", "role": "brief", "label": "Brief"}],
        output_path=packet_path,
        title="Interface Plan Context",
    )

    cli_plan_result = runner.invoke(
        app,
        [
            "compose",
            "plan",
            str(packet_path),
            "--profile",
            "research_brief",
            "-o",
            str(cli_plan),
            "--json",
        ],
    )
    cli_render_result = runner.invoke(
        app,
        [
            "compose",
            "render-ir",
            str(cli_plan),
            "-o",
            str(cli_pdf),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_plan_response = client.post(
        "/v1/tools/pdf.compose.plan/run",
        json={
            "context_packet_path": str(packet_path),
            "profile": "research_brief",
            "output_path": str(api_plan),
        },
    )
    api_render_response = client.post(
        "/v1/tools/pdf.compose.render_ir/run",
        json={"composition_path": str(api_plan), "output_path": str(api_pdf)},
    )
    mcp_plan = json.loads(
        pdf_compose_plan(
            str(packet_path),
            target_profile="research_brief",
            output_path=str(mcp_plan_path),
        )
    )
    mcp_render = json.loads(pdf_compose_render_ir(str(mcp_plan_path), str(mcp_pdf)))

    assert cli_plan_result.exit_code == 0
    assert json.loads(cli_plan_result.stdout)["tool"] == "pdf.compose.plan"
    assert cli_plan.exists()
    assert cli_render_result.exit_code == 0
    assert json.loads(cli_render_result.stdout)["tool"] == "pdf.compose.render_ir"
    assert cli_pdf.exists()
    assert api_plan_response.status_code == 200
    assert api_plan_response.json()["tool"] == "pdf.compose.plan"
    assert api_plan.exists()
    assert api_render_response.status_code == 200
    assert api_render_response.json()["tool"] == "pdf.compose.render_ir"
    assert api_render_response.json()["validation"]["status"] == "passed"
    assert api_pdf.exists()
    assert mcp_plan["tool"] == "pdf.compose.plan"
    assert mcp_plan_path.exists()
    assert mcp_render["tool"] == "pdf.compose.render_ir"
    assert mcp_render["validation"]["status"] == "passed"
    assert mcp_pdf.exists()


def test_compose_from_context_html_renderer_is_exposed_to_cli_rest_mcp(tmp_path: Path) -> None:
    packet_path = tmp_path / "html.context.packet.json"
    build_context_packet(
        [{"text": "Create an HTML package and PDF.", "role": "brief", "label": "Brief"}],
        output_path=packet_path,
        title="HTML Interface Context",
    )
    cli_pdf = tmp_path / "cli-html.pdf"
    cli_html = tmp_path / "cli-html.html"
    api_pdf = tmp_path / "api-html.pdf"
    api_html = tmp_path / "api-html.html"
    mcp_pdf = tmp_path / "mcp-html.pdf"
    mcp_html = tmp_path / "mcp-html.html"

    cli_result = runner.invoke(
        app,
        [
            "compose",
            "from-context",
            str(packet_path),
            "--profile",
            "research_brief",
            "-o",
            str(cli_pdf),
            "--renderer",
            "html",
            "--html-output",
            str(cli_html),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.compose.from_context/run",
        json={
            "context_packet_path": str(packet_path),
            "profile": "research_brief",
            "output_path": str(api_pdf),
            "renderer": "html",
            "html_output_path": str(api_html),
        },
    )
    mcp_payload = json.loads(
        pdf_compose_from_context(
            str(packet_path),
            str(mcp_pdf),
            target_profile="research_brief",
            renderer="html",
            html_output_path=str(mcp_html),
        )
    )

    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["tool"] == "pdf.compose.from_context"
    assert cli_payload["usage"]["renderer"] == "html_package"
    assert cli_pdf.exists()
    assert cli_html.exists()
    assert cli_html.with_suffix(".html-manifest.json").exists()
    assert api_response.status_code == 200
    assert api_response.json()["usage"]["renderer"] == "html_package"
    assert api_pdf.exists()
    assert api_html.exists()
    assert api_html.with_suffix(".html-manifest.json").exists()
    assert mcp_payload["tool"] == "pdf.compose.from_context"
    assert mcp_payload["usage"]["renderer"] == "html_package"
    assert mcp_pdf.exists()
    assert mcp_html.exists()
    assert mcp_html.with_suffix(".html-manifest.json").exists()


def test_render_html_package_is_exposed_to_cli_rest_mcp(tmp_path: Path) -> None:
    image = tmp_path / "diagram.png"
    Image.new("RGB", (80, 40), color=(40, 80, 120)).save(image)
    package = write_composition_html_package(
        composition_ir={
            "composition_id": "comp_render_interfaces",
            "context_packet_id": "ctxpkt_render_interfaces",
            "target_profile_id": "technical_audit",
            "blocks": [
                {
                    "block_id": "figure_1",
                    "type": "image",
                    "title": "Architecture Figure",
                    "source_refs": ["ctx_image"],
                    "render_hints": {"path": str(image), "caption": "Local image evidence."},
                }
            ],
        },
        source_map=[{"block_id": "figure_1", "source_ref": "ctx_image", "type": "image"}],
        target_profile={"profile_id": "technical_audit", "title": "Audit"},
        render_plan={"title": "Audit"},
        html_output_path=tmp_path / "audit.html",
        source_tool="pdf.compose.from_context",
    )
    manifest_path = package["html_package_manifest_path"]
    cli_pdf = tmp_path / "cli-rendered.pdf"
    api_pdf = tmp_path / "api-rendered.pdf"
    mcp_pdf = tmp_path / "mcp-rendered.pdf"

    cli_result = runner.invoke(
        app,
        [
            "render-html-package",
            manifest_path,
            "-o",
            str(cli_pdf),
            "--renderer-backend",
            "local_html_package_fallback",
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.render.html_package/run",
        json={
            "package_path": manifest_path,
            "output_path": str(api_pdf),
            "renderer_backend": "local_html_package_fallback",
        },
    )
    browser_pdf = tmp_path / "browser-rendered.pdf"
    browser_response = client.post(
        "/v1/tools/pdf.render.html_package/run",
        json={
            "package_path": manifest_path,
            "output_path": str(browser_pdf),
            "renderer_backend": "browser_chromium",
        },
    )
    mcp_payload = json.loads(
        mcp_server.pdf_render_html_package(
            manifest_path,
            str(mcp_pdf),
            renderer_backend="local_html_package_fallback",
        )
    )

    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["tool"] == "pdf.render.html_package"
    assert cli_payload["usage"]["renderer"] == "local_html_package_fallback"
    assert cli_payload["usage"]["requested_renderer_backend"] == "local_html_package_fallback"
    assert cli_pdf.exists()
    assert api_response.status_code == 200
    assert api_response.json()["tool"] == "pdf.render.html_package"
    assert api_response.json()["usage"]["requested_renderer_backend"] == "local_html_package_fallback"
    assert api_response.json()["usage"]["html_package_manifest"]["asset_count"] == 1
    assert api_pdf.exists()
    assert browser_response.status_code == 400
    browser_payload = browser_response.json()
    assert browser_payload["status"] == "failed"
    assert browser_payload["error"]["code"] == "dependency_missing"
    assert browser_payload["usage"]["renderer"] == "browser_chromium"
    assert browser_payload["usage"]["render_skip_reason"] == "renderer_backend_unavailable"
    assert not browser_pdf.exists()
    assert mcp_payload["tool"] == "pdf.render.html_package"
    assert mcp_payload["validation"]["status"] == "passed"
    assert mcp_payload["usage"]["requested_renderer_backend"] == "local_html_package_fallback"
    assert mcp_pdf.exists()


def test_inline_table_context_composes_as_table_block(tmp_path: Path) -> None:
    output_pdf = tmp_path / "metrics.pdf"
    packet = build_context_packet(
        [
            {
                "table": {
                    "columns": ["metric", "value"],
                    "rows": [["latency_ms", "42"], ["error_rate", "0.01"]],
                },
                "role": "data_evidence",
                "label": "Runtime Metrics",
            }
        ],
        output_path=tmp_path / "packet.json",
        title="Metrics Context",
    ).usage["context_packet"]

    assert packet["items"][0]["type"] == "data"
    assert packet["items"][0]["metadata"]["row_count"] == 2
    assert packet["items"][0]["content"]["table"]["columns"] == ["metric", "value"]

    result = compose_from_context(packet, target_profile="evidence_packet_pdf", output_path=output_pdf)

    block = result.usage["composition_ir"]["blocks"][2]
    assert block["type"] == "table"
    assert block["render_hints"]["columns"] == ["metric", "value"]
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "Runtime Metrics" in text
    assert "latency_ms" in text


def test_build_context_packet_adds_table_evidence(tmp_path: Path) -> None:
    output_pdf = tmp_path / "table-evidence.pdf"
    packet = build_context_packet(
        [
            {
                "table": {
                    "columns": ["metric", "value", "healthy"],
                    "rows": [
                        ["latency_ms", "42", "true"],
                        ["error_rate", "0.01", "true"],
                        ["queue_depth", "7", "false"],
                    ],
                },
                "role": "data_evidence",
                "label": "Runtime Metrics",
            }
        ],
        output_path=tmp_path / "table.packet.json",
        title="Table Evidence Context",
    ).usage["context_packet"]

    item = packet["items"][0]
    table_evidence = item["metadata"]["table_evidence"]
    assert table_evidence["row_count"] == 3
    assert table_evidence["column_count"] == 3
    assert table_evidence["preview_row_count"] == 3
    assert table_evidence["column_types"] == {
        "metric": "string",
        "value": "number",
        "healthy": "boolean",
    }
    assert len(table_evidence["table_hash"]) == 64
    assert item["content"]["table"]["table_evidence"]["table_hash"] == table_evidence["table_hash"]
    assert packet["source_graph"]["nodes"][0]["evidence"]["table_evidence"]["table_hash"] == table_evidence["table_hash"]
    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []

    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)

    table_block = next(block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "table")
    assert table_block["render_hints"]["table_evidence"]["column_types"]["value"] == "number"
    assert table_block["render_hints"]["table_evidence"]["table_hash"] == table_evidence["table_hash"]
    assert "Table evidence: 3 rows, 3 columns" in result.usage["generated_markdown"]


def test_build_context_packet_adds_code_evidence(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "\n".join(
            [
                "class RiskModel:",
                "    def score(self, value):",
                "        return value * 2",
                "",
                "def risky_total(items):",
                "    return sum(items)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output_pdf = tmp_path / "code-evidence.pdf"

    packet = build_context_packet(
        [{"path": str(source), "role": "code_evidence", "label": "Risk Scoring Code"}],
        output_path=tmp_path / "code.packet.json",
        title="Code Evidence Context",
    ).usage["context_packet"]

    item = packet["items"][0]
    code_evidence = item["metadata"]["code_evidence"]
    assert code_evidence["language"] == "python"
    assert code_evidence["line_count"] == 6
    assert code_evidence["char_count"] > 40
    assert len(code_evidence["code_hash"]) == 64
    assert code_evidence["symbol_count"] == 3
    assert {symbol["name"] for symbol in code_evidence["symbols"]} == {"RiskModel", "score", "risky_total"}
    assert item["content"]["code"]["code_evidence"]["code_hash"] == code_evidence["code_hash"]
    assert packet["source_graph"]["nodes"][0]["evidence"]["code_evidence"]["symbol_count"] == 3
    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []

    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)

    code_block = next(block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "code")
    assert code_block["render_hints"]["code_evidence"]["language"] == "python"
    assert code_block["render_hints"]["code_evidence"]["code_hash"] == code_evidence["code_hash"]
    assert "Code evidence: python, 6 lines, 3 symbols" in result.usage["generated_markdown"]
    assert "risky_total" in result.usage["generated_markdown"]


def test_code_evidence_scans_symbols_beyond_preview_window(tmp_path: Path) -> None:
    source = tmp_path / "large_service.py"
    prefix = "\n".join(f"# filler {index:04d} " + ("x" * 96) for index in range(160))
    text = f"{prefix}\n\ndef late_symbol(value):\n    return value\n"
    source.write_text(text, encoding="utf-8")

    packet = build_context_packet(
        [{"path": str(source), "role": "code_evidence"}],
        output_path=tmp_path / "large-code.packet.json",
    ).usage["context_packet"]

    code_evidence = packet["items"][0]["metadata"]["code_evidence"]
    assert code_evidence["char_count"] == len(text)
    assert code_evidence["code_hash"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert "late_symbol" in {symbol["name"] for symbol in code_evidence["symbols"]}
    assert packet["items"][0]["content"]["code"]["code_evidence"]["code_hash"] == code_evidence["code_hash"]


def test_compose_slide_deck_profile_creates_slide_like_pdf(tmp_path: Path) -> None:
    image = tmp_path / "diagram.png"
    Image.new("RGB", (120, 80), color=(20, 100, 90)).save(image)
    packet = build_context_packet(
        [
            {"text": "Create a slide deck for an agent infrastructure review.", "role": "brief"},
            {
                "table": {
                    "columns": ["capability", "status"],
                    "rows": [["context packet", "implemented"], ["slide rendering", "local baseline"]],
                },
                "role": "data_evidence",
                "label": "Capability Matrix",
            },
            {"path": str(image), "role": "image_evidence", "label": "Architecture Diagram"},
        ],
        output_path=tmp_path / "deck.packet.json",
        title="Deck Context",
    ).usage["context_packet"]
    output_pdf = tmp_path / "agent-review-deck.pdf"

    result = compose_from_context(packet, target_profile="slide_deck", output_path=output_pdf)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["target_profile"]["layout_mode"] == "slides"
    assert result.usage["slide_count"] >= 4
    slide_blocks = [
        block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "slide"
    ]
    assert len(slide_blocks) == result.usage["slide_count"]
    assert slide_blocks[0]["render_hints"]["slide_number"] == 1
    assert any("ctx_003" in block["source_refs"] for block in slide_blocks)
    assert any(artifact.mime_type == "application/json" for artifact in result.artifacts)
    facts = inspect_pdf_pages(output_pdf, pages="all")
    assert facts["page_count"] == result.usage["slide_count"]
    assert sum(page["image_count"] for page in facts["pages"]) >= 1
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "AgentPDF Slide Deck" in text
    assert "Capability Matrix" in text
    assert "Architecture Diagram" in text
    assert "Source Map" in text


def test_audio_video_context_composes_traceable_media_blocks(tmp_path: Path) -> None:
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    video = tmp_path / "training.mp4"
    video.write_bytes(b"\x00\x00\x00\x18ftypmp42 local video fixture")
    output_pdf = tmp_path / "media-audit.pdf"
    deck_pdf = tmp_path / "media-deck.pdf"

    packet = build_context_packet(
        [
            {
                "path": str(audio),
                "role": "audio_context",
                "label": "Meeting Audio",
                "transcript": "00:00 Kickoff\n00:12 Decision: keep the local worker boundary explicit.",
                "duration_seconds": 42.5,
                "chapters": [
                    {"start_seconds": 0, "title": "Kickoff"},
                    {"start_seconds": 12, "title": "Decision"},
                ],
            },
            {
                "path": str(video),
                "role": "video_context",
                "label": "Training Video",
                "transcript": "00:00 Dashboard tour\n00:20 Export demo",
                "duration_seconds": 84,
                "keyframes": [{"timestamp_seconds": 20, "label": "Export screen"}],
            },
        ],
        output_path=tmp_path / "media.packet.json",
        title="Media Context",
        intent="Create a target PDF from audio and video evidence.",
    ).usage["context_packet"]

    assert [item["type"] for item in packet["items"]] == ["audio", "video"]
    assert packet["items"][0]["metadata"]["duration_seconds"] == 42.5
    assert packet["items"][0]["metadata"]["chapter_count"] == 2
    assert packet["items"][0]["metadata"]["transcript_char_count"] > 0
    assert packet["items"][0]["content"]["transcript"]["text"].startswith("00:00 Kickoff")
    assert packet["items"][1]["metadata"]["keyframe_count"] == 1
    assert packet["source_graph"]["nodes"][0]["evidence"]["duration_seconds"] == 42.5

    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)
    deck = compose_from_context(packet, target_profile="slide_deck", output_path=deck_pdf)

    blocks = {block["block_id"]: block for block in result.usage["composition_ir"]["blocks"]}
    assert blocks["item_ctx_001"]["type"] == "audio_reference"
    assert blocks["item_ctx_001"]["render_hints"]["transcript_char_count"] > 0
    assert blocks["item_ctx_002"]["type"] == "video_reference"
    assert blocks["item_ctx_002"]["render_hints"]["keyframe_count"] == 1
    assert result.usage["evidence_coverage"]["coverage_ratio"] == 1.0
    assert deck.usage["slide_count"] >= 4
    assert any(
        block["render_hints"]["layout"] == "media"
        for block in deck.usage["composition_ir"]["blocks"]
        if block["type"] == "slide"
    )

    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    deck_text = "\n".join(page.extract_text() or "" for page in PdfReader(deck_pdf).pages)
    assert "Meeting Audio" in text
    assert "Decision: keep the local worker boundary explicit" in text
    assert "Training Video" in text
    assert "Dashboard tour" in text
    assert "Media context uses provided transcript" in result.warnings
    assert "Training Video" in deck_text


def test_build_context_packet_records_media_transcript_sidecar_provenance(tmp_path: Path) -> None:
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    transcript = tmp_path / "meeting.transcript.txt"
    transcript_text = "00:00 Kickoff\n00:18 Decision: cite the transcript sidecar."
    transcript.write_text(transcript_text, encoding="utf-8")
    output_pdf = tmp_path / "sidecar-media.pdf"

    packet = build_context_packet(
        [
            {
                "context_item_id": "ctx_audio",
                "path": str(audio),
                "role": "audio_context",
                "label": "Meeting Audio",
                "transcript_path": str(transcript),
                "duration_seconds": 31,
            }
        ],
        output_path=tmp_path / "sidecar-media.packet.json",
        title="Sidecar Media Context",
    ).usage["context_packet"]

    item = packet["items"][0]
    metadata = item["metadata"]
    content = item["content"]
    expected_hash = hashlib.sha256(transcript.read_bytes()).hexdigest()

    assert content["transcript"]["text"] == transcript_text
    assert content["transcript"]["source"] == "sidecar_file"
    assert content["transcript"]["path"] == transcript.resolve().as_posix()
    assert metadata["transcript_source"] == "sidecar_file"
    assert metadata["transcript_source_path"] == transcript.resolve().as_posix()
    assert metadata["transcript_sha256"] == expected_hash
    assert metadata["transcript_size_bytes"] == len(transcript.read_bytes())

    graph = packet["source_graph"]
    transcript_node = next(node for node in graph["nodes"] if node["type"] == "transcript")
    assert transcript_node["context_item_id"] == "ctx_audio"
    assert transcript_node["source_ref"] == "ctx_audio#transcript"
    assert transcript_node["uri"] == transcript.resolve().as_posix()
    assert transcript_node["evidence"]["sha256"] == expected_hash
    assert transcript_node["evidence"]["transcript_char_count"] == len(transcript_text)
    assert graph["edges"] == [
        {
            "from_node_id": transcript_node["node_id"],
            "to_node_id": "src_001",
            "relation": "provides_transcript_for",
            "context_item_id": "ctx_audio",
            "source_ref": "ctx_audio",
            "sidecar_source_ref": "ctx_audio#transcript",
        }
    ]

    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []

    result = compose_from_context(packet, target_profile="technical_audit", output_path=output_pdf)

    media_block = next(block for block in result.usage["composition_ir"]["blocks"] if block["type"] == "audio_reference")
    assert media_block["render_hints"]["transcript_source"] == "sidecar_file"
    assert media_block["render_hints"]["transcript_source_path"] == transcript.resolve().as_posix()
    assert media_block["render_hints"]["transcript_sha256"] == expected_hash
    assert "Transcript source: `sidecar_file`" in result.usage["generated_markdown"]


def test_context_build_cli_accepts_structured_item_json(tmp_path: Path) -> None:
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    packet_path = tmp_path / "media.packet.json"
    item = {
        "path": str(audio),
        "role": "audio_context",
        "label": "Meeting Audio",
        "transcript": "00:00 Kickoff\n00:12 Decision: keep the local worker boundary explicit.",
        "duration_seconds": 42.5,
    }

    result = runner.invoke(
        app,
        [
            "context",
            "build",
            "--item-json",
            json.dumps(item),
            "-o",
            str(packet_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    packet = payload["usage"]["context_packet"]
    assert packet["items"][0]["type"] == "audio"
    assert packet["items"][0]["content"]["transcript"]["text"].startswith("00:00 Kickoff")
    assert packet["items"][0]["metadata"]["duration_seconds"] == 42.5


def test_context_compose_cli_builds_packet_and_target_pdf(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    packet_path = tmp_path / "context.packet.json"
    output_pdf = tmp_path / "technical-audit.pdf"

    packet_result = runner.invoke(
        app,
        [
            "context",
            "build",
            "--text",
            "Create a technical audit PDF.",
            "--file",
            str(code),
            "-o",
            str(packet_path),
            "--title",
            "Audit Context",
            "--json",
        ],
    )
    compose_result = runner.invoke(
        app,
        [
            "compose",
            "from-context",
            str(packet_path),
            "--profile",
            "technical_audit",
            "-o",
            str(output_pdf),
            "--json",
        ],
    )

    assert packet_result.exit_code == 0
    packet_payload = json.loads(packet_result.stdout)
    assert packet_payload["tool"] == "pdf.context.build_packet"
    assert packet_payload["usage"]["item_count"] == 2
    assert compose_result.exit_code == 0
    compose_payload = json.loads(compose_result.stdout)
    assert compose_payload["tool"] == "pdf.compose.from_context"
    assert compose_payload["usage"]["target_profile"]["profile_id"] == "technical_audit"
    assert compose_payload["validation"]["status"] == "passed"
    assert output_pdf.exists()


def test_compose_from_context_includes_document_text_snippets(tmp_path: Path) -> None:
    document = tmp_path / "brief.md"
    document.write_text("# Field Notes\n\nMargin pressure is the largest risk.\n", encoding="utf-8")
    output_pdf = tmp_path / "brief.pdf"
    packet = build_context_packet(
        [{"path": str(document), "role": "source_document"}],
        output_path=tmp_path / "packet.json",
        title="Document Context",
    ).usage["context_packet"]

    result = compose_from_context(packet, target_profile="research_brief", output_path=output_pdf)

    assert result.status == "succeeded"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "Field Notes" in text
    assert "Margin pressure is the largest risk" in text


def test_compose_from_context_includes_docx_text_snippets(tmp_path: Path) -> None:
    document = tmp_path / "field-notes.docx"
    _write_minimal_docx(
        document,
        [
            "DOCX Field Notes",
            "Margin pressure is the largest risk.",
        ],
    )
    output_pdf = tmp_path / "docx-brief.pdf"
    packet = build_context_packet(
        [{"path": str(document), "role": "source_document", "label": "DOCX Notes"}],
        output_path=tmp_path / "docx.packet.json",
        title="DOCX Document Context",
    ).usage["context_packet"]

    result = compose_from_context(packet, target_profile="research_brief", output_path=output_pdf)

    assert result.status == "succeeded"
    assert packet["items"][0]["metadata"]["document_evidence"]["format"] == "docx"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output_pdf).pages)
    assert "DOCX Field Notes" in text
    assert "Margin pressure is the largest risk" in text


def test_context_compose_api_and_mcp_expose_agent_tools(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def risky_total(items):\n    return sum(items)\n", encoding="utf-8")
    api_packet = tmp_path / "api.packet.json"
    api_pdf = tmp_path / "api-audit.pdf"
    mcp_packet = tmp_path / "mcp.packet.json"
    mcp_pdf = tmp_path / "mcp-audit.pdf"
    client = TestClient(create_app())

    build_response = client.post(
        "/v1/tools/pdf.context.build_packet/run",
        json={
            "context_items": [
                {"text": "Create a technical audit PDF.", "role": "brief"},
                {"path": str(code), "role": "code_evidence"},
            ],
            "output_path": str(api_packet),
            "title": "API Audit Context",
        },
    )
    compose_response = client.post(
        "/v1/tools/pdf.compose.from_context/run",
        json={
            "context_packet_path": str(api_packet),
            "profile": "technical_audit",
            "output_path": str(api_pdf),
        },
    )

    assert build_response.status_code == 200
    assert build_response.json()["tool"] == "pdf.context.build_packet"
    assert compose_response.status_code == 200
    assert compose_response.json()["tool"] == "pdf.compose.from_context"
    assert compose_response.json()["validation"]["status"] == "passed"

    mcp_build = json.loads(
        pdf_context_build_packet(
            [
                {"text": "Create a technical audit PDF.", "role": "brief"},
                {"path": str(code), "role": "code_evidence"},
            ],
            str(mcp_packet),
            title="MCP Audit Context",
        )
    )
    mcp_compose = json.loads(pdf_compose_from_context(str(mcp_packet), str(mcp_pdf), target_profile="technical_audit"))

    assert mcp_build["tool"] == "pdf.context.build_packet"
    assert mcp_compose["tool"] == "pdf.compose.from_context"
    assert mcp_compose["validation"]["status"] == "passed"


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    def xml_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    body = "".join(
        f"<w:p><w:r><w:t>{xml_escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr("word/document.xml", document_xml)


def _fake_tesseract_tsv(
    image_path: Path,
    languages: list[str],
    engine: str,
    psm: int,
) -> str:
    assert image_path.exists()
    assert languages == ["eng"]
    assert engine == "tesseract"
    assert psm == 6
    return (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t40\t12\t96\tHello\n"
        "5\t1\t1\t1\t1\t2\t56\t20\t28\t12\t91\tOCR\n"
    )
