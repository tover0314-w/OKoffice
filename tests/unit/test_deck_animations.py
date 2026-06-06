"""Unit tests for CSS animation system."""
from __future__ import annotations

import pytest

from okoffice.office.deck_animations import (
    apply_animation_to_slide_html,
    generate_animation_css,
    validate_animation_html,
)


class TestGenerateAnimationCSS:
    @pytest.mark.parametrize("recipe", ["cascade", "hero", "quote", "directional", "pipeline"])
    def test_returns_css_for_known_recipes(self, recipe):
        css = generate_animation_css(recipe)
        assert "@keyframes" in css

    def test_returns_empty_for_unknown_recipe(self):
        assert generate_animation_css("nonexistent") == ""

    def test_cascade_respects_item_count(self):
        css4 = generate_animation_css("cascade", item_count=4)
        css2 = generate_animation_css("cascade", item_count=2)
        assert css4.count("nth-child") == 4
        assert css2.count("nth-child") == 2

    def test_pipeline_respects_item_count(self):
        css3 = generate_animation_css("pipeline", item_count=3)
        assert css3.count("nth-child") == 3

    def test_hero_has_slide_left(self):
        css = generate_animation_css("hero")
        assert "heroSlideLeft" in css

    def test_quote_has_mark_scale(self):
        css = generate_animation_css("quote")
        assert "quoteMarkScale" in css

    def test_directional_has_left_and_right(self):
        css = generate_animation_css("directional")
        assert "slideFromLeft" in css
        assert "slideFromRight" in css


class TestApplyAnimationToSlideHtml:
    def test_applies_class_and_style(self):
        html = '<section><div class="slide-content"><p>hello</p></div></section>'
        result = apply_animation_to_slide_html(html, "hero")
        assert "anim-hero" in result
        assert "<style>" in result

    def test_unknown_recipe_returns_original(self):
        html = '<section><div class="slide-content"><p>hello</p></div></section>'
        assert apply_animation_to_slide_html(html, "nonexistent") == html

    def test_preserves_content(self):
        html = '<section><div class="slide-content"><p>hello</p></div></section>'
        result = apply_animation_to_slide_html(html, "cascade", item_count=3)
        assert "<p>hello</p>" in result


class TestValidateAnimationHtml:
    def test_clean_html_passes(self):
        html = "<style>@keyframes fade { from { opacity: 0; } to { opacity: 1; } }</style>"
        assert validate_animation_html(html) == []

    def test_too_many_keyframes(self):
        keyframes = "".join(
            f"@keyframes anim{i} {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}"
            for i in range(25)
        )
        html = f"<style>{keyframes}</style>"
        issues = validate_animation_html(html)
        assert any("Too many" in i for i in issues)

    def test_total_duration_too_long(self):
        long_css = "animation-duration: 3.0s; " * 5
        html = f"<style>{long_css}</style>"
        issues = validate_animation_html(html)
        assert any("too long" in i for i in issues)
