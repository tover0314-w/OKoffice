from okoffice.authoring.design import PRESETS, resolve_theme
from okoffice.authoring.models import DesignTokens
from okoffice.office.deck_themes import (
    resolve_font_stack,
    tokens_to_css,
    tokens_to_css_variables,
    tokens_to_pptx_defaults,
)


def test_tokens_to_css_variables_returns_all_vars() -> None:
    tokens = DesignTokens()
    variables = tokens_to_css_variables(tokens)
    assert variables["--color-primary"] == "#2563EB"
    assert variables["--color-accent"] == "#0F766E"
    assert variables["--font-heading"] == tokens.heading_font
    assert variables["--font-body"] == tokens.body_font
    assert variables["--size-heading"] == "36px"
    assert variables["--size-subtitle"] == "22px"
    assert variables["--size-body"] == "16px"
    assert variables["--slide-padding"] == "48px"
    assert variables["--slide-gap"] == "28px"


def test_tokens_to_css_produces_root_block() -> None:
    tokens = DesignTokens()
    css = tokens_to_css(tokens)
    assert css.startswith(":root {")
    assert "--color-primary: #2563EB;" in css
    assert "--size-heading: 36px;" in css


def test_resolve_font_stack_heading_vs_body() -> None:
    tokens = DesignTokens(heading_font="Georgia, serif", body_font="Arial, sans-serif")
    assert resolve_font_stack(tokens, heading=True) == "Georgia, serif"
    assert resolve_font_stack(tokens, heading=False) == "Arial, sans-serif"


def test_tokens_to_pptx_defaults_maps_fonts() -> None:
    tokens = DesignTokens(heading_font="Georgia, serif", body_font="Arial, sans-serif")
    defaults = tokens_to_pptx_defaults(tokens)
    assert defaults["heading_font"] == "Georgia"
    assert defaults["body_font"] == "Arial"
    assert defaults["heading_size_pt"] == tokens.heading_size_px * 0.75
    assert defaults["primary_color_hex"] == "2563EB"
    assert defaults["dark_color_hex"] == "111827"


def test_tokens_to_pptx_defaults_falls_back_to_arial() -> None:
    tokens = DesignTokens(heading_font="Noto Sans CJK SC, UnknownFont, sans-serif")
    defaults = tokens_to_pptx_defaults(tokens)
    assert defaults["heading_font"] == "Arial"


def test_resolve_theme_returns_preset() -> None:
    tokens = resolve_theme("board_review")
    assert tokens.theme == "board_review"
    assert tokens.primary_color == "#1E3A5F"


def test_resolve_theme_falls_back_to_business_tech() -> None:
    tokens = resolve_theme("nonexistent")
    assert tokens.theme == "business_tech"


def test_design_tokens_extended_fields_validate() -> None:
    tokens = DesignTokens(heading_size_px=48, subtitle_size_px=28, line_height=1.6)
    assert tokens.heading_size_px == 48
    assert tokens.subtitle_size_px == 28
    assert tokens.line_height == 1.6


def test_design_tokens_rejects_invalid_font_size() -> None:
    import pytest

    with pytest.raises(ValueError):
        DesignTokens(heading_size_px=2)
    with pytest.raises(ValueError):
        DesignTokens(body_size_px=200)


def test_design_tokens_rejects_invalid_line_height() -> None:
    import pytest

    with pytest.raises(ValueError):
        DesignTokens(line_height=0.5)
    with pytest.raises(ValueError):
        DesignTokens(heading_line_height=4.0)


def test_preset_themes_have_consistent_fields() -> None:
    for name, preset in PRESETS.items():
        assert preset.theme == name, f"Preset {name} has theme={preset.theme}"
        assert preset.primary_color.startswith("#"), f"Preset {name} primary_color invalid"
        assert preset.heading_size_px >= 6, f"Preset {name} heading_size_px too small"
