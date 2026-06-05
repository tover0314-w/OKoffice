from __future__ import annotations

from typing import Any
from uuid import uuid4

from okoffice.schemas.models import ToolResult


def plan_workflow(goal: str, input_path: str | None = None) -> ToolResult:
    tool = "pdf.workflow.plan"
    normalized_goal = goal.strip()
    steps = _base_inspection_steps(input_path)
    agents = {
        "planner": "Turns the goal into a local-first PDF tool chain.",
        "inspector": "Collects document and page evidence before edits or AI steps.",
        "validator": "Checks parseability, page count, renderability, and warnings.",
    }

    if _mentions_any(normalized_goal, {"chat", "ask", "question", "answer", "rag", "cite", "citation"}):
        agents.update(
            {
                "parser": "Builds Document IR from the local text layer.",
                "retriever": "Creates and queries a local cited index.",
                "citation_checker": "Maps answers back to page and bbox evidence.",
            }
        )
        steps.extend(
            [
                _step(
                    "parse",
                    "parser",
                    "pdf.ai.parse.lite",
                    "Create local Document IR before retrieval.",
                    {"input_path": input_path or "<input.pdf>", "pages": "all"},
                ),
                _step(
                    "index",
                    "retriever",
                    "pdf.ai.rag.ingest",
                    "Build a local index with page and bbox citations.",
                    {
                        "input_path": input_path or "<input.pdf>",
                        "index_path": "<output.index.json>",
                        "pages": "all",
                    },
                ),
                _step(
                    "answer",
                    "retriever",
                    "pdf.ai.rag.query",
                    "Return an extractive local answer with cited chunks.",
                    {"index_path": "<output.index.json>", "query": "<question>"},
                ),
                _step(
                    "cite",
                    "citation_checker",
                    "pdf.ai.rag.cite_answer",
                    "Verify the final answer against local page and bbox evidence.",
                    {"index_path": "<output.index.json>", "answer": "<answer>"},
                ),
                _step(
                    "highlight_sources",
                    "citation_checker",
                    "pdf.ai.rag.highlight_sources",
                    "Create a highlighted source PDF so agents can hand back visual evidence.",
                    {
                        "index_path": "<output.index.json>",
                        "answer": "<answer>",
                        "output_path": "<highlighted.pdf>",
                    },
                ),
            ]
        )

    if _mentions_any(normalized_goal, {"image", "figure", "chart", "scan", "vision", "ocr"}):
        agents["vision_router"] = "Extracts embedded images for OCR or future vision workers."
        steps.append(
            _step(
                "extract_images",
                "vision_router",
                "pdf.convert.extract_images",
                "Expose figures, scans, and embedded images as artifacts.",
                {"input_path": input_path or "<input.pdf>", "pages": "all", "out_dir": "<images-dir>"},
            )
        )

    if _mentions_any(normalized_goal, {"compress", "optimize", "repair", "fix", "small", "share"}):
        agents["optimizer"] = "Runs deterministic rewrite and size-reduction tools."
        if _mentions_any(normalized_goal, {"compress", "optimize", "small", "share"}):
            steps.append(
                _step(
                    "compress",
                    "optimizer",
                    "pdf.optimize.compress",
                    "Reduce size while preserving pages and validation evidence.",
                    {"input_path": input_path or "<input.pdf>", "output_path": "<compressed.pdf>"},
                )
            )
        if _mentions_any(normalized_goal, {"repair", "fix"}):
            steps.append(
                _step(
                    "repair",
                    "optimizer",
                    "pdf.optimize.repair",
                    "Rewrite a parseable PDF object structure.",
                    {"input_path": "<compressed-or-input.pdf>", "output_path": "<repaired.pdf>"},
                )
            )

    if _mentions_any(normalized_goal, {"create", "markdown", "report", "template", "pdf from"}):
        agents["template_designer"] = "Selects deterministic local templates and style packs."
        steps.append(
            _step(
                "create",
                "template_designer",
                "pdf.convert.markdown_to_pdf",
                "Create a validated PDF from Markdown and a local style pack.",
                {"markdown": "<markdown>", "output_path": "<output.pdf>", "style_pack": "plain_report"},
            )
        )

    steps.extend(
        [
            _step(
                "validate",
                "validator",
                "pdf.validation.validate_output",
                "Confirm the final PDF parses and has expected page count.",
                {"path": "<final.pdf>"},
            ),
            _step(
                "render_check",
                "validator",
                "pdf.validation.render_check",
                "Render representative pages before handing results back to an agent or user.",
                {"path": "<final.pdf>", "pages": "1"},
            ),
        ]
    )

    workflow = {
        "plan_id": f"wfplan_{uuid4().hex[:12]}",
        "goal": normalized_goal,
        "input_path": input_path,
        "agents": agents,
        "steps": steps,
        "cloud_boundary": {
            "local_first": True,
            "requires_model": False,
            "cloud_candidates": _cloud_candidates(normalized_goal),
            "note": "This plan uses local OSS tools first; cloud workers should be opt-in.",
        },
    }
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        usage={"workflow": workflow},
        next_recommended_tools=[steps[0]["tool"]] if steps else ["pdf.inspect.document"],
    )


def _base_inspection_steps(input_path: str | None) -> list[dict[str, Any]]:
    target = input_path or "<input.pdf>"
    return [
        _step(
            "inspect_document",
            "inspector",
            "pdf.inspect.document",
            "Collect document-level facts before choosing operations.",
            {"path": target},
        ),
        _step(
            "inspect_pages",
            "inspector",
            "pdf.inspect.pages",
            "Collect page geometry, text-layer, image-count, and optional render evidence.",
            {"input_path": target, "pages": "all", "render_check": True},
        ),
    ]


def _step(
    step_id: str,
    agent: str,
    tool: str,
    reason: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "agent": agent,
        "tool": tool,
        "reason": reason,
        "input": payload,
        "expected_output": "ToolResult JSON with artifacts, warnings, usage, and next recommendations.",
    }


def _mentions_any(text: str, keywords: set[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _cloud_candidates(goal: str) -> list[str]:
    candidates = []
    if _mentions_any(goal, {"scan", "ocr", "vision", "chart", "formula", "latex"}):
        candidates.append("pdf.ai.parse.agentic")
    if _mentions_any(goal, {"translate", "rewrite", "summarize", "generate"}):
        candidates.append("hosted_model_worker")
    return candidates
