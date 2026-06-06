"""CSS-only background effects for HTML deck track.

Provides gradient and pattern backgrounds that work without JavaScript,
respecting the CSP policy of script-src 'none'.
"""
from __future__ import annotations

from typing import Any

from okoffice.authoring.models import DesignTokens


def generate_background_css(effect_id: str, tokens: DesignTokens) -> str:
    generators = {
        "gradient_subtle": _gradient_subtle,
        "gradient_mesh": _gradient_mesh,
        "gradient_noise": _gradient_noise,
    }
    gen = generators.get(effect_id)
    if not gen:
        return ""
    return gen(tokens)


def apply_background_to_slide(
    slide_html: str,
    effect_id: str,
    tokens: DesignTokens,
) -> str:
    css = generate_background_css(effect_id, tokens)
    if not css:
        return slide_html
    bg_class = f"bg-{effect_id.replace('_', '-')}"
    if 'class="slide-content' in slide_html:
        slide_html = slide_html.replace(
            'class="slide-content',
            f'class="slide-content {bg_class}',
            1,
        )
    if "</section>" in slide_html:
        slide_html = slide_html.replace(
            "</section>",
            f"<style>{css}</style></section>",
            1,
        )
    return slide_html


def _gradient_subtle(tokens: DesignTokens) -> str:
    primary = tokens.primary_color
    bg = tokens.background_color
    return (
        ".bg-gradient-subtle { "
        f"background: radial-gradient(ellipse at 20% 50%, {primary}11 0%, transparent 50%), "
        f"radial-gradient(ellipse at 80% 50%, {primary}08 0%, transparent 50%), "
        f"{bg}; }}\n"
    )


def _gradient_mesh(tokens: DesignTokens) -> str:
    primary = tokens.primary_color
    accent = tokens.accent_color
    bg = tokens.background_color
    return (
        ".bg-gradient-mesh { "
        f"background: "
        f"radial-gradient(at 10% 20%, {primary}15 0%, transparent 40%), "
        f"radial-gradient(at 80% 30%, {accent}12 0%, transparent 35%), "
        f"radial-gradient(at 50% 80%, {primary}10 0%, transparent 45%), "
        f"radial-gradient(at 90% 70%, {accent}08 0%, transparent 30%), "
        f"{bg}; }}\n"
    )


def _gradient_noise(tokens: DesignTokens) -> str:
    bg = tokens.background_color
    dark = tokens.dark_color
    return (
        ".bg-gradient-noise { "
        f"background-color: {bg}; "
        f"background-image: "
        f"repeating-linear-gradient(45deg, {dark}03 0px, {dark}03 1px, transparent 1px, transparent 4px), "
        f"repeating-linear-gradient(-45deg, {dark}02 0px, {dark}02 1px, transparent 1px, transparent 6px), "
        f"radial-gradient(ellipse at 30% 40%, {bg} 0%, transparent 70%); "
        "}\n"
    )
