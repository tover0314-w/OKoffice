from __future__ import annotations

import html
import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from okoffice.artifacts.store import build_artifact
from okoffice.authoring.design import resolve_theme
from okoffice.authoring.models import DesignTokens
from okoffice.office.deck_themes import (
    SLIDE_LAYOUTS,
    layout_to_css,
    layout_to_pptx_shapes,
    select_layout,
    tokens_to_css,
    tokens_to_pptx_defaults,
)
from okoffice.office.deck_templates import render_template_slide
from okoffice.office.inspect import inspect_office_file
from okoffice.office.ooxml import DECK_NS, count_members, read_xml, sorted_members, zip_names
from okoffice.office.shared import dedupe_strings as _dedupe, failed_result, job_id, validation_report_status
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path


INSPECT_TOOL_NAME = "deck.inspect.presentation"
CREATE_FROM_OUTLINE_TOOL_NAME = "deck.create.from_outline"
CREATE_PRESENTATION_TOOL_NAME = "deck.create.presentation"
RENDER_HTML_TOOL_NAME = "deck.render.html"
VALIDATE_HTML_TOOL_NAME = "deck.validation.html_preview"
EXPORT_PPTX_TOOL_NAME = "deck.export.pptx"
VALIDATE_TOOL_NAME = "deck.validate.presentation"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
HTML_MIME_TYPE = "text/html"
REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
REL_URI = REL_NS["rel"]
OFFICE_REL_URI = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
OFFICE_R = f"{{{OFFICE_REL_URI}}}"
PLACEHOLDER_MARKERS = ("{{", "}}", "[[", "]]", "<<", ">>", "TODO", "TBD", "lorem ipsum")


def inspect_deck_presentation(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return failed_result(
            INSPECT_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Deck inspect failed."),
        )
    if preflight.usage["format"]["detected_format"] != "pptx":
        return failed_result(
            INSPECT_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="deck.inspect.presentation requires a PPTX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    presentation_root = read_xml(source_path, "ppt/presentation.xml")
    if presentation_root is None:
        return failed_result(
            INSPECT_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="deck.inspect.presentation requires ppt/presentation.xml in the PPTX package.",
                details={"path": source_path.as_posix()},
            ),
        )
    inventory = _deck_inventory(source_path, names, presentation_root)
    summary = inventory["summary"]
    warnings = list(preflight.warnings)
    if summary["external_link_count"]:
        warnings.append("External presentation relationship targets were detected.")
    warnings = _dedupe(warnings)

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=INSPECT_TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="presentation_xml_present", status="passed"),
                ValidationCheck(
                    name="slide_inventory",
                    status="passed" if summary["slide_count"] else "warning",
                    details={"slide_count": summary["slide_count"]},
                ),
                ValidationCheck(
                    name="package_safety_markers",
                    status="warning" if warnings else "passed",
                    details=inventory["package"],
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "presentation": {
                "path": source_path.as_posix(),
                "format": "pptx",
                "package_type": preflight.usage["format"]["package_type"],
                "slide_count": summary["slide_count"],
                "text_run_count": summary["text_run_count"],
            },
            "summary": summary,
            "slides": inventory["slides"],
            "shapes": inventory["shapes"],
            "notes": _CountedList(inventory["notes"], notes_slide_count=len(inventory["notes"])),
            "layouts": {"layout_count": count_members(names, prefix="ppt/slideLayouts/")},
            "theme": {"theme_count": summary["theme_count"]},
            "themes": inventory["themes"],
            "media": _CountedList(inventory["media"], media_count=len(inventory["media"])),
            "charts": _CountedList(inventory["charts"], chart_count=len(inventory["charts"])),
            "package": inventory["package"],
            "layout": {
                "rendered_layout_claimed": False,
                "preview_available": False,
                "render_worker_required": "pptx_contact_sheet_renderer",
            },
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "deck.edit.patch",
            "deck.validation.presentation",
            "deck.validation.contact_sheet",
            "deck.export.pdf",
            "office.context.build_packet",
        ],
    )


class _CountedList(list[dict[str, Any]]):
    def __init__(self, values: list[dict[str, Any]], **counts: int) -> None:
        super().__init__(values)
        self._counts = counts

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, str):
            return self._counts[key]
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._counts.get(key, default)


def _deck_inventory(source_path: Path, names: set[str], presentation_root: object) -> dict[str, Any]:
    presentation_rels = _relationship_map(read_xml(source_path, "ppt/_rels/presentation.xml.rels"), "ppt/presentation.xml")
    slide_order = _slide_order(presentation_root, presentation_rels, names)
    slides: list[dict[str, Any]] = []
    shapes: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []
    external_links = [rel for rel in presentation_rels.values() if rel["target_mode"].lower() == "external"]
    allow_note_fallback = not any(name.startswith("ppt/slides/_rels/") and name.endswith(".rels") for name in names)

    for slide_number, slide in enumerate(slide_order, start=1):
        slide_part = slide["part"]
        slide_id = str(slide["slide_id"])
        slide_root = read_xml(source_path, slide_part)
        slide_rels = _relationship_map(read_xml(source_path, _rels_part_for(slide_part)), slide_part)
        external_links.extend([rel for rel in slide_rels.values() if rel["target_mode"].lower() == "external"])
        slide_shapes = _slide_shapes(source_path, slide_root, slide_number=slide_number, slide_id=slide_id)
        slide_charts = _slide_charts(slide_root, slide_rels, slide_number=slide_number, slide_id=slide_id)
        slide_media = _slide_media(slide_root, slide_rels, slide_number=slide_number, slide_id=slide_id)
        note_payload = _slide_notes(
            source_path,
            slide_rels,
            names,
            slide_number=slide_number,
            slide_id=slide_id,
            allow_fallback=allow_note_fallback,
        )
        if note_payload is not None:
            notes.append(note_payload)
        shapes.extend(slide_shapes)
        charts.extend(slide_charts)
        media.extend(slide_media)
        title = next((shape["text"] for shape in slide_shapes if shape.get("placeholder") == "title" and shape["text"]), "")
        if not title:
            title = slide_shapes[0]["text"] if slide_shapes else ""
        slides.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "part": slide_part,
                "title": title,
                "text": "\n".join(shape["text"] for shape in slide_shapes if shape["text"]),
                "text_run_count": sum(int(shape["text_run_count"]) for shape in slide_shapes),
                "shape_count": len(slide_shapes),
                "chart_count": len(slide_charts),
                "media_count": len(slide_media),
                "has_notes": note_payload is not None and bool(note_payload.get("text")),
                "locator": {"kind": "deck", "slide": slide_number, "slide_id": slide_id},
            }
        )

    charts.extend(_orphan_charts(names, charts))
    media.extend(_orphan_media(names, media))
    themes = _themes(source_path, names)
    package = {
        "macro_enabled": source_path.suffix.lower() == ".pptm" or any(name.lower().endswith("vbaproject.bin") for name in names),
        "has_external_relationships": bool(external_links),
        "external_relationships": external_links,
    }
    summary = {
        "slide_count": len(slides),
        "slide_with_notes_count": len([slide for slide in slides if slide["has_notes"]]),
        "shape_count": len(shapes),
        "text_run_count": sum(int(slide["text_run_count"]) for slide in slides),
        "chart_count": len(charts),
        "media_count": len(media),
        "theme_count": len(themes),
        "external_link_count": len(external_links),
    }
    return {
        "summary": summary,
        "slides": slides,
        "shapes": shapes,
        "notes": notes,
        "charts": charts,
        "media": media,
        "themes": themes,
        "package": package,
    }


def _slide_order(presentation_root: object, presentation_rels: dict[str, dict[str, str]], names: set[str]) -> list[dict[str, str]]:
    slides = []
    for index, slide_id_node in enumerate(presentation_root.findall(".//p:sldId", DECK_NS), start=1):
        rel_id = slide_id_node.get(f"{OFFICE_R}id")
        target = presentation_rels.get(str(rel_id), {}).get("target") if rel_id else None
        if target and target in names:
            slides.append({"slide_id": str(slide_id_node.get("id") or 255 + index), "part": target})
    if slides:
        return slides
    return [
        {"slide_id": str(255 + index), "part": member}
        for index, member in enumerate(sorted_members(names, prefix="ppt/slides/slide"), start=1)
    ]


