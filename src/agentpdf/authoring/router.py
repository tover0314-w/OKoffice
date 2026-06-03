from __future__ import annotations

from uuid import uuid4

from pydantic import ValidationError

from agentpdf.authoring.models import AuthoringBrief, AuthoringRoute, RouteAlternative
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


def plan_authoring_route(brief: AuthoringBrief | dict[str, object]) -> ToolResult:
    try:
        parsed = brief if isinstance(brief, AuthoringBrief) else AuthoringBrief.model_validate(brief)
    except ValidationError as exc:
        return _failed(
            "pdf.authoring.plan",
            "Authoring brief is invalid or unsafe.",
            payload="brief",
            validation_error=exc,
        )
    route = _route(parsed)
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.authoring.plan",
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="authoring_route_selected",
                    status="passed",
                    details={"recommended_authoring_format": route.recommended_authoring_format},
                )
            ],
        ),
        usage={
            "authoring_plan": route.model_dump(mode="json"),
            "brief": parsed.model_dump(mode="json"),
        },
        next_recommended_tools=["pdf.storyboard.plan"],
    )


def _route(brief: AuthoringBrief) -> AuthoringRoute:
    validation = [
        "source_package_manifest",
        "render_check",
        "blank_page_check",
        "page_count_check",
    ]
    cloud_boundary = {
        "local_first": True,
        "requires_model": False,
        "requires_network": False,
        "cloud_candidates": ["managed_browser_render", "llm_storyboard_revision"],
    }

    if brief.deliverable == "existing_pdf_operation":
        return AuthoringRoute(
            authoring_route_id=_route_id(),
            recommended_authoring_format="pdf_native",
            route_reason="Do not re-author existing PDF operations; use PDF-native tools for safer output.",
            alternatives=[
                RouteAlternative(
                    authoring_format="html",
                    fit="low",
                    reason="HTML would lose original PDF structure.",
                ),
                RouteAlternative(
                    authoring_format="docx",
                    fit="low",
                    reason="DOCX conversion is not needed for native PDF edits.",
                ),
            ],
            validation_required=["validate_output", "render_check"],
            cloud_boundary=cloud_boundary,
        )

    if brief.deliverable in {"report", "whitepaper"} or brief.page_count > 18:
        return AuthoringRoute(
            authoring_route_id=_route_id(),
            recommended_authoring_format="docx",
            route_reason="Text-heavy report with long sections, tables, or review flow fits DOCX-first authoring.",
            alternatives=[
                RouteAlternative(
                    authoring_format="html",
                    fit="medium",
                    reason="Useful for rich visual pages, less ideal for long prose editing.",
                ),
                RouteAlternative(
                    authoring_format="markdown",
                    fit="medium",
                    reason="Good for simple local reports with limited layout.",
                ),
                RouteAlternative(
                    authoring_format="pptx",
                    fit="low",
                    reason="Slides are awkward for long-form text.",
                ),
            ],
            validation_required=validation,
            cloud_boundary=cloud_boundary,
        )

    return AuthoringRoute(
        authoring_route_id=_route_id(),
        recommended_authoring_format="html",
        route_reason="Deck-style PDF with fixed pages, visual cards, source footers, and CSS-controlled layout.",
        alternatives=[
            RouteAlternative(
                authoring_format="pptx",
                fit="medium",
                reason="Good when the user needs editable slide source.",
            ),
            RouteAlternative(
                authoring_format="markdown",
                fit="low",
                reason="Fast but too limited for rich deck layouts.",
            ),
            RouteAlternative(
                authoring_format="reportlab",
                fit="low",
                reason="Precise but expensive to hand-tune for visual decks.",
            ),
        ],
        validation_required=validation,
        cloud_boundary=cloud_boundary,
    )


def _route_id() -> str:
    return f"route_{uuid4().hex[:12]}"


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"


def _failed(
    tool: str,
    message: str,
    *,
    payload: str,
    validation_error: ValidationError,
) -> ToolResult:
    error = AgentPDFError(
        code="authoring_invalid_brief",
        message=message,
        retry_hint="Provide a non-empty topic and a page_count between 1 and 80.",
        details={"payload": payload, "validation_errors": validation_error.errors(include_context=False)},
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[message],
        error=error,
    )
