from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from okoffice.authoring.models import DesignTokens


LayoutKind = Literal[
    "cover", "title_only", "title_subtitle", "title_bullets",
    "two_column", "metrics", "comparison", "image_left", "image_right",
    "section_cards", "funnel", "risk_grid", "sources",
    "foreword", "agenda", "section_divider", "insight_cards", "stats", "quote", "process_flow", "cta",
]


class ShapeDef(BaseModel):
    purpose: str
    x: int
    y: int
    cx: int
    cy: int
    css_area: str = ""
    font_role: Literal["heading", "body", "kicker", "notes"] = "body"
    bold: bool = False
    bullet: bool = False


class SlideLayout(BaseModel):
    kind: LayoutKind
    shapes: list[ShapeDef]
    css_grid_template: str = ""


CSS_CLASS_TO_LAYOUT: dict[str, str] = {
    "layout-cover": "cover",
    "layout-title_only": "title_only",
    "layout-title_subtitle": "title_subtitle",
    "layout-title_bullets": "title_bullets",
    "layout-two_column": "two_column",
    "layout-metrics": "metrics",
    "layout-comparison": "comparison",
    "layout-image_left": "image_left",
    "layout-image_right": "image_right",
    "layout-section_cards": "section_cards",
    "layout-funnel": "funnel",
    "layout-risk_grid": "risk_grid",
    "layout-sources": "sources",
    "layout-foreword": "foreword",
    "layout-agenda": "agenda",
    "layout-section_divider": "section_divider",
    "layout-insight_cards": "insight_cards",
    "layout-stats": "stats",
    "layout-quote": "quote",
    "layout-process_flow": "process_flow",
    "layout-cta": "cta",
}


