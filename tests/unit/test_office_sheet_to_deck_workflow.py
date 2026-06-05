import json
from pathlib import Path

from typer.testing import CliRunner


def test_sheet_to_deck_workflow_creates_validated_presentation(tmp_path: Path) -> None:
    from agentpdf.office.deck import inspect_deck_presentation
    from agentpdf.office.workflows import sheet_to_deck

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    result = sheet_to_deck(
        workbook_path=workbook,
        output_path=output,
        title="Vendor Renewal Review",
        profile="board_review",
    )

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.sheet_to_deck"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert output.exists()

    assert [step["tool"] for step in result.usage["steps"]] == [
        "sheet.inspect.workbook",
        "sheet.validation.formulas",
        "deck.create.presentation",
        "deck.inspect.presentation",
        "deck.validation.presentation",
        "deck.validation.contact_sheet",
    ]
    assert result.usage["summary"] == {
        "sheet_count": 4,
        "source_row_count": 1,
        "slide_count": 2,
        "source_ref_count": 4,
        "deck_inspection_status": "passed",
        "deck_validation_status": "warning",
        "contact_sheet_status": "skipped",
    }
    assert result.usage["workflow"]["mutates_inputs"] is False
    assert result.usage["deck"]["summary"]["slide_count"] == 2
    assert result.usage["deck_validation"]["validation"]["status"] == "warning"
    assert result.usage["contact_sheet_validation"]["validation"]["status"] == "skipped"
    assert "office.bundle.export" in result.next_recommended_tools

    inspected = inspect_deck_presentation(output)
    assert inspected.status == "succeeded"
    assert inspected.usage["slides"][1]["title"] == "Acme Corp"


def test_okoffice_sheet_to_deck_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    result = CliRunner().invoke(
        app,
        [
            "workflow",
            "sheet-to-deck",
            "--workbook",
            str(workbook),
            "-o",
            str(output),
            "--title",
            "Vendor Renewal Review",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.workflow.sheet_to_deck"
    assert payload["usage"]["summary"]["slide_count"] == 2
    assert output.exists()


def test_sheet_to_deck_workflow_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.sheet_to_deck/run",
        json={"workbook_path": str(workbook), "output_path": str(output), "title": "Vendor Renewal Review"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.workflow.sheet_to_deck"
    assert payload["usage"]["summary"]["contact_sheet_status"] == "skipped"


def test_sheet_to_deck_workflow_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import office_workflow_sheet_to_deck

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    payload = json.loads(office_workflow_sheet_to_deck(str(workbook), str(output), title="Vendor Renewal Review"))

    assert payload["tool"] == "office.workflow.sheet_to_deck"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["source_row_count"] == 1


def test_sheet_to_deck_workflow_runs_through_generic_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.sheet_to_deck",
                    "input": {"workbook_path": str(workbook), "output_path": str(output), "title": "Vendor Renewal Review"},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.workflow.sheet_to_deck"
    assert step["validation"]["status"] == "warning"


def _write_evidence_workbook(tmp_path: Path) -> Path:
    from agentpdf.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    workbook_path = tmp_path / "evidence.xlsx"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")
    result = write_sheet_workbook(evidence_path=evidence_path, output_path=workbook_path)
    assert result.status == "succeeded"
    return workbook_path


def _evidence() -> dict[str, object]:
    return {
        "extraction_id": "extract_test",
        "schema_name": "vendor_renewal",
        "fields": [
            {"name": "vendor", "type": "string", "aliases": ["Vendor"], "required": True},
            {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"], "required": True},
            {"name": "annual_amount", "type": "number", "aliases": ["Annual amount"], "required": True},
            {"name": "risk", "type": "string", "aliases": ["Risk"], "required": False},
        ],
        "rows": [
            {
                "row_id": "row_001",
                "values": {
                    "vendor": "Acme Corp",
                    "renewal_date": "2026-09-30",
                    "annual_amount": "120000",
                    "risk": "High",
                },
                "field_evidence": {
                    "vendor": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "renewal_date": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "annual_amount": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "risk": {"source_ref": "ctx_002#s1", "source_type": "slide"},
                },
            }
        ],
        "source_refs": [
            {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
            {"source_ref": "ctx_002#s1", "source_type": "slide"},
        ],
        "method": "local_label_value_match_v0",
    }
