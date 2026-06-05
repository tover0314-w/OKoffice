from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

from agentpdf.office.ir import DeckLocator
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path


P_NS = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE_R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"
CORE_NS = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
PRESENTATION_PART = "ppt/presentation.xml"
PRESENTATION_RELS_PART = "ppt/_rels/presentation.xml.rels"


def inspect_deck_presentation(path: str | Path) -> ToolResult:
    tool = "deck.inspect.presentation"
    try:
        resolved = resolve_input_path(path)
        usage, warnings = _inspect_pptx(resolved)
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=tool,
            validation=_validation_report(resolved, usage, warnings),
            warnings=warnings,
            usage=usage,
            next_recommended_tools=[
                "deck.validation.contact_sheet",
                "deck.validation.presentation",
                "office.context.build_packet",
            ],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def _inspect_pptx(path: Path) -> tuple[dict[str, Any], list[str]]:
    if path.suffix.lower() not in {".pptx", ".pptm"} or not zipfile.is_zipfile(path):
        raise AgentPDFException(
            "unsupported_file_type",
            f"Deck inspect requires a readable PPTX/PPTM package: {path.name}",
            details={"path": path.as_posix()},
        )
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        unsafe_entries = [name for name in names if _unsafe_zip_entry(name)]
        if unsafe_entries:
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Presentation package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_entries},
            )
        if PRESENTATION_PART not in names:
            raise AgentPDFException(
                "unsupported_file_type",
                "Presentation package is missing ppt/presentation.xml.",
                details={"path": path.as_posix()},
            )
        presentation = ElementTree.fromstring(archive.read(PRESENTATION_PART))
        presentation_rels = _read_relationships(archive, PRESENTATION_RELS_PART, PRESENTATION_PART, names)
        external_relationships = _external_relationships(archive, names)
        slides, shapes, notes, charts, media = _read_slides(archive, presentation, presentation_rels, names)
        themes = _read_themes(archive, presentation_rels, names)
        metadata = _read_core_metadata(archive, names)
        package = _package_markers(path, names, external_relationships)

    if package["macro_enabled"]:
        warnings.append("Macro-enabled presentation package markers were detected; macros are not executed.")
    if package["has_external_relationships"]:
        warnings.append("External presentation relationship targets were detected.")

    usage = {
        "file": {
            "path": path.as_posix(),
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        },
        "summary": {
            "slide_count": len(slides),
            "slide_with_notes_count": len([slide for slide in slides if slide["has_notes"]]),
            "shape_count": len(shapes),
            "text_run_count": sum(len(slide["text_runs"]) for slide in slides),
            "chart_count": len(charts),
            "media_count": len(media),
            "theme_count": len(themes),
            "external_link_count": len(external_relationships),
        },
        "metadata": metadata,
        "package": package,
        "slides": slides,
        "shapes": shapes,
        "notes": notes,
        "charts": charts,
        "media": media,
        "themes": themes,
        "layout": {
            "rendered_layout_claimed": False,
            "render_evidence": "not_available_in_local_pptx_inspect",
        },
    }
    return usage, warnings


