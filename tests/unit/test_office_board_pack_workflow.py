import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_board_pack_bundles_artifacts_manifest_and_validation(tmp_path: Path) -> None:
    from agentpdf.office.workflows import board_pack

    workbook_path, deck_path = _write_board_pack_inputs(tmp_path)
    output_path = tmp_path / "board-pack.zip"

    result = board_pack([workbook_path, deck_path], output_path, title="Q4 Board Pack")

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.board_pack"
    assert output_path.exists()
    assert result.artifacts[0].path == output_path
    assert result.artifacts[0].source_tool == "office.workflow.board_pack"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["input_count"] == 2
    assert result.usage["summary"]["packaged_file_count"] == 2
    assert result.usage["summary"]["validation_result_count"] == 2
    assert "office.bundle.verify" in result.next_recommended_tools

    with zipfile.ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "artifacts/model.xlsx" in names
        assert "artifacts/board-review.pptx" in names
        assert "okoffice-manifest.json" in names
        assert "okoffice-validation.json" in names
        manifest = json.loads(archive.read("okoffice-manifest.json"))
        validation = json.loads(archive.read("okoffice-validation.json"))

    assert manifest["product"] == "okoffice"
    assert manifest["workflow"] == "office.workflow.board_pack"
    assert manifest["title"] == "Q4 Board Pack"
    assert [entry["archive_path"] for entry in manifest["files"]] == [
        "artifacts/model.xlsx",
        "artifacts/board-review.pptx",
    ]
    validation_tools = {item["tool"] for item in validation["validation_results"]}
    assert {"sheet.validate.workbook", "deck.validate.presentation"} <= validation_tools


def test_board_pack_rejects_empty_inputs(tmp_path: Path) -> None:
    from agentpdf.office.workflows import board_pack

    result = board_pack([], tmp_path / "empty.zip")

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"


def test_board_pack_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import office_workflow_board_pack
    from agentpdf.workflows.runner import run_workflow
    from okoffice.cli.main import app

    workbook_path, deck_path = _write_board_pack_inputs(tmp_path)
    cli_output = tmp_path / "cli.zip"
    api_output = tmp_path / "api.zip"
    mcp_output = tmp_path / "mcp.zip"
    workflow_output = tmp_path / "workflow.zip"

    runner = CliRunner()
    cli = runner.invoke(
        app,
        [
            "workflow",
            "board-pack",
            str(workbook_path),
            str(deck_path),
            "-o",
            str(cli_output),
            "--title",
            "Board Pack",
            "--json",
        ],
    )
    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.board_pack/run",
        json={"files": [str(workbook_path), str(deck_path)], "output_path": str(api_output), "title": "Board Pack"},
    )
    mcp_payload = json.loads(
        office_workflow_board_pack([str(workbook_path), str(deck_path)], str(mcp_output), title="Board Pack")
    )
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.board_pack",
                    "input": {
                        "files": [str(workbook_path), str(deck_path)],
                        "output_path": str(workflow_output),
                        "title": "Board Pack",
                    },
                }
            ]
        }
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "office.workflow.board_pack"
    assert cli_output.exists()
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["packaged_file_count"] == 2
    assert api_output.exists()
    assert mcp_payload["tool"] == "office.workflow.board_pack"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "office.workflow.board_pack"


def test_board_pack_is_listed_in_manifests() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["office.workflow.board_pack"]["status"] == "beta"
    assert target["office.workflow.board_pack"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["office_workflow_board_pack"]["maps_to"] == "office.workflow.board_pack"


def _write_board_pack_inputs(tmp_path: Path) -> tuple[Path, Path]:
    from agentpdf.office.deck import create_deck_from_outline
    from agentpdf.office.xlsx import write_xlsx

    workbook_path = tmp_path / "model.xlsx"
    deck_path = tmp_path / "board-review.pptx"
    write_xlsx(
        workbook_path,
        [
            (
                "Model",
                [
                    ["Metric", "Value"],
                    ["Revenue", 120],
                    ["Margin", 0.32],
                ],
            ),
            (
                "SourceRefs",
                [
                    ["record_index", "source_path", "source_refs_json"],
                    [1, "source.docx", "[]"],
                    [2, "source.docx", "[]"],
                ],
            ),
        ],
    )
    create_deck_from_outline(
        {
            "slides": [
                {"title": "Board Review", "bullets": ["Revenue grew", "Margin held"]},
                {"title": "Next Steps", "bullets": ["Validate bundle"]},
            ]
        },
        deck_path,
    )
    return workbook_path, deck_path
