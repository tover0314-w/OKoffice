"""CSS-only animation system for HTML deck track.

Provides 5 animation recipes as CSS @keyframes and animation properties.
All animations are pure CSS (no JavaScript) to respect the CSP policy
of script-src 'none'.
"""
from __future__ import annotations

from typing import Any

RecipeName = str  # cascade | hero | quote | directional | pipeline


def generate_animation_css(
    recipe: RecipeName,
    slide_class: str = "",
    item_count: int = 4,
) -> str:
    generators = {
        "cascade": _cascade_css,
        "hero": _hero_css,
        "quote": _quote_css,
        "directional": _directional_css,
        "pipeline": _pipeline_css,
    }
    gen = generators.get(recipe)
    if not gen:
        return ""
    return gen(slide_class=slide_class, item_count=item_count)


def apply_animation_to_slide_html(
    slide_html: str,
    recipe: RecipeName,
    item_count: int = 4,
) -> str:
    css = generate_animation_css(recipe, item_count=item_count)
    if not css:
        return slide_html
    animated_class = f"anim-{recipe}"
    if 'class="slide-content' in slide_html:
        slide_html = slide_html.replace(
            'class="slide-content',
            f'class="slide-content {animated_class}',
            1,
        )
    if "</section>" in slide_html:
        slide_html = slide_html.replace(
            "</section>",
            f"<style>{css}</style></section>",
            1,
        )
    return slide_html


def validate_animation_html(html_text: str) -> list[str]:
    issues: list[str] = []
    keyframe_count = html_text.count("@keyframes")
    if keyframe_count > 20:
        issues.append(f"Too many animation keyframes: {keyframe_count} (max 20)")
    total_duration_ms = 0
    import re
    for m in re.finditer(r"animation-duration:\s*([\d.]+)s", html_text):
        total_duration_ms += float(m.group(1)) * 1000
    if total_duration_ms > 10000:
        issues.append(f"Total animation duration too long: {total_duration_ms}ms (max 10000ms)")
    return issues


def _cascade_css(*, slide_class: str = "", item_count: int = 4) -> str:
    items_css = ""
    for i in range(item_count):
        delay = i * 150
        items_css += (
            f".anim-cascade .cascade-item:nth-child({i+1}) {{ "
            f"animation: fadeSlideUp 0.5s ease-out {delay}ms both; }}\n"
        )
    return (
        "@keyframes fadeSlideUp {\n"
        "  from { opacity: 0; transform: translateY(16px); }\n"
        "  to { opacity: 1; transform: translateY(0); }\n"
        "}\n"
        f"{items_css}"
        ".anim-cascade .cascade-item { opacity: 0; }\n"
    )


def _hero_css(*, slide_class: str = "", item_count: int = 3) -> str:
    return (
        "@keyframes heroSlideLeft {\n"
        "  from { opacity: 0; transform: translateX(-40px); }\n"
        "  to { opacity: 1; transform: translateX(0); }\n"
        "}\n"
        "@keyframes heroFadeIn {\n"
        "  from { opacity: 0; }\n"
        "  to { opacity: 1; }\n"
        "}\n"
        ".anim-hero h1, .anim-hero .h-hero { "
        "  animation: heroSlideLeft 0.7s ease-out both; }\n"
        ".anim-hero .subtitle, .anim-hero .h-sub { "
        "  animation: heroFadeIn 0.6s ease-out 0.3s both; }\n"
        ".anim-hero .cascade-item { "
        "  animation: heroFadeIn 0.5s ease-out 0.6s both; }\n"
    )


def _quote_css(*, slide_class: str = "", item_count: int = 3) -> str:
    return (
        "@keyframes quoteMarkScale {\n"
        "  from { opacity: 0; transform: scale(0.5); }\n"
        "  to { opacity: 0.3; transform: scale(1); }\n"
        "}\n"
        "@keyframes quoteTextFade {\n"
        "  from { opacity: 0; transform: translateY(12px); }\n"
        "  to { opacity: 1; transform: translateY(0); }\n"
        "}\n"
        "@keyframes attributionSlide {\n"
        "  from { opacity: 0; transform: translateY(8px); }\n"
        "  to { opacity: 1; transform: translateY(0); }\n"
        "}\n"
        ".anim-quote .quote-mark { "
        "  animation: quoteMarkScale 0.6s ease-out both; }\n"
        ".anim-quote .quote-text { "
        "  animation: quoteTextFade 0.7s ease-out 0.2s both; }\n"
        ".anim-quote .attribution { "
        "  animation: attributionSlide 0.5s ease-out 0.8s both; }\n"
    )


def _directional_css(*, slide_class: str = "", item_count: int = 4) -> str:
    return (
        "@keyframes slideFromLeft {\n"
        "  from { opacity: 0; transform: translateX(-30px); }\n"
        "  to { opacity: 1; transform: translateX(0); }\n"
        "}\n"
        "@keyframes slideFromRight {\n"
        "  from { opacity: 0; transform: translateX(30px); }\n"
        "  to { opacity: 1; transform: translateX(0); }\n"
        "}\n"
        "@keyframes dividerReveal {\n"
        "  from { opacity: 0; transform: scaleY(0); }\n"
        "  to { opacity: 1; transform: scaleY(1); }\n"
        "}\n"
        ".anim-directional .col-left { "
        "  animation: slideFromLeft 0.6s ease-out both; }\n"
        ".anim-directional .divider { "
        "  animation: dividerReveal 0.4s ease-out 0.3s both; }\n"
        ".anim-directional .col-right { "
        "  animation: slideFromRight 0.6s ease-out 0.5s both; }\n"
    )


def _pipeline_css(*, slide_class: str = "", item_count: int = 4) -> str:
    steps_css = ""
    for i in range(item_count):
        delay = i * 200
        steps_css += (
            f".anim-pipeline .pipeline-step:nth-child({i+1}) {{ "
            f"animation: pipelineReveal 0.4s ease-out {delay}ms both; }}\n"
        )
    return (
        "@keyframes pipelineReveal {\n"
        "  from { opacity: 0.15; transform: scale(0.95); }\n"
        "  to { opacity: 1; transform: scale(1); }\n"
        "}\n"
        f"{steps_css}"
        ".anim-pipeline .pipeline-step { opacity: 0.15; }\n"
    )
