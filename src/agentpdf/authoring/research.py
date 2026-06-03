from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from pydantic import ValidationError

from agentpdf.authoring.models import AuthoringBrief, EvidenceCard, SourceCard
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


def plan_research(brief: AuthoringBrief | Mapping[str, object]) -> ToolResult:
    try:
        parsed_brief = brief if isinstance(brief, AuthoringBrief) else AuthoringBrief.model_validate(brief)
    except ValidationError as exc:
        return _failed(
            "pdf.research.plan",
            "Authoring brief is invalid or unsafe.",
            code="authoring_invalid_brief",
            payload="brief",
            validation_error=exc,
        )

    plan = {
        "research_plan_id": f"research_plan_{uuid4().hex[:12]}",
        "topic": parsed_brief.topic,
        "goal": parsed_brief.goal,
        "audience": parsed_brief.audience,
        "language": parsed_brief.language,
        "requires_network": False,
        "research_questions": _research_questions(parsed_brief),
        "search_queries": _search_queries(parsed_brief),
        "priority_source_types": ["official", "report", "documentation", "dataset", "credible_media"],
        "evidence_needed": ["market_context", "key_change", "opportunity_map", "risks", "next_steps"],
        "rejected_source_patterns": [
            "unsourced claims",
            "stale data without dates",
            "marketing pages without supporting evidence",
        ],
        "cloud_boundary": {
            "local_first": True,
            "requires_model": False,
            "requires_network": False,
            "cloud_candidates": ["managed_web_research", "llm_source_summarization"],
        },
    }
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.research.plan",
        validation=_validation("research_plan_created", {"question_count": len(plan["research_questions"])}),
        usage={"research_plan": plan, "brief": parsed_brief.model_dump(mode="json")},
        next_recommended_tools=["pdf.research.source_cards"],
    )


def normalize_source_cards(
    *,
    brief: AuthoringBrief | Mapping[str, object] | None = None,
    sources: list[Mapping[str, object]] | None = None,
) -> ToolResult:
    try:
        parsed_brief = (
            brief
            if isinstance(brief, AuthoringBrief)
            else AuthoringBrief.model_validate(brief)
            if brief is not None
            else None
        )
        cards = [
            _source_card(index=index, raw=raw)
            for index, raw in enumerate(_require_source_list(sources), start=1)
        ]
    except AgentPDFException as exc:
        return _failed_from_exception("pdf.research.source_cards", exc)
    except ValidationError as exc:
        return _failed(
            "pdf.research.source_cards",
            "Source card payload is invalid or unsafe.",
            code="unsafe_input_rejected",
            payload="sources",
            validation_error=exc,
        )

    warnings = [] if cards else ["No sources were supplied; source_cards is empty."]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.research.source_cards",
        warnings=warnings,
        validation=_validation("source_cards_normalized", {"source_card_count": len(cards)}),
        usage={
            "source_cards": [card.model_dump(mode="json") for card in cards],
            "source_card_count": len(cards),
            "brief": parsed_brief.model_dump(mode="json") if parsed_brief else None,
            "cloud_boundary": {
                "local_first": True,
                "requires_model": False,
                "requires_network": False,
                "fetches_sources": False,
            },
        },
        next_recommended_tools=["pdf.research.evidence_cards"],
    )


def extract_evidence_cards(
    *,
    source_cards: list[SourceCard | Mapping[str, object]] | None = None,
) -> ToolResult:
    try:
        parsed_sources = [
            card if isinstance(card, SourceCard) else SourceCard.model_validate(card)
            for card in _require_source_list(source_cards)
        ]
        cards = _evidence_cards(parsed_sources)
    except AgentPDFException as exc:
        return _failed_from_exception("pdf.research.evidence_cards", exc)
    except ValidationError as exc:
        return _failed(
            "pdf.research.evidence_cards",
            "Evidence source payload is invalid or unsafe.",
            code="unsafe_input_rejected",
            payload="source_cards",
            validation_error=exc,
        )

    warnings = [] if cards else ["No evidence cards were extracted from the supplied source cards."]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.research.evidence_cards",
        warnings=warnings,
        validation=_validation("evidence_cards_extracted", {"evidence_card_count": len(cards)}),
        usage={
            "evidence_cards": [card.model_dump(mode="json") for card in cards],
            "evidence_card_count": len(cards),
            "cloud_boundary": {
                "local_first": True,
                "requires_model": False,
                "requires_network": False,
                "synthesizes_new_claims": False,
            },
        },
        next_recommended_tools=["pdf.storyboard.plan"],
    )


