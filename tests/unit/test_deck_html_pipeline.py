import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_deck_render_html_writes_preview_package_and_manifest(tmp_path: Path) -> None:
    from okoffice.office.deck import render_deck_html, validate_deck_html_preview

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
    from okoffice.office.deck import render_deck_html, validate_deck_html_preview

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
    from okoffice.office.deck import export_deck_pptx, inspect_deck_presentation, render_deck_html

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
    assert result.usage["export"]["route"] == "html_manifest_to_editable_pptx_baseline"
    assert result.usage["summary"]["slide_count"] == 2
    assert inspect.status == "succeeded"
    assert inspect.usage["presentation"]["slide_count"] == 2
    assert "deck.validate.presentation" in result.next_recommended_tools


def test_deck_html_pipeline_renders_validates_and_exports_pptx_from_workbook_plan(tmp_path: Path) -> None:
    from okoffice.office.deck import (
        export_deck_pptx,
        render_deck_html,
        validate_deck_html_preview,
        validate_deck_presentation,
    )
    from okoffice.office.deck_plan import compose_deck_plan

    workbook_path = tmp_path / "evidence.xlsx"
    plan_path = tmp_path / "board-review.plan.json"
    html_path = tmp_path / "board-review.html"
    deck_path = tmp_path / "board-review.pptx"
    _write_html_pipeline_workbook(workbook_path)

    plan = compose_deck_plan(workbook_path, output_path=plan_path, title="Renewal Board Review")
    rendered = render_deck_html(plan_path, html_path)
    preview = validate_deck_html_preview(html_path)
    exported = export_deck_pptx(html_path, deck_path)
    validated = validate_deck_presentation(deck_path)
    manifest_path = html_path.with_suffix(".html-manifest.json")

    assert plan.status == "succeeded"
    assert rendered.status == "succeeded"
    assert rendered.tool == "deck.render.html"
    assert html_path.exists()
    assert manifest_path.exists()
    assert not (tmp_path / "board-review.html.pptx").exists()
    assert rendered.usage["summary"]["slide_count"] >= 4
    assert rendered.usage["html_package"]["manifest_path"] == manifest_path.as_posix()
    assert rendered.usage["html_package"]["slide_dom_anchor_count"] == rendered.usage["summary"]["slide_count"]
    assert "deck.validation.html_preview" in rendered.next_recommended_tools

    html_text = html_path.read_text(encoding="utf-8")
    assert 'data-okoffice-deck-preview="true"' in html_text
    assert 'data-slide-id="slide_001"' in html_text
    assert "Renewal Board Review" in html_text

    assert preview.status == "succeeded"
    assert preview.tool == "deck.validation.html_preview"
    assert preview.validation is not None
    assert preview.validation.status == "passed"
    assert preview.usage["summary"]["slide_count"] == rendered.usage["summary"]["slide_count"]
    assert preview.usage["summary"]["placeholder_text_count"] == 0
    assert preview.usage["html_preview"]["offline_assets"] is True
    assert preview.usage["taste_qa"]["status"] == "passed"

    assert exported.status == "succeeded"
    assert exported.tool == "deck.export.pptx"
    assert deck_path.exists()
    assert exported.usage["summary"]["slide_count"] == rendered.usage["summary"]["slide_count"]
    assert exported.usage["export"]["source_format"] == "html_slide_package"
    assert exported.usage["export"]["route"] == "html_manifest_to_editable_pptx_baseline"
    assert "deck.validate.presentation" in exported.next_recommended_tools
    assert validated.status == "succeeded"
    assert validated.validation is not None
    assert validated.validation.status == "passed"


def test_deck_html_pipeline_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import deck_export_pptx, deck_render_html, deck_validation_html_preview
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

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
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

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


def _write_html_pipeline_workbook(path: Path) -> None:
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
                    [1, "renewals.docx", '[{"cell_ref":"B2","source_ref":"docx:renewals:table_1:B2"}]'],
                    [2, "renewals.docx", '[{"cell_ref":"B3","source_ref":"docx:renewals:table_1:B3"}]'],
                    [3, "renewals.docx", '[{"cell_ref":"B4","source_ref":"docx:renewals:table_1:B4"}]'],
                ],
            ),
        ],
    )


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
