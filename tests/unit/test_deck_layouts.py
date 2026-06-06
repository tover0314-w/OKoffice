import pytest

from okoffice.office.deck_themes import (
    SLIDE_LAYOUTS,
    SlideLayout,
    layout_to_css,
    layout_to_pptx_shapes,
    select_layout,
)


class TestSlideLayouts:
    def test_all_layouts_have_required_fields(self) -> None:
        for name, layout in SLIDE_LAYOUTS.items():
            assert layout.kind == name
            assert len(layout.shapes) > 0
            for shape in layout.shapes:
                assert shape.purpose
                assert shape.cx > 0
                assert shape.cy > 0

    def test_layout_count(self) -> None:
        assert len(SLIDE_LAYOUTS) == 21

    def test_cover_layout_has_kicker_title_subtitle(self) -> None:
        cover = SLIDE_LAYOUTS["cover"]
        purposes = [s.purpose for s in cover.shapes]
        assert "kicker" in purposes
        assert "title" in purposes
        assert "subtitle" in purposes

    def test_title_bullets_has_three_shapes(self) -> None:
        tb = SLIDE_LAYOUTS["title_bullets"]
        assert len(tb.shapes) == 3
        assert tb.shapes[2].bullet is True

    def test_metrics_layout_has_three_metric_slots(self) -> None:
        metrics = SLIDE_LAYOUTS["metrics"]
        metric_purposes = [s.purpose for s in metrics.shapes if s.purpose.startswith("metric_")]
        assert len(metric_purposes) == 3

    def test_two_column_layout_has_col_left_and_right(self) -> None:
        two_col = SLIDE_LAYOUTS["two_column"]
        purposes = [s.purpose for s in two_col.shapes]
        assert "col_left" in purposes
        assert "col_right" in purposes


class TestSelectLayout:
    def test_explicit_layout_name(self) -> None:
        slide = {"title": "X", "layout": "cover"}
        assert select_layout(slide).kind == "cover"

    def test_title_only_when_no_bullets_no_subtitle(self) -> None:
        slide = {"title": "X"}
        assert select_layout(slide).kind == "title_only"

    def test_title_subtitle_when_no_bullets(self) -> None:
        slide = {"title": "X", "subtitle": "Y"}
        assert select_layout(slide).kind == "title_subtitle"

    def test_title_bullets_when_bullets_present(self) -> None:
        slide = {"title": "X", "bullets": ["a", "b"]}
        assert select_layout(slide).kind == "title_bullets"

    def test_unknown_layout_falls_back(self) -> None:
        slide = {"title": "X", "layout": "nonexistent"}
        assert select_layout(slide).kind in ("title_only", "title_bullets", "title_subtitle")


class TestLayoutToCss:
    def test_produces_grid_template_areas(self) -> None:
        layout = SLIDE_LAYOUTS["title_bullets"]
        css = layout_to_css(layout)
        assert "grid-template-areas" in css
        assert "title" in css

    def test_empty_grid_returns_empty_string(self) -> None:
        layout = SlideLayout(kind="cover", shapes=[], css_grid_template="")
        assert layout_to_css(layout) == ""


class TestLayoutToPptxShapes:
    DEFAULTS = {
        "heading_font": "Arial",
        "body_font": "Arial",
        "heading_size_pt": 27.0,
        "body_size_pt": 12.0,
        "kicker_size_pt": 8.25,
        "notes_size_pt": 9.0,
        "primary_color_hex": "2563EB",
        "dark_color_hex": "111827",
    }

    def test_title_bullets_produces_shapes(self) -> None:
        slide = {"title": "Hello", "subtitle": "World", "bullets": ["a", "b", "c"]}
        shapes = layout_to_pptx_shapes(SLIDE_LAYOUTS["title_bullets"], slide, self.DEFAULTS)
        assert len(shapes) == 3
        assert shapes[0]["name"] == "title"
        assert shapes[0]["bold"] is True

    def test_shape_font_role_maps_to_size(self) -> None:
        slide = {"title": "Hello", "subtitle": "World", "bullets": ["a"]}
        shapes = layout_to_pptx_shapes(SLIDE_LAYOUTS["title_bullets"], slide, self.DEFAULTS)
        title_shape = next(s for s in shapes if s["name"] == "title")
        bullet_shape = next(s for s in shapes if s["name"] == "bullets")
        assert title_shape["size_pt"] > bullet_shape["size_pt"]

    def test_empty_slide_produces_minimal_shapes(self) -> None:
        slide = {"title": "Only Title"}
        shapes = layout_to_pptx_shapes(SLIDE_LAYOUTS["title_only"], slide, self.DEFAULTS)
        assert len(shapes) == 1
        assert shapes[0]["lines"] == ["Only Title"]
