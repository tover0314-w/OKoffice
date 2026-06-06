from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4

from pydantic import ValidationError

from okoffice.authoring.models import DesignTokens
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


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
    "ink_classic": {
        "theme": "ink_classic",
        "primary_color": "#0a0a0b",
        "accent_color": "#44403c",
        "warning_color": "#92400e",
        "background_color": "#f1efea",
        "dark_color": "#0a0a0b",
    },
    "indigo_porcelain": {
        "theme": "indigo_porcelain",
        "primary_color": "#0a1f3d",
        "accent_color": "#3b82f6",
        "warning_color": "#b45309",
        "background_color": "#f1f3f5",
        "dark_color": "#0a1f3d",
    },
    "forest_ink": {
        "theme": "forest_ink",
        "primary_color": "#1a2e1f",
        "accent_color": "#4ade80",
        "warning_color": "#a16207",
        "background_color": "#f5f1e8",
        "dark_color": "#1a2e1f",
    },
    "kraft_paper": {
        "theme": "kraft_paper",
        "primary_color": "#2a1e13",
        "accent_color": "#92400e",
        "warning_color": "#b45309",
        "background_color": "#eedfc7",
        "dark_color": "#2a1e13",
    },
    "dune": {
        "theme": "dune",
        "primary_color": "#1f1a14",
        "accent_color": "#c2956a",
        "warning_color": "#a16207",
        "background_color": "#f0e6d2",
        "dark_color": "#1f1a14",
    },
}

