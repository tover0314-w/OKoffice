from agentpdf.authoring.models import AuthoringBrief, EvidenceCard
from agentpdf.authoring.pages import write_pages_from_storyboard
from agentpdf.authoring.router import plan_authoring_route
from agentpdf.authoring.storyboard import plan_storyboard


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
