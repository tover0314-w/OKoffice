import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_compose_deck_plan_returns_source_mapped_composition_ir(tmp_path: Path) -> None:
    from okoffice.office.deck_plan import compose_deck_plan

    workbook_path = tmp_path / "evidence.xlsx"
    output_path = tmp_path / "composition-plan.json"
    _write_evidence_workbook(workbook_path)

    result = compose_deck_plan(
        workbook_path,
        output_path=output_path,
        title="Renewal Board Review",
        style="executive",
    )

    assert result.status == "succeeded"
    assert result.tool == "deck.compose.plan"
    assert output_path.exists()
    assert result.artifacts[0].path == output_path
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["slide_count"] >= 4
    assert result.usage["summary"]["source_coverage"]["status"] == "complete"
    assert result.usage["composition_ir"]["schema"] == "okoffice.deck.composition"
    assert result.usage["composition_ir"]["kind"] == "deck.composition"
    assert result.usage["composition_ir"]["title"] == "Renewal Board Review"
    assert result.usage["composition_ir"]["style"] == "executive"
    assert result.usage["composition_ir"]["source"]["workbook_path"] == workbook_path.as_posix()
    assert result.usage["outline"]["slides"][0]["title"] == "Renewal Board Review"
    assert "deck.create.presentation" in result.next_recommended_tools
    assert "deck.create.from_outline" in result.next_recommended_tools

    sheet_slide = result.usage["composition_ir"]["slides"][2]
    assert sheet_slide["slide_type"] == "sheet_snapshot"
    assert sheet_slide["claims"]
    assert sheet_slide["source_refs"]
    assert sheet_slide["workbook_ranges"][0]["sheet_name"] == "Model"

    written_plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_plan["tool"] == "deck.compose.plan"
    assert written_plan["composition_ir"]["slides"][0]["title"] == "Renewal Board Review"


def test_compose_deck_plan_rejects_empty_profile(tmp_path: Path) -> None:
    from okoffice.office.deck_plan import compose_deck_plan
    from okoffice.office.xlsx import write_xlsx

    workbook_path = tmp_path / "empty.xlsx"
    write_xlsx(workbook_path, [("Model", [["Metric", "Value"]])])

    result = compose_deck_plan(workbook_path)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"


def test_compose_deck_plan_rejects_output_path_that_matches_input(tmp_path: Path) -> None:
    from okoffice.office.deck_plan import compose_deck_plan
    from okoffice.office.sheet import read_sheet_workbook

    workbook_path = tmp_path / "evidence.xlsx"
    _write_evidence_workbook(workbook_path)
    original_bytes = workbook_path.read_bytes()

    result = compose_deck_plan(workbook_path, output_path=workbook_path)
    read_result = read_sheet_workbook(workbook_path)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    assert workbook_path.read_bytes() == original_bytes
    assert read_result.status == "succeeded"


def test_compose_deck_plan_loads_source_refs_beyond_profile_row_limit(tmp_path: Path) -> None:
    from okoffice.office.deck_plan import compose_deck_plan
    from okoffice.office.xlsx import write_xlsx

    workbook_path = tmp_path / "large-source-map.xlsx"
    source_refs_rows = [["record_index", "source_path", "source_refs_json"]]
    for record_index in range(1, 199):
        source_refs_rows.append(
            [
                record_index,
                "renewals.docx",
                f'[{{"source_ref":"docx:renewals:row_{record_index}"}}]',
            ]
        )
    write_xlsx(
        workbook_path,
        [
            ("East", [["Region", "Revenue"], *[["East", row] for row in range(1, 100)]]),
            ("West", [["Region", "Revenue"], *[["West", row] for row in range(100, 199)]]),
            ("SourceRefs", source_refs_rows),
        ],
    )

    result = compose_deck_plan(workbook_path, max_rows_per_sheet=100)
    sheet_slides = [
        slide for slide in result.usage["composition_ir"]["slides"] if slide["slide_type"] == "sheet_snapshot"
    ]

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert len(sheet_slides) == 2
    assert sheet_slides[0]["source_refs"]
    assert sheet_slides[1]["source_refs"]
    assert sheet_slides[1]["source_refs"][0]["record_index"] == 100


def test_compose_deck_plan_handles_malformed_source_ref_record_index(tmp_path: Path) -> None:
    from okoffice.office.deck_plan import compose_deck_plan
    from okoffice.office.xlsx import write_xlsx

    workbook_path = tmp_path / "bad-source-ref.xlsx"
    write_xlsx(
        workbook_path,
        [
            ("Model", [["Region", "Revenue"], ["East", 120]]),
            (
                "SourceRefs",
                [
                    ["record_index", "source_path", "source_refs_json"],
                    ["1e309", "renewals.docx", '[{"source_ref":"docx:renewals:row_1"}]'],
                ],
            ),
        ],
    )

    result = compose_deck_plan(workbook_path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"


def test_compose_deck_plan_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import deck_compose_plan
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    workbook_path = tmp_path / "evidence.xlsx"
    cli_output = tmp_path / "cli-plan.json"
    api_output = tmp_path / "api-plan.json"
    workflow_output = tmp_path / "workflow-plan.json"
    _write_evidence_workbook(workbook_path)

    runner = CliRunner()
    cli = runner.invoke(
        app,
        [
            "deck",
            "compose-plan",
            str(workbook_path),
            "-o",
            str(cli_output),
            "--title",
            "Board Review",
            "--json",
        ],
    )
    response = TestClient(create_app()).post(
        "/v1/tools/deck.compose.plan/run",
        json={"workbook_path": str(workbook_path), "output_path": str(api_output), "title": "Board Review"},
    )
    mcp_payload = json.loads(deck_compose_plan(str(workbook_path), title="Board Review"))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.compose.plan",
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
    assert json.loads(cli.stdout)["tool"] == "deck.compose.plan"
    assert cli_output.exists()
    assert response.status_code == 200
    assert response.json()["usage"]["composition_ir"]["title"] == "Board Review"
    assert api_output.exists()
    assert mcp_payload["tool"] == "deck.compose.plan"
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "deck.compose.plan"


def test_deck_compose_plan_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["deck.compose.plan"]["status"] == "beta"
    assert target["deck.compose.plan"]["implemented"] is True
    assert target["deck.create.presentation"]["status"] == "beta"
    assert target["deck.create.presentation"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["deck_compose_plan"]["maps_to"] == "deck.compose.plan"
    assert entries["deck_create_presentation"]["maps_to"] == "deck.create.presentation"


def _write_evidence_workbook(path: Path) -> None:
    from okoffice.office.xlsx import write_xlsx

    write_xlsx(
        path,
        [
            (
                "Model",
                [
                    ["Region", "Revenue", "Margin", "Renewal Risk"],
                    ["East", 120, 0.32, "Low"],
                    ["West", 98, 0.29, "Medium"],
                    ["North", 110, 0.31, "Low"],
                ],
            ),
            (
                "SourceRefs",
                [
                    ["record_index", "source_path", "source_refs_json"],
                    [1, "renewals.docx", "[{\"cell_ref\":\"B2\",\"source_ref\":\"docx:renewals:table_1:B2\"}]"],
                    [2, "renewals.docx", "[{\"cell_ref\":\"B3\",\"source_ref\":\"docx:renewals:table_1:B3\"}]"],
                    [3, "renewals.docx", "[{\"cell_ref\":\"B4\",\"source_ref\":\"docx:renewals:table_1:B4\"}]"],
                ],
            ),
        ],
    )