PRESETS: dict[str, DesignTokens] = {
    "business_tech": DesignTokens(theme="business_tech"),
    "consulting": DesignTokens(theme="consulting", primary_color="#1D4ED8", accent_color="#0E7490", background_color="#FFFFFF"),
    "editorial": DesignTokens(theme="editorial", primary_color="#7C2D12", accent_color="#166534", warning_color="#A16207", background_color="#FFFBEB", dark_color="#1F2937"),
    "minimal": DesignTokens(theme="minimal", primary_color="#111827", accent_color="#475569", warning_color="#92400E", background_color="#FFFFFF", dark_color="#020617"),
    "dark_executive": DesignTokens(
        theme="dark_executive",
        font_family="Noto Sans CJK SC, Georgia, serif",
        heading_font="Noto Sans CJK SC, Georgia, serif",
        body_font="Noto Sans CJK SC, Georgia, serif",
        primary_color="#60A5FA", accent_color="#34D399", warning_color="#FBBF24",
        background_color="#0F172A", dark_color="#F1F5F9",
        heading_size_px=38, subtitle_size_px=24, body_size_px=17,
        line_height=1.35, heading_line_height=1.15, slide_padding_px=52, slide_gap_px=32,
    ),
    "board_review": DesignTokens(
        theme="board_review",
        font_family="Noto Sans CJK SC, Garamond, serif",
        heading_font="Noto Sans CJK SC, Garamond, serif",
        body_font="Noto Sans CJK SC, Garamond, serif",
        primary_color="#1E3A5F", accent_color="#C9A959", warning_color="#B45309",
        background_color="#FBF9F6", dark_color="#1C1917",
        heading_size_px=32, subtitle_size_px=20, body_size_px=15,
        line_height=1.45, heading_line_height=1.2, slide_padding_px=56, slide_gap_px=30,
    ),
    "pitch": DesignTokens(
        theme="pitch",
        font_family="Noto Sans CJK SC, Inter, sans-serif",
        heading_font="Noto Sans CJK SC, Inter, sans-serif",
        body_font="Noto Sans CJK SC, Inter, sans-serif",
        primary_color="#4F46E5", accent_color="#F59E0B", warning_color="#EF4444",
        background_color="#FFFFFF", dark_color="#0F172A",
        heading_size_px=40, subtitle_size_px=24, body_size_px=17,
        line_height=1.35, heading_line_height=1.1, slide_padding_px=48, slide_gap_px=24,
    ),
    "research_brief": DesignTokens(
        theme="research_brief",
        font_family="Noto Sans CJK SC, Source Serif Pro, serif",
        heading_font="Noto Sans CJK SC, Source Serif Pro, serif",
        body_font="Noto Sans CJK SC, Source Serif Pro, serif",
        primary_color="#1E40AF", accent_color="#059669", warning_color="#D97706",
        background_color="#F9FAFB", dark_color="#111827",
        heading_size_px=32, subtitle_size_px=20, body_size_px=14,
        line_height=1.5, heading_line_height=1.25, slide_padding_px=56, slide_gap_px=28,
    ),
    "ink_classic": DesignTokens(
        theme="ink_classic",
        font_family="Noto Sans CJK SC, Inter, sans-serif",
        heading_font="Noto Serif SC, Playfair Display, Georgia, serif",
        body_font="Noto Sans CJK SC, Inter, sans-serif",
        display_font="Noto Serif SC, Playfair Display, Georgia, serif",
        mono_font="IBM Plex Mono, Courier New, monospace",
        primary_color="#0a0a0b", accent_color="#44403c", warning_color="#92400e",
        background_color="#f1efea", dark_color="#0a0a0b",
        heading_size_px=42, subtitle_size_px=22, body_size_px=16, caption_size_px=10,
        line_height=1.45, heading_line_height=1.1, slide_padding_px=60, slide_gap_px=32,
        rhythm="anchor", shadow_restraint="none", gradient_sophistication="flat",
    ),
    "indigo_porcelain": DesignTokens(
        theme="indigo_porcelain",
        font_family="Noto Sans CJK SC, Inter, sans-serif",
        heading_font="Noto Serif SC, Playfair Display, Georgia, serif",
        body_font="Noto Sans CJK SC, Inter, sans-serif",
        display_font="Noto Serif SC, Playfair Display, Georgia, serif",
        mono_font="IBM Plex Mono, Courier New, monospace",
        primary_color="#0a1f3d", accent_color="#3b82f6", warning_color="#b45309",
        background_color="#f1f3f5", dark_color="#0a1f3d",
        heading_size_px=40, subtitle_size_px=22, body_size_px=16, caption_size_px=10,
        line_height=1.45, heading_line_height=1.1, slide_padding_px=60, slide_gap_px=32,
        rhythm="dense", shadow_restraint="subtle", gradient_sophistication="subtle",
    ),
    "forest_ink": DesignTokens(
        theme="forest_ink",
        font_family="Noto Sans CJK SC, Inter, sans-serif",
        heading_font="Noto Serif SC, Playfair Display, Georgia, serif",
        body_font="Noto Sans CJK SC, Inter, sans-serif",
        display_font="Noto Serif SC, Playfair Display, Georgia, serif",
        mono_font="IBM Plex Mono, Courier New, monospace",
        primary_color="#1a2e1f", accent_color="#4ade80", warning_color="#a16207",
        background_color="#f5f1e8", dark_color="#1a2e1f",
        heading_size_px=40, subtitle_size_px=22, body_size_px=16, caption_size_px=10,
        line_height=1.45, heading_line_height=1.1, slide_padding_px=60, slide_gap_px=32,
        rhythm="breathing", shadow_restraint="none", gradient_sophistication="flat",
    ),
    "kraft_paper": DesignTokens(
        theme="kraft_paper",
        font_family="Noto Sans CJK SC, Inter, sans-serif",
        heading_font="Noto Serif SC, Playfair Display, Georgia, serif",
        body_font="Noto Sans CJK SC, Inter, sans-serif",
        display_font="Noto Serif SC, Playfair Display, Georgia, serif",
        mono_font="IBM Plex Mono, Courier New, monospace",
        primary_color="#2a1e13", accent_color="#92400e", warning_color="#b45309",
        background_color="#eedfc7", dark_color="#2a1e13",
        heading_size_px=40, subtitle_size_px=22, body_size_px=16, caption_size_px=10,
        line_height=1.45, heading_line_height=1.1, slide_padding_px=60, slide_gap_px=32,
        rhythm="anchor", shadow_restraint="none", gradient_sophistication="flat",
    ),
    "dune": DesignTokens(
        theme="dune",
        font_family="Noto Sans CJK SC, Inter, sans-serif",
        heading_font="Noto Serif SC, Playfair Display, Georgia, serif",
        body_font="Noto Sans CJK SC, Inter, sans-serif",
        display_font="Noto Serif SC, Playfair Display, Georgia, serif",
        mono_font="IBM Plex Mono, Courier New, monospace",
        primary_color="#1f1a14", accent_color="#c2956a", warning_color="#a16207",
        background_color="#f0e6d2", dark_color="#1f1a14",
        heading_size_px=40, subtitle_size_px=22, body_size_px=16, caption_size_px=10,
        line_height=1.45, heading_line_height=1.1, slide_padding_px=60, slide_gap_px=32,
        rhythm="breathing", shadow_restraint="subtle", gradient_sophistication="subtle",
    ),
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


def resolve_theme(theme_name: str) -> DesignTokens:
    if theme_name in PRESETS:
        return PRESETS[theme_name]
    return PRESETS["business_tech"]


def _failed(message: str, *, validation_error: ValidationError) -> ToolResult:
    error = OKofficeError(
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