def _slide_shapes(source_path: Path, slide_root: object | None, *, slide_number: int, slide_id: str) -> list[dict[str, Any]]:
    if slide_root is None:
        return []
    shapes = []
    for shape in slide_root.findall(".//p:sp", DECK_NS):
        c_nv_pr = shape.find(".//p:cNvPr", DECK_NS)
        placeholder = shape.find(".//p:ph", DECK_NS)
        shape_id = str(c_nv_pr.get("id") if c_nv_pr is not None else len(shapes) + 1)
        placeholder_type = placeholder.get("type") if placeholder is not None else None
        text_runs = [str(node.text or "") for node in shape.findall(".//a:t", DECK_NS)]
        text = "".join(text_runs).strip()
        shapes.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "shape_id": shape_id,
                "name": c_nv_pr.get("name") if c_nv_pr is not None else None,
                "placeholder": placeholder_type,
                "text": text,
                "text_run_count": len(text_runs),
                "locator": {
                    "kind": "deck",
                    "slide": slide_number,
                    "slide_id": slide_id,
                    "shape_id": shape_id,
                    **({"placeholder": placeholder_type} if placeholder_type else {}),
                },
            }
        )
    return shapes


def _slide_notes(
    source_path: Path,
    slide_rels: dict[str, dict[str, str]],
    names: set[str],
    *,
    slide_number: int,
    slide_id: str,
    allow_fallback: bool,
) -> dict[str, Any] | None:
    note_rel = next((rel for rel in slide_rels.values() if rel["type"].endswith("/notesSlide")), None)
    if note_rel is None and not allow_fallback:
        return None
    note_part = note_rel["target"] if note_rel is not None else f"ppt/notesSlides/notesSlide{slide_number}.xml"
    if note_part not in names:
        return None
    note_root = read_xml(source_path, note_part)
    text = _text_content(note_root)
    return {
        "slide_number": slide_number,
        "slide_id": slide_id,
        "part": note_part,
        "text": text,
        "locator": {"kind": "deck", "slide": slide_number, "slide_id": slide_id, "notes": True},
    }


def _slide_charts(
    slide_root: object | None,
    slide_rels: dict[str, dict[str, str]],
    *,
    slide_number: int,
    slide_id: str,
) -> list[dict[str, Any]]:
    if slide_root is None:
        return []
    charts = []
    for index, chart in enumerate(slide_root.findall(".//c:chart", {**DECK_NS, "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}), start=1):
        rel_id = chart.get(f"{OFFICE_R}id")
        target = slide_rels.get(str(rel_id), {}).get("target", "")
        chart_id = PurePosixPath(target).stem if target else f"chart{index}"
        charts.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "chart_id": chart_id,
                "part": target,
                "locator": {"kind": "deck", "slide": slide_number, "slide_id": slide_id, "shape_id": chart_id},
            }
        )
    return charts


def _orphan_charts(names: set[str], charts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {str(chart.get("part") or "") for chart in charts}
    orphans = []
    for part in sorted_members(names, prefix="ppt/charts/"):
        if part in existing:
            continue
        chart_id = PurePosixPath(part).stem
        orphans.append(
            {
                "slide_number": None,
                "slide_id": None,
                "chart_id": chart_id,
                "part": part,
                "locator": {"kind": "deck", "shape_id": chart_id},
            }
        )
    return orphans


def _slide_media(
    slide_root: object | None,
    slide_rels: dict[str, dict[str, str]],
    *,
    slide_number: int,
    slide_id: str,
) -> list[dict[str, Any]]:
    if slide_root is None:
        return []
    media = []
    for index, blip in enumerate(slide_root.findall(".//a:blip", DECK_NS), start=1):
        rel_id = blip.get(f"{OFFICE_R}embed") or blip.get(f"{OFFICE_R}link")
        rel = slide_rels.get(str(rel_id), {})
        target = rel.get("target", "")
        media.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "media_id": str(rel_id or f"media{index}"),
                "kind": _media_kind(rel.get("type", ""), target),
                "part": target,
                "locator": {"kind": "deck", "slide": slide_number, "slide_id": slide_id, "media_id": str(rel_id or index)},
            }
        )
    return media


def _orphan_media(names: set[str], media: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = {str(item.get("part") or "") for item in media}
    orphans = []
    for index, part in enumerate(sorted(name for name in names if name.startswith("ppt/media/")), start=1):
        if part in existing:
            continue
        orphans.append(
            {
                "slide_number": None,
                "slide_id": None,
                "media_id": f"media{index}",
                "kind": _media_kind("", part),
                "part": part,
                "locator": {"kind": "deck", "media_id": f"media{index}"},
            }
        )
    return orphans


def _themes(source_path: Path, names: set[str]) -> list[dict[str, Any]]:
    themes = []
    for index, part in enumerate(sorted_members(names, prefix="ppt/theme/"), start=1):
        root = read_xml(source_path, part)
        themes.append(
            {
                "theme_id": f"theme{index}",
                "part": part,
                "name": root.get("name") if root is not None else None,
            }
        )
    return themes


def _relationship_map(root: object | None, source_part: str) -> dict[str, dict[str, str]]:
    if root is None:
        return {}
    relationships = {}
    for rel in root.findall(".//rel:Relationship", REL_NS):
        rel_id = str(rel.get("Id") or "")
        target = str(rel.get("Target") or "")
        relationships[rel_id] = {
            "id": rel_id,
            "type": str(rel.get("Type") or ""),
            "target": target if str(rel.get("TargetMode") or "").lower() == "external" else _resolve_target(source_part, target),
            "target_mode": str(rel.get("TargetMode") or ""),
        }
    return relationships


def _rels_part_for(source_part: str) -> str:
    path = PurePosixPath(source_part)
    return str(path.parent / "_rels" / f"{path.name}.rels")


def _resolve_target(source_part: str, target: str) -> str:
    if "://" in target:
        return target
    base = PurePosixPath(source_part).parent
    parts = []
    for part in (base / target).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def _text_content(root: object | None) -> str:
    if root is None:
        return ""
    return "".join(str(node.text or "") for node in root.findall(".//a:t", DECK_NS)).strip()


def _media_kind(rel_type: str, target: str) -> str:
    if rel_type.endswith("/image") or PurePosixPath(target).suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}:
        return "image"
    return "media"