SLIDE_LAYOUTS: dict[str, SlideLayout] = {
    "cover": SlideLayout(
        kind="cover",
        shapes=[
            ShapeDef(purpose="kicker", x=650000, y=520000, cx=10900000, cy=300000, css_area="kicker", font_role="kicker"),
            ShapeDef(purpose="title", x=650000, y=900000, cx=10900000, cy=1400000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="subtitle", x=650000, y=2500000, cx=10900000, cy=500000, css_area="subtitle", font_role="heading"),
        ],
        css_grid_template="kicker title subtitle",
    ),
    "title_only": SlideLayout(
        kind="title_only",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=1400000, cx=10900000, cy=1400000, css_area="title", font_role="heading", bold=True),
        ],
        css_grid_template="title",
    ),
    "title_subtitle": SlideLayout(
        kind="title_subtitle",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=900000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="subtitle", x=650000, y=1700000, cx=10900000, cy=430000, css_area="subtitle", font_role="heading"),
        ],
        css_grid_template="title subtitle",
    ),
    "title_bullets": SlideLayout(
        kind="title_bullets",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="subtitle", x=650000, y=1260000, cx=10900000, cy=430000, css_area="subtitle", font_role="heading"),
            ShapeDef(purpose="bullets", x=900000, y=2050000, cx=10300000, cy=3300000, css_area="bullets", font_role="body", bullet=True),
        ],
        css_grid_template="title subtitle bullets",
    ),
    "two_column": SlideLayout(
        kind="two_column",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="col_left", x=400000, y=1800000, cx=5500000, cy=3800000, css_area="col_left", font_role="body", bullet=True),
            ShapeDef(purpose="col_right", x=6200000, y=1800000, cx=5500000, cy=3800000, css_area="col_right", font_role="body", bullet=True),
        ],
        css_grid_template="title col_left col_right",
    ),
    "metrics": SlideLayout(
        kind="metrics",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="metric_1", x=400000, y=1800000, cx=3500000, cy=2800000, css_area="metric_1", font_role="heading", bold=True),
            ShapeDef(purpose="metric_2", x=4100000, y=1800000, cx=3500000, cy=2800000, css_area="metric_2", font_role="heading", bold=True),
            ShapeDef(purpose="metric_3", x=7800000, y=1800000, cx=3500000, cy=2800000, css_area="metric_3", font_role="heading", bold=True),
        ],
        css_grid_template="title metric_1 metric_2 metric_3",
    ),
    "comparison": SlideLayout(
        kind="comparison",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="col_left_header", x=400000, y=1500000, cx=5500000, cy=400000, css_area="col_left_header", font_role="heading", bold=True),
            ShapeDef(purpose="col_right_header", x=6200000, y=1500000, cx=5500000, cy=400000, css_area="col_right_header", font_role="heading", bold=True),
            ShapeDef(purpose="col_left", x=400000, y=2100000, cx=5500000, cy=3500000, css_area="col_left", font_role="body", bullet=True),
            ShapeDef(purpose="col_right", x=6200000, y=2100000, cx=5500000, cy=3500000, css_area="col_right", font_role="body", bullet=True),
        ],
        css_grid_template="title col_left_header col_right_header col_left col_right",
    ),
    "image_left": SlideLayout(
        kind="image_left",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="image_area", x=400000, y=1500000, cx=5500000, cy=3800000, css_area="image_area", font_role="body"),
            ShapeDef(purpose="text_area", x=6200000, y=1500000, cx=5500000, cy=3800000, css_area="text_area", font_role="body", bullet=True),
        ],
        css_grid_template="title image_area text_area",
    ),
    "image_right": SlideLayout(
        kind="image_right",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="text_area", x=400000, y=1500000, cx=5500000, cy=3800000, css_area="text_area", font_role="body", bullet=True),
            ShapeDef(purpose="image_area", x=6200000, y=1500000, cx=5500000, cy=3800000, css_area="image_area", font_role="body"),
        ],
        css_grid_template="title text_area image_area",
    ),
    "section_cards": SlideLayout(
        kind="section_cards",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="card_1", x=400000, y=1500000, cx=3500000, cy=3800000, css_area="card_1", font_role="body", bullet=True),
            ShapeDef(purpose="card_2", x=4100000, y=1500000, cx=3500000, cy=3800000, css_area="card_2", font_role="body", bullet=True),
            ShapeDef(purpose="card_3", x=7800000, y=1500000, cx=3500000, cy=3800000, css_area="card_3", font_role="body", bullet=True),
        ],
        css_grid_template="title card_1 card_2 card_3",
    ),
    "funnel": SlideLayout(
        kind="funnel",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="stage_1", x=2000000, y=1500000, cx=8000000, cy=700000, css_area="stage_1", font_role="heading", bold=True),
            ShapeDef(purpose="stage_2", x=3000000, y=2300000, cx=6000000, cy=700000, css_area="stage_2", font_role="heading", bold=True),
            ShapeDef(purpose="stage_3", x=4000000, y=3100000, cx=4000000, cy=700000, css_area="stage_3", font_role="heading", bold=True),
            ShapeDef(purpose="stage_4", x=5000000, y=3900000, cx=2000000, cy=700000, css_area="stage_4", font_role="heading", bold=True),
        ],
        css_grid_template="title stage_1 stage_2 stage_3 stage_4",
    ),
    "risk_grid": SlideLayout(
        kind="risk_grid",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="axis_y", x=400000, y=1500000, cx=1500000, cy=4200000, css_area="axis_y", font_role="kicker"),
            ShapeDef(purpose="axis_x", x=2100000, y=5300000, cx=8000000, cy=400000, css_area="axis_x", font_role="kicker"),
            ShapeDef(purpose="grid_cells", x=2100000, y=1500000, cx=8000000, cy=3800000, css_area="grid_cells", font_role="body"),
        ],
        css_grid_template="title axis_y axis_x grid_cells",
    ),
    "sources": SlideLayout(
        kind="sources",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="source_list", x=650000, y=1500000, cx=10900000, cy=4500000, css_area="source_list", font_role="body"),
        ],
        css_grid_template="title source_list",
    ),
    "foreword": SlideLayout(
        kind="foreword",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="subtitle", x=650000, y=1400000, cx=10900000, cy=430000, css_area="subtitle", font_role="heading"),
            ShapeDef(purpose="body_text", x=650000, y=2100000, cx=10900000, cy=3500000, css_area="body_text", font_role="body"),
        ],
        css_grid_template="title subtitle body_text",
    ),
    "agenda": SlideLayout(
        kind="agenda",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="col_left", x=400000, y=1500000, cx=5500000, cy=4000000, css_area="col_left", font_role="body", bullet=True),
            ShapeDef(purpose="col_right", x=6200000, y=1500000, cx=5500000, cy=4000000, css_area="col_right", font_role="body", bullet=True),
        ],
        css_grid_template="title col_left col_right",
    ),
    "section_divider": SlideLayout(
        kind="section_divider",
        shapes=[
            ShapeDef(purpose="kicker", x=650000, y=2200000, cx=10900000, cy=400000, css_area="kicker", font_role="kicker"),
            ShapeDef(purpose="title", x=650000, y=2800000, cx=10900000, cy=1200000, css_area="title", font_role="heading", bold=True),
        ],
        css_grid_template="kicker title",
    ),
    "insight_cards": SlideLayout(
        kind="insight_cards",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="card_1", x=400000, y=1500000, cx=3500000, cy=3800000, css_area="card_1", font_role="body", bullet=True),
            ShapeDef(purpose="card_2", x=4100000, y=1500000, cx=3500000, cy=3800000, css_area="card_2", font_role="body", bullet=True),
            ShapeDef(purpose="card_3", x=7800000, y=1500000, cx=3500000, cy=3800000, css_area="card_3", font_role="body", bullet=True),
        ],
        css_grid_template="title card_1 card_2 card_3",
    ),
    "stats": SlideLayout(
        kind="stats",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="metric_1", x=400000, y=1500000, cx=2600000, cy=3200000, css_area="metric_1", font_role="heading", bold=True),
            ShapeDef(purpose="metric_2", x=3200000, y=1500000, cx=2600000, cy=3200000, css_area="metric_2", font_role="heading", bold=True),
            ShapeDef(purpose="metric_3", x=6000000, y=1500000, cx=2600000, cy=3200000, css_area="metric_3", font_role="heading", bold=True),
            ShapeDef(purpose="metric_4", x=8800000, y=1500000, cx=2600000, cy=3200000, css_area="metric_4", font_role="heading", bold=True),
        ],
        css_grid_template="title metric_1 metric_2 metric_3 metric_4",
    ),
    "quote": SlideLayout(
        kind="quote",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=1800000, cx=10900000, cy=1600000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="subtitle", x=650000, y=3800000, cx=10900000, cy=600000, css_area="subtitle", font_role="body"),
            ShapeDef(purpose="kicker", x=650000, y=4800000, cx=10900000, cy=400000, css_area="kicker", font_role="kicker"),
        ],
        css_grid_template="title subtitle kicker",
    ),
    "process_flow": SlideLayout(
        kind="process_flow",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=520000, cx=10900000, cy=700000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="stage_1", x=400000, y=1500000, cx=2600000, cy=3800000, css_area="stage_1", font_role="body"),
            ShapeDef(purpose="stage_2", x=3200000, y=1500000, cx=2600000, cy=3800000, css_area="stage_2", font_role="body"),
            ShapeDef(purpose="stage_3", x=6000000, y=1500000, cx=2600000, cy=3800000, css_area="stage_3", font_role="body"),
            ShapeDef(purpose="stage_4", x=8800000, y=1500000, cx=2600000, cy=3800000, css_area="stage_4", font_role="body"),
        ],
        css_grid_template="title stage_1 stage_2 stage_3 stage_4",
    ),
    "cta": SlideLayout(
        kind="cta",
        shapes=[
            ShapeDef(purpose="title", x=650000, y=1500000, cx=10900000, cy=1400000, css_area="title", font_role="heading", bold=True),
            ShapeDef(purpose="subtitle", x=650000, y=3200000, cx=10900000, cy=600000, css_area="subtitle", font_role="body"),
            ShapeDef(purpose="body_text", x=650000, y=4200000, cx=10900000, cy=1200000, css_area="body_text", font_role="body"),
        ],
        css_grid_template="title subtitle body_text",
    ),
}


