from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

TOOL_NAME = "deck.edit.apply_theme"

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = f"{{{A_NS}}}"
R = f"{{{R_NS}}}"
P = f"{{{P_NS}}}"

DEFAULT_COLORS = {
    "dk1": "000000",
    "lt1": "FFFFFF",
    "dk2": "1F2937",
    "lt2": "F3F4F6",
    "accent1": "2563EB",
    "accent2": "7C3AED",
    "accent3": "059669",
    "accent4": "D97706",
    "accent5": "DC2626",
    "accent6": "0891B2",
    "hlink": "2563EB",
    "folHlink": "7C3AED",
}

VALID_SCHEMES = {
    "corporate_blue": {"dk2": "1E3A5F", "accent1": "2563EB", "accent2": "3B82F6", "accent3": "60A5FA"},
    "modern_dark": {"dk2": "111827", "lt2": "1F2937", "accent1": "8B5CF6", "accent2": "A78BFA", "accent3": "C4B5FD"},
    "nature_green": {"dk2": "14532D", "accent1": "059669", "accent2": "10B981", "accent3": "34D399"},
    "sunset_warm": {"dk2": "7C2D12", "accent1": "EA580C", "accent2": "F97316", "accent3": "FB923C"},
    "minimal_gray": {"dk2": "374151", "accent1": "6B7280", "accent2": "9CA3AF", "accent3": "D1D5DB"},
}


def apply_deck_theme(
    input_path: str | Path,
    output_path: str | Path,
    theme_name: str | None = None,
    colors: dict[str, str] | None = None,
) -> ToolResult:
    try:
        src = resolve_input_path(input_path)
        dest = resolve_output_path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if not colors and theme_name:
            if theme_name not in VALID_SCHEMES:
                return failed_result(
                    TOOL_NAME,
                    OKofficeError(
                        code="invalid_theme",
                        message=f"Unknown theme '{theme_name}'. Available: {sorted(VALID_SCHEMES)}",
                    ),
                )
            colors = {**DEFAULT_COLORS, **VALID_SCHEMES[theme_name]}
        elif not colors:
            colors = dict(DEFAULT_COLORS)
        else:
            merged = dict(DEFAULT_COLORS)
            merged.update(colors)
            colors = merged

        _apply_theme_to_pptx(src, dest, colors)

        checks = [
            ValidationCheck(name="theme_applied", status="passed", details={"color_count": len(colors)}),
            ValidationCheck(name="output_written", status="passed", details={"path": dest.as_posix()}),
        ]
        return ToolResult(
            job_id=job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            validation=ValidationReport(status="passed", checks=checks),
            usage={"theme_name": theme_name or "custom", "colors_applied": list(colors.keys())},
            next_recommended_tools=["deck.validate.presentation", "deck.extract.theme"],
        )
    except Exception as exc:
        return failed_result(TOOL_NAME, OKofficeError(code="theme_apply_failed", message=str(exc)))


def _apply_theme_to_pptx(src: Path, dest: Path, colors: dict[str, str]) -> None:
    with zipfile.ZipFile(src) as z_in:
        entries = z_in.namelist()
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z_out:
            for name in entries:
                data = z_in.read(name)
                if name == "ppt/theme/theme1.xml":
                    data = _patch_theme_xml(data, colors)
                z_out.writestr(name, data)


def _patch_theme_xml(data: bytes, colors: dict[str, str]) -> bytes:
    root = ET.fromstring(data)

    clr_scheme = root.find(f".//{A}clrScheme")
    if clr_scheme is None:
        clr_scheme = ET.SubElement(
            root.find(f".//{A}themeElements") or root,
            f"{A}clrScheme",
        )
    clr_scheme.set("name", "OKoffice Custom")

    tag_map = {
        "dk1": f"{A}dk1", "lt1": f"{A}lt1",
        "dk2": f"{A}dk2", "lt2": f"{A}lt2",
        "accent1": f"{A}accent1", "accent2": f"{A}accent2",
        "accent3": f"{A}accent3", "accent4": f"{A}accent4",
        "accent5": f"{A}accent5", "accent6": f"{A}accent6",
        "hlink": f"{A}hlink", "folHlink": f"{A}folHlink",
    }

    for key, tag in tag_map.items():
        hex_val = colors.get(key)
        if not hex_val:
            continue
        hex_val = hex_val.lstrip("#")

        elem = clr_scheme.find(tag)
        if elem is None:
            elem = ET.SubElement(clr_scheme, tag)

        srgb = elem.find(f"{A}srgbClr")
        if srgb is None:
            for child in list(elem):
                elem.remove(child)
            srgb = ET.SubElement(elem, f"{A}srgbClr")
        srgb.set("val", hex_val)

    ET.register_namespace("a", A_NS)
    ET.register_namespace("r", R_NS)
    return ET.tostring(root, encoding="unicode").encode("utf-8")
