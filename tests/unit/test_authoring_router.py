from okoffice.authoring.models import AuthoringBrief
from okoffice.authoring.router import plan_authoring_route


def test_plan_authoring_route_prefers_html_for_visual_deck() -> None:
    result = plan_authoring_route(
        AuthoringBrief(
            topic="Independent developers going global",
            page_count=12,
            deliverable="deck",
            style="business_research",
            research_required=True,
            citation_required=True,
        )
    )

    plan = result.usage["authoring_plan"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.authoring.plan"
    assert plan["recommended_authoring_format"] == "html"
    assert "Deck-style PDF" in plan["route_reason"]
    assert "render_check" in plan["validation_required"]
    assert plan["cloud_boundary"]["local_first"] is True
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.validation.checks[0].name == "authoring_route_selected"
    assert result.next_recommended_tools == ["pdf.storyboard.plan"]


def test_plan_authoring_route_prefers_docx_for_text_heavy_report() -> None:
    result = plan_authoring_route(
        AuthoringBrief(
            topic="Security policy",
            page_count=24,
            deliverable="report",
            style="whitepaper",
        )
    )

    plan = result.usage["authoring_plan"]

    assert plan["recommended_authoring_format"] == "docx"
    assert "Text-heavy" in plan["route_reason"]
    assert any(item["authoring_format"] == "html" for item in plan["alternatives"])


def test_plan_authoring_route_prefers_pdf_native_for_existing_pdf_operation() -> None:
    result = plan_authoring_route(
        AuthoringBrief(
            topic="Merge uploaded PDFs",
            deliverable="existing_pdf_operation",
            output_format="pdf",
        )
    )

    plan = result.usage["authoring_plan"]

    assert plan["recommended_authoring_format"] == "pdf_native"
    assert "Do not re-author" in plan["route_reason"]


def test_plan_authoring_route_returns_stable_error_code_for_invalid_brief() -> None:
    result = plan_authoring_route({"topic": "", "page_count": 0})

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_brief"


def test_plan_authoring_route_returns_failed_tool_result_for_bad_brief() -> None:
    result = plan_authoring_route({"topic": "", "page_count": 0})

    assert result.status == "failed"
    assert result.tool == "pdf.authoring.plan"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_brief"
    assert result.error.details["payload"] == "brief"
