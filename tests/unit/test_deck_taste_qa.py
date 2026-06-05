from okoffice.authoring.models import DesignTokens
from okoffice.office.deck_taste_qa import (
    check_8_second_scan,
    check_color_contrast,
    check_slide_consistency,
    check_typography_hierarchy,
    check_whitespace_ratio,
    compute_taste_score,
)


class TestColorContrast:
    def test_good_contrast_passes(self) -> None:
        tokens = DesignTokens(primary_color="#111827", background_color="#FFFFFF")
        result = check_color_contrast(tokens)
        assert result["score"] >= 0.5

    def test_low_contrast_flagged(self) -> None:
        tokens = DesignTokens(primary_color="#CCCCCC", background_color="#FFFFFF")
        result = check_color_contrast(tokens)
        assert len(result["issues"]) > 0


class TestTypographyHierarchy:
    def test_valid_hierarchy_passes(self) -> None:
        tokens = DesignTokens()
        result = check_typography_hierarchy(tokens)
        assert result["score"] == 1.0
        assert not result["issues"]

    def test_heading_not_larger_than_subtitle_fails(self) -> None:
        tokens = DesignTokens(heading_size_px=20, subtitle_size_px=30)
        result = check_typography_hierarchy(tokens)
        assert len(result["issues"]) > 0


class TestWhitespaceRatio:
    def test_normal_padding_passes(self) -> None:
        tokens = DesignTokens()
        result = check_whitespace_ratio(tokens)
        assert result["score"] > 0

    def test_tight_padding_flagged(self) -> None:
        tokens = DesignTokens(slide_padding_px=10)
        result = check_whitespace_ratio(tokens)
        assert len(result["issues"]) > 0


class TestSlideConsistency:
    def test_consistent_tokens_pass(self) -> None:
        tokens = DesignTokens()
        result = check_slide_consistency(tokens)
        assert result["score"] >= 0.8


class TestEightSecondScan:
    def test_large_heading_passes(self) -> None:
        tokens = DesignTokens(heading_size_px=36)
        result = check_8_second_scan(tokens)
        assert result["score"] >= 0.8

    def test_tiny_heading_flagged(self) -> None:
        tokens = DesignTokens(heading_size_px=14)
        result = check_8_second_scan(tokens)
        assert len(result["issues"]) > 0


class TestComputeTasteScore:
    def test_default_tokens_score_well(self) -> None:
        tokens = DesignTokens()
        result = compute_taste_score(tokens)
        assert result["taste_score"] >= 50
        assert "checks" in result
        assert "issues" in result
        assert "passing" in result

    def test_bad_tokens_score_poorly(self) -> None:
        tokens = DesignTokens(
            heading_size_px=14,
            subtitle_size_px=14,
            body_size_px=14,
            primary_color="#CCCCCC",
            background_color="#FFFFFF",
            slide_padding_px=5,
        )
        result = compute_taste_score(tokens)
        assert result["taste_score"] < 80
        assert len(result["issues"]) > 0

    def test_checks_have_all_five_categories(self) -> None:
        tokens = DesignTokens()
        result = compute_taste_score(tokens)
        assert set(result["checks"].keys()) == {
            "color_contrast",
            "typography_hierarchy",
            "whitespace_ratio",
            "slide_consistency",
            "eight_second_scan",
        }

    def test_score_is_between_0_and_100(self) -> None:
        for theme_name in ["business_tech", "board_review", "pitch", "research_brief"]:
            from okoffice.authoring.design import resolve_theme
            tokens = resolve_theme(theme_name)
            result = compute_taste_score(tokens)
            assert 0 <= result["taste_score"] <= 100
