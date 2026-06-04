import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_validate_deck_presentation_reports_artifact_quality(tmp_path: Path) -> None:
    from agentpdf.office.deck import create_deck_from_outline, validate_deck_presentation

    deck_path = tmp_path / "board-review.pptx"
    create_deck_from_outline(_outline(), deck_path)

    result = validate_deck_presentation(deck_path)

    assert result.status == "succeeded"
    assert result.tool == "deck.validate.presentation"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["slide_count"] == 2
    assert result.usage["summary"]["blank_slide_count"] == 0
    assert result.usage["summary"]["placeholder_text_count"] == 0
    assert result.usage["summary"]["text_run_count"] >= 5
    assert result.usage["slides"][0]["text_run_count"] >= 3
    assert "office.workflow.board_pack" in result.next_recommended_tools


def test_validate_deck_presentation_warns_on_placeholder_leakage(tmp_path: Path) -> None:
    from agentpdf.office.deck import create_deck_from_outline, validate_deck_presentation

    deck_path = tmp_path / "placeholder.pptx"
    outline = _outline()
    outline["slides"][1]["bullets"] = ["{{ revenue }}", "TODO: replace source note"]
    create_deck_from_outline(outline, deck_path)

    result = validate_deck_presentation(deck_path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"]["placeholder_text_count"] == 2
    assert any(check.name == "placeholder_leakage_absent" and check.status == "warning" for check in result.validation.checks)
    assert any("placeholder" in warning.lower() for warning in result.warnings)


def test_validate_deck_presentation_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import deck_validate_presentation
    from agentpdf.office.deck import create_deck_from_outline
    from agentpdf.workflows.runner import run_workflow
    from okoffice.cli.main import app

    deck_path = tmp_path / "board-review.pptx"
    create_deck_from_outline(_outline(), deck_path)

    runner = CliRunner()
    cli = runner.invoke(app, ["deck", "validate", str(deck_path), "--json"])
    response = TestClient(create_app()).post("/v1/tools/deck.validate.presentation/run", json={"path": str(deck_path)})
    mcp_payload = json.loads(deck_validate_presentation(str(deck_path)))
    workflow = run_workflow({"steps": [{"tool": "deck.validate.presentation", "input": {"path": str(deck_path)}}]})

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "deck.validate.presentation"
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["slide_count"] == 2
    assert mcp_payload["tool"] == "deck.validate.presentation"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "deck.validate.presentation"


def test_deck_validate_presentation_is_listed_in_manifests() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["deck.validate.presentation"]["status"] == "beta"
    assert target["deck.validate.presentation"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["deck_validate_presentation"]["maps_to"] == "deck.validate.presentation"


def _outline() -> dict[str, object]:
    return {
        "title": "Q4 Board Review",
        "slides": [
            {
                "title": "Q4 Board Review",
                "subtitle": "Generated locally by OKoffice",
                "bullets": ["Evidence-backed outputs", "Validated artifacts"],
            },
            {
                "title": "Revenue Snapshot",
                "bullets": ["Revenue grew 18%", "Gross margin held steady"],
            },
        ],
    }
