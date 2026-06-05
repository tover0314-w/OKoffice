from __future__ import annotations

from pathlib import Path

from okoffice.tools.runner import (
    run_authoring_plan,
    run_create_html_package,
    run_pages_write,
    run_qa_visual_report,
    run_render_html_package,
    run_storyboard_plan,
    run_workflow_research_deck,
)
from okoffice.workflows.runner import run_workflow


def _brief() -> dict[str, object]:
    return {
        "topic": "Independent developers going global",
        "goal": "Create a concise strategy deck",
        "audience": "founders",
        "language": "en",
        "page_count": 4,
        "deliverable": "deck",
        "research_required": True,
        "citation_required": True,
    }


def _evidence() -> list[dict[str, object]]:
    return [
        {
            "id": "ev_market",
            "claim": "Mobile monetization remains strong.",
            "evidence": "Revenue growth continues while downloads flatten.",
            "source_title": "State of Mobile 2026",
            "source_url": "https://example.com/mobile",
            "source_date": "2026-01-01",
            "confidence": "medium",
            "usable_for": ["market_context", "executive_summary"],
        }
    ]


def test_runner_authoring_chain_creates_html_package_and_visual_qa(tmp_path: Path) -> None:
    route = run_authoring_plan(_brief()).usage["authoring_plan"]
    storyboard = run_storyboard_plan(
        brief=_brief(),
        authoring_plan=route,
        evidence_cards=_evidence(),
    ).usage["storyboard"]
    pages = run_pages_write(
        brief=_brief(),
        storyboard=storyboard,
        evidence_cards=_evidence(),
        design_tokens={"theme": "business_tech"},
    ).usage["page_document"]
    html = run_create_html_package(
        page_document=pages,
        html_output_path=tmp_path / "deck.html",
        title="Independent developers going global",
    )
    pdf_path = tmp_path / "deck.pdf"
    rendered = run_render_html_package(html.usage["html_package_manifest_path"], pdf_path)
    qa = run_qa_visual_report(
        input_path=pdf_path,
        expected_page_count=rendered.validation.page_count if rendered.validation else None,
        html_package_manifest_path=html.usage["html_package_manifest_path"],
        pages="1",
    )

    assert html.status == "succeeded"
    assert rendered.status == "succeeded"
    assert qa.status == "succeeded"
    assert qa.tool == "pdf.qa.visual_report"
    assert pdf_path.exists()


def test_workflow_research_deck_returns_supported_local_steps(tmp_path: Path) -> None:
    plan = run_workflow_research_deck(
        brief=_brief(),
        evidence_cards=_evidence(),
        html_output_path=str(tmp_path / "deck.html"),
        pdf_output_path=str(tmp_path / "deck.pdf"),
    )

    workflow = plan.usage["workflow"]
    tools = [step["tool"] for step in workflow["steps"]]
    dry_run = run_workflow(workflow, dry_run=True)

    assert plan.tool == "pdf.workflow.research_deck"
    assert tools == [
        "pdf.authoring.plan",
        "pdf.storyboard.plan",
        "pdf.pages.write",
        "pdf.create.html_package",
        "pdf.render.html_package",
        "pdf.qa.visual_report",
    ]
    assert dry_run.status == "succeeded"
    assert dry_run.usage["workflow_run"]["planned_steps"] == 6


def test_workflow_research_deck_default_placeholders_execute() -> None:
    plan = run_workflow_research_deck(brief=_brief(), evidence_cards=_evidence())

    result = run_workflow(plan.usage["workflow"])

    assert result.status == "succeeded"
    run = result.usage["workflow_run"]
    assert run["executed_steps"] == 6
    assert run["failed_steps"] == 0
    assert Path(run["bindings"]["<deck.html>"]).name == "deck.html"
    assert Path(run["bindings"]["<deck.pdf>"]).name == "deck.pdf"
    assert Path(run["bindings"]["<final.pdf>"]).exists()


def test_workflow_research_deck_execute_mode_runs_and_returns_artifacts(tmp_path: Path) -> None:
    result = run_workflow_research_deck(
        brief=_brief(),
        evidence_cards=_evidence(),
        html_output_path=str(tmp_path / "deck.html"),
        pdf_output_path=str(tmp_path / "deck.pdf"),
        artifact_dir=tmp_path / "workflow-artifacts",
        execute=True,
    )

    run = result.usage["workflow_run"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.workflow.research_deck"
    assert run["executed_steps"] == 6
    assert run["failed_steps"] == 0
    assert Path(run["bindings"]["<final.pdf>"]).exists()
    assert Path(run["bindings"]["<html_package_manifest_path>"]).exists()
    assert result.usage["workflow"]["steps"][-1]["tool"] == "pdf.qa.visual_report"
    assert any(artifact.mime_type == "application/pdf" for artifact in result.artifacts)


def test_workflow_runner_rejects_bad_authoring_qa_expected_page_count() -> None:
    result = run_workflow(
        {
            "steps": [
                {
                    "step_id": "visual_qa",
                    "tool": "pdf.qa.visual_report",
                    "input": {
                        "input_path": "deck.pdf",
                        "expected_page_count": "abc",
                    },
                }
            ]
        }
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    run = result.usage["workflow_run"]
    assert run["executed_steps"] == 1
    assert run["failed_steps"] == 1
    assert run["step_results"][0]["error"]["code"] == "unsafe_input_rejected"
