from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from okoffice.schemas.models import ToolResult


def plan_research_deck_workflow(
    *,
    brief: Mapping[str, Any],
    evidence_cards: list[Mapping[str, Any]] | None = None,
    html_output_path: str = "<deck.html>",
    pdf_output_path: str = "<deck.pdf>",
) -> ToolResult:
    cards = evidence_cards or []
    workflow = {
        "plan_id": f"wfplan_{uuid4().hex[:12]}",
        "workflow_kind": "research_deck",
        "goal": f"Create a verified research deck for {brief.get('topic', 'untitled topic')}",
        "agents": {
            "brief_parser": "Normalizes the brief and local assumptions.",
            "authoring_router": "Chooses the source format before rendering.",
            "storyboard_builder": "Creates one idea per page.",
            "page_writer": "Writes page JSON with source footers.",
            "visual_designer": "Writes the local HTML/CSS source package.",
            "validator": "Runs render, blank-page, page-count, and manifest checks.",
        },
        "cloud_boundary": {
            "local_first": True,
            "requires_model": False,
            "requires_network": False,
            "cloud_candidates": [
                "managed_research",
                "llm_insight_synthesis",
                "browser_render_farm",
            ],
        },
        "steps": [
            {
                "step_id": "authoring_plan",
                "agent": "authoring_router",
                "tool": "pdf.authoring.plan",
                "reason": "Choose authoring route before building the source package.",
                "input": {"brief": dict(brief)},
            },
            {
                "step_id": "storyboard",
                "agent": "storyboard_builder",
                "tool": "pdf.storyboard.plan",
                "reason": "Create exact page structure before writing content.",
                "input": {
                    "brief": dict(brief),
                    "authoring_plan": "<authoring_plan>",
                    "evidence_cards": list(cards),
                },
            },
            {
                "step_id": "pages",
                "agent": "page_writer",
                "tool": "pdf.pages.write",
                "reason": "Convert storyboard into page JSON with source footers.",
                "input": {
                    "brief": dict(brief),
                    "storyboard": "<storyboard>",
                    "evidence_cards": list(cards),
                    "design_tokens": {"theme": "business_tech"},
                },
            },
            {
                "step_id": "html_package",
                "agent": "visual_designer",
                "tool": "pdf.create.html_package",
                "reason": "Write a self-contained local HTML/CSS package.",
                "input": {
                    "page_document": "<page_document>",
                    "html_output_path": html_output_path,
                    "title": str(brief.get("topic", "OKoffice Deck")),
                },
            },
            {
                "step_id": "render",
                "agent": "visual_designer",
                "tool": "pdf.render.html_package",
                "reason": "Render the source package into a PDF artifact.",
                "input": {
                    "package_path": "<html_package_manifest_path>",
                    "output_path": pdf_output_path,
                },
            },
            {
                "step_id": "visual_qa",
                "agent": "validator",
                "tool": "pdf.qa.visual_report",
                "reason": "Verify page count, renderability, blank pages, and source manifest safety.",
                "input": {
                    "input_path": pdf_output_path,
                    "expected_page_count": "<rendered_page_count>",
                    "html_package_manifest_path": "<html_package_manifest_path>",
                    "pages": "all",
                },
            },
        ],
    }
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool="pdf.workflow.research_deck",
        usage={"workflow": workflow},
        next_recommended_tools=["pdf.workflow.run"],
    )
