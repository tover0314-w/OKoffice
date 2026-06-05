import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_office_workflow_plan_runs_through_runner_rest_mcp_workflow_and_cli() -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_workflow_plan
    from okoffice.tools.runner import run_office_workflow_plan
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    payload = {
        "goal": "Build an evidence workbook and board deck from mixed source files.",
        "input_paths": ["memo.docx", "filing.pdf"],
        "output_paths": ["model.xlsx", "board-deck.pptx"],
    }

    runner_result = run_office_workflow_plan(**payload)
    rest_response = TestClient(create_app()).post("/v1/tools/office.workflow.plan/run", json=payload)
    mcp_payload = json.loads(
        office_workflow_plan(
            goal=str(payload["goal"]),
            input_paths=list(payload["input_paths"]),
            output_paths=list(payload["output_paths"]),
        )
    )
    workflow = run_workflow({"steps": [{"tool": "office.workflow.plan", "input": payload}]})
    cli = CliRunner().invoke(
        app,
        [
            "workflow",
            "plan",
            "--goal",
            str(payload["goal"]),
            "--input",
            "memo.docx",
            "--input",
            "filing.pdf",
            "--output",
            "model.xlsx",
            "--output",
            "board-deck.pptx",
            "--json",
        ],
    )

    assert runner_result.status == "succeeded"
    assert runner_result.tool == "office.workflow.plan"
    assert runner_result.usage["plan"]["input_formats"] == ["docx", "pdf"]
    assert runner_result.usage["plan"]["output_formats"] == ["xlsx", "pptx"]
    assert "office.workflow.sheet_to_deck" in runner_result.next_recommended_tools

    assert rest_response.status_code == 200
    assert rest_response.json()["tool"] == "office.workflow.plan"
    assert rest_response.json()["usage"]["plan"]["output_formats"] == ["xlsx", "pptx"]

    assert mcp_payload["tool"] == "office.workflow.plan"
    assert mcp_payload["usage"]["plan"]["input_formats"] == ["docx", "pdf"]

    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "office.workflow.plan"

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "office.workflow.plan"


def test_office_workflow_plan_is_listed_in_mcp_catalog() -> None:
    catalog = json.loads(open("schemas/mcp-tools.catalog.json", encoding="utf-8").read())
    entries = {tool["name"]: tool for tool in catalog["tools"]}

    assert entries["office_workflow_plan"]["maps_to"] == "office.workflow.plan"
    assert entries["office_workflow_plan"]["status"] == "beta"
