import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_deck_create_presentation_writes_editable_pptx_from_evidence_workbook(tmp_path: Path) -> None:
    from agentpdf.office.deck import inspect_deck_presentation
    from agentpdf.office.deck_writer import create_deck_presentation

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    result = create_deck_presentation(
        workbook_path=workbook,
        output_path=output,
        title="Vendor Renewal Review",
        profile="board_review",
    )

    assert result.status == "succeeded"
    assert result.tool == "deck.create.presentation"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output.exists()
    assert zipfile.is_zipfile(output)
    assert result.artifacts[0].path == output.resolve()

    summary = result.usage["summary"]
    assert summary == {
        "slide_count": 2,
        "row_count": 1,
        "field_count": 4,
        "source_ref_count": 4,
        "notes_slide_count": 1,
    }
    assert result.usage["slides"][0]["title"] == "Vendor Renewal Review"
    assert result.usage["slides"][1]["source_refs"] == ["ctx_001#p1", "ctx_002#s1"]
    assert result.usage["presentation_manifest"]["mutates_inputs"] is False
    assert "deck.inspect.presentation" in result.next_recommended_tools
    assert "office.workflow.sheet_to_deck" in result.next_recommended_tools

    inspected = inspect_deck_presentation(output)
    assert inspected.status == "succeeded"
    assert inspected.usage["summary"]["slide_count"] == 2
    assert inspected.usage["summary"]["slide_with_notes_count"] == 1
    assert inspected.usage["slides"][1]["title"] == "Acme Corp"

    slide2 = _read_zip_text(output, "ppt/slides/slide2.xml")
    notes2 = _read_zip_text(output, "ppt/notesSlides/notesSlide1.xml")
    assert "Renewal date: 2026-09-30" in slide2
    assert "Annual amount: 120000" in slide2
    assert "Risk: High" in slide2
    assert "Sources: ctx_001#p1, ctx_002#s1" in notes2


def test_okoffice_deck_create_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    result = CliRunner().invoke(
        app,
        ["deck", "create", "--from-workbook", str(workbook), "-o", str(output), "--title", "Vendor Renewal Review", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "deck.create.presentation"
    assert payload["usage"]["summary"]["slide_count"] == 2
    assert output.exists()


def test_deck_create_presentation_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    response = TestClient(create_app()).post(
        "/v1/tools/deck.create.presentation/run",
        json={"workbook_path": str(workbook), "output_path": str(output), "title": "Vendor Renewal Review"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "deck.create.presentation"
    assert payload["usage"]["summary"]["source_ref_count"] == 4


def test_deck_create_presentation_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import deck_create_presentation

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    payload = json.loads(deck_create_presentation(str(workbook), str(output), title="Vendor Renewal Review"))

    assert payload["tool"] == "deck.create.presentation"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["row_count"] == 1


def test_deck_create_presentation_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "board-review.pptx"

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.create.presentation",
                    "input": {"workbook_path": str(workbook), "output_path": str(output), "title": "Vendor Renewal Review"},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "deck.create.presentation"
    assert step["validation"]["status"] == "passed"


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
                    "vendor": {
                        "source_ref": "ctx_001#p1",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Vendor: Acme Corp",
                        "confidence": 0.95,
                    },
                    "renewal_date": {
                        "source_ref": "ctx_001#p1",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Renewal date: 2026-09-30",
                        "confidence": 0.95,
                    },
                    "annual_amount": {
                        "source_ref": "ctx_001#p1",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Annual amount: $120,000",
                        "confidence": 0.95,
                    },
                    "risk": {
                        "source_ref": "ctx_002#s1",
                        "source_type": "slide",
                        "locator": {"kind": "deck", "slide": 1, "slide_id": "256"},
                        "excerpt": "Risk: High",
                        "confidence": 0.95,
                    },
                },
            }
        ],
        "source_refs": [
            {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
            {"source_ref": "ctx_002#s1", "source_type": "slide"},
        ],
        "method": "local_label_value_match_v0",
    }


def _read_zip_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
