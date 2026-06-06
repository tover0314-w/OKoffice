"""Unit tests for the SVG to DrawingML converter."""
from __future__ import annotations

import pytest

from okoffice.office.deck_svg2pptx import (
    ConvertContext,
    DrawingMLSlide,
    SVGDocument,
    SVGElement,
    convert_gradient_from_svg,
    convert_shadow_from_filter,
    convert_svg_slide,
    drawingml_slide_to_xml,
    parse_svg,
    px_to_emu_x,
    px_to_emu_y,
    _svg_color_to_hex,
)


def _ctx(**overrides) -> ConvertContext:
    defaults = {"svg_width": 1280.0, "svg_height": 720.0}
    defaults.update(overrides)
    return ConvertContext(**defaults)


class TestColorConversion:
    def test_hex_6_digit(self):
        assert _svg_color_to_hex("#2563EB") == "2563EB"

    def test_hex_3_digit(self):
        assert _svg_color_to_hex("#F00") == "FF0000"

    def test_named_color(self):
        assert _svg_color_to_hex("red") == "FF0000"

    def test_rgb_functional(self):
        assert _svg_color_to_hex("rgb(255, 128, 0)") == "FF8000"

    def test_none_returns_black(self):
        assert _svg_color_to_hex("none") == "000000"

    def test_empty_returns_black(self):
        assert _svg_color_to_hex("") == "000000"


class TestEmuConversion:
    def test_px_to_emu_x(self):
        ctx = _ctx()
        result = px_to_emu_x(1280.0, ctx)
        assert result == 12192000  # full slide width

    def test_px_to_emu_y(self):
        ctx = _ctx()
        result = px_to_emu_y(720.0, ctx)
        assert result == 6858000  # full slide height

    def test_half_width(self):
        ctx = _ctx()
        result = px_to_emu_x(640.0, ctx)
        assert result == 6096000


