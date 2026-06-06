"""Unit tests for CSS background effects."""
from __future__ import annotations

import pytest

from okoffice.authoring.models import DesignTokens
from okoffice.office.deck_backgrounds import (
    apply_background_to_slide,
    generate_background_css,
)


def _tokens() -> DesignTokens:
    return DesignTokens(
        primary_color="#2563eb",
        accent_color="#7c3aed",
        background_color="#ffffff",
        dark_color="#1e293b",
    )


class TestGenerateBackgroundCSS:
    @pytest.mark.parametrize("effect_id", ["gradient_subtle", "gradient_mesh", "gradient_noise"])
    def test_returns_css_for_known_effects(self, effect_id):
        css = generate_background_css(effect_id, _tokens())
        assert "background" in css

    def test_returns_empty_for_unknown_effect(self):
        assert generate_background_css("nonexistent", _tokens()) == ""

    def test_subtle_uses_primary(self):
        css = generate_background_css("gradient_subtle", _tokens())
        assert "#2563eb" in css

    def test_mesh_uses_accent(self):
        css = generate_background_css("gradient_mesh", _tokens())
        assert "#7c3aed" in css

    def test_noise_uses_dark(self):
        css = generate_background_css("gradient_noise", _tokens())
        assert "#1e293b" in css


class TestApplyBackgroundToSlide:
    def test_applies_class_and_style(self):
        html = '<section><div class="slide-content"><p>hello</p></div></section>'
        result = apply_background_to_slide(html, "gradient_subtle", _tokens())
        assert "bg-gradient-subtle" in result
        assert "<style>" in result

    def test_unknown_effect_returns_original(self):
        html = '<section><div class="slide-content"><p>hello</p></div></section>'
        assert apply_background_to_slide(html, "nonexistent", _tokens()) == html

    def test_preserves_content(self):
        html = '<section><div class="slide-content"><p>hello</p></div></section>'
        result = apply_background_to_slide(html, "gradient_mesh", _tokens())
        assert "<p>hello</p>" in result