def select_layout(slide: dict[str, Any]) -> SlideLayout:
    explicit = slide.get("layout")
    if explicit and explicit in SLIDE_LAYOUTS:
        return SLIDE_LAYOUTS[explicit]
    css_class = str(slide.get("css_class") or "")
    if css_class:
        for token in css_class.split():
            mapped = CSS_CLASS_TO_LAYOUT.get(token)
            if mapped and mapped in SLIDE_LAYOUTS:
                return SLIDE_LAYOUTS[mapped]
    has_subtitle = bool(slide.get("subtitle"))
    bullets = slide.get("bullets", [])
    metrics = slide.get("metrics", [])
    if metrics and len(metrics) >= 3:
        return SLIDE_LAYOUTS["stats"] if len(metrics) >= 4 else SLIDE_LAYOUTS["metrics"]
    if not bullets:
        if has_subtitle:
            return SLIDE_LAYOUTS["title_subtitle"]
        return SLIDE_LAYOUTS["title_only"]
    if len(bullets) > 6:
        return SLIDE_LAYOUTS["two_column"]
    if len(bullets) > 3:
        return SLIDE_LAYOUTS["insight_cards"]
    return SLIDE_LAYOUTS["title_bullets"]


def layout_to_css(layout: SlideLayout) -> str:
    if not layout.css_grid_template:
        return ""
    col_count = len(layout.css_grid_template.split())
    return (
        f".slide-content.layout-{layout.kind} {{ "
        f"grid-template-areas: \"{layout.css_grid_template}\"; "
        f"grid-template-columns: repeat({col_count}, 1fr); }}"
    )


