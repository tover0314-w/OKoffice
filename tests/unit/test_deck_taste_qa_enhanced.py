"""Unit tests for enhanced taste QA checks."""
from __future__ import annotations

import pytest

from okoffice.authoring.models import DesignTokens
from okoffice.office.deck_taste_qa import (
    check_content_density,
    check_rhythm_variation,
    check_shadow_restraint,
    check_template_consistency,
    compute_taste_score,
)


def _tokens(**overrides) -> DesignTokens:
    defaults = dict(
        primary_color="#1e293b",
        accent_color="#2563eb",
        background_color="#ffffff",
        dark_color="#0f172a",
        heading_size_px=36,
        subtitle_size_px=24,
        body_size_px=16,
        kicker_size_px=12,
        heading_line_height=1.2,
        line_height=1.6,
        slide_padding_px=48,
        heading_font="Inter",
        body_font="Inter",
        max_bullets_per_slide=6,
        max_cards_per_slide=6,
    )
    defaults.update(overrides)
    return DesignTokens(**defaults)


class TestCheckRhythmVariation:
    def test_perfect_score_with_diverse_layouts(self):
        slides = [
            {"layout": "cover"},
            {"layout": "agenda"},
            {"layout": "text"},
            {"layout": "stats"},
        ]
        result = check_rhythm_variation(slides)
        assert result["score"] >= 0.9
        assert result["issues"] == []

    def test_penalizes_uniform_layouts(self):
        slides = [{"layout": "text"}] * 10
        result = check_rhythm_variation(slides)
        assert result["score"] < 0.5
        assert any("monotonous" in i for i in result["issues"])

    def test_penalizes_long_run(self):
        slides = [{"layout": "text"}] * 6 + [{"layout": "cover"}]
        result = check_rhythm_variation(slides)
        assert any("repeated" in i for i in result["issues"])

    def test_short_deck_gets_perfect_score(self):
        result = check_rhythm_variation([{"layout": "text"}])
        assert result["score"] == 1.0

    def test_empty_slides_gets_perfect_score(self):
        result = check_rhythm_variation([])
        assert result["score"] == 1.0


class TestCheckContentDensity:
    def test_within_limits(self):
        tokens = _tokens()
        slides = [{"bullets": [f"item {i}" for i in range(4)]}]
        result = check_content_density(slides, tokens)
        assert result["score"] == 1.0
        assert result["violations"] == 0

    def test_exceeds_bullet_limit(self):
        tokens = _tokens(max_bullets_per_slide=3)
        slides = [{"bullets": [f"item {i}" for i in range(6)]}]
        result = check_content_density(slides, tokens)
        assert result["violations"] >= 1
        assert result["score"] < 1.0

    def test_exceeds_card_limit(self):
        tokens = _tokens(max_cards_per_slide=3)
        slides = [{"cards": [f"card {i}" for i in range(6)]}]
        result = check_content_density(slides, tokens)
        assert result["violations"] >= 1

    def test_body_string_split(self):
        tokens = _tokens(max_bullets_per_slide=3)
        slides = [{"body": "line1\nline2\nline3\nline4"}]
        result = check_content_density(slides, tokens)
        assert result["violations"] >= 1

    def test_no_bullets_no_violations(self):
        tokens = _tokens()
        slides = [{"title": "Hello"}]
        result = check_content_density(slides, tokens)
        assert result["violations"] == 0


class TestCheckShadowRestraint:
    def test_clean_combo(self):
        tokens = _tokens(shadow_restraint="none", gradient_sophistication="flat")
        result = check_shadow_restraint(tokens)
        assert result["score"] == 1.0

    def test_warns_on_rich_combo(self):
        tokens = _tokens(shadow_restraint="medium", gradient_sophistication="rich")
        result = check_shadow_restraint(tokens)
        assert any("clutter" in i for i in result["issues"])
        assert result["score"] < 0.5

    def test_warns_on_medium_shadow(self):
        tokens = _tokens(shadow_restraint="medium", gradient_sophistication="subtle")
        result = check_shadow_restraint(tokens)
        assert any("medium shadows" in i for i in result["issues"])


class TestCheckTemplateConsistency:
    def test_empty_list_perfect(self):
        result = check_template_consistency([])
        assert result["score"] == 1.0

    def test_two_templates_good(self):
        result = check_template_consistency(["a", "a", "b", "b", "a"])
        assert result["score"] == 1.0

    def test_too_many_templates_penalized(self):
        result = check_template_consistency(["a", "b", "c", "d", "e"])
        assert result["score"] < 1.0
        assert any("distinct templates" in i for i in result["issues"])

    def test_single_template_many_slides(self):
        result = check_template_consistency(["a"] * 8)
        assert any("single template" in i for i in result["issues"])


class TestComputeTasteScoreWithNewChecks:
    def test_includes_new_check_keys(self):
        tokens = _tokens()
        result = compute_taste_score(tokens)
        assert "rhythm_variation" in result["checks"]
        assert "content_density" in result["checks"]
        assert "shadow_restraint" in result["checks"]
        assert "template_consistency" in result["checks"]

    def test_with_slides_and_templates(self):
        tokens = _tokens()
        slides = [
            {"layout": "cover", "bullets": ["a", "b"]},
            {"layout": "text", "bullets": ["c"]},
        ]
        result = compute_taste_score(
            tokens,
            slides=slides,
            used_templates=["cover-minimal", "title-serif"],
        )
        assert result["taste_score"] > 0
        assert result["checks"]["rhythm_variation"]["score"] >= 0.5
        assert result["checks"]["template_consistency"]["score"] == 1.0
