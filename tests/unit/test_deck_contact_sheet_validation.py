import json
from pathlib import Path

from typer.testing import CliRunner


def test_deck_contact_sheet_validation_returns_structured_worker_skip(tmp_path: Path) -> None:
    from okoffice.office.deck_validation import validate_deck_contact_sheet

    deck = _write_deck(tmp_path)

    result = validate_deck_contact_sheet(deck)

    assert result.status == "succeeded"
    assert result.tool == "deck.validation.contact_sheet"
    assert result.validation is not None
    assert result.validation.status == "skipped"
    assert result.usage["summary"] == {
        "slide_count": 2,
        "rendered_contact_sheet": False,
        "worker_status": "not_configured",
    }
    assert result.usage["contact_sheet"]["preview_artifact_path"] is None
    assert "Contact-sheet render worker is not configured." in result.warnings
    assert "deck.inspect.presentation" in result.next_recommended_tools


def test_okoffice_deck_validate_contact_sheet_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    deck = _write_deck(tmp_path)

    result = CliRunner().invoke(app, ["deck", "validate-contact-sheet", str(deck), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "deck.validation.contact_sheet"
    assert payload["validation"]["status"] == "skipped"


def test_deck_contact_sheet_validation_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    deck = _write_deck(tmp_path)

    response = TestClient(create_app()).post(
        "/v1/tools/deck.validation.contact_sheet/run",
        json={"path": str(deck)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "deck.validation.contact_sheet"
    assert payload["usage"]["summary"]["worker_status"] == "not_configured"


def test_deck_contact_sheet_validation_runs_through_mcp_function(tmp_path: Path) -> None:
    from okoffice.mcp.server import deck_validate_contact_sheet

    deck = _write_deck(tmp_path)

    payload = json.loads(deck_validate_contact_sheet(str(deck)))

    assert payload["tool"] == "deck.validation.contact_sheet"
    assert payload["status"] == "succeeded"
    assert payload["validation"]["status"] == "skipped"


def test_deck_contact_sheet_validation_runs_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    deck = _write_deck(tmp_path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.validation.contact_sheet",
                    "input": {"path": str(deck)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "deck.validation.contact_sheet"
    assert step["validation"]["status"] == "skipped"


def _write_deck(tmp_path: Path) -> Path:
    from okoffice.office.deck_writer import create_deck_presentation
    from okoffice.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    workbook_path = tmp_path / "evidence.xlsx"
    output_path = tmp_path / "board-review.pptx"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")
    workbook = write_sheet_workbook(evidence_path=evidence_path, output_path=workbook_path)
    assert workbook.status == "succeeded"
    deck = create_deck_presentation(
        workbook_path=workbook_path,
        output_path=output_path,
        title="Vendor Renewal Review",
    )
    assert deck.status == "succeeded"
    return output_path


def _evidence() -> dict[str, object]:
    return {
        "extraction_id": "extract_test",
        "schema_name": "vendor_renewal",
        "fields": [
            {"name": "vendor", "type": "string"},
            {"name": "renewal_date", "type": "date"},
        ],
        "rows": [
            {
                "row_id": "row_001",
                "values": {"vendor": "Acme Corp", "renewal_date": "2026-09-30"},
                "field_evidence": {
                    "vendor": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "renewal_date": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                },
            }
        ],
        "source_refs": [{"source_ref": "ctx_001#p1", "source_type": "word_paragraph"}],
    }
