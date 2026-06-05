import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_deck_render_html_writes_preview_package_and_manifest(tmp_path: Path) -> None:
    from agentpdf.office.deck import render_deck_html, validate_deck_html_preview

    html_path = tmp_path / "board-review.html"

    result = render_deck_html(_plan_payload(), html_path)
    validation = validate_deck_html_preview(html_path)
    manifest_path = Path(result.usage["html_package"]["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result.status == "succeeded"
    assert result.tool == "deck.render.html"
    assert html_path.exists()
    assert manifest_path.exists()
    assert result.artifacts[0].source_tool == "deck.render.html"
    assert result.usage["summary"]["slide_count"] == 2
    assert result.usage["html_package"]["offline_assets"] is True
    assert result.usage["html_package"]["slide_dom_anchor_count"] == 2
    assert manifest["tool"] == "deck.render.html"
    assert manifest["outline"]["slides"][1]["title"] == "Revenue Snapshot"
    assert manifest["slides"][0]["dom_anchor"] == "#slide-1"
    assert "deck.validation.html_preview" in result.next_recommended_tools
    assert validation.status == "succeeded"
    assert validation.validation is not None
    assert validation.validation.status == "passed"
    assert validation.usage["summary"]["slide_count"] == 2
    assert validation.usage["summary"]["placeholder_text_count"] == 0


def test_deck_html_preview_validation_reports_placeholder_leakage(tmp_path: Path) -> None:
    from agentpdf.office.deck import render_deck_html, validate_deck_html_preview

    html_path = tmp_path / "placeholder.html"
    payload = _plan_payload()
    payload["outline"]["slides"][0]["bullets"] = ["{{todo}}"]

    render_deck_html(payload, html_path)
    result = validate_deck_html_preview(html_path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"]["placeholder_text_count"] == 1
    assert any("placeholder" in warning.lower() for warning in result.warnings)


def test_deck_export_pptx_converts_html_preview_to_editable_pptx(tmp_path: Path) -> None:
    from agentpdf.office.deck import export_deck_pptx, inspect_deck_presentation, render_deck_html

    html_path = tmp_path / "board-review.html"
    pptx_path = tmp_path / "board-review.pptx"
    render_deck_html(_plan_payload(), html_path)

    result = export_deck_pptx(html_path, pptx_path)
    inspect = inspect_deck_presentation(pptx_path)

    assert result.status == "succeeded"
    assert result.tool == "deck.export.pptx"
    assert pptx_path.exists()
    assert result.artifacts[0].source_tool == "deck.export.pptx"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["export"]["source_format"] == "html_slide_package"
    assert result.usage["export"]["route"] == "local_outline_export"
    assert result.usage["summary"]["slide_count"] == 2
    assert inspect.status == "succeeded"
    assert inspect.usage["presentation"]["slide_count"] == 2
    assert "deck.validate.presentation" in result.next_recommended_tools


def test_deck_html_pipeline_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import deck_export_pptx, deck_render_html, deck_validation_html_preview
    from agentpdf.workflows.runner import run_workflow
    from okoffice.cli.main import app

    plan_path = tmp_path / "plan.json"
    cli_html = tmp_path / "cli.html"
    api_html = tmp_path / "api.html"
    mcp_html = tmp_path / "mcp.html"
    workflow_html = tmp_path / "workflow.html"
    workflow_pptx = tmp_path / "workflow.pptx"
    plan_path.write_text(json.dumps(_plan_payload()), encoding="utf-8")

    runner = CliRunner()
    cli = runner.invoke(app, ["deck", "render-html", str(plan_path), "-o", str(cli_html), "--json"])
    response = TestClient(create_app()).post(
        "/v1/tools/deck.render.html/run",
        json={"plan_path": str(plan_path), "output_path": str(api_html)},
    )
    mcp_payload = json.loads(deck_render_html(str(plan_path), str(mcp_html)))
    mcp_validation = json.loads(deck_validation_html_preview(str(mcp_html)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "deck.render.html",
                    "input": {"plan_path": str(plan_path), "output_path": str(workflow_html)},
                },
                {
                    "tool": "deck.export.pptx",
                    "input": {"html_path": str(workflow_html), "output_path": str(workflow_pptx)},
                },
            ]
        }
    )
    mcp_export = json.loads(deck_export_pptx(str(mcp_html), str(tmp_path / "mcp.pptx")))

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "deck.render.html"
    assert cli_html.exists()
    assert response.status_code == 200
    assert response.json()["tool"] == "deck.render.html"
    assert api_html.exists()
    assert mcp_payload["tool"] == "deck.render.html"
    assert mcp_validation["tool"] == "deck.validation.html_preview"
    assert mcp_export["tool"] == "deck.export.pptx"
    assert workflow.status == "succeeded"
    assert workflow_pptx.exists()
    assert [step["tool"] for step in workflow.usage["workflow_run"]["step_results"]] == [
        "deck.render.html",
        "deck.export.pptx",
    ]


def test_deck_html_pipeline_is_listed_in_manifests() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["deck.render.html"]["status"] == "beta"
    assert target["deck.render.html"]["implemented"] is True
    assert target["deck.validation.html_preview"]["status"] == "beta"
    assert target["deck.validation.html_preview"]["implemented"] is True
    assert target["deck.export.pptx"]["status"] == "beta"
    assert target["deck.export.pptx"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["deck_render_html"]["maps_to"] == "deck.render.html"
    assert entries["deck_validation_html_preview"]["maps_to"] == "deck.validation.html_preview"
    assert entries["deck_export_pptx"]["maps_to"] == "deck.export.pptx"


def _plan_payload() -> dict[str, object]:
    return {
        "tool": "deck.compose.plan",
        "composition_ir": {
            "schema": "okoffice.deck.composition",
            "kind": "deck.composition",
            "title": "Board Review",
            "style": "executive",
            "slides": [
                {
                    "slide_id": "slide_001",
                    "slide_index": 1,
                    "slide_type": "title",
                    "title": "Board Review",
                    "bullets": ["Evidence-backed outputs"],
                    "source_refs": [{"source_ref": "workbook:Summary!A1:B4"}],
                },
                {
                    "slide_id": "slide_002",
                    "slide_index": 2,
                    "slide_type": "sheet_snapshot",
                    "title": "Revenue Snapshot",
                    "bullets": ["Revenue grew 18%", "Margin held steady"],
                    "source_refs": [{"source_ref": "workbook:Model!A1:D3"}],
                },
            ],
        },
        "outline": {
            "title": "Board Review",
            "style": "executive",
            "slides": [
                {
                    "title": "Board Review",
                    "subtitle": "Evidence-backed outputs",
                    "bullets": ["Evidence-backed outputs"],
                    "notes": "Source: Summary!A1:B4",
                },
                {
                    "title": "Revenue Snapshot",
                    "bullets": ["Revenue grew 18%", "Margin held steady"],
                    "notes": "Source: Model!A1:D3",
                },
            ],
        },
    }
