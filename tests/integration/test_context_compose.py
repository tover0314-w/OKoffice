import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from PIL import Image
from pypdf import PdfReader
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.compose.context import compose_from_context
from agentpdf.context.packet import build_context_packet
from agentpdf.core.pdf import create_text_pdf, inspect_pdf_pages
from agentpdf.mcp.server import pdf_compose_from_context, pdf_context_build_packet


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