def validate_deck_presentation(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return failed_result(
            VALIDATE_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Deck validation failed."),
        )
    if preflight.usage["format"]["detected_format"] != "pptx":
        return failed_result(
            VALIDATE_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="deck.validate.presentation requires a PPTX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    presentation_root = read_xml(source_path, "ppt/presentation.xml")
    relationship_root = read_xml(source_path, "ppt/_rels/presentation.xml.rels")
    slide_members = sorted_members(names, prefix="ppt/slides/slide")
    slide_summaries = _slide_validation_summaries(source_path, slide_members)
    missing_targets = _missing_slide_relationship_targets(slide_members, relationship_root)
    blank_slide_count = sum(1 for slide in slide_summaries if slide["is_blank"])
    placeholder_texts = [
        text for slide in slide_summaries for text in slide["placeholder_texts"] if isinstance(text, str)
    ]
    text_run_count = sum(int(slide["text_run_count"]) for slide in slide_summaries)
    safety = preflight.usage["safety"]
    warnings = list(preflight.warnings)
    if blank_slide_count:
        warnings.append(f"Deck validation found blank slides: {blank_slide_count}.")
    if placeholder_texts:
        warnings.append(f"Deck validation found placeholder-like text runs: {len(placeholder_texts)}.")
    if bool(safety.get("macro_enabled", False)):
        warnings.append("Macro-enabled presentation markers were detected; macros are not executed.")
    if bool(safety.get("has_external_relationships", False)):
        warnings.append("External Office relationship targets were detected.")

    checks = [
        ValidationCheck(name="format_is_pptx", status="passed", details=preflight.usage["format"]),
        _validation_check(
            "presentation_xml_present",
            condition=presentation_root is not None,
            failed_status="failed",
            passed_details={"member": "ppt/presentation.xml"},
            failed_message="Presentation package is missing ppt/presentation.xml.",
        ),
        _validation_check(
            "slide_count_nonzero",
            condition=len(slide_members) > 0,
            failed_status="failed",
            passed_details={"slide_count": len(slide_members)},
            failed_message="Presentation contains no slide XML parts.",
        ),
        _validation_check(
            "slide_relationship_targets_present",
            condition=not missing_targets,
            failed_status="failed",
            passed_details={"missing_target_count": len(missing_targets)},
            failed_message="Presentation relationships do not reference every slide part.",
        ),
        _validation_check(
            "text_runs_present",
            condition=text_run_count > 0,
            failed_status="warning",
            passed_details={"text_run_count": text_run_count},
            failed_message="Presentation contains no text runs.",
        ),
        _validation_check(
            "blank_slides_absent",
            condition=blank_slide_count == 0,
            failed_status="warning",
            passed_details={"blank_slide_count": blank_slide_count},
            failed_message="Presentation contains blank slides.",
        ),
        _validation_check(
            "placeholder_leakage_absent",
            condition=not placeholder_texts,
            failed_status="warning",
            passed_details={"placeholder_text_count": len(placeholder_texts)},
            failed_message="Presentation contains placeholder-like text.",
        ),
        _validation_check(
            "macros_absent",
            condition=not bool(safety.get("macro_enabled", False)),
            failed_status="warning",
            passed_details={"macro_enabled": bool(safety.get("macro_enabled", False))},
            failed_message="Macro-enabled presentation markers detected.",
        ),
        _validation_check(
            "external_relationships_absent",
            condition=not bool(safety.get("has_external_relationships", False)),
            failed_status="warning",
            passed_details={"has_external_relationships": bool(safety.get("has_external_relationships", False))},
            failed_message="External Office relationship targets detected.",
        ),
    ]

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=VALIDATE_TOOL_NAME,
        validation=ValidationReport(
            status=validation_report_status(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "presentation": {
                "path": source_path.as_posix(),
                "format": "pptx",
                "package_type": preflight.usage["format"]["package_type"],
            },
            "summary": {
                "slide_count": len(slide_members),
                "text_run_count": text_run_count,
                "blank_slide_count": blank_slide_count,
                "placeholder_text_count": len(placeholder_texts),
                "missing_relationship_target_count": len(missing_targets),
                "notes_slide_count": count_members(names, prefix="ppt/notesSlides/"),
                "layout_count": count_members(names, prefix="ppt/slideLayouts/"),
                "theme_count": count_members(names, prefix="ppt/theme/"),
                "media_count": _media_count(names),
                "chart_count": count_members(names, prefix="ppt/charts/"),
            },
            "slides": slide_summaries,
            "placeholder_texts": placeholder_texts[:25],
            "missing_relationship_targets": missing_targets,
            "safety": safety,
        },
        next_recommended_tools=[
            "office.workflow.board_pack",
            "deck.inspect.presentation",
            "deck.export.pdf",
            "office.context.build_packet",
        ],
    )


def create_deck_from_outline(outline: dict[str, Any], output_path: str | Path) -> ToolResult:
    return _create_deck_from_outline_html_first(
        outline,
        output_path,
        tool_name=CREATE_FROM_OUTLINE_TOOL_NAME,
        plan_payload=None,
    )


def create_deck_presentation(outline_or_plan: dict[str, Any], output_path: str | Path) -> ToolResult:
    outline = _presentation_outline(outline_or_plan)
    input_source = _presentation_input_source(outline_or_plan)
    return _create_deck_from_outline_html_first(
        outline,
        output_path,
        tool_name=CREATE_PRESENTATION_TOOL_NAME,
        plan_payload=outline_or_plan if input_source == "composition_plan" else None,
    )


def _create_deck_from_outline_html_first(
    outline: dict[str, Any],
    output_path: str | Path,
    *,
    tool_name: str,
    plan_payload: dict[str, Any] | None = None,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except OKofficeException as exc:
        return failed_result(tool_name, exc.to_error())

    slides = _outline_slides(outline)
    if not slides:
        return failed_result(
            tool_name,
            OKofficeError(
                code="unsafe_input_rejected",
                message=f"{tool_name} requires at least one slide.",
            ),
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    input_source = "outline" if plan_payload is None else "composition_plan"
    html_path = output.with_suffix(".preview.html")
    render_input = plan_payload if plan_payload is not None else outline

    html_result = render_deck_html(render_input, html_path)
    if html_result.status != "succeeded":
        return _create_deck_from_outline(
            outline, output, tool_name=tool_name, input_source=input_source,
        )

    preview_result = validate_deck_html_preview(html_path)
    preview_warnings = list(preview_result.warnings) if preview_result.status == "succeeded" else []

    export_result = export_deck_pptx(html_path, output)
    if export_result.status != "succeeded":
        return _create_deck_from_outline(
            outline, output, tool_name=tool_name, input_source=input_source,
        )

    combined_artifacts = list(html_result.artifacts) + [
        artifact for artifact in export_result.artifacts
        if artifact.artifact_id not in {a.artifact_id for a in html_result.artifacts}
    ]
    html_validation_status = preview_result.validation.status if preview_result.validation else "skipped"
    combined_checks = [
        ValidationCheck(
            name="html_preview_rendered",
            status="passed",
            details={"html_path": html_path.as_posix(), "slide_count": len(slides)},
        ),
        ValidationCheck(
            name="html_preview_taste_qa",
            status=html_validation_status,
            details={"taste_qa": preview_result.usage.get("taste_qa", {}) if preview_result.usage else {}},
        ),
        *(export_result.validation.checks if export_result.validation else []),
    ]
    all_warnings = list(html_result.warnings) + preview_warnings + list(export_result.warnings)

    usage = dict(export_result.usage)
    usage["input"] = {"source": input_source}
    usage["slides"] = slides
    usage["route"] = "html_first"
    usage["html_preview"] = {
        "path": html_path.as_posix(),
        "manifest_path": html_path.with_suffix(".html-manifest.json").as_posix(),
        "taste_qa": preview_result.usage.get("taste_qa", {}) if preview_result.usage else {},
    }

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=tool_name,
        artifacts=combined_artifacts,
        validation=ValidationReport(
            status=validation_report_status(combined_checks),
            checks=combined_checks,
            warnings=all_warnings,
        ),
        warnings=all_warnings,
        usage=usage,
        next_recommended_tools=[
            "deck.validate.presentation",
            "deck.inspect.presentation",
            "deck.validation.html_preview",
            "office.workflow.board_pack",
        ],
    )


def render_deck_html(
    plan_or_path: dict[str, Any] | str | Path,
    output_path: str | Path,
    *,
    artifact_dir: str | Path | None = None,
) -> ToolResult:
    try:
        payload, input_source, input_path = _load_deck_plan_payload(plan_or_path)
        output = resolve_output_path(output_path)
        manifest_path = _html_manifest_path(output, artifact_dir=artifact_dir)
    except OKofficeException as exc:
        return failed_result(RENDER_HTML_TOOL_NAME, exc.to_error())

    outline = _presentation_outline(payload)
    slides = _outline_slides(outline)
    if not slides:
        return failed_result(
            RENDER_HTML_TOOL_NAME,
            OKofficeError(
                code="unsafe_input_rejected",
                message="deck.render.html requires a deck composition plan or outline with at least one slide.",
            ),
        )

    composition_slides = _composition_slides(payload)
    slide_entries = _html_slide_entries(slides, composition_slides)
    placeholder_texts = _placeholder_texts_from_slides(slides)
    source_ref_count = sum(len(entry["source_refs"]) for entry in slide_entries)
    design_tokens = _resolve_design_tokens(payload)
    manifest = {
        "tool": RENDER_HTML_TOOL_NAME,
        "html_path": output.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "source": {
            "type": input_source,
            **({"path": input_path.as_posix()} if input_path is not None else {}),
        },
        "render_profile": "okoffice-html-slide-package-v0",
        "offline_assets": True,
        "composition_ir": payload.get("composition_ir") if isinstance(payload.get("composition_ir"), dict) else None,
        "outline": outline,
        "slides": slide_entries,
        "summary": {
            "slide_count": len(slides),
            "source_ref_count": source_ref_count,
            "placeholder_text_count": len(placeholder_texts),
        },
    }
    html_document = _html_deck_document(outline=outline, slides=slide_entries, manifest_path=manifest_path, design_tokens=design_tokens)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_document, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    checks = [
        ValidationCheck(name="outline_normalized", status="passed", details={"slide_count": len(slides)}),
        ValidationCheck(name="html_written", status="passed", details={"path": output.as_posix(), "mime_type": HTML_MIME_TYPE}),
        ValidationCheck(name="manifest_written", status="passed", details={"path": manifest_path.as_posix()}),
        ValidationCheck(
            name="offline_assets_declared",
            status="passed",
            details={"offline_assets": True, "remote_asset_count": 0},
        ),
        _validation_check(
            "placeholder_leakage_absent",
            condition=not placeholder_texts,
            failed_status="warning",
            passed_details={"placeholder_text_count": len(placeholder_texts)},
            failed_message="HTML deck package contains placeholder-like text.",
        ),
    ]
    warnings = []
    if placeholder_texts:
        warnings.append(f"HTML deck package contains placeholder-like text: {len(placeholder_texts)}.")
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=RENDER_HTML_TOOL_NAME,
        artifacts=[
            build_artifact(output, RENDER_HTML_TOOL_NAME),
            build_artifact(manifest_path, RENDER_HTML_TOOL_NAME),
        ],
        validation=ValidationReport(status=validation_report_status(checks), checks=checks, warnings=warnings),
        warnings=warnings,
        usage={
            "summary": {
                "slide_count": len(slides),
                "source_ref_count": source_ref_count,
                "placeholder_text_count": len(placeholder_texts),
            },
            "html_package": {
                "path": output.as_posix(),
                "manifest_path": manifest_path.as_posix(),
                "offline_assets": True,
                "slide_dom_anchor_count": len(slide_entries),
                "render_profile": "okoffice-html-slide-package-v0",
                "preview_contract": "html-first-local-baseline",
            },
            "input": {
                "source": input_source,
                **({"path": input_path.as_posix()} if input_path is not None else {}),
            },
            "slides": slide_entries,
        },
        next_recommended_tools=[
            "deck.validation.html_preview",
            "deck.validation.contact_sheet",
            "deck.export.pptx",
            "office.workflow.board_pack",
        ],
    )


def validate_deck_html_preview(path: str | Path) -> ToolResult:
    try:
        html_path = resolve_input_path(path)
        manifest_path = _resolve_html_manifest_path(html_path)
    except OKofficeException as exc:
        return failed_result(VALIDATE_HTML_TOOL_NAME, exc.to_error())

    html_text = html_path.read_text(encoding="utf-8", errors="replace")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return failed_result(
            VALIDATE_HTML_TOOL_NAME,
            OKofficeError(
                code="unsafe_input_rejected",
                message="HTML deck manifest is not valid JSON.",
                details={"manifest_path": manifest_path.as_posix(), "error": str(exc)},
            ),
        )

    manifest_slides = manifest.get("slides", []) if isinstance(manifest, dict) else []
    slides = manifest_slides if isinstance(manifest_slides, list) else []
    outline = manifest.get("outline", {}) if isinstance(manifest, dict) else {}
    normalized_slides = _outline_slides(_presentation_outline(outline if isinstance(outline, dict) else {}))
    if not normalized_slides and slides:
        normalized_slides = [
            {
                "slide_index": int(slide.get("slide_index", index)) if isinstance(slide, dict) else index,
                "title": str(slide.get("title") or f"Slide {index}") if isinstance(slide, dict) else f"Slide {index}",
                "subtitle": "",
                "bullets": [],
                "bullet_count": 0,
                "notes": "",
            }
            for index, slide in enumerate(slides, start=1)
        ]
    placeholder_texts = _placeholder_texts_from_slides(normalized_slides)
    remote_asset_count = _remote_asset_count(html_text)
    dom_anchor_count = html_text.count('class="okoffice-slide"')
    script_count = html_text.lower().count("<script")
    density = _html_preview_density(normalized_slides)
    overflow_risks = [item for item in density if item["overflow_risk"]]
    taste_status = "passed" if not placeholder_texts and not remote_asset_count and not script_count and not overflow_risks else "warning"
    warnings = []
    if placeholder_texts:
        warnings.append(f"HTML deck preview contains placeholder-like text: {len(placeholder_texts)}.")
    if remote_asset_count:
        warnings.append("HTML deck preview references remote or file assets.")
    if script_count:
        warnings.append("HTML deck preview contains script tags; scripts should not run in preview validation.")
    if overflow_risks:
        warnings.append(f"HTML deck preview has slides with overflow or density risk: {len(overflow_risks)}.")

    taste_result = _run_design_token_taste_qa(manifest)
    checks = [
        ValidationCheck(name="html_file_present", status="passed", details={"path": html_path.as_posix()}),
        ValidationCheck(name="manifest_present", status="passed", details={"path": manifest_path.as_posix()}),
        _validation_check(
            "slide_count_nonzero",
            condition=len(slides) > 0,
            failed_status="failed",
            passed_details={"slide_count": len(slides)},
            failed_message="HTML deck package manifest contains no slides.",
        ),
        _validation_check(
            "slide_dom_anchors_match_manifest",
            condition=dom_anchor_count == len(slides),
            failed_status="failed",
            passed_details={"dom_anchor_count": dom_anchor_count, "manifest_slide_count": len(slides)},
            failed_message="HTML slide DOM anchors do not match manifest slide count.",
        ),
        _validation_check(
            "offline_assets_only",
            condition=remote_asset_count == 0,
            failed_status="warning",
            passed_details={"remote_asset_count": remote_asset_count},
            failed_message="HTML deck preview references remote or file assets.",
        ),
        _validation_check(
            "scripts_absent",
            condition=script_count == 0,
            failed_status="warning",
            passed_details={"script_count": script_count},
            failed_message="HTML deck preview contains script tags.",
        ),
        _validation_check(
            "placeholder_leakage_absent",
            condition=not placeholder_texts,
            failed_status="warning",
            passed_details={"placeholder_text_count": len(placeholder_texts)},
            failed_message="HTML deck preview contains placeholder-like text.",
        ),
        _validation_check(
            "visual_density_baseline",
            condition=not overflow_risks,
            failed_status="warning",
            passed_details={"overflow_risk_count": len(overflow_risks)},
            failed_message="HTML deck preview contains dense slides that may overflow.",
        ),
        ValidationCheck(
            name="taste_qa_baseline",
            status=taste_status,
            details={
                "status": taste_status,
                "checks": [
                    "placeholder leakage",
                    "offline assets",
                    "script absence",
                    "basic visual density",
                ],
            },
        ),
        _validation_check(
            "taste_qa_score",
            condition=taste_result.get("passing", False),
            passed_details=taste_result,
            failed_status="warning",
            failed_message="Design token taste QA score below 70.",
        ),
    ]
    return ToolResult(
        job_id=job_id(),
        status="succeeded" if validation_report_status(checks) != "failed" else "failed",
        tool=VALIDATE_HTML_TOOL_NAME,
        validation=ValidationReport(status=validation_report_status(checks), checks=checks, warnings=warnings),
        warnings=warnings,
        usage={
            "summary": {
                "slide_count": len(slides),
                "slide_dom_anchor_count": dom_anchor_count,
                "placeholder_text_count": len(placeholder_texts),
                "remote_asset_count": remote_asset_count,
                "script_count": script_count,
                "overflow_risk_count": len(overflow_risks),
            },
            "html_preview": {
                "path": html_path.as_posix(),
                "manifest_path": manifest_path.as_posix(),
                "offline_assets": remote_asset_count == 0,
                "slide_dom_anchor_count": dom_anchor_count,
                "screenshot_status": "not_requested",
                "browser_render_required_for_contact_sheet": "deck.validation.contact_sheet",
            },
            "html_package": {
                "path": html_path.as_posix(),
                "manifest_path": manifest_path.as_posix(),
                "offline_assets": remote_asset_count == 0,
                "render_profile": manifest.get("render_profile") if isinstance(manifest, dict) else None,
            },
            "visual_density": {
                "status": "passed" if not overflow_risks else "warning",
                "slides": density,
                "overflow_risks": overflow_risks,
            },
            "taste_qa": {
                "status": taste_status,
                "method": "static_html_baseline",
                "checks": [
                    "slide anchors",
                    "offline assets",
                    "placeholder leakage",
                    "visual density",
                    "script absence",
                ],
                "design_token_score": taste_result,
            },
            "placeholder_texts": placeholder_texts[:25],
            "slides": slides,
        },
        next_recommended_tools=[
            "deck.validation.contact_sheet",
            "deck.export.pptx",
            "deck.render.html",
            "office.workflow.board_pack",
        ],
    )


def export_deck_pptx(html_path: str | Path, output_path: str | Path) -> ToolResult:
    try:
        source = resolve_input_path(html_path)
        manifest_path = _resolve_html_manifest_path(source)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OKofficeException as exc:
        return failed_result(EXPORT_PPTX_TOOL_NAME, exc.to_error())
    except json.JSONDecodeError as exc:
        return failed_result(
            EXPORT_PPTX_TOOL_NAME,
            OKofficeError(
                code="unsafe_input_rejected",
                message="HTML deck manifest is not valid JSON.",
                details={"html_path": str(html_path), "error": str(exc)},
            ),
        )

    outline = manifest.get("outline") if isinstance(manifest, dict) else None
    if not isinstance(outline, dict):
        return failed_result(
            EXPORT_PPTX_TOOL_NAME,
            OKofficeError(
                code="unsafe_input_rejected",
                message="deck.export.pptx requires an HTML deck manifest with an outline.",
                details={"html_path": source.as_posix(), "manifest_path": manifest_path.as_posix()},
            ),
        )

    design_tokens = _resolve_design_tokens(manifest) if isinstance(manifest, dict) else None
    result = _create_deck_from_outline(
        outline,
        output_path,
        tool_name=EXPORT_PPTX_TOOL_NAME,
        input_source="html_slide_package",
        design_tokens=design_tokens,
    )
    if result.status != "succeeded":
        return result
    result.usage["export"] = {
        "source_format": "html_slide_package",
        "route": "html_manifest_to_editable_pptx_layout_aware",
        "html_path": source.as_posix(),
        "html_manifest_path": manifest_path.as_posix(),
        "output_format": "pptx",
        "editable_text": True,
        "component_tree_exporter": "layout_aware_outline_exporter",
    }
    source_map_path = Path(output_path).expanduser().resolve().with_suffix(".deck-source-map.json")
    _write_pptx_source_map(
        source_map_path,
        html_path=source,
        manifest_path=manifest_path,
        output_path=Path(output_path).expanduser().resolve(),
        manifest=manifest,
    )
    result.artifacts.append(build_artifact(source_map_path, EXPORT_PPTX_TOOL_NAME))
    result.usage["export"]["source_map_path"] = source_map_path.as_posix()
    result.next_recommended_tools = [
        "deck.validate.presentation",
        "deck.inspect.presentation",
        "office.workflow.board_pack",
    ]
    return result


def _load_deck_plan_payload(plan_or_path: dict[str, Any] | str | Path) -> tuple[dict[str, Any], str, Path | None]:
    if isinstance(plan_or_path, dict):
        return plan_or_path, _presentation_input_source(plan_or_path), None
    source_path = resolve_input_path(plan_or_path)
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OKofficeException(
            "unsafe_input_rejected",
            f"Deck plan JSON could not be parsed: {source_path}",
            details={"path": source_path.as_posix(), "error": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise OKofficeException(
            "unsafe_input_rejected",
            "Deck plan JSON must contain an object payload.",
            details={"path": source_path.as_posix()},
        )
    return payload, _presentation_input_source(payload), source_path


def _html_manifest_path(output: Path, *, artifact_dir: str | Path | None) -> Path:
    manifest_name = output.with_suffix(".html-manifest.json").name
    if artifact_dir is None:
        return output.with_suffix(".html-manifest.json")
    return resolve_output_path(Path(artifact_dir) / manifest_name)


def _resolve_html_manifest_path(html_path: Path) -> Path:
    return resolve_input_path(html_path.with_suffix(".html-manifest.json"))


def _composition_slides(payload: dict[str, Any]) -> list[dict[str, Any]]:
    composition_ir = payload.get("composition_ir") if isinstance(payload, dict) else None
    raw_slides = composition_ir.get("slides", []) if isinstance(composition_ir, dict) else []
    if not isinstance(raw_slides, list):
        return []
    return [slide for slide in raw_slides if isinstance(slide, dict)]


def _html_slide_entries(
    slides: list[dict[str, Any]],
    composition_slides: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entries = []
    for index, slide in enumerate(slides, start=1):
        composition = composition_slides[index - 1] if index - 1 < len(composition_slides) else {}
        source_refs = composition.get("source_refs", []) if isinstance(composition, dict) else []
        if not isinstance(source_refs, list):
            source_refs = []
        workbook_ranges = composition.get("workbook_ranges", []) if isinstance(composition, dict) else []
        if not isinstance(workbook_ranges, list):
            workbook_ranges = []
        entries.append(
            {
                "slide_index": index,
                "slide_id": str(composition.get("slide_id") or f"slide_{index:03d}") if isinstance(composition, dict) else f"slide_{index:03d}",
                "dom_anchor": f"#slide-{index}",
                "title": slide["title"],
                "subtitle": slide.get("subtitle", ""),
                "bullets": list(slide.get("bullets", [])),
                "bullet_count": len(slide.get("bullets", [])),
                "notes": slide.get("notes", ""),
                "layout": slide.get("layout"),
                "source_refs": [ref for ref in source_refs if isinstance(ref, dict)],
                "workbook_ranges": [ref for ref in workbook_ranges if isinstance(ref, dict)],
            }
        )
    return entries


def _placeholder_texts_from_slides(slides: list[dict[str, Any]]) -> list[str]:
    texts = []
    for slide in slides:
        texts.extend(
            str(value)
            for value in [slide.get("title", ""), slide.get("subtitle", ""), slide.get("notes", "")]
            if str(value).strip()
        )
        bullets = slide.get("bullets", [])
        if isinstance(bullets, list):
            texts.extend(str(bullet) for bullet in bullets if str(bullet).strip())
    return [text for text in texts if _looks_like_placeholder(text)]


def _remote_asset_count(html_text: str) -> int:
    lowered = html_text.lower()
    return sum(lowered.count(marker) for marker in ("http://", "https://", "file://", "javascript:"))


def _html_preview_density(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    density = []
    for index, slide in enumerate(slides, start=1):
        bullets = slide.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = []
        text_values = [
            str(slide.get("title") or ""),
            str(slide.get("subtitle") or ""),
            str(slide.get("notes") or ""),
            *[str(bullet) for bullet in bullets],
        ]
        character_count = sum(len(value) for value in text_values)
        bullet_count = len([bullet for bullet in bullets if str(bullet).strip()])
        density.append(
            {
                "slide_index": int(slide.get("slide_index", index)),
                "character_count": character_count,
                "bullet_count": bullet_count,
                "visual_density_score": round((character_count / 1200) + (bullet_count / 12), 3),
                "overflow_risk": character_count > 1200 or bullet_count > 9,
            }
        )
    return density


def _write_pptx_source_map(
    path: Path,
    *,
    html_path: Path,
    manifest_path: Path,
    output_path: Path,
    manifest: dict[str, Any],
) -> None:
    slides = manifest.get("slides", []) if isinstance(manifest.get("slides"), list) else []
    payload = {
        "tool": EXPORT_PPTX_TOOL_NAME,
        "source_format": "html_slide_package",
        "output_format": "pptx",
        "html_path": html_path.as_posix(),
        "html_manifest_path": manifest_path.as_posix(),
        "pptx_path": output_path.as_posix(),
        "route": "html_manifest_to_editable_pptx_baseline",
        "slides": [
            {
                "slide_index": slide.get("slide_index"),
                "slide_id": slide.get("slide_id"),
                "dom_anchor": slide.get("dom_anchor"),
                "source_refs": slide.get("source_refs", []),
                "workbook_ranges": slide.get("workbook_ranges", []),
            }
            for slide in slides
            if isinstance(slide, dict)
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _html_deck_document(
    *,
    outline: dict[str, Any],
    slides: list[dict[str, Any]],
    manifest_path: Path,
    design_tokens: DesignTokens | None = None,
) -> str:
    tokens = design_tokens or resolve_theme("business_tech")
    title = str(outline.get("title") or "OKoffice Deck Preview")
    slide_markup = "\n".join(_html_slide(slide, tokens=tokens) for slide in slides)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8" />',
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
            "  <meta http-equiv=\"Content-Security-Policy\" "
            "content=\"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'none';\" />",
            f"  <meta name=\"okoffice:manifest\" content=\"{_html(manifest_path.name)}\" />",
            '  <meta name="okoffice:renderer" content="deck-html-slide-package-v0" />',
            f"  <title>{_html(title)}</title>",
            "  <style>",
            _html_deck_stylesheet(tokens),
            "  </style>",
            "</head>",
            '<body data-okoffice-deck-preview="true">',
            f'  <main class="okoffice-deck" data-okoffice-deck-preview="true" aria-label="{_html(title)}">',
            slide_markup,
            "  </main>",
            "</body>",
            "</html>",
        ]
    )


def _html_slide(slide: dict[str, Any], *, tokens: DesignTokens | None = None) -> str:
    template_id = slide.get("template_id")
    if template_id:
        rendered = render_template_slide(template_id, slide, tokens)
        if rendered:
            source_refs = slide.get("source_refs", [])
            src_markup = ""
            if source_refs:
                items = "\n".join(
                    f"<li>{_html(_source_ref_label(ref))}</li>" for ref in source_refs if isinstance(ref, dict)
                )
                src_markup = f'<aside class="source-map"><ul>{items}</ul></aside>'
            return (
                f'    <section class="okoffice-slide" id="slide-{int(slide["slide_index"])}" '
                f'data-slide-index="{int(slide["slide_index"])}" data-slide-id="{_html(slide.get("slide_id", ""))}" '
                f'data-template="{_html(template_id)}">'
                f'<div class="slide-content layout-template">{rendered}{src_markup}</div></section>'
            )
    layout = select_layout(slide)
    source_refs = slide.get("source_refs", [])
    workbook_ranges = slide.get("workbook_ranges", [])
    bullets = slide.get("bullets", [])
    source_markup = ""
    if source_refs:
        source_items = "\n".join(
            f"        <li>{_html(_source_ref_label(ref))}</li>" for ref in source_refs if isinstance(ref, dict)
        )
        source_markup = "\n".join(
            [
                "      <aside class=\"source-map\">",
                "        <h3>Source Map</h3>",
                "        <ul>",
                source_items,
                "        </ul>",
                "      </aside>",
            ]
        )
    range_markup = ""
    if workbook_ranges:
        range_items = "\n".join(
            f"        <li>{_html(_workbook_range_label(ref))}</li>" for ref in workbook_ranges if isinstance(ref, dict)
        )
        range_markup = "\n".join(
            [
                "      <aside class=\"source-map workbook-ranges\">",
                "        <h3>Workbook Ranges</h3>",
                "        <ul>",
                range_items,
                "        </ul>",
                "      </aside>",
            ]
        )
    bullet_markup = "\n".join(f"        <li>{_html(bullet)}</li>" for bullet in bullets)
    subtitle = str(slide.get("subtitle") or "")
    notes = str(slide.get("notes") or "")
    body_text = str(slide.get("body") or "")
    metrics = slide.get("metrics", [])
    # Build region elements from layout shapes
    regions: list[str] = []
    for shape_def in layout.shapes:
        purpose = shape_def.purpose
        area = shape_def.css_area
        if purpose == "kicker":
            regions.append(f"        <p class=\"slide-kicker\" style=\"grid-area: kicker\">Slide {int(slide['slide_index']):02d}</p>")
        elif purpose == "title":
            regions.append(f"        <h1 style=\"grid-area: title\">{_html(slide['title'])}</h1>")
        elif purpose == "subtitle" and subtitle:
            regions.append(f"        <p class=\"subtitle\" style=\"grid-area: subtitle\">{_html(subtitle)}</p>")
        elif purpose == "bullets" and bullet_markup:
            regions.append(f"        <ul style=\"grid-area: bullets\">{bullet_markup}</ul>")
        elif purpose in ("metric_1", "metric_2", "metric_3", "metric_4"):
            idx = {"metric_1": 0, "metric_2": 1, "metric_3": 2, "metric_4": 3}.get(purpose, 0)
            if metrics and idx < len(metrics):
                regions.append(f"        <div class=\"metric\" style=\"grid-area: {area}\"><span class=\"metric-value\">{_html(str(metrics[idx]))}</span></div>")
        elif purpose == "body_text":
            content = body_text or bullet_markup
            if content:
                if body_text:
                    regions.append(f"        <div class=\"body-text\" style=\"grid-area: {area}\">{_html(body_text)}</div>")
                elif bullets:
                    regions.append(f"        <ul style=\"grid-area: {area}\">{bullet_markup}</ul>")
        elif purpose in ("col_left_header", "col_right_header"):
            header_val = slide.get(purpose, "")
            if not header_val:
                header_val = "Option A" if purpose == "col_left_header" else "Option B"
            regions.append(f"        <div class=\"col-header\" style=\"grid-area: {area}\">{_html(str(header_val))}</div>")
        elif purpose == "col_left":
            left_bullets = bullets[:len(bullets) // 2 + len(bullets) % 2] if bullets else []
            if left_bullets:
                left_markup = "\n".join(f"        <li>{_html(b)}</li>" for b in left_bullets)
                regions.append(f"        <ul style=\"grid-area: {area}\">{left_markup}</ul>")
        elif purpose == "col_right":
            right_bullets = bullets[len(bullets) // 2 + len(bullets) % 2:] if bullets else []
            if right_bullets:
                right_markup = "\n".join(f"        <li>{_html(b)}</li>" for b in right_bullets)
                regions.append(f"        <ul style=\"grid-area: {area}\">{right_markup}</ul>")
        elif purpose in ("card_1", "card_2", "card_3"):
            card_idx = {"card_1": 0, "card_2": 1, "card_3": 2}.get(purpose, 0)
            card_bullets = bullets[card_idx * 2:(card_idx + 1) * 2] if bullets else []
            if card_bullets:
                card_markup = "\n".join(f"          <li>{_html(b)}</li>" for b in card_bullets)
                regions.append(f"        <div class=\"card\" style=\"grid-area: {area}\"><ul>{card_markup}</ul></div>")
            elif metrics and card_idx < len(metrics):
                regions.append(f"        <div class=\"card\" style=\"grid-area: {area}\"><span class=\"metric-value\">{_html(str(metrics[card_idx]))}</span></div>")
        elif purpose in ("stage_1", "stage_2", "stage_3", "stage_4"):
            stage_idx = {"stage_1": 0, "stage_2": 1, "stage_3": 2, "stage_4": 3}.get(purpose, 0)
            stage_bullets = bullets[stage_idx:stage_idx + 1] if bullets and stage_idx < len(bullets) else []
            if stage_bullets:
                stage_markup = "\n".join(f"          <li>{_html(b)}</li>" for b in stage_bullets)
                regions.append(f"        <div class=\"stage\" style=\"grid-area: {area}\"><span class=\"stage-number\">{stage_idx + 1}</span><ul>{stage_markup}</ul></div>")
        elif purpose == "source_list" and bullets:
            src_markup = "\n".join(f"        <li>{_html(b)}</li>" for b in bullets)
            regions.append(f"        <ol class=\"source-list\" style=\"grid-area: {area}\">{src_markup}</ol>")
        elif purpose == "image_area":
            regions.append(f"        <div class=\"image-placeholder\" style=\"grid-area: {area}\"><span>Image</span></div>")
        elif purpose in ("axis_y", "axis_x"):
            axis_val = slide.get(purpose, "")
            if axis_val:
                regions.append(f"        <div class=\"axis-label\" style=\"grid-area: {area}\">{_html(str(axis_val))}</div>")
        elif purpose == "grid_cells" and bullets:
            grid_markup = "\n".join(f"        <li>{_html(b)}</li>" for b in bullets)
            regions.append(f"        <ul class=\"grid-cells\" style=\"grid-area: {area}\">{grid_markup}</ul>")
    if notes:
        regions.append(f"        <p class=\"speaker-notes\">{_html(notes)}</p>")
    layout_class = f" layout-{layout.kind}"
    return "\n".join(
        [
            f'    <section class="okoffice-slide" id="slide-{int(slide["slide_index"])}" data-slide-index="{int(slide["slide_index"])}" data-slide-id="{_html(slide.get("slide_id", ""))}">',
            f"      <div class=\"slide-content{layout_class}\">",
            *[r for r in regions if r],
            source_markup,
            range_markup,
            "      </div>",
            "    </section>",
        ]
    )


def _html_deck_stylesheet(tokens: DesignTokens) -> str:
    vars_css = tokens_to_css(tokens)
    layout_rules = "\n".join(
        layout_to_css(layout) for layout in SLIDE_LAYOUTS.values() if layout.css_grid_template
    )
    return f"""
    {vars_css}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--color-bg); color: var(--color-dark); font-family: var(--font-body); }}
    .okoffice-deck {{ display: grid; gap: var(--slide-gap); padding: var(--slide-gap); }}
    .okoffice-slide {{
      width: min(100%, 1280px);
      aspect-ratio: 16 / 9;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d9ddd3;
      box-shadow: 0 18px 50px rgba(17, 24, 39, 0.12);
      overflow: hidden;
    }}
    .slide-content {{
      height: 100%;
      display: grid;
      gap: 18px;
      padding: var(--slide-padding);
    }}
    {layout_rules}
    .slide-kicker {{
      margin: 0;
      color: var(--color-accent);
      font-size: var(--size-kicker);
      font-family: var(--font-heading);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    h1 {{
      max-width: 960px;
      margin: 0;
      color: var(--color-dark);
      font-size: var(--size-heading);
      font-family: var(--font-heading);
      line-height: var(--line-height-heading);
      letter-spacing: -0.01em;
    }}
    .subtitle {{
      margin: 0;
      color: var(--color-primary);
      font-size: var(--size-subtitle);
      font-family: var(--font-heading);
      line-height: var(--line-height);
    }}
    ul {{
      align-self: start;
      margin: 0;
      padding-left: 28px;
      color: var(--color-dark);
      font-size: var(--size-body);
      font-family: var(--font-body);
      line-height: var(--line-height);
    }}
    li {{ margin: 12px 0; }}
    .metric {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
      border-radius: 8px;
      background: linear-gradient(135deg, var(--color-bg) 0%, #ffffff 100%);
      border: 1px solid #e5e7eb;
    }}
    .metric-value {{
      font-size: 36px;
      font-weight: 700;
      font-family: var(--font-heading);
      color: var(--color-dark);
      line-height: 1.1;
    }}
    .metric-label {{
      font-size: var(--size-caption);
      color: var(--color-accent);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-top: 8px;
    }}
    .card {{
      padding: 20px 18px;
      border-radius: 8px;
      background: #fafaf8;
      border: 1px solid #e5e7eb;
      display: flex;
      flex-direction: column;
      align-self: start;
    }}
    .card ul {{
      padding-left: 20px;
      margin: 0;
    }}
    .card li {{
      margin: 8px 0;
      font-size: var(--size-body);
    }}
    .card .metric-value {{
      font-size: 28px;
      text-align: center;
      display: block;
      margin-bottom: 8px;
    }}
    .stage {{
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 18px 12px;
      border-radius: 8px;
      background: var(--color-bg);
      border: 1px solid #d9ddd3;
      position: relative;
      align-self: start;
    }}
    .stage-number {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--color-accent);
      color: #ffffff;
      font-size: 14px;
      font-weight: 700;
      font-family: var(--font-heading);
      margin-bottom: 10px;
    }}
    .stage ul {{
      padding-left: 18px;
      margin: 0;
      text-align: left;
    }}
    .stage li {{
      margin: 6px 0;
      font-size: 14px;
    }}
    .slide-content.layout-process_flow .stage::after {{
      content: "→";
      position: absolute;
      right: -18px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 22px;
      color: var(--color-accent);
      font-weight: 700;
    }}
    .slide-content.layout-process_flow .stage:last-child::after {{
      display: none;
    }}
    .col-header {{
      font-size: 18px;
      font-weight: 700;
      font-family: var(--font-heading);
      color: var(--color-accent);
      text-align: center;
      padding: 8px 0;
      border-bottom: 2px solid var(--color-accent);
      margin-bottom: 4px;
    }}
    .body-text {{
      font-size: var(--size-body);
      font-family: var(--font-body);
      line-height: var(--line-height);
      color: var(--color-dark);
      max-width: 800px;
    }}
    .slide-content.layout-foreword .body-text {{
      font-size: 18px;
      line-height: 1.65;
      columns: 2;
      column-gap: 32px;
      column-rule: 1px solid #e5e7eb;
    }}
    .slide-content.layout-section_divider {{
      align-items: center;
      justify-content: center;
      text-align: center;
      border-top: 4px solid var(--color-accent);
    }}
    .slide-content.layout-section_divider h1 {{
      max-width: 100%;
      font-size: 48px;
    }}
    .slide-content.layout-quote {{
      align-items: center;
      justify-content: center;
      text-align: center;
    }}
    .slide-content.layout-quote h1 {{
      max-width: 100%;
      font-size: 28px;
      font-style: italic;
      font-family: var(--font-display);
      line-height: 1.4;
    }}
    .slide-content.layout-quote h1::before {{
      content: "\\201C";
      font-size: 64px;
      color: var(--color-accent);
      display: block;
      line-height: 0.5;
      margin-bottom: 12px;
      font-style: normal;
    }}
    .slide-content.layout-cta {{
      align-items: center;
      justify-content: center;
      text-align: center;
      background: linear-gradient(135deg, var(--color-bg) 0%, #ffffff 100%);
    }}
    .slide-content.layout-cta h1 {{
      max-width: 100%;
      font-size: 44px;
    }}
    .slide-content.layout-cta .subtitle {{
      font-size: 24px;
      color: var(--color-accent);
      font-weight: 600;
    }}
    .slide-content.layout-cover {{
      align-items: center;
      justify-content: center;
      text-align: center;
      border-left: 6px solid var(--color-accent);
    }}
    .slide-content.layout-cover h1 {{
      max-width: 100%;
      font-size: 52px;
    }}
    .image-placeholder {{
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--color-bg);
      border: 2px dashed #d9ddd3;
      border-radius: 8px;
      color: var(--color-accent);
      font-size: 14px;
      font-family: var(--font-body);
    }}
    .axis-label {{
      font-size: var(--size-caption);
      color: var(--color-accent);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-family: var(--font-heading);
    }}
    .grid-cells {{
      list-style: none;
      padding: 0;
      display: grid;
      gap: 8px;
    }}
    .grid-cells li {{
      padding: 8px 12px;
      background: var(--color-bg);
      border-radius: 4px;
      font-size: 13px;
      margin: 0;
    }}
    .source-list {{
      padding-left: 24px;
      font-size: 14px;
      line-height: 1.8;
      color: #4b5563;
    }}
    .source-list li {{
      margin: 4px 0;
    }}
    .speaker-notes {{
      margin: 0;
      color: #6b7280;
      font-size: var(--size-notes);
      font-family: var(--font-body);
    }}
    .source-map {{
      border-top: 1px solid #e5e7eb;
      padding-top: 10px;
      color: #4b5563;
      font-size: 13px;
    }}
    .source-map h3 {{
      margin: 0 0 6px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0;
      color: var(--color-primary);
    }}
    .source-map ul, .source-map li {{ font-size: 13px; line-height: 1.3; margin: 3px 0; }}
    @media (max-width: 760px) {{
      .okoffice-deck {{ padding: 14px; gap: 18px; }}
      .slide-content {{ padding: 30px; gap: 10px; }}
      h1 {{ font-size: 30px; }}
      .subtitle {{ font-size: 18px; }}
      ul {{ font-size: 18px; padding-left: 22px; }}
      .metric-value {{ font-size: 28px; }}
      .slide-content.layout-foreword .body-text {{ columns: 1; }}
    }}
    """.strip()


def _source_ref_label(ref: dict[str, Any]) -> str:
    for key in ("source_ref", "locator", "text", "source_path", "raw_source_ref"):
        value = ref.get(key)
        if value:
            return str(value)
    return json.dumps(ref, ensure_ascii=False, sort_keys=True)


def _workbook_range_label(ref: dict[str, Any]) -> str:
    sheet = str(ref.get("sheet_name") or "").strip()
    range_ref = str(ref.get("range_ref") or "").strip()
    if sheet and range_ref:
        return f"{sheet}!{range_ref}"
    return range_ref or sheet or json.dumps(ref, ensure_ascii=False, sort_keys=True)


def _html(value: object) -> str:
    return html.escape(str(value), quote=True)


def _create_deck_from_outline(
    outline: dict[str, Any],
    output_path: str | Path,
    *,
    tool_name: str,
    input_source: str = "outline",
    design_tokens: DesignTokens | None = None,
) -> ToolResult:
    try:
        output = resolve_output_path(output_path)
    except OKofficeException as exc:
        return failed_result(tool_name, exc.to_error())

    slides = _outline_slides(outline)
    if not slides:
        return failed_result(
            tool_name,
            OKofficeError(
                code="unsafe_input_rejected",
                message=f"{tool_name} requires at least one slide.",
            ),
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    _write_outline_pptx(output, slides, design_tokens)
    artifact = build_artifact(output, tool_name)
    inspect_result = inspect_deck_presentation(output)
    inspect_status = inspect_result.validation.status if inspect_result.validation is not None else "failed"
    return ToolResult(
        job_id=job_id(),
        status="succeeded" if inspect_result.status == "succeeded" else "failed",
        tool=tool_name,
        artifacts=[artifact],
        validation=ValidationReport(
            status=inspect_status,
            checks=[
                ValidationCheck(
                    name="outline_normalized",
                    status="passed",
                    details={
                        "slide_count": len(slides),
                        "total_bullet_count": sum(len(slide["bullets"]) for slide in slides),
                    },
                ),
                ValidationCheck(
                    name="pptx_written",
                    status="passed" if inspect_result.status == "succeeded" else "failed",
                    details={"path": output.as_posix(), "mime_type": PPTX_MIME_TYPE},
                ),
            ],
        ),
        warnings=list(inspect_result.warnings),
        usage={
            "summary": {
                "slide_count": len(slides),
                "total_bullet_count": sum(len(slide["bullets"]) for slide in slides),
                "text_run_count": inspect_result.usage.get("presentation", {}).get("text_run_count", 0),
            },
            "input": {"source": input_source},
            "presentation": {
                "path": output.as_posix(),
                "format": "pptx",
                "artifact_id": artifact.artifact_id,
            },
            "slides": slides,
        },
        next_recommended_tools=[
            "deck.inspect.presentation",
            "deck.validate.presentation",
            "office.workflow.sheet_to_deck",
            "office.workflow.board_pack",
        ],
    )


def _resolve_design_tokens(payload: dict[str, Any]) -> DesignTokens:
    theme_name = str(payload.get("theme") or payload.get("design_tokens", {}).get("theme") or "business_tech")
    raw = payload.get("design_tokens") or {}
    base = resolve_theme(theme_name)
    if not raw:
        return base
    overrides = {k: v for k, v in raw.items() if v is not None}
    return base.model_copy(update=overrides)


def _run_design_token_taste_qa(manifest: dict[str, Any]) -> dict[str, Any]:
    from okoffice.office.deck_taste_qa import compute_taste_score

    tokens = _resolve_design_tokens(manifest)
    return compute_taste_score(tokens)


def _presentation_outline(outline_or_plan: dict[str, Any]) -> dict[str, Any]:
    outline = outline_or_plan.get("outline") if isinstance(outline_or_plan, dict) else None
    return outline if isinstance(outline, dict) else outline_or_plan


def _presentation_input_source(outline_or_plan: dict[str, Any]) -> str:
    if isinstance(outline_or_plan.get("outline"), dict):
        return "composition_plan"
    return "outline"


def _outline_slides(outline: dict[str, Any]) -> list[dict[str, Any]]:
    raw_slides = outline.get("slides", [])
    if not isinstance(raw_slides, list):
        raw_slides = []
    slides = []
    for index, raw_slide in enumerate(raw_slides, start=1):
        if not isinstance(raw_slide, dict):
            continue
        title = str(raw_slide.get("title") or f"Slide {index}").strip()
        subtitle = str(raw_slide.get("subtitle") or "").strip()
        bullets = raw_slide.get("bullets", [])
        if not isinstance(bullets, list):
            bullets = [bullets]
        normalized_bullets = [str(bullet).strip() for bullet in bullets if str(bullet).strip()]
        notes = str(raw_slide.get("notes") or "").strip()
        layout = str(raw_slide.get("layout") or "").strip() or None
        metrics = raw_slide.get("metrics", [])
        if not isinstance(metrics, list):
            metrics = [metrics]
        normalized_metrics = [str(m).strip() for m in metrics if str(m).strip()]
        body = str(raw_slide.get("body") or "").strip()
        slide_dict: dict[str, Any] = {
            "slide_index": index,
            "title": title,
            "subtitle": subtitle,
            "bullets": normalized_bullets,
            "bullet_count": len(normalized_bullets),
            "notes": notes,
            "layout": layout,
            "metrics": normalized_metrics,
            "body": body,
        }
        for key in ("col_left_header", "col_right_header", "axis_y", "axis_x",
                     "template_id", "source_refs", "workbook_ranges"):
            val = raw_slide.get(key)
            if val is not None:
                slide_dict[key] = val
        slides.append(slide_dict)
    return slides


def _write_outline_pptx(path: Path, slides: list[dict[str, Any]], design_tokens: DesignTokens | None = None) -> None:
    pptx_defaults = tokens_to_pptx_defaults(design_tokens) if design_tokens else None
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(slides)))
        archive.writestr("_rels/.rels", _root_relationships())
        archive.writestr("ppt/presentation.xml", _presentation_xml(len(slides)))
        archive.writestr("ppt/_rels/presentation.xml.rels", _presentation_relationships(len(slides)))
        for index, slide in enumerate(slides, start=1):
            archive.writestr(f"ppt/slides/slide{index}.xml", _slide_xml(slide, pptx_defaults))
            archive.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", _empty_relationships())


def _content_types(slide_count: int) -> str:
    slide_overrides = "".join(
        '<Override PartName="/ppt/slides/slide{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'.format(
            index=index
        )
        for index in range(1, slide_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        f"{slide_overrides}</Types>"
    )


def _root_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="ppt/presentation.xml"/>'
        "</Relationships>"
    )


def _presentation_xml(slide_count: int) -> str:
    slide_ids = "".join(
        f'<p:sldId id="{255 + index}" r:id="rId{index}"/>' for index in range(1, slide_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<p:sldIdLst>{slide_ids}</p:sldIdLst>"
        '<p:sldSz cx="12192000" cy="6858000" type="wide"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    )


def _presentation_relationships(slide_count: int) -> str:
    relationships = "".join(
        '<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        'Target="slides/slide{index}.xml"/>'.format(index=index)
        for index in range(1, slide_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}</Relationships>"
    )


def _empty_relationships() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )


def _slide_xml(slide: dict[str, Any], pptx_defaults: dict | None = None) -> str:
    d = pptx_defaults or {}
    layout = select_layout(slide)
    shape_defs = layout_to_pptx_shapes(layout, slide, d)
    shape_xml = "".join(
        _text_shape(
            shape_id=s["shape_id"],
            name=s["name"],
            x=s["x"],
            y=s["y"],
            cx=s["cx"],
            cy=s["cy"],
            lines=s["lines"],
            bullet=s["bullet"],
            font=s["font"],
            size_pt=s["size_pt"],
            color_hex=s["color_hex"],
            bold=s["bold"],
        )
        for s in shape_defs
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<p:cSld><p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"Group\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        f"{shape_xml}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
    )


def _text_shape(
    *,
    shape_id: int,
    name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    lines: list[str],
    bullet: bool = False,
    font: str = "Arial",
    size_pt: float = 12.0,
    color_hex: str = "111827",
    bold: bool = False,
) -> str:
    paragraphs = "".join(_paragraph(line, bullet=bullet, font=font, size_pt=size_pt, color_hex=color_hex, bold=bold) for line in lines if str(line).strip())
    return (
        "<p:sp>"
        f'<p:nvSpPr><p:cNvPr id="{shape_id}" name="{_xml(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>"
        f"<p:txBody><a:bodyPr wrap=\"square\"/><a:lstStyle/>{paragraphs}</p:txBody>"
        "</p:sp>"
    )


def _paragraph(text: str, *, bullet: bool, font: str = "Arial", size_pt: float = 12.0, color_hex: str = "111827", bold: bool = False) -> str:
    bullet_xml = "<a:buChar char=\"•\"/>" if bullet else ""
    bold_attr = ' b="1"' if bold else ""
    rpr = f'<a:rPr lang="en-US" altLang="zh-CN" sz="{int(size_pt * 100)}" dirty="0"{bold_attr}><a:latin typeface="{font}"/><a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill></a:rPr>'
    return f"<a:p><a:pPr>{bullet_xml}</a:pPr><a:r>{rpr}<a:t>{_xml(text)}</a:t></a:r></a:p>"


def _xml(value: object) -> str:
    return html.escape(str(value), quote=True)


def _slide_text_run_count(path: Path, slide_members: list[str]) -> int:
    count = 0
    for member in slide_members:
        slide_root = read_xml(path, member)
        if slide_root is not None:
            count += len(slide_root.findall(".//a:t", DECK_NS))
    return count


def _slide_validation_summaries(path: Path, slide_members: list[str]) -> list[dict[str, Any]]:
    summaries = []
    for index, member in enumerate(slide_members, start=1):
        slide_root = read_xml(path, member)
        texts = []
        if slide_root is not None:
            texts = [str(text_node.text or "") for text_node in slide_root.findall(".//a:t", DECK_NS)]
        nonempty_texts = [text.strip() for text in texts if text.strip()]
        placeholder_texts = [text for text in nonempty_texts if _looks_like_placeholder(text)]
        summaries.append(
            {
                "slide_index": index,
                "member": member,
                "text_run_count": len(texts),
                "nonempty_text_run_count": len(nonempty_texts),
                "character_count": sum(len(text) for text in nonempty_texts),
                "is_blank": not nonempty_texts,
                "placeholder_text_count": len(placeholder_texts),
                "placeholder_texts": placeholder_texts[:10],
            }
        )
    return summaries


def _missing_slide_relationship_targets(slide_members: list[str], relationship_root: object | None) -> list[str]:
    if relationship_root is None:
        return list(slide_members)
    targets = {
        str(relationship.get("Target") or "").replace("\\", "/")
        for relationship in relationship_root.findall(".//rel:Relationship", REL_NS)
    }
    expected_targets = {member.replace("ppt/", "") for member in slide_members}
    return sorted(expected_targets - targets)


def _looks_like_placeholder(text: str) -> bool:
    normalized = text.lower()
    return any(marker.lower() in normalized for marker in PLACEHOLDER_MARKERS)


def _validation_check(
    name: str,
    *,
    condition: bool,
    failed_status: str,
    passed_details: dict[str, Any],
    failed_message: str,
) -> ValidationCheck:
    if condition:
        return ValidationCheck(name=name, status="passed", details=passed_details)
    return ValidationCheck(
        name=name,
        status=failed_status,
        details=passed_details,
        message=failed_message,
    )


def _media_count(names: set[str]) -> int:
    return sum(1 for name in names if name.startswith("ppt/media/"))
