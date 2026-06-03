from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from pydantic import ValidationError

from agentpdf.authoring.models import AuthoringBrief, EvidenceCard, Storyboard, StoryboardPage
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


DEFAULT_DECK_ARC = [
    ("cover", "cover", "Frame the topic and audience."),
    ("executive_summary", "three_cards", "Summarize the central recommendation."),
    ("market_context", "metrics", "Show why the market matters."),
    ("key_change", "comparison", "Explain the important shift."),
    ("opportunity_map", "matrix", "Map practical opportunities."),
    ("business_model", "funnel", "Describe how value becomes revenue."),
    ("risk_compliance", "risk_grid", "Surface risks before execution."),
    ("conclusion_sources", "sources", "Close with action and sources."),
]


def plan_storyboard(
    *,
    brief: AuthoringBrief | Mapping[str, object],
    authoring_plan: Mapping[str, object] | None = None,
    evidence_cards: list[EvidenceCard | Mapping[str, object]] | None = None,
) -> ToolResult:
    try:
        parsed_brief = brief if isinstance(brief, AuthoringBrief) else AuthoringBrief.model_validate(brief)
    except ValidationError as exc:
        return _failed(
            "pdf.storyboard.plan",
            "Authoring brief is invalid or unsafe.",
            code="authoring_invalid_brief",
            payload="brief",
            validation_error=exc,
        )
    try:
        cards = [
            card if isinstance(card, EvidenceCard) else EvidenceCard.model_validate(card)
            for card in (evidence_cards or [])
        ]
    except ValidationError as exc:
        return _failed(
            "pdf.storyboard.plan",
            "Evidence card payload is invalid or unsafe.",
            code="authoring_invalid_storyboard",
            payload="evidence_cards",
            validation_error=exc,
        )
    storyboard = _build_storyboard(parsed_brief, cards)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.storyboard.plan",
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="storyboard_page_count_matches",
                    status="passed",
                    details={
                        "page_count": storyboard.page_count,
                        "pages": len(storyboard.pages),
                    },
                )
            ],
            page_count=storyboard.page_count,
        ),
        usage={
            "storyboard": storyboard.model_dump(mode="json"),
            "brief": parsed_brief.model_dump(mode="json"),
            "authoring_plan": dict(authoring_plan or {}),
        },
        next_recommended_tools=["pdf.pages.write"],
    )


def _build_storyboard(brief: AuthoringBrief, cards: list[EvidenceCard]) -> Storyboard:
    arc = _arc_for_page_count(brief.page_count)
    pages = [
        StoryboardPage(
            page_number=index,
            page_type=page_type,
            title=_title_for(brief, page_type, index),
            core_claim=claim,
            layout=layout,
            evidence_refs=_evidence_refs_for(page_type, cards),
            notes=_notes_for(brief, page_type),
        )
        for index, (page_type, layout, claim) in enumerate(arc, start=1)
    ]
    return Storyboard(
        storyboard_id=f"story_{uuid4().hex[:12]}",
        page_count=brief.page_count,
        pages=pages,
    )


def _arc_for_page_count(page_count: int) -> list[tuple[str, str, str]]:
    if page_count == 1:
        return [DEFAULT_DECK_ARC[0]]
    if page_count <= len(DEFAULT_DECK_ARC):
        return DEFAULT_DECK_ARC[: page_count - 1] + [DEFAULT_DECK_ARC[-1]]

    arc = list(DEFAULT_DECK_ARC[:-1])
    while len(arc) < page_count - 1:
        number = len(arc)
        arc.append(
            (
                f"deep_dive_{number}",
                "section_cards",
                "Add a focused deep-dive page while preserving one idea per page.",
            )
        )
    arc.append(DEFAULT_DECK_ARC[-1])
    return arc


def _title_for(brief: AuthoringBrief, page_type: str, index: int) -> str:
    if page_type == "cover":
        return brief.topic
    titles = {
        "executive_summary": "The Main Recommendation",
        "market_context": "The Market Still Rewards Focused Products",
        "key_change": "Creation Is Easier, Differentiation Is Harder",
        "opportunity_map": "Small Teams Win With Narrow, High-Trust Workflows",
        "business_model": "Subscription Is an Operating System",
        "risk_compliance": "Compliance and Trust Need Early Design",
        "conclusion_sources": "What to Do Next",
    }
    return titles.get(page_type, f"Deep Dive {index}")


def _evidence_refs_for(page_type: str, cards: list[EvidenceCard]) -> list[str]:
    refs = [
        card.id
        for card in cards
        if page_type in card.usable_for
        or page_type.replace("_", " ") in " ".join(card.usable_for)
        or any(token in page_type for token in card.usable_for)
    ]
    if not refs and page_type in {"executive_summary", "conclusion_sources"}:
        refs = [card.id for card in cards[:3]]
    return refs


def _notes_for(brief: AuthoringBrief, page_type: str) -> list[str]:
    notes = [f"Audience: {brief.audience or 'general'}"]
    if brief.citation_required and page_type != "cover":
        notes.append("Include a source footer when evidence is available.")
    return notes


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"


def _failed(
    tool: str,
    message: str,
    *,
    code: str,
    payload: str,
    validation_error: ValidationError,
) -> ToolResult:
    error = AgentPDFError(
        code=code,
        message=message,
        retry_hint="Provide a valid local authoring payload and retry.",
        details={"payload": payload, "validation_errors": validation_error.errors(include_context=False)},
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[message],
        error=error,
    )