def layout_to_pptx_shapes(layout: SlideLayout, slide: dict[str, Any], pptx_defaults: dict) -> list[dict]:
    shapes = []
    shape_id = 2
    for shape_def in layout.shapes:
        lines = _shape_lines(shape_def, slide)
        if not lines:
            continue
        font = _font_for_role(shape_def.font_role, pptx_defaults)
        size = _size_for_role(shape_def.font_role, pptx_defaults)
        color = _color_for_role(shape_def.font_role, pptx_defaults)
        shapes.append({
            "shape_id": shape_id,
            "name": shape_def.purpose,
            "x": shape_def.x,
            "y": shape_def.y,
            "cx": shape_def.cx,
            "cy": shape_def.cy,
            "lines": lines,
            "bullet": shape_def.bullet,
            "font": font,
            "size_pt": size,
            "color_hex": color,
            "bold": shape_def.bold,
        })
        shape_id += 1
    return shapes


def _shape_lines(shape: ShapeDef, slide: dict[str, Any]) -> list[str]:
    purpose = shape.purpose
    if purpose == "title":
        return [slide.get("title", "")]
    if purpose == "subtitle":
        sub = slide.get("subtitle", "")
        return [sub] if sub else []
    if purpose == "bullets":
        return list(slide.get("bullets", []))
    if purpose == "kicker":
        return [f"Slide {slide.get('slide_index', 0):02d}"]
    if purpose == "body_text":
        body = slide.get("body", "")
        if body:
            return [body]
        bullets = slide.get("bullets", [])
        return bullets if bullets else []
    if purpose in ("col_left", "text_area", "card_1", "stage_1", "source_list"):
        bullets = slide.get("bullets", [])
        if bullets:
            return bullets[:len(bullets) // 2 + 1] if purpose in ("col_left", "text_area") else bullets[:4]
        return []
    if purpose in ("col_right", "card_2", "stage_2"):
        bullets = slide.get("bullets", [])
        if bullets:
            return bullets[len(bullets) // 2 + 1:] if purpose == "col_right" else bullets[:4]
        return []
    if purpose in ("card_3", "stage_3", "stage_4"):
        bullets = slide.get("bullets", [])
        return bullets[:4] if bullets else []
    if purpose in ("metric_1", "metric_2", "metric_3", "metric_4"):
        metrics = slide.get("metrics", [])
        idx = {"metric_1": 0, "metric_2": 1, "metric_3": 2, "metric_4": 3}.get(purpose, 0)
        if metrics and idx < len(metrics):
            return [str(metrics[idx])]
        return []
    return []


def _font_for_role(role: str, defaults: dict) -> str:
    return defaults.get("heading_font", "Arial") if role == "heading" else defaults.get("body_font", "Arial")


def _size_for_role(role: str, defaults: dict) -> float:
    sizes = {
        "heading": defaults.get("heading_size_pt", 27.0),
        "body": defaults.get("body_size_pt", 12.0),
        "kicker": defaults.get("kicker_size_pt", 8.25),
        "notes": defaults.get("notes_size_pt", 9.0),
    }
    return sizes.get(role, 12.0)


def _color_for_role(role: str, defaults: dict) -> str:
    return defaults.get("primary_color_hex", "2563EB") if role == "heading" else defaults.get("dark_color_hex", "111827")


def tokens_to_css_variables(tokens: DesignTokens) -> dict[str, str]:
    return {
        "--color-primary": tokens.primary_color,
        "--color-accent": tokens.accent_color,
        "--color-warning": tokens.warning_color,
        "--color-bg": tokens.background_color,
        "--color-dark": tokens.dark_color,
        "--font-display": tokens.display_font,
        "--font-heading": tokens.heading_font,
        "--font-body": tokens.body_font,
        "--font-mono": tokens.mono_font,
        "--size-heading": f"{tokens.heading_size_px}px",
        "--size-subtitle": f"{tokens.subtitle_size_px}px",
        "--size-body": f"{tokens.body_size_px}px",
        "--size-caption": f"{tokens.caption_size_px}px",
        "--size-kicker": f"{tokens.kicker_size_px}px",
        "--size-notes": f"{tokens.notes_size_px}px",
        "--line-height": str(tokens.line_height),
        "--line-height-heading": str(tokens.heading_line_height),
        "--slide-padding": f"{tokens.slide_padding_px}px",
        "--slide-gap": f"{tokens.slide_gap_px}px",
    }


def tokens_to_css(tokens: DesignTokens) -> str:
    vars_block = "\n".join(
        f"  {k}: {v};" for k, v in tokens_to_css_variables(tokens).items()
    )
    return f":root {{\n{vars_block}\n}}"


def resolve_font_stack(tokens: DesignTokens, *, heading: bool = False) -> str:
    return tokens.heading_font if heading else tokens.body_font


_PPTX_FONT_MAP: dict[str, str] = {
    "Arial": "Arial",
    "Helvetica": "Helvetica",
    "Georgia": "Georgia",
    "Garamond": "Garamond",
    "Inter": "Inter",
    "serif": "Times New Roman",
    "sans-serif": "Arial",
    "Source Serif Pro": "Times New Roman",
}


def _first_known_font(font_stack: str) -> str:
    for face in font_stack.split(","):
        face = face.strip()
        if face in _PPTX_FONT_MAP:
            return _PPTX_FONT_MAP[face]
        for key, mapped in _PPTX_FONT_MAP.items():
            if key.lower() in face.lower():
                return mapped
    return "Arial"


def tokens_to_pptx_defaults(tokens: DesignTokens) -> dict:
    return {
        "heading_font": _first_known_font(tokens.heading_font),
        "body_font": _first_known_font(tokens.body_font),
        "heading_size_pt": tokens.heading_size_px * 0.75,
        "subtitle_size_pt": tokens.subtitle_size_px * 0.75,
        "body_size_pt": tokens.body_size_px * 0.75,
        "kicker_size_pt": tokens.kicker_size_px * 0.75,
        "notes_size_pt": tokens.notes_size_px * 0.75,
        "primary_color_hex": tokens.primary_color.lstrip("#"),
        "accent_color_hex": tokens.accent_color.lstrip("#"),
        "dark_color_hex": tokens.dark_color.lstrip("#"),
        "background_color_hex": tokens.background_color.lstrip("#"),
    }
