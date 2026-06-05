from okoffice.authoring.models import AuthoringBrief, EvidenceCard
from okoffice.authoring.pages import write_pages_from_storyboard
from okoffice.authoring.router import plan_authoring_route
from okoffice.authoring.storyboard import plan_storyboard, validate_claim_spine


def _brief() -> AuthoringBrief:
    return AuthoringBrief(
        topic="Independent developers going global",
        goal="Create a concise strategy deck",
        audience="founders",
        language="en",
        page_count=8,
        deliverable="deck",
        research_required=True,
        citation_required=True,
    )


def _evidence() -> list[EvidenceCard]:
    return [
        EvidenceCard(
            id="ev_market",
            claim="Mobile monetization remains strong.",
            evidence="Revenue growth continues while downloads flatten.",
            source_title="State of Mobile 2026",
            source_url="https://example.com/mobile",
            source_date="2026-01-01",
            confidence="medium",
            usable_for=["market_context", "summary"],
        ),
        EvidenceCard(
            id="ev_subscription",
            claim="Subscription operations matter.",
            evidence="Trial conversion and retention vary widely by paywall design.",
            source_title="Subscription Apps 2026",
            source_url="https://example.com/subscriptions",
            source_date="2026-02-01",
            confidence="medium",
            usable_for=["business_model"],
        ),
    ]


def test_plan_storyboard_creates_exact_page_count_and_evidence_refs() -> None:
    brief = _brief()
    route = plan_authoring_route(brief).usage["authoring_plan"]

    result = plan_storyboard(brief=brief, authoring_plan=route, evidence_cards=_evidence())

    storyboard = result.usage["storyboard"]
    assert result.status == "succeeded"
    assert result.tool == "pdf.storyboard.plan"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.validation.checks[0].name == "storyboard_page_count_matches"
    assert storyboard["page_count"] == 8
    assert len(storyboard["pages"]) == 8
    assert storyboard["pages"][0]["page_type"] == "cover"
    assert storyboard["pages"][-1]["page_type"] == "conclusion_sources"
    assert any("ev_market" in page["evidence_refs"] for page in storyboard["pages"])
    assert result.next_recommended_tools == ["pdf.pages.write"]


def test_plan_storyboard_one_page_brief_creates_cover_page() -> None:
    brief = AuthoringBrief(topic="One page deck", page_count=1)
    route = plan_authoring_route(brief).usage["authoring_plan"]

    result = plan_storyboard(brief=brief, authoring_plan=route)

    storyboard = result.usage["storyboard"]
    assert storyboard["page_count"] == 1
    assert len(storyboard["pages"]) == 1
    assert storyboard["pages"][0]["page_type"] == "cover"
    assert storyboard["pages"][0]["layout"] == "cover"


def test_write_pages_from_storyboard_creates_page_document_with_source_footers() -> None:
    brief = _brief()
    route = plan_authoring_route(brief).usage["authoring_plan"]
    storyboard = plan_storyboard(
        brief=brief,
        authoring_plan=route,
        evidence_cards=_evidence(),
    ).usage["storyboard"]

    result = write_pages_from_storyboard(
        brief=brief,
        storyboard=storyboard,
        evidence_cards=_evidence(),
        design_tokens={"theme": "business_tech"},
    )

    document = result.usage["page_document"]
    assert result.status == "succeeded"
    assert result.tool == "pdf.pages.write"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.validation.checks[0].name == "page_document_page_count_matches"
    assert document["page_count"] == 8
    assert len(document["pages"]) == 8
    assert document["pages"][0]["layout"] == "cover"
    assert document["pages"][1]["blocks"]
    assert any("State of Mobile 2026" in page["source_footer"] for page in document["pages"])
    assert result.next_recommended_tools == ["pdf.create.html_package"]


