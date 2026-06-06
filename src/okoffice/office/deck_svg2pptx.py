"""SVG to DrawingML converter for high-fidelity PPTX export.

Converts SVG slides into OOXML DrawingML shapes that produce natively
editable shapes in PowerPoint.  SVG is chosen as the intermediate format
because it shares the same world view as DrawingML: absolute-coordinate
2D vector graphics with positioned elements, gradients, and text.
"""
from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree

from okoffice.authoring.models import DesignTokens, GradientSophistication, ShadowRestraint

EMU_PER_PX = 9525
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

_NAMED_COLORS: dict[str, str] = {
    "black": "000000", "white": "FFFFFF", "red": "FF0000", "green": "008000",
    "blue": "0000FF", "yellow": "FFFF00", "cyan": "00FFFF", "magenta": "FF00FF",
    "gray": "808080", "grey": "808080", "orange": "FFA500", "purple": "800080",
    "navy": "000080", "teal": "008080", "maroon": "800000", "olive": "808000",
    "lime": "00FF00", "aqua": "00FFFF", "fuchsia": "FF00FF", "silver": "C0C0C0",
    "transparent": "000000",
}


@dataclass(frozen=True)
class SVGElement:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: tuple[SVGElement, ...] = ()
    text: str = ""


@dataclass(frozen=True)
class SVGDocument:
    width: float = 1280.0
    height: float = 720.0
    elements: tuple[SVGElement, ...] = ()
    view_box: str = "0 0 1280 720"


@dataclass(frozen=True)
class DrawingMLShape:
    shape_id: int
    xml: str


@dataclass(frozen=True)
class DrawingMLSlide:
    shapes: tuple[DrawingMLShape, ...] = ()
    background_xml: str = ""
    images: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ConvertContext:
    slide_width_emu: int = 12192000
    slide_height_emu: int = 6858000
    svg_width: float = 1280.0
    svg_height: float = 720.0
    next_id: int = 2
    shadow_restraint: ShadowRestraint = "subtle"
    gradient_sophistication: GradientSophistication = "subtle"
    images: tuple[dict[str, Any], ...] = ()


def _scale_x(ctx: ConvertContext) -> float:
    return ctx.slide_width_emu / ctx.svg_width if ctx.svg_width else EMU_PER_PX


def _scale_y(ctx: ConvertContext) -> float:
    return ctx.slide_height_emu / ctx.svg_height if ctx.svg_height else EMU_PER_PX


def px_to_emu_x(px: float, ctx: ConvertContext) -> int:
    return int(px * _scale_x(ctx))


def px_to_emu_y(px: float, ctx: ConvertContext) -> int:
    return int(px * _scale_y(ctx))


def parse_svg(svg_text: str) -> SVGDocument:
    root = ElementTree.fromstring(svg_text)
    vb = root.get("viewBox", f"0 0 {root.get('width', '1280')} {root.get('height', '720')}")
    w = float(root.get("width", "1280"))
    h = float(root.get("height", "720"))
    parts = vb.split()
    svg_w = float(parts[2]) if len(parts) >= 3 else w
    svg_h = float(parts[3]) if len(parts) >= 4 else h
    elements = tuple(_parse_element(child) for child in root)
    return SVGDocument(width=svg_w, height=svg_h, elements=elements, view_box=vb)


def _parse_element(node: ElementTree.Element) -> SVGElement:
    tag = node.tag.replace(f"{{{SVG_NS}}}", "").replace(f"{{{XLINK_NS}}}", "")
    attrs = {k.replace(f"{{{SVG_NS}}}", "").replace(f"{{{XLINK_NS}}}", ""): v for k, v in node.attrib.items()}
    children = tuple(_parse_element(c) for c in node)
    return SVGElement(tag=tag, attrs=attrs, children=children, text=node.text or "")


