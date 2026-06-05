import json
from pathlib import Path

from typer.testing import CliRunner

from tests.unit.test_deck_contact_sheet_validation import _write_deck


def test_deck_presentation_validation_returns_structural_baseline(tmp_path: Path) -> None:
    from okoffice.office.deck_validation import validate_deck_presentation

    deck = _write_deck(tmp_path)

    result = validate_deck_presentation(deck)

    assert result.status == "succeeded"
    assert result.tool == "deck.validation.presentation"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"] == {
        "slide_count": 2,
        "missing_title_count": 0,
        "slide_without_notes_count": 1,
        "shape_count": 4,
        "chart_count": 0,
        "media_count": 0,
        "theme_count": 1,
        "external_link_count": 0,
        "macro_enabled": False,
    }
    assert result.usage["render_evidence"]["status"] == "skipped"
    assert result.usage["render_evidence"]["required_worker"] == "pptx_contact_sheet_renderer"
    assert result.usage["placeholder_overflow"]["status"] == "structural_only"
    assert "Presentation has slides without speaker notes: 1." in result.warnings

    checks = {check.name: check for check in result.validation.checks}
    assert checks["presentation_reopened_by_inspect"].status == "passed"
    assert checks["slide_titles_present"].status == "passed"
    assert checks["notes_policy"].status == "warning"
    assert checks["contact_sheet_render_evidence"].status == "skipped"
    assert "deck.validation.contact_sheet" in result.next_recommended_tools


def test_okoffice_deck_validate_presentation_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    deck = _write_deck(tmp_path)

    result = CliRunner().invoke(app, ["deck", "validate-presentation", str(deck), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "deck.validation.presentation"
    assert payload["usage"]["summary"]["slide_count"] == 2


def test_deck_presentation_validation_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    deck = _write_deck(tmp_path)

    response = TestClient(create_app()).post(
        "/v1/tools/deck.validation.presentation/run",
        json={"path": str(deck)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "deck.validation.presentation"
    assert payload["usage"]["summary"]["missing_title_count"] == 0


def test_deck_presentation_validation_runs_through_mcp_function(tmp_path: Path) -> None:
    from okoffice.mcp.server import deck_validate_presentation

    deck = _write_deck(tmp_path)

    payload = json.loads(deck_validate_presentation(str(deck)))

    assert payload["tool"] == "deck.validation.presentation"
    assert payload["status"] == "succeeded"
    assert payload["validation"]["status"] == "warning"


def test_deck_presentation_validation_runs_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    deck = _write_deck(tmp_path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.validation.presentation",
                    "input": {"path": str(deck)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "deck.validation.presentation"
    assert step["validation"]["status"] == "warning"