class TestParseSvg:
    def test_simple_rect(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect x="10" y="20" width="200" height="100" fill="#FF0000"/></svg>'
        doc = parse_svg(svg)
        assert doc.width == 1280.0
        assert doc.height == 720.0
        assert len(doc.elements) == 1
        assert doc.elements[0].tag == "rect"
        assert doc.elements[0].attrs["fill"] == "#FF0000"

    def test_nested_group(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><g><rect x="0" y="0" width="100" height="100"/></g></svg>'
        doc = parse_svg(svg)
        assert len(doc.elements) == 1
        assert doc.elements[0].tag == "g"
        assert len(doc.elements[0].children) == 1

    def test_text_element(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><text x="50" y="100" font-size="24">Hello</text></svg>'
        doc = parse_svg(svg)
        assert doc.elements[0].tag == "text"
        assert doc.elements[0].text == "Hello"


class TestConvertRect:
    def test_produces_shape_xml(self):
        elem = SVGElement(tag="rect", attrs={"x": "10", "y": "20", "width": "200", "height": "100", "fill": "#FF0000"})
        from okoffice.office.deck_svg2pptx import _convert_rect
        result = _convert_rect(elem, _ctx())
        assert len(result) == 1
        assert "rect" in result[0]
        assert "FF0000" in result[0]

    def test_zero_size_returns_empty(self):
        elem = SVGElement(tag="rect", attrs={"x": "10", "y": "20", "width": "0", "height": "0"})
        from okoffice.office.deck_svg2pptx import _convert_rect
        result = _convert_rect(elem, _ctx())
        assert result == []


class TestConvertCircle:
    def test_produces_ellipse_shape(self):
        elem = SVGElement(tag="circle", attrs={"cx": "100", "cy": "100", "r": "50", "fill": "#00FF00"})
        from okoffice.office.deck_svg2pptx import _convert_circle
        result = _convert_circle(elem, _ctx())
        assert len(result) == 1
        assert "ellipse" in result[0]


class TestConvertText:
    def test_produces_text_shape(self):
        elem = SVGElement(tag="text", attrs={"x": "50", "y": "100", "font-size": "24", "fill": "#000000"}, text="Hello World")
        from okoffice.office.deck_svg2pptx import _convert_text
        result = _convert_text(elem, _ctx())
        assert len(result) == 1
        assert "Hello World" in result[0]
        assert "txBody" in result[0]

    def test_empty_text_returns_empty(self):
        elem = SVGElement(tag="text", attrs={"x": "50", "y": "100"}, text="")
        from okoffice.office.deck_svg2pptx import _convert_text
        result = _convert_text(elem, _ctx())
        assert result == []


class TestConvertLine:
    def test_produces_line_shape(self):
        elem = SVGElement(tag="line", attrs={"x1": "0", "y1": "0", "x2": "100", "y2": "100", "stroke": "#333"})
        from okoffice.office.deck_svg2pptx import _convert_line
        result = _convert_line(elem, _ctx())
        assert len(result) == 1
        assert "line" in result[0]


class TestConvertPath:
    def test_simple_moveto_lineto(self):
        elem = SVGElement(tag="path", attrs={"d": "M 10 10 L 100 100", "fill": "none", "stroke": "#000"})
        from okoffice.office.deck_svg2pptx import _convert_path
        result = _convert_path(elem, _ctx())
        assert len(result) == 1
        assert "custGeom" in result[0]

    def test_empty_path_returns_empty(self):
        elem = SVGElement(tag="path", attrs={"d": ""})
        from okoffice.office.deck_svg2pptx import _convert_path
        result = _convert_path(elem, _ctx())
        assert result == []


class TestConvertGroup:
    def test_group_recursion(self):
        child = SVGElement(tag="rect", attrs={"x": "0", "y": "0", "width": "100", "height": "100", "fill": "#F00"})
        group = SVGElement(tag="g", attrs={}, children=(child,))
        from okoffice.office.deck_svg2pptx import _convert_group
        result = _convert_group(group, _ctx())
        assert len(result) == 1


class TestConvertSlide:
    def test_full_slide_conversion(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><rect x="0" y="0" width="1280" height="720" fill="#F0F0F0"/><text x="100" y="200" font-size="36">Title</text></svg>'
        doc = parse_svg(svg)
        slide = convert_svg_slide(doc, 1)
        assert isinstance(slide, DrawingMLSlide)
        assert len(slide.shapes) == 2

    def test_empty_slide(self):
        doc = SVGDocument()
        slide = convert_svg_slide(doc, 1)
        assert len(slide.shapes) == 0


class TestDrawingmlSlideToXml:
    def test_produces_valid_xml(self):
        from okoffice.office.deck_svg2pptx import DrawingMLShape
        shapes = (DrawingMLShape(shape_id=2, xml='<p:sp><p:nvSpPr><p:cNvPr id="2" name="test"/></p:nvSpPr></p:sp>'),)
        slide = DrawingMLSlide(shapes=shapes)
        xml = drawingml_slide_to_xml(slide)
        assert '<?xml version="1.0"' in xml
        assert "p:sld" in xml
        assert "spTree" in xml

    def test_empty_slide_xml(self):
        slide = DrawingMLSlide()
        xml = drawingml_slide_to_xml(slide)
        assert "p:sld" in xml


class TestShadowConversion:
    def test_subtle_shadow(self):
        ctx = _ctx(shadow_restraint="subtle")
        result = convert_shadow_from_filter(4.0, 2.0, 2.0, "#000000", ctx)
        assert "outerShdw" in result

    def test_none_restraint_produces_no_shadow(self):
        ctx = _ctx(shadow_restraint="none")
        result = convert_shadow_from_filter(4.0, 2.0, 2.0, "#000000", ctx)
        assert result == ""


class TestGradientConversion:
    def test_subtle_gradient(self):
        ctx = _ctx(gradient_sophistication="subtle")
        stops = [(0.0, "#FF0000", 1.0), (1.0, "#0000FF", 1.0)]
        result = convert_gradient_from_svg(stops, "linear", 90.0, ctx)
        assert "gradFill" in result

    def test_flat_produces_no_fill(self):
        ctx = _ctx(gradient_sophistication="flat")
        stops = [(0.0, "#FF0000", 1.0), (1.0, "#0000FF", 1.0)]
        result = convert_gradient_from_svg(stops, "linear", 90.0, ctx)
        assert "noFill" in result