def convert_svg_slide(
    svg_doc: SVGDocument,
    slide_index: int,
    tokens: DesignTokens | None = None,
) -> DrawingMLSlide:
    ctx = ConvertContext(
        svg_width=svg_doc.width,
        svg_height=svg_doc.height,
        shadow_restraint=tokens.shadow_restraint if tokens else "subtle",
        gradient_sophistication=tokens.gradient_sophistication if tokens else "subtle",
    )
    shapes: list[DrawingMLShape] = []
    shape_id = ctx.next_id
    images: list[dict[str, Any]] = []
    for elem in svg_doc.elements:
        if elem.tag == "defs":
            continue
        ctx = ConvertContext(
            slide_width_emu=ctx.slide_width_emu,
            slide_height_emu=ctx.slide_height_emu,
            svg_width=ctx.svg_width,
            svg_height=ctx.svg_height,
            next_id=shape_id,
            shadow_restraint=ctx.shadow_restraint,
            gradient_sophistication=ctx.gradient_sophistication,
            images=tuple(images),
        )
        result = _convert_element(elem, ctx)
        if result:
            for s in result:
                shapes.append(DrawingMLShape(shape_id=shape_id, xml=s))
                shape_id += 1
        images = list(ctx.images)
    return DrawingMLSlide(shapes=tuple(shapes), images=tuple(images))


def _convert_element(elem: SVGElement, ctx: ConvertContext) -> list[str] | None:
    dispatch = {
        "rect": _convert_rect,
        "circle": _convert_circle,
        "ellipse": _convert_ellipse,
        "line": _convert_line,
        "path": _convert_path,
        "text": _convert_text,
        "image": _convert_image,
        "g": _convert_group,
        "polygon": _convert_polygon,
        "polyline": _convert_polyline,
    }
    handler = dispatch.get(elem.tag)
    if handler:
        return handler(elem, ctx)
    return None


def _parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_transform(transform: str) -> tuple[float, float, float, float]:
    if not transform:
        return 0.0, 0.0, 1.0, 1.0
    tx, ty, sx, sy = 0.0, 0.0, 1.0, 1.0
    m = re.search(r"translate\(\s*([-\d.]+)\s*,?\s*([-\d.]*)\s*\)", transform)
    if m:
        tx, ty = _parse_float(m.group(1)), _parse_float(m.group(2))
    m = re.search(r"scale\(\s*([-\d.]+)\s*,?\s*([-\d.]*)\s*\)", transform)
    if m:
        sx = _parse_float(m.group(1))
        sy = _parse_float(m.group(2)) if m.group(2) else sx
    return tx, ty, sx, sy


def _svg_color_to_hex(color: str) -> str:
    color = color.strip()
    if not color or color == "none" or color == "currentColor":
        return "000000"
    if color.startswith("#"):
        h = color[1:]
        if len(h) == 3:
            return h[0] * 2 + h[1] * 2 + h[2] * 2
        return h.upper()
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
    if m:
        return f"{int(m.group(1)):02X}{int(m.group(2)):02X}{int(m.group(3)):02X}"
    return _NAMED_COLORS.get(color.lower(), "000000")


def _fill_xml(elem: SVGElement, ctx: ConvertContext) -> str:
    fill = elem.attrs.get("fill", "none")
    opacity = _parse_float(elem.attrs.get("fill-opacity", "1.0"), 1.0)
    if fill == "none":
        return "<a:noFill/>"
    hex_color = _svg_color_to_hex(fill)
    if opacity < 1.0:
        pct = int(opacity * 100000)
        return f'<a:solidFill><a:srgbClr val="{hex_color}"><a:alpha val="{ pct }"/></a:srgbClr></a:solidFill>'
    return f'<a:solidFill><a:srgbClr val="{hex_color}"/></a:solidFill>'


