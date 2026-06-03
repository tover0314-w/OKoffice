from __future__ import annotations

from agentpdf.authoring.design import select_design_tokens
from agentpdf.authoring.pages import write_pages_from_storyboard
from agentpdf.authoring.research import extract_evidence_cards, normalize_source_cards, plan_research
from agentpdf.authoring.revise import revise_pages
from agentpdf.authoring.storyboard import plan_storyboard


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


def _raw_sources() -> list[dict[str, object]]:
    return [
        {
            "title": "State of Mobile 2026",
            "publisher": "Example Research",
            "date": "2026-01-01",
            "url": "https://example.com/mobile",
            "source_type": "report",
            "summary": "Mobile monetization remains strong while downloads flatten.",
            "key_points": [
                "Revenue growth continues while downloads flatten.",
                "Non-game subscriptions keep expanding.",
            ],
            "usable_for": ["market_context", "executive_summary"],
        }
    ]


def test_research_plan_returns_local_source_strategy_without_fetching() -> None:
    result = plan_research(_brief())

    plan = result.usage["research_plan"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.research.plan"
    assert plan["topic"] == "Independent developers going global"
    assert plan["requires_network"] is False
    assert plan["cloud_boundary"]["local_first"] is True
    assert len(plan["research_questions"]) >= 5
    assert any("Independent developers going global" in query for query in plan["search_queries"])
    assert result.next_recommended_tools == ["pdf.research.source_cards"]


def test_source_cards_normalize_agent_supplied_sources_without_network_fetch() -> None:
    result = normalize_source_cards(brief=_brief(), sources=_raw_sources())

    cards = result.usage["source_cards"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.research.source_cards"
    assert cards[0]["id"] == "source_001"
    assert cards[0]["fetch_status"] == "not_fetched"
    assert cards[0]["reliability"] == "high"
    assert cards[0]["useful_for"] == ["market_context", "executive_summary"]
    assert result.next_recommended_tools == ["pdf.research.evidence_cards"]


def test_source_cards_reject_unsafe_urls() -> None:
    result = normalize_source_cards(
        brief=_brief(),
        sources=[{"title": "Unsafe", "url": "javascript:alert(1)", "summary": "bad"}],
    )

    assert result.status == "failed"
    assert result.tool == "pdf.research.source_cards"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"


def test_evidence_cards_extract_claims_from_source_cards() -> None:
    source_cards = normalize_source_cards(brief=_brief(), sources=_raw_sources()).usage["source_cards"]

    result = extract_evidence_cards(source_cards=source_cards)

    cards = result.usage["evidence_cards"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.research.evidence_cards"
    assert cards[0]["id"] == "ev_source_001_01"
    assert cards[0]["claim"] == "Revenue growth continues while downloads flatten."
    assert cards[0]["source_title"] == "State of Mobile 2026"
    assert cards[0]["usable_for"] == ["market_context", "executive_summary"]
    assert result.next_recommended_tools == ["pdf.storyboard.plan"]


def test_design_tokens_selects_safe_theme_and_rejects_injection() -> None:
    selected = select_design_tokens(
        theme="consulting",
        overrides={"primary_color": "#123456"},
    )
    unsafe = select_design_tokens(
        theme="consulting",
        overrides={"font_family": "Arial; background:url(https://example.com/x)"},
    )

    assert selected.status == "succeeded"
    assert selected.tool == "pdf.design.tokens"
    assert selected.usage["design_tokens"]["primary_color"] == "#123456"
    assert selected.next_recommended_tools == ["pdf.pages.write", "pdf.create.html_package"]
    assert unsafe.status == "failed"
    assert unsafe.error is not None
    assert unsafe.error.code == "unsafe_input_rejected"


def test_pages_revise_updates_content_while_preserving_evidence_refs() -> None:
    brief = _brief()
    evidence_cards = extract_evidence_cards(
        source_cards=normalize_source_cards(brief=brief, sources=_raw_sources()).usage["source_cards"]
    ).usage["evidence_cards"]
    storyboard = plan_storyboard(brief=brief, evidence_cards=evidence_cards).usage["storyboard"]
    page_document = write_pages_from_storyboard(
        brief=brief,
        storyboard=storyboard,
        evidence_cards=evidence_cards,
    ).usage["page_document"]

    result = revise_pages(
        page_document=page_document,
        revisions=[
            {
                "page_number": 2,
                "title": "Updated Executive Summary",
                "blocks": [{"type": "claim", "text": "Updated but still source-backed."}],
            }
        ],
    )

    revised = result.usage["page_document"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.pages.revise"
    assert revised["pages"][1]["title"] == "Updated Executive Summary"
    assert revised["pages"][1]["evidence_refs"] == page_document["pages"][1]["evidence_refs"]
    assert result.usage["revision_report"]["changed_pages"] == [2]
    assert result.next_recommended_tools == ["pdf.create.html_package", "pdf.qa.visual_report"]
