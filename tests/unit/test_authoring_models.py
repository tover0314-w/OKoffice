from okoffice.authoring.models import (
    AuthoringBrief,
    DesignTokens,
    EvidenceCard,
    PageDocument,
    PageSpec,
    Storyboard,
    StoryboardPage,
)


def test_authoring_brief_normalizes_defaults() -> None:
    brief = AuthoringBrief(topic="OKoffice authoring", page_count=6)

    assert brief.topic == "OKoffice authoring"
    assert brief.page_count == 6
    assert brief.language == "en"
    assert brief.deliverable == "deck"
    assert brief.research_required is False
    assert brief.citation_required is False


def test_authoring_brief_rejects_zero_pages() -> None:
    try:
        AuthoringBrief(topic="Bad", page_count=0)
    except ValueError as exc:
        assert "page_count" in str(exc)
    else:
        raise AssertionError("Expected page_count validation error")


def test_evidence_card_serializes_source_metadata() -> None:
    card = EvidenceCard(
        id="ev_1",
        claim="Revenue is growing.",
        evidence="A report says revenue is growing.",
        source_title="State of Apps",
        source_url="https://example.com/apps",
        source_date="2026-01-01",
        publisher="Example",
        confidence="medium",
        usable_for=["market_context"],
    )

    payload = card.model_dump(mode="json")

    assert payload["id"] == "ev_1"
    assert payload["confidence"] == "medium"
    assert payload["usable_for"] == ["market_context"]


def test_storyboard_and_page_document_dump_json() -> None:
    storyboard = Storyboard(
        storyboard_id="story_test",
        page_count=2,
        pages=[
            StoryboardPage(
                page_number=1,
                page_type="cover",
                title="OKoffice",
                core_claim="Frame the deck.",
                layout="cover",
            ),
            StoryboardPage(
                page_number=2,
                page_type="summary",
                title="Main point",
                core_claim="Show the key point.",
                layout="three_cards",
                evidence_refs=["ev_1"],
            ),
        ],
    )
    document = PageDocument(
        page_document_id="pages_test",
        page_count=2,
        pages=[
            PageSpec(page_number=1, layout="cover", title="OKoffice"),
            PageSpec(
                page_number=2,
                layout="three_cards",
                title="Main point",
                blocks=[{"type": "text", "text": "Show the key point."}],
                source_footer="Source: State of Apps",
            ),
        ],
        design_tokens=DesignTokens(theme="business_tech"),
    )

    assert '"storyboard_id":"story_test"' in storyboard.model_dump_json()
    assert document.model_dump(mode="json")["design_tokens"]["theme"] == "business_tech"


def test_design_tokens_reject_unsafe_color_and_font_values() -> None:
    try:
        DesignTokens(
            primary_color="#fff; background: url(https://example.com/x)",
            font_family="Arial; @import url(https://example.com/x.css)",
        )
    except ValueError as exc:
        message = str(exc)
        assert "primary_color" in message
        assert "font_family" in message
    else:
        raise AssertionError("Expected design token validation error")


def test_design_tokens_accept_hex_colors_and_font_stack() -> None:
    tokens = DesignTokens(
        primary_color="#2563EB",
        accent_color="#0F766E",
        warning_color="#b80",
        background_color="#fff",
        dark_color="#111827",
        font_family="Noto Sans CJK SC, Arial, sans-serif",
    )

    assert tokens.primary_color == "#2563EB"
    assert tokens.warning_color == "#b80"
    assert tokens.font_family == "Noto Sans CJK SC, Arial, sans-serif"