def _stroke_xml(elem: SVGElement, ctx: ConvertContext) -> str:
    stroke = elem.attrs.get("stroke", "none")
    if stroke == "none":
        return "<a:ln><a:noFill/></a:ln>"
    hex_color = _svg_color_to_hex(stroke)
    sw = _parse_float(elem.attrs.get("stroke-width", "1"), 1.0)
    w_emu = int(sw * EMU_PER_PX)
    return f'<a:ln w="{w_emu}"><a:solidFill><a:srgbClr val="{hex_color}"/></a:solidFill></a:ln>'


def _xfrm_xml(x: int, y: int, cx: int, cy: int) -> str:
    return f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'


def _xml_escape(value: str) -> str:
    return html.escape(value, quote=True)


# --- Element converters ---

def _convert_rect(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    tx, ty, sx, sy = _parse_transform(elem.attrs.get("transform", ""))
    x = (_parse_float(elem.attrs.get("x", "0")) + tx) * _scale_x(ctx)
    y = (_parse_float(elem.attrs.get("y", "0")) + ty) * _scale_y(ctx)
    w = _parse_float(elem.attrs.get("width", "0")) * _scale_x(ctx) * sx
    h = _parse_float(elem.attrs.get("height", "0")) * _scale_y(ctx) * sy
    if w <= 0 or h <= 0:
        return []
    rx = elem.attrs.get("rx")
    fill = _fill_xml(elem, ctx)
    stroke = _stroke_xml(elem, ctx)
    if rx and _parse_float(rx) > 0:
        geom = f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {int(_parse_float(rx) / _parse_float(elem.attrs.get("width", "100")) * 50000)}"/></a:avLst></a:prstGeom>'
    else:
        geom = '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="rect_{ctx.next_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>{_xfrm_xml(int(x), int(y), int(w), int(h))}{geom}{fill}{stroke}</p:spPr>'
        f'</p:sp>'
    )
    return [xml]


