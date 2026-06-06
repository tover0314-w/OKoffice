"""Fine-grained resume design tokens with base + delta theme system.

Inspired by RenderCV's YAML delta pattern: themes define only the fields
that differ from a base preset. Resolution merges base + delta.

Each field maps to a specific element in the resume layout (name, section
title, entry title, body, etc.) for precise per-element typography control.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from okoffice.schemas.errors import OKofficeException


class ResumeDesignTokens(BaseModel):
    """Fine-grained design tokens for resume rendering.

    Every field has a default, so callers only need to override
    what differs from the preset.
    """

    # --- Base theme reference ---
    base_theme: str = Field(
        "resume_modern",
        description="Base theme ID to inherit defaults from",
    )

    # --- Page ---
    page_size: Literal["letter", "A4"] = Field(
        "letter",
        description="Page size — 'letter' (8.5x11in) for US, 'A4' for international",
    )
    margins_top_pt: float = Field(42, description="Top margin in points", ge=0)
    margins_bottom_pt: float = Field(42, description="Bottom margin in points", ge=0)
    margins_left_pt: float = Field(48, description="Left margin in points", ge=0)
    margins_right_pt: float = Field(48, description="Right margin in points", ge=0)

    # --- Name ---
    name_font: str = Field("Helvetica-Bold", description="Font for candidate name")
    name_size_pt: float = Field(18, description="Name font size in points", ge=6, le=36)
    name_color: str = Field("#0f172a", description="Name text color (hex)")

    # --- Headline ---
    headline_font: str = Field("Helvetica", description="Font for headline")
    headline_size_pt: float = Field(11, description="Headline font size", ge=6, le=24)
    headline_color: str = Field("#475569", description="Headline text color")

    # --- Contact ---
    contact_font: str = Field("Helvetica", description="Font for contact info")
    contact_size_pt: float = Field(9, description="Contact info font size", ge=6, le=14)
    contact_color: str = Field("#475569", description="Contact info color")

    # --- Section title ---
    section_title_font: str = Field(
        "Helvetica-Bold", description="Font for section headers",
    )
    section_title_size_pt: float = Field(
        11, description="Section header font size", ge=8, le=20,
    )
    section_title_color: str = Field("#0f766e", description="Section header color")
    section_title_spacing_before_pt: float = Field(
        12, description="Space before section header", ge=0, le=36,
    )
    section_title_spacing_after_pt: float = Field(
        4, description="Space after section header", ge=0, le=24,
    )
    section_title_underline: bool = Field(
        True, description="Draw underline below section header",
    )

    # --- Entry title (job title, degree) ---
    entry_title_font: str = Field(
        "Helvetica-Bold", description="Font for entry titles (job titles, degree names)",
    )
    entry_title_size_pt: float = Field(10, description="Entry title font size", ge=6, le=18)
    entry_title_color: str = Field("#0f172a", description="Entry title color")

    # --- Entry organization ---
    entry_org_font: str = Field("Helvetica", description="Font for organization name")
    entry_org_size_pt: float = Field(10, description="Organization font size", ge=6, le=16)
    entry_org_color: str = Field("#0f172a", description="Organization color")

    # --- Entry date ---
    entry_date_font: str = Field("Helvetica", description="Font for date ranges")
    entry_date_size_pt: float = Field(9, description="Date font size", ge=6, le=14)
    entry_date_color: str = Field("#64748b", description="Date color")

    # --- Body / bullets ---
    body_font: str = Field("Helvetica", description="Body/bullet text font")
    body_size_pt: float = Field(9, description="Body text font size", ge=6, le=14)
    body_color: str = Field("#1f2937", description="Body text color")
    body_line_spacing: float = Field(
        1.35, description="Line spacing multiplier for body text", ge=0.8, le=3.0,
    )
    bullet_indent_pt: float = Field(14, description="Indent for bullet items", ge=0)
    bullet_spacing_pt: float = Field(2, description="Spacing between bullet items", ge=0)

    # --- ATS safety ---
    ats_safe_fonts_only: bool = Field(
        True,
        description="Restrict to ATS-safe fonts (Arial, Calibri, Garamond, Helvetica, Times)",
    )
    ats_single_column: bool = Field(
        True, description="Force single-column layout for ATS compatibility",
    )
    ats_standard_margins: bool = Field(
        True, description="Enforce minimum 1-inch (72pt) margins for ATS",
    )

    @field_validator("name_color", "headline_color", "contact_color",
                     "section_title_color", "entry_title_color",
                     "entry_org_color", "entry_date_color", "body_color")
    @classmethod
    def _validate_hex_color(cls, v: str) -> str:
        if not v.startswith("#") or len(v) not in (4, 7):
            raise ValueError(f"Color must be hex (#RGB or #RRGGBB), got: {v}")
        return v


# --- Presets ---

RESUME_TOKEN_PRESETS: dict[str, ResumeDesignTokens] = {
    "resume_modern": ResumeDesignTokens(
        base_theme="resume_modern",
        page_size="letter",
        margins_top_pt=42, margins_bottom_pt=42,
        margins_left_pt=48, margins_right_pt=48,
        name_font="Helvetica-Bold", name_size_pt=18, name_color="#0f172a",
        section_title_color="#0f766e",
        section_title_underline=True,
    ),
    "resume_classic": ResumeDesignTokens(
        base_theme="resume_classic",
        page_size="letter",
        margins_top_pt=72, margins_bottom_pt=72,
        margins_left_pt=72, margins_right_pt=72,
        name_font="Times-Bold", name_size_pt=16, name_color="#000000",
        headline_font="Times-Roman", headline_size_pt=11, headline_color="#333333",
        contact_font="Times-Roman", contact_size_pt=10, contact_color="#333333",
        section_title_font="Times-Bold", section_title_size_pt=12,
        section_title_color="#000000",
        section_title_underline=True,
        entry_title_font="Times-Bold", entry_title_color="#000000",
        entry_org_font="Times-Roman", entry_org_color="#000000",
        entry_date_font="Times-Roman", entry_date_color="#555555",
        body_font="Times-Roman", body_size_pt=10, body_color="#1a1a1a",
    ),
    "resume_minimal": ResumeDesignTokens(
        base_theme="resume_minimal",
        page_size="letter",
        margins_top_pt=54, margins_bottom_pt=54,
        margins_left_pt=54, margins_right_pt=54,
        name_font="Helvetica-Bold", name_size_pt=20, name_color="#111827",
        headline_font="Helvetica", headline_size_pt=10, headline_color="#6b7280",
        section_title_font="Helvetica",
        section_title_size_pt=10, section_title_color="#111827",
        section_title_spacing_before_pt=16,
        section_title_underline=False,
        entry_title_font="Helvetica-Bold",
        entry_title_size_pt=10, entry_title_color="#111827",
        body_size_pt=9,
    ),
    "resume_technical": ResumeDesignTokens(
        base_theme="resume_technical",
        page_size="letter",
        margins_top_pt=42, margins_bottom_pt=42,
        margins_left_pt=48, margins_right_pt=48,
        name_font="Courier-Bold", name_size_pt=16, name_color="#0f172a",
        headline_font="Courier", headline_size_pt=10, headline_color="#475569",
        section_title_font="Courier-Bold",
        section_title_size_pt=10, section_title_color="#2563eb",
        section_title_underline=False,
        entry_title_font="Courier-Bold",
        body_font="Courier", body_size_pt=9,
    ),
    "resume_ats_safe": ResumeDesignTokens(
        base_theme="resume_ats_safe",
        page_size="letter",
        margins_top_pt=72, margins_bottom_pt=72,
        margins_left_pt=72, margins_right_pt=72,
        name_font="Helvetica-Bold", name_size_pt=16, name_color="#000000",
        headline_font="Helvetica", headline_size_pt=11, headline_color="#333333",
        contact_font="Helvetica", contact_size_pt=10, contact_color="#333333",
        section_title_font="Helvetica-Bold",
        section_title_size_pt=12, section_title_color="#000000",
        section_title_underline=True,
        entry_title_font="Helvetica-Bold",
        entry_title_size_pt=10, entry_title_color="#000000",
        entry_org_font="Helvetica", entry_org_color="#000000",
        entry_date_font="Helvetica", entry_date_color="#555555",
        body_font="Helvetica", body_size_pt=10, body_color="#1a1a1a",
        ats_safe_fonts_only=True,
        ats_single_column=True,
        ats_standard_margins=True,
    ),
    "onepage_compact": ResumeDesignTokens(
        base_theme="onepage_compact",
        page_size="letter",
        margins_top_pt=24, margins_bottom_pt=24,
        margins_left_pt=32, margins_right_pt=32,
        name_font="Helvetica-Bold", name_size_pt=14, name_color="#0f172a",
        headline_font="Helvetica", headline_size_pt=9, headline_color="#475569",
        contact_font="Helvetica", contact_size_pt=8, contact_color="#475569",
        section_title_font="Helvetica-Bold",
        section_title_size_pt=9, section_title_color="#0f766e",
        section_title_spacing_before_pt=6,
        section_title_spacing_after_pt=2,
        section_title_underline=True,
        entry_title_font="Helvetica-Bold",
        entry_title_size_pt=9, entry_title_color="#0f172a",
        entry_org_font="Helvetica", entry_org_size_pt=8, entry_org_color="#0f172a",
        entry_date_font="Helvetica", entry_date_size_pt=8, entry_date_color="#64748b",
        body_font="Helvetica", body_size_pt=8, body_color="#1f2937",
        body_line_spacing=1.15,
        bullet_indent_pt=10, bullet_spacing_pt=1,
        ats_safe_fonts_only=True,
        ats_single_column=True,
        ats_standard_margins=False,
    ),
}


ATS_SAFE_FONT_NAMES = frozenset({
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique",
    "Arial", "Arial-Bold", "Calibri", "Garamond",
    "system-sans",
})


def _ats_font(value: str, bold: bool = False) -> str:
    """Map any font request to an ATS-safe equivalent."""
    normalized = value.lower().replace(" ", "")
    if normalized in {"serif", "garamond", "times", "times-roman", "timesroman"}:
        return "Times-Bold" if bold else "Times-Roman"
    if normalized in {"mono", "courier", "monospace"}:
        return "Courier-Bold" if bold else "Courier"
    return "Helvetica-Bold" if bold else "Helvetica"


def resolve_resume_tokens(
    base_name: str = "resume_modern",
    delta: dict[str, Any] | None = None,
) -> ResumeDesignTokens:
    """Resolve base preset with optional delta overrides.

    Args:
        base_name: Preset name from RESUME_TOKEN_PRESETS.
        delta: Optional dict of field overrides to merge on top of the base.

    Returns:
        A validated ResumeDesignTokens instance.

    Raises:
        OKofficeException: If base_name is not found.
    """
    base = RESUME_TOKEN_PRESETS.get(base_name)
    if base is None:
        raise OKofficeException(
            "unsupported_file_type",
            f"Unknown resume design token preset: '{base_name}'. "
            f"Available: {sorted(RESUME_TOKEN_PRESETS.keys())}",
            recovery_hint=(
                f"Use one of the built-in presets: {', '.join(sorted(RESUME_TOKEN_PRESETS.keys()))}. "
                f"Or provide a full ResumeDesignTokens dict as delta."
            ),
        )
    if not delta:
        return base.model_copy()
    merged = base.model_dump()
    for key, value in delta.items():
        if key in ResumeDesignTokens.model_fields:
            merged[key] = value
    return ResumeDesignTokens.model_validate(merged)


def resolve_resume_tokens_from_source(
    source: str | dict[str, Any] | Path | ResumeDesignTokens | None = None,
) -> ResumeDesignTokens:
    """Resolve tokens from any source: preset name, dict, file path, or instance.

    Args:
        source: One of:
            - None → returns resume_modern preset
            - str matching a preset name → returns that preset
            - str path to .json → loads and resolves as delta
            - dict → resolves as delta on resume_modern
            - Path → loads .json and resolves
            - ResumeDesignTokens → returns as-is
    """
    if source is None:
        return RESUME_TOKEN_PRESETS["resume_modern"].model_copy()

    if isinstance(source, ResumeDesignTokens):
        return source

    if isinstance(source, Path) or (isinstance(source, str) and source.endswith(".json")):
        path = Path(source) if isinstance(source, str) else source
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            base_name = data.get("base_theme", "resume_modern")
            return resolve_resume_tokens(base_name, delta=data)
        return resolve_resume_tokens("resume_modern")

    if isinstance(source, str):
        if source in RESUME_TOKEN_PRESETS:
            return RESUME_TOKEN_PRESETS[source].model_copy()
        return resolve_resume_tokens("resume_modern", delta={"base_theme": source})

    if isinstance(source, dict):
        base_name = source.get("base_theme", "resume_modern")
        return resolve_resume_tokens(base_name, delta=source)

    return RESUME_TOKEN_PRESETS["resume_modern"].model_copy()


__all__ = [
    "ATS_SAFE_FONT_NAMES",
    "RESUME_TOKEN_PRESETS",
    "ResumeDesignTokens",
    "_ats_font",
    "resolve_resume_tokens",
    "resolve_resume_tokens_from_source",
]
