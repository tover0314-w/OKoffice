import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.compose.context import list_target_profiles, validate_target_profile
from agentpdf.mcp.server import pdf_target_profiles, pdf_target_validate_profile


runner = CliRunner()


def test_target_profile_catalog_describes_agent_slots(tmp_path: Path) -> None:
    output_path = tmp_path / "target-profiles.json"

    result = list_target_profiles(output_path=output_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.target.profiles"
    assert result.artifacts[0].mime_type == "application/json"
    catalog = result.usage["profile_catalog"]
    assert catalog["profile_count"] >= 5
    technical = catalog["profiles"]["technical_audit"]
    assert technical["layout_slots"]["code_review"]["accepts"] == ["code"]
    assert "visual_evidence" in technical["layout_slots"]
    assert "media_evidence" in technical["layout_slots"]
    assert {"audio", "video"}.issubset(set(technical["accepted_context_types"]))
    slide_deck = catalog["profiles"]["slide_deck"]
    assert slide_deck["layout_mode"] == "slides"
    assert "slide" in slide_deck["accepted_block_types"]
    assert slide_deck["layout_slots"]["evidence_slide"]["repeats"] is True
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["profile_catalog_version"] == "0.1"


def test_validate_target_profile_reports_agent_compatibility(tmp_path: Path) -> None:
    report_path = tmp_path / "profile-validation.json"
    profile = {
        "profile_id": "board_media_packet",
        "name": "Board Media Packet",
        "layout_mode": "document",
        "style_pack": "paper_ink",
        "sections": ["Executive Summary", "Media Evidence", "Source Map"],
        "layout_slots": {
            "summary": {"accepts": ["section", "citation"], "required": True},
            "media_evidence": {"accepts": ["audio_reference", "video_reference"], "required": False},
        },
        "accepted_block_types": ["section", "citation", "audio_reference", "video_reference"],
        "accepted_context_types": ["text", "audio", "video", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    }

    result = validate_target_profile(profile, output_path=report_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.target.validate_profile"
    validation = result.usage["profile_validation"]
    assert validation["is_valid"] is True
    assert validation["profile"]["profile_id"] == "board_media_packet"
    assert validation["compatibility"]["layout_mode"] == "document"
    assert validation["compatibility"]["accepted_context_types"] == ["text", "audio", "video", "web_link"]
    assert "pdf.compose.from_context" in result.next_recommended_tools
    assert json.loads(report_path.read_text(encoding="utf-8"))["is_valid"] is True


def test_target_profile_cli_api_mcp_are_exposed(tmp_path: Path) -> None:
    catalog_path = tmp_path / "profiles.json"
    profile_path = tmp_path / "custom-profile.json"
    report_path = tmp_path / "custom-profile.validation.json"
    profile = {
        "profile_id": "learning_media_deck",
        "name": "Learning Media Deck",
        "layout_mode": "slides",
        "style_pack": "paper_ink",
        "layout_slots": {
            "title": {"accepts": ["section"], "required": True},
            "evidence_slide": {"accepts": ["slide", "audio_reference", "video_reference"], "repeats": True},
        },
        "accepted_block_types": ["slide", "section", "audio_reference", "video_reference"],
        "accepted_context_types": ["text", "audio", "video", "image"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    }
    profile_path.write_text(json.dumps(profile), encoding="utf-8")

    catalog_cli = runner.invoke(app, ["target", "profiles", "-o", str(catalog_path), "--json"])
    validate_cli = runner.invoke(
        app,
        ["target", "validate", "--profile-json", str(profile_path), "-o", str(report_path), "--json"],
    )

    assert catalog_cli.exit_code == 0
    assert json.loads(catalog_cli.stdout)["tool"] == "pdf.target.profiles"
    assert validate_cli.exit_code == 0
    assert json.loads(validate_cli.stdout)["usage"]["profile_validation"]["is_valid"] is True

    client = TestClient(create_app())
    api_catalog = client.post(
        "/v1/tools/pdf.target.profiles/run",
        json={"output_path": str(tmp_path / "api-profiles.json")},
    )
    api_validate = client.post(
        "/v1/tools/pdf.target.validate_profile/run",
        json={"target_profile": profile, "output_path": str(tmp_path / "api-profile.validation.json")},
    )

    assert api_catalog.status_code == 200
    assert api_catalog.json()["tool"] == "pdf.target.profiles"
    assert api_validate.status_code == 200
    assert api_validate.json()["usage"]["profile_validation"]["is_valid"] is True

    mcp_catalog = json.loads(pdf_target_profiles(str(tmp_path / "mcp-profiles.json")))
    mcp_validate = json.loads(pdf_target_validate_profile(profile, str(tmp_path / "mcp-profile.validation.json")))

    assert mcp_catalog["tool"] == "pdf.target.profiles"
    assert mcp_validate["tool"] == "pdf.target.validate_profile"
