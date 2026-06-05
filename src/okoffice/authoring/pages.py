from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from pydantic import ValidationError

from okoffice.authoring.models import (
    AuthoringBrief,
    DesignTokens,
    EvidenceCard,
    PageDocument,
    PageSpec,
    Storyboard,
    StoryboardPage,
)
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


def write_pages_from_storyboard(
    *,
    brief: AuthoringBrief | Mapping[str, object],
    storyboard: Storyboard | Mapping[str, object],
    evidence_cards: list[EvidenceCard | Mapping[str, object]] | None = None,
    design_tokens: DesignTokens | Mapping[str, object] | None = None,
) -> ToolResult:
    try:
        parsed_brief = brief if isinstance(brief, AuthoringBrief) else AuthoringBrief.model_validate(brief)
    except ValidationError as exc:
        return _failed(
            "Authoring brief is invalid or unsafe.",
            code="authoring_invalid_brief",
            payload="brief",
            validation_error=exc,
        )
    try:
        parsed_storyboard = (
            storyboard if isinstance(storyboard, Storyboard) else Storyboard.model_validate(storyboard)
        )
    except ValidationError as exc:
        return _failed(
            "Storyboard payload is invalid or unsafe.",
            code="authoring_invalid_storyboard",
            payload="storyboard",
            validation_error=exc,
        )
    try:
        cards = [
            card if isinstance(card, EvidenceCard) else EvidenceCard.model_validate(card)
            for card in (evidence_cards or [])
        ]
    except ValidationError as exc:
        return _failed(
            "Evidence card payload is invalid or unsafe.",
            code="authoring_invalid_page_document",
            payload="evidence_cards",
            validation_error=exc,
        )
    try:
        tokens = (
            design_tokens
            if isinstance(design_tokens, DesignTokens)
            else DesignTokens.model_validate(design_tokens or {})
        )
    except ValidationError as exc:
        return _failed(
            "Design token payload is invalid or unsafe.",
            code="unsafe_input_rejected",
            payload="design_tokens",
            validation_error=exc,
        )
    document = PageDocument(
        page_document_id=f"pages_{uuid4().hex[:12]}",
        page_count=parsed_storyboard.page_count,
        pages=[_page_spec(parsed_brief, page, cards) for page in parsed_storyboard.pages],
        design_tokens=tokens,
    )
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.pages.write",
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="page_document_page_count_matches",
                    status="passed",
                    details={"page_count": document.page_count, "pages": len(document.pages)},
                )
            ],
            page_count=document.page_count,
        ),
        usage={
            "page_document": document.model_dump(mode="json"),
            "brief": parsed_brief.model_dump(mode="json"),
        },
        next_recommended_tools=["pdf.create.html_package"],
    )


def _page_spec(brief: AuthoringBrief, page: StoryboardPage, cards: list[EvidenceCard]) -> PageSpec:
    evidence = [card for card in cards if card.id in page.evidence_refs]
    footer = _source_footer(evidence)
    if page.layout == "cover":
        blocks = [
            {"type": "hero", "text": brief.goal or f"A {brief.deliverable} about {brief.topic}."},
            {"type": "meta", "text": f"Audience: {brief.audience or 'general'}"},
        ]
    elif page.layout == "sources":
        blocks = [
            {
                "type": "source_list",
                "items": [
                    {
                        "title": card.source_title,
                        "url": card.source_url,
                        "publisher": card.publisher,
                        "date": card.source_date,
                    }
                    for card in cards
                ],
            }
        ]
    else:
        blocks = [
            {"type": "claim", "text": page.core_claim},
            {
                "type": "evidence_cards",
                "items": [
                    {
                        "claim": card.claim,
                        "evidence": card.evidence,
                        "source_title": card.source_title,
                        "confidence": card.confidence,
                    }
                    for card in evidence
                ],
            },
        ]
    return PageSpec(
        page_number=page.page_number,
        layout=page.layout,
        title=page.title,
        subtitle=page.core_claim,
        blocks=blocks,
        source_footer=footer,
        evidence_refs=list(page.evidence_refs),
    )


def _source_footer(cards: list[EvidenceCard]) -> str:
    titles = [card.source_title for card in cards if card.source_title]
    if not titles:
        return ""
    return "Sources: " + "; ".join(dict.fromkeys(titles))


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"


def _failed(
    message: str,
    *,
    code: str,
    payload: str,
    validation_error: ValidationError,
) -> ToolResult:
    error = OKofficeError(
        code=code,
        message=message,
        retry_hint="Provide a valid local authoring payload and retry.",
        details={"payload": payload, "validation_errors": validation_error.errors(include_context=False)},
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool="pdf.pages.write",
        warnings=[message],
        error=error,
    )
