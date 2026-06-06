from __future__ import annotations

from pathlib import Path
from typing import Any

from okoffice.office.deck import _deck_inventory, _themes
from okoffice.office.inspect import inspect_office_file
from okoffice.office.ooxml import DECK_NS, read_xml, zip_names
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport

EXTRACT_TEXT_TOOL = "deck.extract.text"
EXTRACT_NOTES_TOOL = "deck.extract.notes"
EXTRACT_SHAPES_TOOL = "deck.extract.shapes"
EXTRACT_MEDIA_TOOL = "deck.extract.media"
EXTRACT_CHARTS_TOOL = "deck.extract.charts"
EXTRACT_THEME_TOOL = "deck.extract.theme"
PRESENTATION_PART = "ppt/presentation.xml"


def _preflight(path: str | Path, tool: str) -> tuple[Path, Any, Any] | ToolResult:
    preflight = inspect_office_file(Path(path))
    if preflight.status == "failed":
        return failed_result(
            tool,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Preflight failed."),
        )
    if preflight.usage["format"]["detected_format"] != "pptx":
        return failed_result(
            tool,
            OKofficeError(
                code="unsupported_file_type",
                message=f"{tool} requires a PPTX file.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )
    source_path = Path(preflight.usage["file"]["path"])
    presentation_root = read_xml(source_path, PRESENTATION_PART)
    if presentation_root is None:
        return failed_result(
            tool,
            OKofficeError(
                code="unsupported_file_type",
                message=f"{tool} requires {PRESENTATION_PART} in the package.",
            ),
        )
    return source_path, presentation_root, preflight


def _inventory(path: str | Path, tool: str) -> tuple[dict[str, Any], Path] | ToolResult:
    result = _preflight(path, tool)
    if isinstance(result, ToolResult):
        return result
    source_path, presentation_root, preflight = result
    names = zip_names(source_path)
    inventory = _deck_inventory(source_path, names, presentation_root)
    return inventory, source_path


# -- 1. deck.extract.text -----------------------------------------------------

def extract_deck_text(path: str | Path) -> ToolResult:
    result = _inventory(path, EXTRACT_TEXT_TOOL)
    if isinstance(result, ToolResult):
        return result
    inventory, source_path = result

    slides = inventory["slides"]
    text_items: list[dict[str, Any]] = []
    for slide in slides:
        text_items.append({
            "slide_number": slide["slide_number"],
            "text": slide["text"],
            "locator": slide["locator"],
        })

    full_text = "\n".join(item["text"] for item in text_items if item["text"])
    character_count = len(full_text)

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_TEXT_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="text_extracted",
                    status="passed",
                    details={"slide_count": len(slides), "character_count": character_count},
                ),
            ],
        ),
        usage={
            "summary": {"slide_count": len(slides), "character_count": character_count},
            "slides": text_items,
        },
        next_recommended_tools=[
            "deck.extract.shapes",
            "deck.extract.notes",
            "office.context.build_packet",
        ],
    )


# -- 2. deck.extract.notes ----------------------------------------------------

def extract_deck_notes(path: str | Path) -> ToolResult:
    result = _inventory(path, EXTRACT_NOTES_TOOL)
    if isinstance(result, ToolResult):
        return result
    inventory, source_path = result

    notes = inventory["notes"]
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_NOTES_TOOL,
        validation=ValidationReport(
            status="warning" if not notes else "passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="notes_extracted",
                    status="passed" if notes else "warning",
                    details={"notes_count": len(notes)},
                ),
            ],
            warnings=[] if notes else ["No speaker notes found in the deck."],
        ),
        warnings=[] if notes else ["No speaker notes found in the deck."],
        usage={
            "summary": {"notes_count": len(notes)},
            "notes": [
                {
                    "slide_number": note["slide_number"],
                    "slide_id": note["slide_id"],
                    "text": note["text"],
                    "part": note["part"],
                    "locator": note["locator"],
                }
                for note in notes
            ],
        },
        next_recommended_tools=[
            "deck.extract.text",
            "deck.extract.shapes",
        ],
    )


# -- 3. deck.extract.shapes ---------------------------------------------------