def _read_slides(
    archive: zipfile.ZipFile,
    presentation: ElementTree.Element,
    presentation_rels: dict[str, dict[str, str]],
    names: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    slides: list[dict[str, Any]] = []
    shapes: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []

    for index, slide_id_node in enumerate(presentation.findall(f"{P_NS}sldIdLst/{P_NS}sldId"), start=1):
        rel_id = slide_id_node.attrib.get(f"{OFFICE_R_NS}id")
        slide_id = slide_id_node.attrib.get("id")
        part = presentation_rels.get(str(rel_id), {}).get("target") if rel_id else None
        slide_shapes: list[dict[str, Any]] = []
        slide_notes: list[dict[str, Any]] = []
        slide_charts: list[dict[str, Any]] = []
        slide_media: list[dict[str, Any]] = []
        text_runs: list[str] = []
        title: str | None = None
        if part and part in names:
            slide_root = ElementTree.fromstring(archive.read(part))
            slide_rels = _slide_relationships(archive, part, names)
            slide_shapes = _read_shapes(slide_root, index, slide_id)
            text_runs = [text for shape in slide_shapes for text in shape["text_runs"]]
            title = _slide_title(slide_shapes)
            slide_notes = _read_notes(archive, index, slide_id, slide_rels, names)
            slide_charts = _read_charts(index, slide_id, slide_rels, names)
            slide_media = _read_media(index, slide_id, slide_rels, names)

        shapes.extend(slide_shapes)
        notes.extend(slide_notes)
        charts.extend(slide_charts)
        media.extend(slide_media)
        slides.append(
            {
                "slide_number": index,
                "slide_id": slide_id,
                "part": part,
                "title": title,
                "text_runs": text_runs,
                "shape_count": len(slide_shapes),
                "chart_count": len(slide_charts),
                "media_count": len(slide_media),
                "has_notes": bool(slide_notes),
                "locator": _locator(slide=index, slide_id=slide_id),
            }
        )

    return slides, shapes, notes, charts, media


def _read_shapes(slide_root: ElementTree.Element, slide_number: int, slide_id: str | None) -> list[dict[str, Any]]:
    shapes = []
    for shape in slide_root.findall(f".//{P_NS}sp"):
        properties = shape.find(f"{P_NS}nvSpPr")
        c_nv_pr = properties.find(f"{P_NS}cNvPr") if properties is not None else None
        nv_pr = properties.find(f"{P_NS}nvPr") if properties is not None else None
        placeholder = _placeholder(nv_pr)
        shape_id = c_nv_pr.attrib.get("id") if c_nv_pr is not None else None
        name = c_nv_pr.attrib.get("name") if c_nv_pr is not None else None
        text_runs = _text_runs(shape)
        shapes.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "shape_id": shape_id,
                "name": name,
                "placeholder": placeholder,
                "text": "\n".join(text_runs),
                "text_runs": text_runs,
                "locator": _locator(
                    slide=slide_number,
                    slide_id=slide_id,
                    shape_id=shape_id,
                    placeholder=placeholder,
                ),
            }
        )
    return shapes


def _placeholder(nv_pr: ElementTree.Element | None) -> str | None:
    if nv_pr is None:
        return None
    ph = nv_pr.find(f"{P_NS}ph")
    if ph is None:
        return None
    return ph.attrib.get("type") or ph.attrib.get("idx")


def _slide_title(shapes: list[dict[str, Any]]) -> str | None:
    for shape in shapes:
        if shape["placeholder"] in {"title", "ctrTitle"} and shape["text"]:
            return str(shape["text"])
    for shape in shapes:
        if shape["text"]:
            return str(shape["text"])
    return None


def _read_notes(
    archive: zipfile.ZipFile,
    slide_number: int,
    slide_id: str | None,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    notes = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/notesSlide") or relationship["target"] not in names:
            continue
        root = ElementTree.fromstring(archive.read(relationship["target"]))
        notes.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "part": relationship["target"],
                "text": "\n".join(_text_runs(root)),
                "locator": _locator(slide=slide_number, slide_id=slide_id, notes=True),
            }
        )
    return notes


def _read_charts(
    slide_number: int,
    slide_id: str | None,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    charts = []
    for relationship in relationships.values():
        if not relationship["type"].endswith("/chart") or relationship["target"] not in names:
            continue
        chart_id = PurePosixPath(relationship["target"]).stem
        charts.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "chart_id": chart_id,
                "part": relationship["target"],
                "locator": _locator(slide=slide_number, slide_id=slide_id, shape_id=chart_id),
            }
        )
    return charts


