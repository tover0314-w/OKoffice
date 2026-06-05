import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_create_deck_presentation_accepts_outline_payload(tmp_path: Path) -> None:
    from agentpdf.office.deck import create_deck_presentation, inspect_deck_presentation

    output_path = tmp_path / "board-review.pptx"

    result = create_deck_presentation(_outline(), output_path)
    inspect = inspect_deck_presentation(output_path)

    assert result.status == "succeeded"
    assert result.tool == "deck.create.presentation"
    assert output_path.exists()
    assert result.artifacts[0].source_tool == "deck.create.presentation"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["slide_count"] == 3
    assert result.usage["slides"][1]["bullet_count"] == 2
    assert inspect.status == "succeeded"
    assert inspect.usage["presentation"]["slide_count"] == 3
    assert "deck.validate.presentation" in result.next_recommended_tools
    with zipfile.ZipFile(output_path) as archive:
        assert "ppt/presentation.xml" in archive.namelist()
        assert "ppt/slides/slide3.xml" in archive.namelist()


def test_create_deck_presentation_accepts_composition_plan_payload(tmp_path: Path) -> None:
    from agentpdf.office.deck import create_deck_presentation

    output_path = tmp_path / "from-plan.pptx"
    plan_payload = {
        "tool": "deck.compose.plan",
        "composition_ir": {"title": "Board Review"},
        "outline": _outline(),
    }

    result = create_deck_presentation(plan_payload, output_path)

    assert result.status == "succeeded"
    assert result.tool == "deck.create.presentation"
    assert output_path.exists()
    assert result.usage["summary"]["slide_count"] == 3
    assert result.usage["input"]["source"] == "composition_plan"


def test_create_deck_presentation_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import deck_create_presentation
    from agentpdf.workflows.runner import run_workflow
    from okoffice.cli.main import app

    outline_path = tmp_path / "outline.json"
    cli_output = tmp_path / "cli.pptx"
    api_output = tmp_path / "api.pptx"
    mcp_output = tmp_path / "mcp.pptx"
    workflow_output = tmp_path / "workflow.pptx"
    outline_path.write_text(json.dumps(_outline()), encoding="utf-8")

    cli = CliRunner().invoke(
        app,
        ["deck", "create-presentation", str(outline_path), "-o", str(cli_output), "--json"],
    )
    response = TestClient(create_app()).post(
        "/v1/tools/deck.create.presentation/run",
        json={"outline": _outline(), "output_path": str(api_output)},
    )
    mcp_payload = json.loads(deck_create_presentation(_outline(), str(mcp_output)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.create.presentation",
                    "input": {"outline": _outline(), "output_path": str(workflow_output)},
                }
            ]
        }
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "deck.create.presentation"
    assert cli_output.exists()
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["slide_count"] == 3
    assert api_output.exists()
    assert mcp_payload["tool"] == "deck.create.presentation"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "deck.create.presentation"


def test_deck_create_presentation_is_listed_in_manifests() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["deck.create.presentation"]["status"] == "beta"
    assert target["deck.create.presentation"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["deck_create_presentation"]["maps_to"] == "deck.create.presentation"


def _outline() -> dict[str, object]:
    return {
        "title": "Q4 Board Review",
        "subtitle": "OKoffice generated outline",
        "slides": [
            {
                "title": "Q4 Board Review",
                "subtitle": "Revenue, pipeline, and execution focus",
                "bullets": ["Local-first artifacts", "Evidence-backed outputs"],
            },
            {
                "title": "Revenue Snapshot",
                "bullets": ["Revenue grew 18%", "Gross margin held steady"],
                "notes": "Source: model.xlsx",
            },
            {
                "title": "Next Steps",
                "bullets": ["Validate workbook", "Create board pack"],
            },
        ],
    }