def test_write_pages_from_storyboard_returns_stable_error_code_for_invalid_storyboard() -> None:
    result = write_pages_from_storyboard(
        brief={"topic": "Broken storyboard"},
        storyboard={"storyboard_id": "story_bad", "page_count": 2, "pages": []},
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_storyboard"


def test_plan_storyboard_returns_failed_tool_result_for_bad_brief() -> None:
    result = plan_storyboard(brief={"topic": "", "page_count": 0})

    assert result.status == "failed"
    assert result.tool == "pdf.storyboard.plan"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_brief"
    assert result.error.details["payload"] == "brief"


def test_plan_storyboard_returns_failed_tool_result_for_page_count_mismatch() -> None:
    result = plan_storyboard(
        brief={"topic": "Mismatch", "page_count": 2},
        authoring_plan={},
        evidence_cards=[],
    )
    result.usage["storyboard"]["pages"].pop()

    # Revalidating this damaged storyboard through pages should fail as a ToolResult.
    pages_result = write_pages_from_storyboard(
        brief={"topic": "Mismatch", "page_count": 2},
        storyboard=result.usage["storyboard"],
    )

    assert pages_result.status == "failed"
    assert pages_result.tool == "pdf.pages.write"
    assert pages_result.error is not None
    assert pages_result.error.code == "authoring_invalid_storyboard"
    assert pages_result.error.details["payload"] == "storyboard"


def test_write_pages_from_storyboard_returns_failed_tool_result_for_bad_storyboard() -> None:
    result = write_pages_from_storyboard(
        brief={"topic": "Bad storyboard"},
        storyboard={"storyboard_id": "story_bad", "page_count": 2, "pages": []},
    )

    assert result.status == "failed"
    assert result.tool == "pdf.pages.write"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_storyboard"
    assert result.error.details["payload"] == "storyboard"


def test_write_pages_from_storyboard_returns_failed_tool_result_for_bad_design_tokens() -> None:
    brief = AuthoringBrief(topic="Bad tokens", page_count=1)
    storyboard = plan_storyboard(brief=brief).usage["storyboard"]

    result = write_pages_from_storyboard(
        brief=brief,
        storyboard=storyboard,
        design_tokens={
            "primary_color": "#fff; background: url(https://example.com/x)",
            "font_family": "Arial; @import url(https://example.com/x.css)",
        },
    )

    assert result.status == "failed"
    assert result.tool == "pdf.pages.write"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    assert result.error.details["payload"] == "design_tokens"


# --- Phase 4: Narrative Arc Tests ---


class TestArcTemplates:
    def test_pitch_deck_arc_has_six_pages(self) -> None:
        brief = AuthoringBrief(topic="Startup pitch", page_count=6, style="pitch_deck")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        page_types = [p["page_type"] for p in storyboard["pages"]]
        assert page_types == ["cover", "problem", "solution", "market", "traction", "ask"]

    def test_board_review_arc(self) -> None:
        brief = AuthoringBrief(topic="Board review", page_count=6, style="board_review")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        page_types = [p["page_type"] for p in storyboard["pages"]]
        assert page_types == ["cover", "executive_summary", "performance", "risk_compliance", "recommendation", "conclusion_sources"]

    def test_research_brief_arc(self) -> None:
        brief = AuthoringBrief(topic="Research brief", page_count=6, style="research_brief")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        page_types = [p["page_type"] for p in storyboard["pages"]]
        assert page_types == ["cover", "executive_summary", "methodology", "findings", "implications", "conclusion_sources"]

    def test_status_update_arc(self) -> None:
        brief = AuthoringBrief(topic="Status update", page_count=5, style="status_update")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        page_types = [p["page_type"] for p in storyboard["pages"]]
        assert page_types == ["cover", "summary", "progress", "blockers", "next_steps"]

    def test_training_arc(self) -> None:
        brief = AuthoringBrief(topic="Training module", page_count=6, style="training")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        page_types = [p["page_type"] for p in storyboard["pages"]]
        assert page_types == ["cover", "why_it_matters", "core_concept", "example", "practice", "summary"]

    def test_unknown_style_falls_back_to_default_arc(self) -> None:
        brief = AuthoringBrief(topic="Custom style", page_count=4, style="custom_unknown")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        assert result.status == "succeeded"
        assert storyboard["pages"][0]["page_type"] == "cover"
        assert storyboard["pages"][-1]["page_type"] == "conclusion_sources"

    def test_pitch_deck_with_extra_pages_adds_deep_dives(self) -> None:
        brief = AuthoringBrief(topic="Extended pitch", page_count=9, style="pitch_deck")
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        assert len(storyboard["pages"]) == 9
        assert storyboard["pages"][-1]["page_type"] == "ask"
        deep_dive_pages = [p for p in storyboard["pages"] if p["page_type"].startswith("deep_dive_")]
        assert len(deep_dive_pages) == 3


class TestInsightTitles:
    def test_evidence_card_claim_used_as_title(self) -> None:
        brief = AuthoringBrief(topic="Market analysis", page_count=8, style="business_research")
        cards = [
            EvidenceCard(
                id="ev1",
                claim="Mobile monetization remains strong",
                evidence="Revenue growth continues.",
                source_title="State of Mobile 2026",
                source_url="https://example.com",
                usable_for=["market_context"],
            ),
        ]
        result = plan_storyboard(brief=brief, evidence_cards=cards)
        storyboard = result.usage["storyboard"]
        market_page = next(p for p in storyboard["pages"] if p["page_type"] == "market_context")
        assert market_page["title"] == "Mobile monetization remains strong"

    def test_evidence_card_too_long_claim_not_used_as_title(self) -> None:
        brief = AuthoringBrief(topic="Market analysis", page_count=8, style="business_research")
        long_claim = "A" * 90
        cards = [
            EvidenceCard(
                id="ev1",
                claim=long_claim,
                evidence="Revenue growth continues.",
                source_title="State of Mobile 2026",
                source_url="https://example.com",
                usable_for=["market_context"],
            ),
        ]
        result = plan_storyboard(brief=brief, evidence_cards=cards)
        storyboard = result.usage["storyboard"]
        market_page = next(p for p in storyboard["pages"] if p["page_type"] == "market_context")
        assert market_page["title"] != long_claim

    def test_cover_page_uses_topic_not_insight(self) -> None:
        brief = AuthoringBrief(topic="My Topic", page_count=8)
        cards = [
            EvidenceCard(
                id="ev1",
                claim="Some insight for cover",
                evidence="Evidence.",
                source_title="Source",
                source_url="https://example.com",
                usable_for=["cover"],
            ),
        ]
        result = plan_storyboard(brief=brief, evidence_cards=cards)
        storyboard = result.usage["storyboard"]
        assert storyboard["pages"][0]["title"] == "My Topic"


class TestClaimSpineValidation:
    def test_valid_storyboard_passes_spine_check(self) -> None:
        brief = AuthoringBrief(topic="Strategy deck", page_count=8)
        result = plan_storyboard(brief=brief)
        storyboard = result.usage["storyboard"]
        from okoffice.authoring.models import Storyboard
        parsed = Storyboard.model_validate(storyboard)
        spine = validate_claim_spine(parsed)
        assert spine["valid"] is True
        assert len(spine["issues"]) == 0
        assert len(spine["spine"]) == 8

    def test_empty_core_claim_flagged(self) -> None:
        from okoffice.authoring.models import Storyboard, StoryboardPage
        pages = [
            StoryboardPage(page_number=1, page_type="cover", title="T", core_claim="Frame the topic.", layout="cover"),
            StoryboardPage(page_number=2, page_type="body", title="B", core_claim="", layout="title_bullets"),
        ]
        storyboard = Storyboard(storyboard_id="s1", page_count=2, pages=pages)
        spine = validate_claim_spine(storyboard)
        assert spine["valid"] is False
        assert any("empty core claim" in issue for issue in spine["issues"])

    def test_duplicate_claim_flagged(self) -> None:
        from okoffice.authoring.models import Storyboard, StoryboardPage
        pages = [
            StoryboardPage(page_number=1, page_type="cover", title="T", core_claim="Same claim here", layout="cover"),
            StoryboardPage(page_number=2, page_type="body", title="B", core_claim="Same claim here", layout="title_bullets"),
        ]
        storyboard = Storyboard(storyboard_id="s2", page_count=2, pages=pages)
        spine = validate_claim_spine(storyboard)
        assert spine["valid"] is False
        assert any("repeats" in issue for issue in spine["issues"])

    def test_closing_page_without_action_flagged(self) -> None:
        from okoffice.authoring.models import Storyboard, StoryboardPage
        pages = [
            StoryboardPage(page_number=1, page_type="cover", title="T", core_claim="Frame.", layout="cover"),
            StoryboardPage(page_number=2, page_type="conclusion_sources", title="End", core_claim="Just some data.", layout="sources"),
        ]
        storyboard = Storyboard(storyboard_id="s3", page_count=2, pages=pages)
        spine = validate_claim_spine(storyboard)
        assert spine["valid"] is False
        assert any("call to action" in issue.lower() or "conclusion" in issue.lower() for issue in spine["issues"])

    def test_plan_storyboard_includes_claim_spine_in_usage(self) -> None:
        brief = AuthoringBrief(topic="Strategy deck", page_count=8)
        result = plan_storyboard(brief=brief)
        assert "claim_spine" in result.usage
        assert result.usage["claim_spine"]["valid"] is True
        assert len(result.usage["claim_spine"]["spine"]) == 8

    def test_plan_storyboard_includes_spine_validation_check(self) -> None:
        brief = AuthoringBrief(topic="Strategy deck", page_count=8)
        result = plan_storyboard(brief=brief)
        check_names = [c.name for c in result.validation.checks]
        assert "claim_spine_coherent" in check_names