def _read_media(
    slide_number: int,
    slide_id: str | None,
    relationships: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    media = []
    for relationship in relationships.values():
        kind = _media_kind(relationship["type"])
        if kind is None or relationship["target"] not in names:
            continue
        media_id = PurePosixPath(relationship["target"]).stem
        media.append(
            {
                "slide_number": slide_number,
                "slide_id": slide_id,
                "kind": kind,
                "media_id": media_id,
                "part": relationship["target"],
                "locator": _locator(slide=slide_number, slide_id=slide_id, shape_id=media_id),
            }
        )
    return media


def _media_kind(relationship_type: str) -> str | None:
    suffix = relationship_type.rsplit("/", maxsplit=1)[-1]
    if suffix in {"image", "audio", "video", "media"}:
        return suffix
    return None


def _read_themes(
    archive: zipfile.ZipFile,
    presentation_rels: dict[str, dict[str, str]],
    names: set[str],
) -> list[dict[str, Any]]:
    theme_parts = {
        relationship["target"]
        for relationship in presentation_rels.values()
        if relationship["type"].endswith("/theme") and relationship["target"] in names
    }
    theme_parts.update(name for name in names if name.startswith("ppt/theme/") and name.endswith(".xml"))
    themes = []
    for part in sorted(theme_parts):
        root = ElementTree.fromstring(archive.read(part))
        themes.append(
            {
                "name": root.attrib.get("name"),
                "part": part,
            }
        )
    return themes


def _read_relationships(
    archive: zipfile.ZipFile,
    rels_part: str,
    source_part: str,
    names: set[str],
) -> dict[str, dict[str, str]]:
    if rels_part not in names:
        return {}
    root = ElementTree.fromstring(archive.read(rels_part))
    relationships = {}
    for relationship in root.findall(f"{REL_NS}Relationship"):
        rel_id = str(relationship.attrib.get("Id") or "")
        target = str(relationship.attrib.get("Target") or "")
        relationships[rel_id] = {
            "id": rel_id,
            "type": str(relationship.attrib.get("Type") or ""),
            "target": _resolve_target(source_part, target),
            "target_mode": str(relationship.attrib.get("TargetMode") or ""),
        }
    return relationships


def _slide_relationships(archive: zipfile.ZipFile, slide_part: str, names: set[str]) -> dict[str, dict[str, str]]:
    return _read_relationships(archive, _rels_part_for(slide_part), slide_part, names)


def _rels_part_for(part: str) -> str:
    path = PurePosixPath(part)
    return str(path.parent / "_rels" / f"{path.name}.rels")


def _resolve_target(source_part: str, target: str) -> str:
    if "://" in target:
        return target
    if target.startswith("/"):
        return target.lstrip("/")
    path = PurePosixPath(source_part).parent / target
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def _external_relationships(archive: zipfile.ZipFile, names: set[str]) -> list[dict[str, str]]:
    relationships = []
    for name in sorted(names):
        if not name.endswith(".rels"):
            continue
        root = ElementTree.fromstring(archive.read(name))
        for relationship in root.findall(f"{REL_NS}Relationship"):
            if relationship.attrib.get("TargetMode") == "External":
                relationships.append(
                    {
                        "relationship_part": name,
                        "type": str(relationship.attrib.get("Type") or ""),
                        "target": str(relationship.attrib.get("Target") or ""),
                    }
                )
    return relationships


def _read_core_metadata(archive: zipfile.ZipFile, names: set[str]) -> dict[str, Any]:
    if "docProps/core.xml" not in names:
        return {}
    root = ElementTree.fromstring(archive.read("docProps/core.xml"))
    return {
        "title": _first_text(root, f"{DC_NS}title"),
        "creator": _first_text(root, f"{DC_NS}creator"),
        "last_modified_by": _first_text(root, f"{CORE_NS}lastModifiedBy"),
    }


def _package_markers(path: Path, names: set[str], external_relationships: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "package_type": "ooxml_pptx",
        "zip_entry_count": len(names),
        "macro_enabled": path.suffix.lower() == ".pptm" or any(name.lower().endswith("vbaproject.bin") for name in names),
        "has_external_relationships": bool(external_relationships),
        "external_relationships": external_relationships,
        "unsafe_package_entries": [name for name in names if _unsafe_zip_entry(name)],
    }


def _unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _text_runs(element: ElementTree.Element) -> list[str]:
    return [node.text for node in element.iter() if node.tag == f"{A_NS}t" and node.text]


def _first_text(root: ElementTree.Element, tag: str) -> str | None:
    node = root.find(tag)
    return node.text if node is not None else None


def _locator(**kwargs: Any) -> dict[str, Any]:
    return DeckLocator(**kwargs).model_dump(mode="json", exclude_none=True)


def _validation_report(path: Path, usage: dict[str, Any], warnings: list[str]) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="input_path_safe", status="passed", message="Input path passed local safety checks."),
            ValidationCheck(name="presentation_xml_present", status="passed", details={"path": path.as_posix()}),
            ValidationCheck(name="structure_extracted", status="passed", details=usage["summary"]),
            ValidationCheck(
                name="layout_claim_explicit",
                status="passed",
                details=usage["layout"],
            ),
        ],
        warnings=warnings,
    )


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
