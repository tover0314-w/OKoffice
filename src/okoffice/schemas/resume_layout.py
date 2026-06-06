"""Resume section layout system with dual CSS/ReportLab rendering.

Follows the deck_themes.py pattern (LayoutKind -> ShapeDef -> Layout -> dual rendering).
Each layout defines positioned regions (shapes) with font roles that map
to ResumeDesignTokens for per-element typography control.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ResumeLayoutKind = Literal[
    "single_column",
    "two_column_sidebar",
    "header_with_contact",
]

ResumeFontRole = Literal[
    "name",
    "headline",
    "contact",
    "section_title",
    "entry_title",
    "entry_org",
    "entry_date",
    "body",
]


class ResumeShapeDef(BaseModel):
    """A positioned region within a resume layout."""

    purpose: str = Field(
        ...,
        description=(
            "Semantic role of this region: "
            "'name', 'headline', 'contact', 'section_title', "
            "'entry_title', 'entry_org', 'entry_date', 'body', "
            "'sidebar_section', 'sidebar_title'"
        ),
    )
    x: int = Field(0, description="Column position (0-based, 12-column grid)")
    y: int = Field(0, description="Row position")
    cx: int = Field(12, description="Column span (1-12)")
    cy: int = Field(1, description="Row span")
    css_area: str = Field("", description="CSS grid area name for HTML rendering")
    font_role: ResumeFontRole = Field(
        "body",
        description="Maps to a ResumeDesignTokens field (e.g. 'name' -> name_font/name_size_pt)",
    )
    bold: bool = Field(False, description="Whether this region uses bold weight")
    bullet: bool = Field(False, description="Whether this region renders as bullet list")
    ats_safe: bool = Field(
        True,
        description="Whether this element is ATS-compatible in its layout position",
    )


class ResumeLayout(BaseModel):
    """A resume page layout definition."""

    kind: ResumeLayoutKind = Field(..., description="Layout variant identifier")
    shapes: list[ResumeShapeDef] = Field(
        default_factory=list,
        description="Positioned regions in this layout",
    )
    css_grid_template: str = Field(
        "",
        description="CSS grid-template-areas string for HTML rendering",
    )
    ats_compatible: bool = Field(
        True,
        description="Whether this layout passes ATS single-column layout checks",
    )
    max_entries_per_page: int = Field(
        6,
        description="Maximum entries before automatic page break",
    )


# --- Built-in layouts ---

RESUME_LAYOUTS: dict[str, ResumeLayout] = {
    "single_column": ResumeLayout(
        kind="single_column",
        ats_compatible=True,
        max_entries_per_page=6,
        shapes=[
            ResumeShapeDef(
                purpose="name", x=0, y=0, cx=12, cy=1,
                css_area="name", font_role="name", bold=True,
            ),
            ResumeShapeDef(
                purpose="headline", x=0, y=1, cx=12, cy=1,
                css_area="headline", font_role="headline",
            ),
            ResumeShapeDef(
                purpose="contact", x=0, y=2, cx=12, cy=1,
                css_area="contact", font_role="contact",
            ),
            ResumeShapeDef(
                purpose="section_title", x=0, y=3, cx=12, cy=1,
                css_area="section_title", font_role="section_title", bold=True,
            ),
            ResumeShapeDef(
                purpose="entry_title", x=0, y=4, cx=8, cy=1,
                css_area="entry_title", font_role="entry_title", bold=True,
            ),
            ResumeShapeDef(
                purpose="entry_org", x=8, y=4, cx=4, cy=1,
                css_area="entry_org", font_role="entry_org",
            ),
            ResumeShapeDef(
                purpose="entry_date", x=8, y=5, cx=4, cy=1,
                css_area="entry_date", font_role="entry_date",
            ),
            ResumeShapeDef(
                purpose="body", x=0, y=6, cx=12, cy=2,
                css_area="body", font_role="body", bullet=True,
            ),
        ],
        css_grid_template='"name name name name name name name name name name name name"\n'
        '"headline headline headline headline headline headline headline headline headline headline headline headline"\n'
        '"contact contact contact contact contact contact contact contact contact contact contact contact"\n'
        '"section_title section_title section_title section_title section_title section_title section_title section_title section_title section_title section_title section_title"\n'
        '"entry_title entry_title entry_title entry_title entry_title entry_title entry_title entry_org entry_org entry_org entry_org entry_org"\n'
        '". . . . . . . entry_date entry_date entry_date entry_date entry_date"\n'
        '"body body body body body body body body body body body body"\n'
        '"body body body body body body body body body body body body"',
    ),
    "two_column_sidebar": ResumeLayout(
        kind="two_column_sidebar",
        ats_compatible=False,
        max_entries_per_page=8,
        shapes=[
            # Sidebar (left 4 columns)
            ResumeShapeDef(
                purpose="name", x=0, y=0, cx=4, cy=1,
                css_area="name", font_role="name", bold=True, ats_safe=False,
            ),
            ResumeShapeDef(
                purpose="contact", x=0, y=1, cx=4, cy=1,
                css_area="contact", font_role="contact", ats_safe=False,
            ),
            ResumeShapeDef(
                purpose="sidebar_section", x=0, y=2, cx=4, cy=4,
                css_area="sidebar", font_role="body", bullet=True, ats_safe=False,
            ),
            # Main content (right 8 columns)
            ResumeShapeDef(
                purpose="headline", x=4, y=0, cx=8, cy=1,
                css_area="headline", font_role="headline", ats_safe=False,
            ),
            ResumeShapeDef(
                purpose="section_title", x=4, y=1, cx=8, cy=1,
                css_area="section_title", font_role="section_title", bold=True, ats_safe=False,
            ),
            ResumeShapeDef(
                purpose="entry_title", x=4, y=2, cx=5, cy=1,
                css_area="entry_title", font_role="entry_title", bold=True, ats_safe=False,
            ),
            ResumeShapeDef(
                purpose="entry_date", x=9, y=2, cx=3, cy=1,
                css_area="entry_date", font_role="entry_date", ats_safe=False,
            ),
            ResumeShapeDef(
                purpose="body", x=4, y=3, cx=8, cy=2,
                css_area="body", font_role="body", bullet=True, ats_safe=False,
            ),
        ],
        css_grid_template='"name name name name headline headline headline headline headline headline headline headline"\n'
        '"contact contact contact contact section_title section_title section_title section_title section_title section_title section_title section_title"\n'
        '"sidebar sidebar sidebar sidebar entry_title entry_title entry_title entry_title entry_title entry_date entry_date entry_date"\n'
        '"sidebar sidebar sidebar sidebar body body body body body body body body"\n'
        '"sidebar sidebar sidebar sidebar body body body body body body body body"',
    ),
    "header_with_contact": ResumeLayout(
        kind="header_with_contact",
        ats_compatible=True,
        max_entries_per_page=6,
        shapes=[
            ResumeShapeDef(
                purpose="name", x=0, y=0, cx=12, cy=1,
                css_area="name", font_role="name", bold=True,
            ),
            ResumeShapeDef(
                purpose="headline", x=0, y=1, cx=12, cy=1,
                css_area="headline", font_role="headline",
            ),
            ResumeShapeDef(
                purpose="contact", x=0, y=2, cx=12, cy=1,
                css_area="contact", font_role="contact",
            ),
            ResumeShapeDef(
                purpose="section_title", x=0, y=3, cx=12, cy=1,
                css_area="section_title", font_role="section_title", bold=True,
            ),
            ResumeShapeDef(
                purpose="entry_title", x=0, y=4, cx=8, cy=1,
                css_area="entry_title", font_role="entry_title", bold=True,
            ),
            ResumeShapeDef(
                purpose="entry_date", x=8, y=4, cx=4, cy=1,
                css_area="entry_date", font_role="entry_date",
            ),
            ResumeShapeDef(
                purpose="body", x=0, y=5, cx=12, cy=2,
                css_area="body", font_role="body", bullet=True,
            ),
        ],
        css_grid_template='"name name name name name name name name name name name name"\n'
        '"headline headline headline headline headline headline headline headline headline headline headline headline"\n'
        '"contact contact contact contact contact contact contact contact contact contact contact contact"\n'
        '"section_title section_title section_title section_title section_title section_title section_title section_title section_title section_title section_title section_title"\n'
        '"entry_title entry_title entry_title entry_title entry_title entry_title entry_title entry_title entry_date entry_date entry_date entry_date"\n'
        '"body body body body body body body body body body body body"\n'
        '"body body body body body body body body body body body body"',
    ),
}


def select_resume_layout(
    layout_name: str | None = None,
    ats_mode: bool = True,
) -> ResumeLayout:
    """Select a resume layout, enforcing ATS mode if required.

    Args:
        layout_name: Explicit layout name, or None for auto-selection.
        ats_mode: If True, forces an ATS-compatible layout.

    Returns:
        A ResumeLayout instance.
    """
    if layout_name and layout_name in RESUME_LAYOUTS:
        layout = RESUME_LAYOUTS[layout_name]
    else:
        layout = RESUME_LAYOUTS["single_column"]

    if ats_mode and not layout.ats_compatible:
        return RESUME_LAYOUTS["single_column"]

    return layout


def layout_to_resume_css(layout: ResumeLayout) -> str:
    """Generate CSS grid rules for HTML rendering.

    Returns CSS with grid-template-areas, column sizing,
    and per-purpose typography from design tokens (injected via CSS variables).
    """
    lines = [
        ".okoffice-resume {",
        "  display: grid;",
        f"  grid-template-areas: {layout.css_grid_template};",
        "  grid-template-columns: repeat(12, 1fr);",
        "  gap: 2px;",
        "  padding: var(--resume-padding, 48pt);",
        "}",
        "",
    ]

    for shape in layout.shapes:
        if not shape.css_area:
            continue
        area = shape.css_area
        lines.append(f'[data-purpose="{shape.purpose}"] {{')
        lines.append(f"  grid-area: {area};")
        if shape.bold:
            lines.append("  font-weight: bold;")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "RESUME_LAYOUTS",
    "ResumeFontRole",
    "ResumeLayout",
    "ResumeLayoutKind",
    "ResumeShapeDef",
    "layout_to_resume_css",
    "select_resume_layout",
]