def _convert_circle(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    cx = _parse_float(elem.attrs.get("cx", "0"))
    cy = _parse_float(elem.attrs.get("cy", "0"))
    r = _parse_float(elem.attrs.get("r", "0"))
    if r <= 0:
        return []
    return _make_ellipse(cx - r, cy - r, r * 2, r * 2, elem, ctx)


def _convert_ellipse(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    cx = _parse_float(elem.attrs.get("cx", "0"))
    cy = _parse_float(elem.attrs.get("cy", "0"))
    rx = _parse_float(elem.attrs.get("rx", "0"))
    ry = _parse_float(elem.attrs.get("ry", "0"))
    if rx <= 0 or ry <= 0:
        return []
    return _make_ellipse(cx - rx, cy - ry, rx * 2, ry * 2, elem, ctx)


def _make_ellipse(x: float, y: float, w: float, h: float, elem: SVGElement, ctx: ConvertContext) -> list[str]:
    tx, ty, _, _ = _parse_transform(elem.attrs.get("transform", ""))
    ex = int((x + tx) * _scale_x(ctx))
    ey = int((y + ty) * _scale_y(ctx))
    ew = int(w * _scale_x(ctx))
    eh = int(h * _scale_y(ctx))
    fill = _fill_xml(elem, ctx)
    stroke = _stroke_xml(elem, ctx)
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="oval_{ctx.next_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>{_xfrm_xml(ex, ey, ew, eh)}<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>{fill}{stroke}</p:spPr>'
        f'</p:sp>'
    )
    return [xml]


def _convert_line(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    x1 = _parse_float(elem.attrs.get("x1", "0"))
    y1 = _parse_float(elem.attrs.get("y1", "0"))
    x2 = _parse_float(elem.attrs.get("x2", "0"))
    y2 = _parse_float(elem.attrs.get("y2", "0"))
    min_x, min_y = min(x1, x2), min(y1, y2)
    max_x, max_y = max(x1, x2), max(y1, y2)
    w = max_x - min_x
    h = max_y - min_y
    stroke = elem.attrs.get("stroke", "#000000")
    sw = _parse_float(elem.attrs.get("stroke-width", "1"))
    hex_c = _svg_color_to_hex(stroke)
    w_emu = int(sw * EMU_PER_PX)
    ex = int(min_x * _scale_x(ctx))
    ey = int(min_y * _scale_y(ctx))
    ew = max(int(w * _scale_x(ctx)), w_emu)
    eh = max(int(h * _scale_y(ctx)), w_emu)
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="line_{ctx.next_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>{_xfrm_xml(ex, ey, ew, eh)}<a:prstGeom prst="line"><a:avLst/></a:prstGeom>'
        f'<a:noFill/><a:ln w="{w_emu}"><a:solidFill><a:srgbClr val="{hex_c}"/></a:solidFill></a:ln></p:spPr>'
        f'</p:sp>'
    )
    return [xml]


def _convert_path(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    d = elem.attrs.get("d", "")
    if not d.strip():
        return []
    tx, ty, sx, sy = _parse_transform(elem.attrs.get("transform", ""))
    fill = _fill_xml(elem, ctx)
    stroke = _stroke_xml(elem, ctx)
    path_cmds = _svg_path_to_drawingml(d, tx, ty, sx, sy, ctx)
    if not path_cmds:
        return []
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="path_{ctx.next_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{ctx.slide_width_emu}" cy="{ctx.slide_height_emu}"/></a:xfrm>'
        f'<a:custGeom><a:pathLst><a:w w="0" h="0">{path_cmds}</a:path></a:pathLst></a:custGeom>'
        f'{fill}{stroke}</p:spPr>'
        f'</p:sp>'
    )
    return [xml]


def _svg_path_to_drawingml(d: str, tx: float, ty: float, sx: float, sy: float, ctx: ConvertContext) -> str:
    segments: list[str] = []
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?[\d.]+', d)
    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == 'Z' or cmd == 'z':
            segments.append('<a:close/>')
            continue
        if cmd in ('M', 'L', 'm', 'l', 'H', 'h', 'V', 'v', 'C', 'c', 'S', 's', 'Q', 'q', 'T', 't'):
            coords = _collect_coords(tokens, i)
            if cmd in ('M', 'm', 'L', 'l') and len(coords) >= 2:
                x, y = _apply_transform(coords[0], coords[1], tx, ty, sx, sy)
                ex, ey = int(x * _scale_x(ctx)), int(y * _scale_y(ctx))
                segments.append(f'<a:{ "moveTo" if cmd in ("M", "m") else "lnTo" }><a:pt x="{ex}" y="{ey}"/></a:{"moveTo" if cmd in ("M", "m") else "lnTo"}>')
            elif cmd in ('C', 'c') and len(coords) >= 6:
                pts = []
                for j in range(0, 6, 2):
                    px, py = _apply_transform(coords[j], coords[j+1], tx, ty, sx, sy)
                    pts.append((int(px * _scale_x(ctx)), int(py * _scale_y(ctx))))
                segments.append(f'<a:cubicBezTo><a:pt x="{pts[0][0]}" y="{pts[0][1]}"/><a:pt x="{pts[1][0]}" y="{pts[1][1]}"/><a:pt x="{pts[2][0]}" y="{pts[2][1]}"/></a:cubicBezTo>')
            i += len(coords)
        else:
            break
    return "".join(segments)


def _collect_coords(tokens: list[str], start: int) -> list[float]:
    coords: list[float] = []
    i = start
    while i < len(tokens):
        try:
            coords.append(float(tokens[i]))
            i += 1
        except (ValueError, IndexError):
            break
    return coords


def _apply_transform(x: float, y: float, tx: float, ty: float, sx: float, sy: float) -> tuple[float, float]:
    return x * sx + tx, y * sy + ty


def _convert_text(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    tx, ty, _, _ = _parse_transform(elem.attrs.get("transform", ""))
    x = (_parse_float(elem.attrs.get("x", "0")) + tx) * _scale_x(ctx)
    y = (_parse_float(elem.attrs.get("y", "0")) + ty) * _scale_y(ctx)
    font_size = _parse_float(elem.attrs.get("font-size", "16"), 16)
    fill = elem.attrs.get("fill", "#000000")
    font_family = elem.attrs.get("font-family", "Arial")
    hex_color = _svg_color_to_hex(fill)
    size_pt = int(font_size * 100)
    font_name = font_family.split(",")[0].strip().strip("'\"")
    text = elem.text.strip() if elem.text else ""
    for child in elem.children:
        if child.tag == "tspan" and child.text:
            text += child.text
    if not text:
        return []
    cx = int(ctx.slide_width_emu - x) if x > 0 else ctx.slide_width_emu
    cy = int(font_size * 1.5 * _scale_y(ctx))
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="text_{ctx.next_id}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>{_xfrm_xml(int(x), int(y - cy), cx, cy)}'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>'
        f'<a:p><a:r><a:rPr lang="en-US" sz="{size_pt}" dirty="0">'
        f'<a:latin typeface="{_xml_escape(font_name)}"/>'
        f'<a:solidFill><a:srgbClr val="{hex_color}"/></a:solidFill>'
        f'</a:rPr><a:t>{_xml_escape(text)}</a:t></a:r></a:p>'
        f'</p:txBody></p:sp>'
    )
    return [xml]


def _convert_image(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    href = elem.attrs.get("href") or elem.attrs.get("xlink:href") or ""
    if not href:
        return []
    tx, ty, _, _ = _parse_transform(elem.attrs.get("transform", ""))
    x = int((_parse_float(elem.attrs.get("x", "0")) + tx) * _scale_x(ctx))
    y = int((_parse_float(elem.attrs.get("y", "0")) + ty) * _scale_y(ctx))
    w = int(_parse_float(elem.attrs.get("width", "0")) * _scale_x(ctx))
    h = int(_parse_float(elem.attrs.get("height", "0")) * _scale_y(ctx))
    if w <= 0 or h <= 0:
        return []
    r_id = f"imgR{len(ctx.images) + 1}"
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="image_{ctx.next_id}"/>'
        f'<p:cNvPicPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>{_xfrm_xml(x, y, w, h)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'<a:blipFill><a:blip r:embed="{r_id}"/><a:stretch><a:fillRect/></a:stretch></a:blipFill>'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'</p:sp>'
    )
    return [xml]


def _convert_group(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    results: list[str] = []
    child_id = ctx.next_id
    for child in elem.children:
        child_ctx = ConvertContext(
            slide_width_emu=ctx.slide_width_emu,
            slide_height_emu=ctx.slide_height_emu,
            svg_width=ctx.svg_width,
            svg_height=ctx.svg_height,
            next_id=child_id,
            shadow_restraint=ctx.shadow_restraint,
            gradient_sophistication=ctx.gradient_sophistication,
            images=ctx.images,
        )
        child_result = _convert_element(child, child_ctx)
        if child_result:
            results.extend(child_result)
            child_id += len(child_result)
    return results


def _convert_polygon(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    points_str = elem.attrs.get("points", "")
    return _convert_points_shape(points_str, elem, ctx, closed=True)


def _convert_polyline(elem: SVGElement, ctx: ConvertContext) -> list[str]:
    points_str = elem.attrs.get("points", "")
    return _convert_points_shape(points_str, elem, ctx, closed=False)


def _convert_points_shape(points_str: str, elem: SVGElement, ctx: ConvertContext, closed: bool) -> list[str]:
    if not points_str.strip():
        return []
    pairs = re.findall(r'([-\d.]+)\s*,\s*([-\d.]+)', points_str)
    if len(pairs) < 2:
        return []
    tx, ty, sx, sy = _parse_transform(elem.attrs.get("transform", ""))
    fill = _fill_xml(elem, ctx)
    stroke = _stroke_xml(elem, ctx)
    segments: list[str] = []
    for i, (px_s, py_s) in enumerate(pairs):
        px, py = _apply_transform(_parse_float(px_s), _parse_float(py_s), tx, ty, sx, sy)
        ex, ey = int(px * _scale_x(ctx)), int(py * _scale_y(ctx))
        if i == 0:
            segments.append(f'<a:moveTo><a:pt x="{ex}" y="{ey}"/></a:moveTo>')
        else:
            segments.append(f'<a:lnTo><a:pt x="{ex}" y="{ey}"/></a:lnTo>')
    if closed:
        segments.append('<a:close/>')
    path_xml = "".join(segments)
    xml = (
        f'<p:sp>'
        f'<p:nvSpPr><p:cNvPr id="{ctx.next_id}" name="shape_{ctx.next_id}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{ctx.slide_width_emu}" cy="{ctx.slide_height_emu}"/></a:xfrm>'
        f'<a:custGeom><a:pathLst><a:w w="0" h="0">{path_xml}</a:path></a:pathLst></a:custGeom>'
        f'{fill}{stroke}</p:spPr>'
        f'</p:sp>'
    )
    return [xml]


# --- Shadow and Gradient converters ---

def convert_shadow_from_filter(blur: float, dx: float, dy: float, color: str, ctx: ConvertContext) -> str:
    if ctx.shadow_restraint == "none":
        return ""
    blur_rad = int(blur * EMU_PER_PX * 2)
    max_blur = 50800 if ctx.shadow_restraint == "subtle" else 127000
    blur_rad = min(blur_rad, max_blur)
    dist = int(math.sqrt(dx * dx + dy * dy) * EMU_PER_PX)
    dir_angle = int(math.degrees(math.atan2(dy, dx)) * 60000) % 21600000
    hex_c = _svg_color_to_hex(color)
    return (
        f'<a:effectLst><a:outerShdw blurRad="{blur_rad}" dist="{dist}" dir="{dir_angle}" algn="bl">'
        f'<a:srgbClr val="{hex_c}"><a:alpha val="40000"/></a:srgbClr>'
        f'</a:outerShdw></a:effectLst>'
    )


def convert_gradient_from_svg(stops: list[tuple[float, str, float]], gradient_type: str, angle: float, ctx: ConvertContext) -> str:
    if ctx.gradient_sophistication == "flat":
        return "<a:noFill/>"
    if ctx.gradient_sophistication == "subtle" and len(stops) > 2:
        stops = stops[:2]
    gs_items = []
    for pos, color, opacity in stops:
        hex_c = _svg_color_to_hex(color)
        pct = int(pos * 100000)
        if opacity < 1.0:
            gs_items.append(
                f'<a:gs pos="{pct}"><a:srgbClr val="{hex_c}"><a:alpha val="{int(opacity * 100000)}"/></a:srgbClr></a:gs>'
            )
        else:
            gs_items.append(f'<a:gs pos="{pct}"><a:srgbClr val="{hex_c}"/></a:gs>')
    gs_lst = "".join(gs_items)
    if gradient_type == "radial":
        return f'<a:gradFill><a:gsLst>{gs_lst}</a:gsLst><a:path path="circle"/></a:gradFill>'
    o360 = int(angle * 60000) % 21600000
    return f'<a:gradFill><a:gsLst>{gs_lst}</a:gsLst><a:lin ang="{o360}" scaled="1"/></a:gradFill>'


# --- Slide serialization ---

def drawingml_slide_to_xml(slide: DrawingMLSlide) -> str:
    shapes_xml = "".join(s.xml for s in slide.shapes)
    bg = slide.background_xml
    bg_section = f"<p:bg>{bg}</p:bg>" if bg else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<p:cSld>{bg_section}<p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name="Group"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        f'{shapes_xml}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    )