def extract_deck_shapes(path: str | Path) -> ToolResult:
    result = _inventory(path, EXTRACT_SHAPES_TOOL)
    if isinstance(result, ToolResult):
        return result
    inventory, source_path = result

    shapes = inventory["shapes"]
    shape_items = [
        {
            "slide_number": shape["slide_number"],
            "shape_id": shape["shape_id"],
            "name": shape["name"],
            "placeholder": shape.get("placeholder"),
            "text": shape["text"],
            "text_run_count": shape["text_run_count"],
            "locator": shape["locator"],
        }
        for shape in shapes
    ]

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_SHAPES_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="shapes_extracted",
                    status="passed",
                    details={"shape_count": len(shape_items)},
                ),
            ],
        ),
        usage={
            "summary": {"shape_count": len(shape_items)},
            "shapes": shape_items,
        },
        next_recommended_tools=[
            "deck.extract.text",
            "deck.extract.media",
        ],
    )


# -- 4. deck.extract.media ----------------------------------------------------

def extract_deck_media(path: str | Path) -> ToolResult:
    result = _inventory(path, EXTRACT_MEDIA_TOOL)
    if isinstance(result, ToolResult):
        return result
    inventory, source_path = result

    media = inventory["media"]
    image_count = sum(1 for item in media if item.get("kind") == "image")
    media_items = [
        {
            "slide_number": item["slide_number"],
            "media_id": item["media_id"],
            "kind": item["kind"],
            "part": item["part"],
            "locator": item["locator"],
        }
        for item in media
    ]

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_MEDIA_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="media_extracted",
                    status="passed",
                    details={"media_count": len(media_items), "image_count": image_count},
                ),
            ],
        ),
        usage={
            "summary": {"media_count": len(media_items), "image_count": image_count},
            "media": media_items,
        },
        next_recommended_tools=[
            "deck.extract.charts",
            "deck.extract.text",
        ],
    )


# -- 5. deck.extract.charts ---------------------------------------------------

def extract_deck_charts(path: str | Path) -> ToolResult:
    result = _inventory(path, EXTRACT_CHARTS_TOOL)
    if isinstance(result, ToolResult):
        return result
    inventory, source_path = result

    charts = inventory["charts"]
    chart_items = [
        {
            "slide_number": chart["slide_number"],
            "chart_id": chart["chart_id"],
            "part": chart["part"],
            "locator": chart["locator"],
        }
        for chart in charts
    ]

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_CHARTS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="charts_extracted",
                    status="passed",
                    details={"chart_count": len(chart_items)},
                ),
            ],
        ),
        usage={
            "summary": {"chart_count": len(chart_items)},
            "charts": chart_items,
        },
        next_recommended_tools=[
            "deck.extract.media",
            "deck.extract.shapes",
        ],
    )


# -- 6. deck.extract.theme ----------------------------------------------------

def extract_deck_theme(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_THEME_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, presentation_root, preflight = result

    names = zip_names(source_path)
    themes = _themes(source_path, names)
    theme_items: list[dict[str, Any]] = []

    for theme in themes:
        part = theme["part"]
        theme_root = read_xml(source_path, part)
        item: dict[str, Any] = {
            "theme_id": theme["theme_id"],
            "part": part,
            "name": theme.get("name"),
            "locator": {"kind": "deck", "theme_id": theme["theme_id"], "part": part},
        }
        if theme_root is not None:
            color_scheme = theme_root.find(".//a:clrScheme", DECK_NS)
            if color_scheme is not None:
                item["color_scheme"] = color_scheme.get("name", "")
            font_scheme = theme_root.find(".//a:fontScheme", DECK_NS)
            if font_scheme is not None:
                item["font_scheme"] = font_scheme.get("name", "")
        theme_items.append(item)

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_THEME_TOOL,
        validation=ValidationReport(
            status="warning" if not theme_items else "passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="themes_extracted",
                    status="passed" if theme_items else "warning",
                    details={"theme_count": len(theme_items)},
                ),
            ],
            warnings=[] if theme_items else ["No theme parts found in the package."],
        ),
        warnings=[] if theme_items else ["No theme parts found in the package."],
        usage={
            "summary": {"theme_count": len(theme_items)},
            "themes": theme_items,
        },
        next_recommended_tools=[
            "deck.extract.text",
            "deck.inspect.presentation",
        ],
    )
