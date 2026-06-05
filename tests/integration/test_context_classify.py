import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from typer.testing import CliRunner

from okoffice.api.app import create_app
from okoffice.cli.main import app
from okoffice.context.classify import classify_context
from okoffice.context.packet import build_context_packet
from okoffice.mcp.server import pdf_context_classify
from okoffice.tools.registry import get_tool


runner = CliRunner()


def _build_multisource_packet(tmp_path: Path) -> Path:
    code = tmp_path / "service.py"
    code.write_text("def score(value):\n    return value * 2\n", encoding="utf-8")
    csv = tmp_path / "metrics.csv"
    csv.write_text("metric,value\nlatency_ms,42\nerror_rate,0.01\n", encoding="utf-8")
    image = tmp_path / "diagram.png"
    Image.new("RGB", (96, 48), color=(20, 80, 140)).save(image)
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    packet_path = tmp_path / "context.packet.json"
    build_context_packet(
        [
            {"text": "Create a technical audit PDF with source evidence.", "role": "brief"},
            {"path": str(code), "role": "code_evidence", "label": "Scoring Code"},
            {"path": str(csv), "role": "data_evidence", "label": "Runtime Metrics"},
            {"path": str(image), "role": "image_evidence", "label": "Architecture Diagram"},
            {
                "url": "https://okpdf.dev/docs/context",
                "role": "citation",
                "label": "Context Docs",
                "snippet": "Context packets preserve evidence for agents.",
            },
            {
                "path": str(audio),
                "role": "audio_context",
                "label": "Planning Audio",
                "transcript": "00:00 Keep local provenance explicit.",
                "duration_seconds": 18,
            },
        ],
        output_path=packet_path,
        title="Classification Context",
        intent="Classify sources before composing a target PDF.",
    )
    return packet_path


def test_context_classify_maps_items_to_blocks_slots_and_local_limitations(tmp_path: Path) -> None:
    packet_path = _build_multisource_packet(tmp_path)
    output_path = tmp_path / "context.classification.json"

    result = classify_context(
        packet_path,
        target_profile="technical_audit",
        output_path=output_path,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.classify"
    assert result.artifacts[0].source_tool == "pdf.context.classify"
    assert result.usage["classification_count"] == 6
    assert result.usage["target_profile"]["profile_id"] == "technical_audit"
    assert result.usage["type_counts"] == {
        "audio": 1,
        "code": 1,
        "data": 1,
        "image": 1,
        "text": 1,
        "web_link": 1,
    }
    assert "pdf.compose.from_context" in result.next_recommended_tools
    assert "pdf.compose.add_citation" in result.next_recommended_tools
    assert "pdf.compose.add_media_reference" in result.next_recommended_tools
    assert "Web links are not fetched by local classification." in result.warnings
    assert "Media transcripts are treated as provided evidence." in result.warnings

    by_ref = {item["source_ref"]: item for item in result.usage["classifications"]}
    assert by_ref["ctx_002"]["suggested_block_type"] == "code"
    assert by_ref["ctx_002"]["primary_evidence_kind"] == "code_evidence"
    assert by_ref["ctx_002"]["suggested_target_slots"] == ["code_review"]
    assert "code_review" in by_ref["ctx_002"]["likely_target_uses"]
    assert "local_code_symbol_scan_v0" in by_ref["ctx_002"]["evidence_methods"]
    assert by_ref["ctx_003"]["suggested_block_type"] == "table"
    assert by_ref["ctx_003"]["suggested_target_slots"] == ["evidence_table"]
    assert by_ref["ctx_004"]["suggested_block_type"] == "image"
    assert by_ref["ctx_004"]["suggested_target_slots"] == ["visual_evidence"]
    assert by_ref["ctx_005"]["suggested_block_type"] == "citation"
    assert "web_not_fetched" in by_ref["ctx_005"]["limitations"]
    assert by_ref["ctx_006"]["suggested_block_type"] == "audio_reference"
    assert by_ref["ctx_006"]["suggested_target_slots"] == ["media_evidence"]
    assert "provided_transcript_only" in by_ref["ctx_006"]["limitations"]

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["context_packet_id"] == result.usage["context_packet_id"]
    assert written["classifications"][1]["source_ref"] == "ctx_002"


def test_context_classify_cli_rest_mcp_and_registry_are_exposed(tmp_path: Path) -> None:
    packet_path = _build_multisource_packet(tmp_path)
    cli_output = tmp_path / "cli.classification.json"
    api_output = tmp_path / "api.classification.json"
    mcp_output = tmp_path / "mcp.classification.json"

    cli_result = runner.invoke(
        app,
        [
            "context",
            "classify",
            str(packet_path),
            "--profile",
            "technical_audit",
            "-o",
            str(cli_output),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.context.classify/run",
        json={
            "context_packet_path": str(packet_path),
            "profile": "technical_audit",
            "output_path": str(api_output),
        },
    )
    mcp_result = json.loads(
        pdf_context_classify(
            str(packet_path),
            target_profile="technical_audit",
            output_path=str(mcp_output),
        )
    )

    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["tool"] == "pdf.context.classify"
    assert cli_payload["usage"]["classification_count"] == 6
    assert cli_output.exists()
    assert api_response.status_code == 200
    assert api_response.json()["tool"] == "pdf.context.classify"
    assert api_response.json()["usage"]["classification_count"] == 6
    assert api_output.exists()
    assert mcp_result["tool"] == "pdf.context.classify"
    assert mcp_result["usage"]["classification_count"] == 6
    assert mcp_output.exists()
    assert get_tool("pdf.context.classify").implemented is True
