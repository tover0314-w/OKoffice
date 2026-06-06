"""Typst rendering backend for resume PDF generation.

Generates Typst markup from structured ResumeData and compiles to PDF.
Produces professional-quality output with precise grid layouts, date alignment,
section dividers, and per-element typography — features that the Markdown→ReportLab
pipeline loses by flattening structured data to flat text.

Typst is an optional dependency. Install via: pip install okoffice[typst-renderer]
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from okoffice.schemas.errors import OKofficeException

if TYPE_CHECKING:
    from okoffice.schemas.resume import (
        BulletEntry,
        EducationEntry,
        ExperienceEntry,
        OneLineEntry,
        ResumeData,
        TextEntry,
    )
    from okoffice.schemas.resume_design_tokens import ResumeDesignTokens

from okoffice.core.pdf import ToolResult, _result_for_created_pdf, resolve_output_path

_TOOL = "pdf.compose.resume_pdf"


def _require_typst() -> None:
    try:
        import typst
    except ImportError:
        raise OKofficeException(
            "typst_not_installed",
            "Typst rendering backend requires the 'typst' package.",
            recovery_hint="Install with: pip install okoffice[typst-renderer]",
        )


def _tokens_to_typst_header(tokens: ResumeDesignTokens, ats_mode: bool) -> str:
    lines: list[str] = []

    # Page setup
    paper = "us-letter" if tokens.page_size == "letter" else "a4"
    margin_top = tokens.margins_top_pt
    margin_bottom = tokens.margins_bottom_pt
    margin_left = tokens.margins_left_pt
    margin_right = tokens.margins_right_pt

    if ats_mode and tokens.ats_standard_margins:
        margin_top = margin_bottom = margin_left = margin_right = 72

    lines.append(
        f'#set page(paper: "{paper}", '
        f"margin: (top: {margin_top}pt, bottom: {margin_bottom}pt, "
        f"left: {margin_left}pt, right: {margin_right}pt))"
    )

    # Default text
    base_font = _typst_font_name(tokens.body_font)
    lines.append(f'#set text(font: "{base_font}", size: {tokens.body_size_pt}pt)')
    lines.append("")

    # Design token variables
    lines.append(f'#let name-size = {tokens.name_size_pt}pt')
    lines.append(f'#let name-color = rgb("{tokens.name_color}")')
    lines.append(f'#let headline-size = {tokens.headline_size_pt}pt')
    lines.append(f'#let headline-color = rgb("{tokens.headline_color}")')
    lines.append(f'#let contact-size = {tokens.contact_size_pt}pt')
    lines.append(f'#let contact-color = rgb("{tokens.contact_color}")')
    lines.append(f'#let section-size = {tokens.section_title_size_pt}pt')
    lines.append(f'#let section-color = rgb("{tokens.section_title_color}")')
    lines.append(
        f"#let section-underline = {str(tokens.section_title_underline).lower()}"
    )
    lines.append(f'#let section-spacing-before = {tokens.section_title_spacing_before_pt}pt')
    lines.append(f'#let section-spacing-after = {tokens.section_title_spacing_after_pt}pt')
    lines.append(f'#let entry-title-size = {tokens.entry_title_size_pt}pt')
    lines.append(f'#let entry-title-color = rgb("{tokens.entry_title_color}")')
    lines.append(f'#let entry-org-size = {tokens.entry_org_size_pt}pt')
    lines.append(f'#let entry-org-color = rgb("{tokens.entry_org_color}")')
    lines.append(f'#let date-size = {tokens.entry_date_size_pt}pt')
    lines.append(f'#let date-color = rgb("{tokens.entry_date_color}")')
    lines.append(f'#let body-leading = {tokens.body_line_spacing}em')
    lines.append(f'#let bullet-indent = {tokens.bullet_indent_pt}pt')
    lines.append(f'#let body-color = rgb("{tokens.body_color}")')
    lines.append("")

    # Paragraph and list styling
    lines.append("#set par(leading: body-leading)")
    lines.append(f"#set list(indent: {tokens.bullet_indent_pt}pt, spacing: {tokens.bullet_spacing_pt}pt)")
    lines.append("")

    return "\n".join(lines)


def _typst_font_name(reportlab_font: str) -> str:
    mapping = {
        "Helvetica": "Arial",
        "Helvetica-Bold": "Arial",
        "Helvetica-Oblique": "Arial",
        "Times-Roman": "Times New Roman",
        "Times-Bold": "Times New Roman",
        "Times-Italic": "Times New Roman",
        "Times-BoldItalic": "Times New Roman",
        "Courier": "Courier New",
        "Courier-Bold": "Courier New",
        "Courier-Oblique": "Courier New",
        "Arial": "Arial",
        "Arial-Bold": "Arial",
        "Calibri": "Calibri",
        "Garamond": "Garamond",
    }
    return mapping.get(reportlab_font, "Arial")


def _esc(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("\n", " ")
        .replace('"', '\\"')
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("#", "\\#")
        .replace("@", "\\@")
        .replace("$", "\\$")
        .replace("~", "\\~")
        .replace("`", "\\`")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("<", "\\<")
        .replace(">", "\\>")
        .replace("/", "\\/")
        .replace("^", "\\^")
        .replace("|", "\\|")
        .replace("&", "\\&")
        .replace("=", "\\=")
    )


def _render_date_range(entry: Any) -> str:
    if not entry.date_range:
        return ""
    parts = []
    if entry.date_range.start:
        parts.append(_esc(entry.date_range.start))
    if entry.date_range.end:
        parts.append(_esc(entry.date_range.end))
    return " -- ".join(parts) if parts else ""


def _render_header(resume: ResumeData, tokens: ResumeDesignTokens) -> str:
    parts: list[str] = []
    name_font = _typst_font_name(tokens.name_font)
    headline_font = _typst_font_name(tokens.headline_font)
    contact_font = _typst_font_name(tokens.contact_font)

    parts.append("#align(center)[")
    parts.append(f'  #text(font: "{name_font}", size: name-size, weight: "bold", fill: name-color)[{_esc(resume.name)}]')

    if resume.headline:
        parts.append("  #v(2pt)")
        parts.append(f'  #text(font: "{headline_font}", size: headline-size, fill: headline-color)[{_esc(resume.headline)}]')

    # Contact info as centered grid
    contact_items: list[str] = []
    c = resume.contact
    if c.email:
        contact_items.append(_esc(c.email))
    if c.phone:
        contact_items.append(_esc(c.phone))
    if c.location:
        contact_items.append(_esc(c.location))
    if c.linkedin:
        contact_items.append(_esc(c.linkedin))
    if c.website:
        contact_items.append(_esc(c.website))
    if c.github:
        contact_items.append(_esc(c.github))

    if contact_items:
        n = len(contact_items)
        col_spec = ", ".join(["auto"] * n)
        parts.append("  #v(4pt)")
        parts.append(f"  #grid(")
        parts.append(f"    columns: ({col_spec}),")
        parts.append("    column-gutter: 1.5em,")
        for item in contact_items:
            parts.append(f'    align(center)[#text(font: "{contact_font}", size: contact-size, fill: contact-color)[{item}]],')
        parts.append("  )")

    parts.append("]")
    return "\n".join(parts)


def _render_section_title(title: str, tokens: ResumeDesignTokens) -> str:
    section_font = _typst_font_name(tokens.section_title_font)
    lines = [
        "#v(section-spacing-before)",
        f'#text(font: "{section_font}", size: section-size, weight: "bold", fill: section-color)[{_esc(title)}]',
        "#if section-underline [",
        "  #v(1pt)",
        "  #box(width: 100%, height: 0.5pt, fill: section-color)",
        "]",
        "#v(section-spacing-after)",
    ]
    return "\n".join(lines)


def _render_experience_entry(entry: ExperienceEntry, tokens: ResumeDesignTokens) -> str:
    title_font = _typst_font_name(tokens.entry_title_font)
    org_font = _typst_font_name(tokens.entry_org_font)
    date_font = _typst_font_name(tokens.entry_date_font)

    parts: list[str] = []
    parts.append("#block(breakable: false)[")

    # Title + date on same line via grid
    title_text = _esc(entry.title)
    org_text = _esc(entry.organization) if entry.organization else ""
    loc_text = _esc(entry.location) if entry.location else ""
    date_text = _render_date_range(entry)

    org_line = ""
    if org_text and loc_text:
        org_line = f"{org_text} - {loc_text}"
    elif org_text:
        org_line = org_text
    elif loc_text:
        org_line = loc_text

    if date_text:
        parts.append("  #grid(")
        parts.append("    columns: (1fr, auto),")
        parts.append(
            f'    [#text(font: "{title_font}", size: entry-title-size, weight: "bold", '
            f"fill: entry-title-color)[{title_text}]],"
        )
        parts.append(f'    [#text(font: "{date_font}", size: date-size, fill: date-color)[{date_text}]],')
        parts.append("  )")
    else:
        parts.append(
            f'  #text(font: "{title_font}", size: entry-title-size, weight: "bold", '
            f"fill: entry-title-color)[{title_text}]"
        )

    if org_line:
        parts.append(f'  #text(font: "{org_font}", size: entry-org-size, fill: entry-org-color)[{org_line}]')

    if entry.highlights:
        parts.append("  #v(2pt)")
        parts.append(f'  #set text(fill: body-color)')
        for bullet in entry.highlights:
            parts.append(f"  - {_esc(bullet)}")

    parts.append("]")
    return "\n".join(parts)


def _render_education_entry(entry: EducationEntry, tokens: ResumeDesignTokens) -> str:
    title_font = _typst_font_name(tokens.entry_title_font)
    org_font = _typst_font_name(tokens.entry_org_font)
    date_font = _typst_font_name(tokens.entry_date_font)

    parts: list[str] = []
    parts.append("#block(breakable: false)[")

    title_text = _esc(entry.title)
    org_text = _esc(entry.organization) if entry.organization else ""
    date_text = _render_date_range(entry)

    if date_text:
        parts.append("  #grid(")
        parts.append("    columns: (1fr, auto),")
        parts.append(
            f'    [#text(font: "{title_font}", size: entry-title-size, weight: "bold", '
            f"fill: entry-title-color)[{title_text}]],"
        )
        parts.append(f'    [#text(font: "{date_font}", size: date-size, fill: date-color)[{date_text}]],')
        parts.append("  )")
    else:
        parts.append(
            f'  #text(font: "{title_font}", size: entry-title-size, weight: "bold", '
            f"fill: entry-title-color)[{title_text}]"
        )

    if org_text:
        parts.append(f'  #text(font: "{org_font}", size: entry-org-size, fill: entry-org-color)[{org_text}]')

    gpa = getattr(entry, "gpa", None)
    if gpa:
        parts.append(f'  #text(size: {9}pt, fill: body-color)[GPA: {_esc(gpa)}]')

    honors = getattr(entry, "honors", None) or []
    if honors:
        parts.append("  #v(2pt)")
        for h in honors:
            parts.append(f"  - {_esc(h)}")

    parts.append("]")
    return "\n".join(parts)


def _render_publication_entry(entry: Any, tokens: ResumeDesignTokens) -> str:
    title_font = _typst_font_name(tokens.entry_title_font)
    date_font = _typst_font_name(tokens.entry_date_font)

    parts: list[str] = []
    parts.append("#block(breakable: false)[")

    title_text = _esc(entry.title)
    authors = getattr(entry, "authors", None)
    venue = getattr(entry, "venue", None)
    date_text = _render_date_range(entry)

    pub_line = title_text
    if authors:
        pub_line += f". {_esc(authors)}"
    if venue:
        pub_line += f". {_esc(venue)}"

    if date_text:
        parts.append("  #grid(")
        parts.append("    columns: (1fr, auto),")
        parts.append(f'    [#text(font: "{title_font}", weight: "bold", fill: entry-title-color)[{pub_line}]],')
        parts.append(f'    [#text(font: "{date_font}", size: date-size, fill: date-color)[{date_text}]],')
        parts.append("  )")
    else:
        parts.append(f'  #text(font: "{title_font}", weight: "bold", fill: entry-title-color)[{pub_line}]')

    parts.append("]")
    return "\n".join(parts)


def _render_one_line_entry(entry: OneLineEntry) -> str:
    title_text = _esc(entry.title)
    detail = getattr(entry, "detail", None)
    if detail:
        return f"#text(fill: body-color)[{title_text} --- #text(fill: date-color)[{_esc(detail)}]]"
    return f"#text(fill: body-color)[{title_text}]"


def _render_bullet_entry(entry: BulletEntry) -> str:
    parts: list[str] = []
    for bullet in entry.highlights:
        parts.append(f"- {_esc(bullet)}")
    return "\n".join(parts)


def _render_text_entry(entry: TextEntry) -> str:
    return f"#text(fill: body-color)[{_esc(entry.content)}]"


def _build_typst_markup(
    resume: ResumeData,
    tokens: ResumeDesignTokens,
    ats_mode: bool,
) -> str:
    sections: list[str] = []

    # Design tokens header
    sections.append(_tokens_to_typst_header(tokens, ats_mode))

    # Resume header (name, headline, contact)
    sections.append(_render_header(resume, tokens))
    sections.append("#v(8pt)")

    # Content sections
    for section in sorted(resume.sections, key=lambda s: s.order):
        sections.append(_render_section_title(section.title, tokens))

        entry_parts: list[str] = []
        for entry in section.entries:
            etype = entry.entry_type
            if etype == "experience":
                entry_parts.append(_render_experience_entry(entry, tokens))
            elif etype == "education":
                entry_parts.append(_render_education_entry(entry, tokens))
            elif etype == "publication":
                entry_parts.append(_render_publication_entry(entry, tokens))
            elif etype == "one_line":
                entry_parts.append(_render_one_line_entry(entry))
            elif etype == "bullet":
                entry_parts.append(_render_bullet_entry(entry))
            elif etype == "text":
                entry_parts.append(_render_text_entry(entry))
            else:
                # NormalEntry and fallback
                title = getattr(entry, "title", "")
                if title:
                    entry_parts.append(
                        f'#text(weight: "bold", fill: entry-title-color)[{_esc(title)}]'
                    )
                org = getattr(entry, "organization", "")
                if org:
                    entry_parts.append(
                        f"#text(size: entry-org-size, fill: entry-org-color)[{_esc(org)}]"
                    )
                for bullet in getattr(entry, "highlights", []) or []:
                    entry_parts.append(f"- {_esc(bullet)}")

            entry_parts.append("#v(2pt)")

        sections.append("\n".join(entry_parts))

    return "\n\n".join(sections)


def _compile_typst(typst_markup: str, output_path: Path) -> None:
    import typst

    try:
        compiler = typst.Compiler(root=output_path.parent)
        pdf_bytes = compiler.compile(
            input=typst_markup.encode("utf-8"),
            format="pdf",
        )
        output_path.write_bytes(pdf_bytes)
    except typst.TypstError as exc:
        raise OKofficeException(
            "typst_compilation_error",
            f"Typst compilation failed: {exc}",
            recovery_hint="Check resume content for special characters that may need escaping.",
        ) from exc
    except OSError as exc:
        raise OKofficeException(
            "pdf_write_error",
            f"Failed to write PDF to {output_path}: {exc}",
            recovery_hint="Check that the output directory exists and is writable.",
        ) from exc


def render_resume_typst(
    resume: ResumeData,
    tokens: ResumeDesignTokens,
    layout: str,
    ats_mode: bool,
    output_path: str | Path,
    title: str | None,
) -> ToolResult:
    _require_typst()

    output = resolve_output_path(output_path)
    markup = _build_typst_markup(resume, tokens, ats_mode)
    _compile_typst(markup, output)

    return _result_for_created_pdf(
        tool=_TOOL,
        output=output,
        usage={
            "renderer": "typst",
            "resume_name": resume.name,
            "sections": len(resume.sections),
            "layout": layout,
            "ats_mode": ats_mode,
            "design_tokens_preset": tokens.base_theme,
        },
        next_tools=["pdf.inspect.document", "pdf.validation.ats_compliance_check"],
        source_text=markup,
    )
