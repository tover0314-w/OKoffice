import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_sheet_to_deck_profiles_workbook_and_writes_presentation(tmp_path: Path) -> None:
    from okoffice.office.deck import inspect_deck_presentation
    from okoffice.office.workflows import sheet_to_deck

    workbook_path = tmp_path / "model.xlsx"
    deck_path = tmp_path / "board-review.pptx"
    _write_model_workbook(workbook_path)

    result = sheet_to_deck(workbook_path, deck_path, title="Q4 Board Review")
    inspect = inspect_deck_presentation(deck_path)
    plan_path = deck_path.with_suffix(".plan.json")
    html_path = deck_path.with_suffix(".html")

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.sheet_to_deck"
    assert deck_path.exists()
    assert plan_path.exists()
    assert html_path.exists()
    assert any(artifact.path == deck_path for artifact in result.artifacts)
    assert any(artifact.path == html_path for artifact in result.artifacts)
    assert all(artifact.source_tool == "office.workflow.sheet_to_deck" for artifact in result.artifacts)
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["slide_count"] >= 4
    assert result.usage["summary"]["profiled_sheet_count"] == 1
    assert result.usage["summary"]["data_row_count"] == 3
    assert result.usage["summary"]["source_coverage"]["status"] == "complete"
    assert result.usage["workflow"]["creation_route"]["route"] == "html_first"
    assert result.usage["workflow"]["steps"] == [
        "deck.compose.plan",
        "deck.render.html",
        "deck.validation.html_preview",
        "deck.export.pptx",
        "deck.validate.presentation",
    ]
    assert result.usage["workflow"]["sidecars"]["plan_path"] == plan_path.as_posix()
    assert result.usage["workflow"]["sidecars"]["html_preview_path"] == html_path.as_posix()
    assert result.usage["outline"]["slides"][0]["title"] == "Q4 Board Review"
    assert "Revenue" in result.usage["outline"]["slides"][2]["bullets"][1]
    assert "deck.validation.contact_sheet" in result.next_recommended_tools
    assert inspect.status == "succeeded"
    assert inspect.usage["presentation"]["slide_count"] == result.usage["summary"]["slide_count"]


def test_sheet_to_deck_rejects_empty_profile(tmp_path: Path) -> None:
    from okoffice.office.workflows import sheet_to_deck
    from okoffice.office.xlsx import write_xlsx

    workbook_path = tmp_path / "empty.xlsx"
    write_xlsx(workbook_path, [("Model", [["Metric", "Value"]])])

    result = sheet_to_deck(workbook_path, tmp_path / "empty.pptx")

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"


def test_sheet_to_deck_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_workflow_sheet_to_deck
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    workbook_path = tmp_path / "model.xlsx"
    cli_output = tmp_path / "cli.pptx"
    api_output = tmp_path / "api.pptx"
    mcp_output = tmp_path / "mcp.pptx"
    workflow_output = tmp_path / "workflow.pptx"
    _write_model_workbook(workbook_path)

    runner = CliRunner()
    cli = runner.invoke(
        app,
        [
            "workflow",
            "sheet-to-deck",
            str(workbook_path),
            "-o",
            str(cli_output),
            "--title",
            "Board Review",
            "--json",
        ],
    )
    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.sheet_to_deck/run",
        json={"workbook_path": str(workbook_path), "output_path": str(api_output), "title": "Board Review"},
    )
    mcp_payload = json.loads(office_workflow_sheet_to_deck(str(workbook_path), str(mcp_output), title="Board Review"))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.sheet_to_deck",
                    "input": {
                        "workbook_path": str(workbook_path),
                        "output_path": str(workflow_output),
                        "title": "Board Review",
                    },
                }
            ]
        }
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "office.workflow.sheet_to_deck"
    assert json.loads(cli.stdout)["usage"]["workflow"]["creation_route"]["route"] == "html_first"
    assert cli_output.exists()
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["slide_count"] >= 4
    assert response.json()["usage"]["workflow"]["creation_route"]["route"] == "html_first"
    assert api_output.exists()
    assert mcp_payload["tool"] == "office.workflow.sheet_to_deck"
    assert mcp_payload["usage"]["workflow"]["creation_route"]["route"] == "html_first"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "office.workflow.sheet_to_deck"


def test_sheet_to_deck_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["office.workflow.sheet_to_deck"]["status"] == "beta"
    assert target["office.workflow.sheet_to_deck"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["office_workflow_sheet_to_deck"]["maps_to"] == "office.workflow.sheet_to_deck"


def _write_model_workbook(path: Path) -> None:
    from okoffice.office.xlsx import write_xlsx

    write_xlsx(
        path,
        [
            (
                "Model",
                [
                    ["Region", "Revenue", "Margin"],
                    ["East", 120, 0.32],
                    ["West", 98, 0.29],
                    ["North", 110, 0.31],
                ],
            ),
            (
                "SourceRefs",
                [
                    ["record_index", "source_path", "source_refs_json"],
                    [1, "source.docx", "[{\"cell_ref\":\"B2\"}]"],
                    [2, "source.docx", "[{\"cell_ref\":\"B3\"}]"],
                    [3, "source.docx", "[{\"cell_ref\":\"B4\"}]"],
                ],
            ),
        ],
    )
