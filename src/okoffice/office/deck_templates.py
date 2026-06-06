"""Template index and loader for deck generation.

Loads template metadata from a JSON index and provides template
selection, loading, and preview utilities.  Templates can target
either the HTML track, the SVG track, or both.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from okoffice.authoring.models import TemplateMetadata

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
_INDEX_PATH = _TEMPLATES_DIR / "index.json"
_HTML_DIR = _TEMPLATES_DIR / "html"
_SVG_DIR = _TEMPLATES_DIR / "svg"


@lru_cache(maxsize=1)
def load_template_index() -> list[TemplateMetadata]:
    if not _INDEX_PATH.exists():
        return []
    with open(_INDEX_PATH, encoding="utf-8") as f:
        raw: list[dict[str, Any]] = json.load(f)
    return [TemplateMetadata.model_validate(item) for item in raw]


def select_template(
    metadata: list[TemplateMetadata],
    *,
    mood: str | None = None,
    tone: str | None = None,
    formality: str | None = None,
    density: str | None = None,
    best_for: str | None = None,
    template_id: str | None = None,
) -> TemplateMetadata | None:
    if template_id:
        for m in metadata:
            if m.template_id == template_id:
                return m
        return None
    if not metadata:
        return None
    scored: list[tuple[int, TemplateMetadata]] = []
    for m in metadata:
        score = 0
        if mood and mood.lower() in [x.lower() for x in m.mood]:
            score += 3
        if tone and tone.lower() in [x.lower() for x in m.tone]:
            score += 3
        if formality and m.formality == formality:
            score += 2
        if density and m.density == density:
            score += 2
        if best_for and best_for.lower() in [x.lower() for x in m.best_for]:
            score += 2
        scored.append((score, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored[0][0] > 0 else metadata[0]


def load_html_template(template_id: str) -> str | None:
    path = _HTML_DIR / f"{template_id}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def load_svg_template(template_id: str) -> str | None:
    path = _SVG_DIR / f"{template_id}.svg"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def preview_template_ids() -> list[str]:
    metadata = load_template_index()
    return [m.template_id for m in metadata if m.track in ("html", "both")]


def render_template_slide(
    template_id: str,
    slide_data: dict[str, Any],
    tokens: Any,
) -> str:
    html_template = load_html_template(template_id)
    if not html_template:
        return ""
    replacements = {
        "{{title}}": str(slide_data.get("title", "")),
        "{{subtitle}}": str(slide_data.get("subtitle", "")),
        "{{body}}": str(slide_data.get("body", "")),
        "{{kicker}}": str(slide_data.get("kicker", "")),
    }
    bullets = slide_data.get("bullets", [])
    if isinstance(bullets, list):
        bullet_html = "".join(f"<li>{_esc(b)}</li>" for b in bullets)
        replacements["{{bullets}}"] = f"<ul>{bullet_html}</ul>"
    else:
        replacements["{{bullets}}"] = ""
    result = html_template
    for key, value in replacements.items():
        result = result.replace(key, value)
    tokens_css = _tokens_to_css_vars(tokens) if tokens else ""
    if tokens_css and "<style>" in result:
        result = result.replace("<style>", f"<style>:root{{{tokens_css}}}", 1)
    return result


def generate_template_previews(
    *,
    mood: str | None = None,
    tone: str | None = None,
    count: int = 3,
) -> list[dict[str, Any]]:
    metadata = load_template_index()
    candidates: list[TemplateMetadata] = []
    for m in metadata:
        if mood and mood.lower() not in [x.lower() for x in m.mood]:
            continue
        if tone and tone.lower() not in [x.lower() for x in m.tone]:
            continue
        candidates.append(m)
    if not candidates:
        candidates = metadata
    candidates = candidates[:count]
    previews: list[dict[str, Any]] = []
    for m in candidates:
        html_content = load_html_template(m.template_id)
        if html_content:
            previews.append({
                "template_id": m.template_id,
                "name": m.name,
                "html": html_content,
            })
    return previews


def _esc(text: str) -> str:
    import html
    return html.escape(str(text), quote=True)


def _tokens_to_css_vars(tokens: Any) -> str:
    pairs = []
    for attr in ("primary_color", "accent_color", "warning_color", "background_color", "dark_color"):
        val = getattr(tokens, attr, None)
        if val:
            name = attr.replace("_color", "")
            pairs.append(f"--color-{name}:{val};")
    for attr in ("heading_font", "body_font", "display_font", "mono_font"):
        val = getattr(tokens, attr, None)
        if val:
            name = attr.replace("_font", "")
            pairs.append(f"--font-{name}:{val};")
    return "".join(pairs)
