from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from pydantic import ValidationError

from agentpdf.authoring.models import DesignTokens
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


THEMES: dict[str, dict[str, str]] = {
    "business_tech": {
        "theme": "business_tech",
        "primary_color": "#2563EB",
        "accent_color": "#0F766E",
        "warning_color": "#B45309",
        "background_color": "#F8FAFC",
        "dark_color": "#111827",
    },
    "consulting": {
        "theme": "consulting",
        "primary_color": "#1D4ED8",
        "accent_color": "#0E7490",
        "warning_color": "#B45309",
        "background_color": "#FFFFFF",
        "dark_color": "#111827",
    },
    "editorial": {
        "theme": "editorial",
        "primary_color": "#7C2D12",
        "accent_color": "#166534",
        "warning_color": "#A16207",
        "background_color": "#FFFBEB",
        "dark_color": "#1F2937",
    },
    "minimal": {
        "theme": "minimal",
        "primary_color": "#111827",
        "accent_color": "#475569",
        "warning_color": "#92400E",
        "background_color": "#FFFFFF",
        "dark_color": "#020617",
    },
}


def select_design_tokens(
    theme: str = "business_tech",
    overrides: Mapping[str, object] | None = None,
) -> ToolResult:
    try:
        selected_theme = theme.strip() if theme else "business_tech"
        base = dict(THEMES.get(selected_theme, THEMES["business_tech"]))
        base["theme"] = selected_theme if selected_theme in THEMES else "business_tech"
        for key, value in dict(overrides or {}).items():
            if key in DesignTokens.model_fields:
                base[key] = str(value)
        tokens = DesignTokens.model_validate(base)
    except ValidationError as exc:
        return _failed("Design token payload is invalid or unsafe.", validation_error=exc)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool="pdf.design.tokens",
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="design_tokens_valid",
                    status="passed",
                    details={"theme": tokens.theme},
                )
            ],
        ),
        usage={
            "design_tokens": tokens.model_dump(mode="json"),
            "available_themes": sorted(THEMES),
            "cloud_boundary": {
                "local_first": True,
                "requires_model": False,
                "requires_network": False,
            },
        },
        next_recommended_tools=["pdf.pages.write", "pdf.create.html_package"],
    )


def _failed(message: str, *, validation_error: ValidationError) -> ToolResult:
    error = AgentPDFError(
        code="unsafe_input_rejected",
        message=message,
        retry_hint="Use supported DesignTokens fields with hex color values and a plain local font stack.",
        details={"payload": "design_tokens", "validation_errors": validation_error.errors(include_context=False)},
    )
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool="pdf.design.tokens",
        warnings=[message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