def _source_card(index: int, raw: Mapping[str, object]) -> SourceCard:
    source_type = _source_type(raw)
    title = _first_text(raw, "title", "name", "source_title") or f"Source {index:03d}"
    key_points = _string_list(raw.get("key_points") or raw.get("highlights") or raw.get("claims"))
    summary = _first_text(raw, "summary", "snippet", "description", "evidence") or "; ".join(key_points) or title
    return SourceCard(
        id=_first_text(raw, "id", "source_id") or f"source_{index:03d}",
        title=title,
        publisher=_first_text(raw, "publisher", "author", "organization"),
        source_date=_first_text(raw, "source_date", "date", "published_at"),
        source_url=_safe_source_url(_first_text(raw, "source_url", "url", "href")),
        source_type=source_type,
        reliability=_reliability(raw, source_type),
        summary=summary,
        key_points=key_points or [summary],
        useful_for=_string_list(raw.get("usable_for") or raw.get("useful_for")),
        fetch_status="not_fetched",
    )


def _evidence_cards(sources: list[SourceCard]) -> list[EvidenceCard]:
    cards: list[EvidenceCard] = []
    for source in sources:
        points = source.key_points or ([source.summary] if source.summary else [])
        for point_index, point in enumerate(points[:3], start=1):
            cards.append(
                EvidenceCard(
                    id=f"ev_{source.id}_{point_index:02d}",
                    claim=point,
                    evidence=source.summary or point,
                    source_title=source.title,
                    source_url=source.source_url,
                    source_date=source.source_date,
                    publisher=source.publisher,
                    confidence=source.reliability,
                    usable_for=list(source.useful_for),
                )
            )
    return cards


def _require_source_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise AgentPDFException("unsafe_input_rejected", "Sources must be provided as a JSON array.")
    return value


def _source_type(raw: Mapping[str, object]) -> str:
    candidate = str(raw.get("source_type") or raw.get("type") or "other").strip().lower()
    return candidate if candidate in {"official", "report", "media", "blog", "paper", "documentation", "dataset", "other"} else "other"


def _reliability(raw: Mapping[str, object], source_type: str) -> str:
    candidate = str(raw.get("reliability") or raw.get("confidence") or "").strip().lower()
    if candidate in {"high", "medium", "low"}:
        return candidate
    if source_type in {"official", "report", "documentation", "dataset"}:
        return "high"
    if source_type in {"media", "paper"}:
        return "medium"
    return "low"


def _safe_source_url(value: str | None) -> str | None:
    if not value:
        return None
    original = value.strip()
    parsed = urlparse(original if "://" in original else f"https://{original}")
    if parsed.scheme.lower() not in {"http", "https"}:
        raise AgentPDFException("unsafe_input_rejected", "Source URLs must use http:// or https://.")
    if parsed.username or parsed.password:
        raise AgentPDFException("unsafe_input_rejected", "Source URLs must not include credentials.")
    host = parsed.hostname
    if not host:
        raise AgentPDFException("unsafe_input_rejected", "Source URLs must include a host.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise AgentPDFException("unsafe_input_rejected", "Source URL has an invalid port.") from exc
    netloc = host.lower()
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunparse((parsed.scheme.lower(), netloc, parsed.path or "/", "", parsed.query, parsed.fragment))


def _research_questions(brief: AuthoringBrief) -> list[str]:
    return [
        f"What recent evidence explains why {brief.topic} matters now?",
        f"Which audience segments should a {brief.deliverable} about {brief.topic} prioritize?",
        "What credible data supports the market context?",
        "What are the key risks, constraints, or compliance concerns?",
        "What practical next steps should the target audience take?",
        "Which sources are official, recent, and suitable for citation?",
    ]


def _search_queries(brief: AuthoringBrief) -> list[str]:
    topic = brief.topic
    year = "2026"
    return [
        f"{topic} {year} market report",
        f"{topic} {year} official data",
        f"{topic} subscription benchmarks {year}",
        f"{topic} compliance risks {year}",
        f"{topic} go to market strategy {year}",
    ]


def _first_text(raw: Mapping[str, object], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _validation(name: str, details: dict[str, object]) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[ValidationCheck(name=name, status="passed", details=details)],
    )


def _failed_from_exception(tool: str, exc: AgentPDFException) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[exc.message],
        error=exc.to_error(),
    )


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
        retry_hint="Provide a valid local research payload and retry.",
        details={"payload": payload, "validation_errors": validation_error.errors(include_context=False)},
    )
    return ToolResult(job_id=_job_id(), status="failed", tool=tool, warnings=[message], error=error)


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
