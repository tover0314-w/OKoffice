from __future__ import annotations

import html
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "deck.create.presentation"
S_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE_R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
WORKBOOK_PART = "xl/workbook.xml"
WORKBOOK_RELS_PART = "xl/_rels/workbook.xml.rels"


def create_deck_presentation(
    *,
    workbook_path: str | Path,
    output_path: str | Path,
    title: str | None = None,
    profile: str = "board_review",
    style: dict[str, Any] | None = None,
) -> ToolResult:
    try:
        workbook = resolve_input_path(workbook_path)
        output = resolve_output_path(output_path)
        if output.suffix.lower() != ".pptx":
            raise AgentPDFException(
                "unsupported_file_type",
                "deck.create.presentation writes .pptx output files.",
                details={"output_path": output.as_posix()},
            )

        data = _load_evidence_workbook(workbook)
        deck_title = title or _default_title(workbook)
        style_tokens = _normalize_style(style, profile=profile)
        slides = _compose_slides(data=data, title=deck_title, profile=profile)
        _write_pptx_package(output, slides, title=deck_title, style=style_tokens)

        inspected = inspect_deck_presentation(output)
        if inspected.status != "succeeded":
            raise AgentPDFException(
                "output_validation_failed",
                "Generated presentation could not be inspected.",
                details=inspected.error.model_dump(mode="json") if inspected.error else {},
            )

        warnings = _warnings(data)
        artifacts = [build_artifact(output, source_tool=TOOL_NAME)]
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            artifacts=artifacts,
            validation=_validation_report(data, output, inspected, warnings),
            warnings=warnings,
            usage=_usage(data, output, workbook, profile, slides, style_tokens),
            next_recommended_tools=[
                "deck.inspect.presentation",
                "deck.validation.contact_sheet",
                "deck.validation.presentation",
                "office.workflow.sheet_to_deck",
                "office.bundle.export",
            ],
        )
    except AgentPDFException as exc:
        return _failed(exc.to_error())
    except (KeyError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        return _failed(AgentPDFError(code="invalid_input", message=str(exc)))


def _load_evidence_workbook(path: Path) -> dict[str, Any]:
    if path.suffix.lower() not in {".xlsx", ".xlsm"} or not zipfile.is_zipfile(path):
        raise AgentPDFException(
            "unsupported_file_type",
            f"deck.create.presentation requires a readable evidence XLSX/XLSM workbook: {path.name}",
            details={"path": path.as_posix()},
        )
    with zipfile.ZipFile(path) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        unsafe_entries = [name for name in names if _unsafe_zip_entry(name)]
        if unsafe_entries:
            raise AgentPDFException(
                "unsafe_input_rejected",
                "Workbook package contains unsafe ZIP entry names.",
                details={"unsafe_package_entries": unsafe_entries},
            )
        if WORKBOOK_PART not in names:
            raise AgentPDFException(
                "unsupported_file_type",
                "Workbook package is missing xl/workbook.xml.",
                details={"path": path.as_posix()},
            )

        shared_strings = _read_shared_strings(archive, names)
        workbook = ElementTree.fromstring(archive.read(WORKBOOK_PART))
        workbook_rels = _read_relationships(archive, WORKBOOK_RELS_PART, WORKBOOK_PART, names)
        sheets = _read_sheets(archive, workbook, workbook_rels, names, shared_strings)

    evidence_rows = _table_dicts(sheets.get("Evidence", []))
    source_map_rows = _table_dicts(sheets.get("SourceMap", []))
    if not evidence_rows:
        raise AgentPDFException(
            "invalid_input",
            "Evidence workbook must contain an Evidence sheet with at least one data row.",
            details={"path": path.as_posix()},
        )
    if not source_map_rows:
        raise AgentPDFException(
            "invalid_input",
            "Evidence workbook must contain a SourceMap sheet.",
            details={"path": path.as_posix()},
        )
    row_ids = _ordered_row_ids(source_map_rows)
    rows = []
    for index, values in enumerate(evidence_rows, start=1):
        row_id = row_ids[index - 1] if index <= len(row_ids) else f"row_{index:03d}"
        field_sources = [row for row in source_map_rows if row.get("row_id") == row_id]
        rows.append(
            {
                "row_id": row_id,
                "values": values,
                "source_rows": field_sources,
                "source_refs": _unique([row.get("source_ref", "") for row in field_sources]),
            }
        )
    return {
        "headers": list(evidence_rows[0].keys()),
        "rows": rows,
        "source_map_rows": source_map_rows,
    }


def _read_sheets(
    archive: zipfile.ZipFile,
    workbook: ElementTree.Element,
    workbook_rels: dict[str, dict[str, str]],
    names: set[str],
    shared_strings: list[str],
) -> dict[str, list[list[str]]]:
    sheets: dict[str, list[list[str]]] = {}
    for sheet in workbook.findall(f"{S_NS}sheets/{S_NS}sheet"):
        name = str(sheet.attrib.get("name") or "")
        rel_id = sheet.attrib.get(f"{OFFICE_R_NS}id")
        part = workbook_rels.get(str(rel_id), {}).get("target") if rel_id else None
        if not name or not part or part not in names:
            continue
        root = ElementTree.fromstring(archive.read(part))
        sheets[name] = _worksheet_rows(root, shared_strings)
    return sheets


def _worksheet_rows(root: ElementTree.Element, shared_strings: list[str]) -> list[list[str]]:
    rows = []
    for row in root.findall(f"{S_NS}sheetData/{S_NS}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{S_NS}c"):
            ref = str(cell.attrib.get("r") or "")
            column = _column_index(ref)
            if column == 0:
                continue
            cells[column] = _cell_text(cell, shared_strings)
        if cells:
            width = max(cells)
            rows.append([cells.get(index, "") for index in range(1, width + 1)])
    return rows


def _cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    inline = cell.find(f"{S_NS}is/{S_NS}t")
    if inline is not None:
        return inline.text or ""
    value = cell.find(f"{S_NS}v")
    if value is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text or "0")
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text or ""


def _read_shared_strings(archive: zipfile.ZipFile, names: set[str]) -> list[str]:
    if "xl/sharedStrings.xml" not in names:
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for item in root.findall(f"{S_NS}si"):
        values.append("".join(node.text or "" for node in item.iter() if node.tag == f"{S_NS}t"))
    return values


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


def _table_dicts(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    headers = [header.strip() for header in rows[0]]
    records = []
    for row in rows[1:]:
        records.append({header: row[index] if index < len(row) else "" for index, header in enumerate(headers) if header})
    return records


def _compose_slides(data: dict[str, Any], title: str, profile: str) -> list[dict[str, Any]]:
    slides = [
        {
            "title": title,
            "body": [f"Profile: {profile}", f"Evidence rows: {len(data['rows'])}"],
            "notes": "",
            "source_refs": [],
            "row_id": None,
        }
    ]
    for row in data["rows"]:
        values = row["values"]
        slide_title = values.get("vendor") or _first_non_empty(values) or str(row["row_id"])
        body = [
            f"{_field_label(field)}: {value}"
            for field, value in values.items()
            if value and field != "vendor"
        ]
        source_refs = list(row["source_refs"])
        slides.append(
            {
                "title": slide_title,
                "body": body or ["No populated evidence fields."],
                "notes": f"Sources: {', '.join(source_refs)}" if source_refs else "Sources: none",
                "source_refs": source_refs,
                "row_id": row["row_id"],
            }
        )
    return slides


def _write_pptx_package(path: Path, slides: list[dict[str, Any]], title: str, style: dict[str, str]) -> None:
    notes_slides = [slide for slide in slides if slide["notes"]]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(slides), len(notes_slides)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("docProps/core.xml", _core_props_xml(title))
        archive.writestr("docProps/app.xml", _app_props_xml(len(slides)))
        archive.writestr("ppt/presentation.xml", _presentation_xml(len(slides)))
        archive.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels_xml(len(slides)))
        archive.writestr("ppt/theme/theme1.xml", _theme_xml(style))
        archive.writestr("ppt/slideMasters/slideMaster1.xml", _slide_master_xml())
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", _slide_layout_xml())
        notes_index = 0
        for slide_index, slide in enumerate(slides, start=1):
            archive.writestr(f"ppt/slides/slide{slide_index}.xml", _slide_xml(slide))
            if slide["notes"]:
                notes_index += 1
                archive.writestr(f"ppt/slides/_rels/slide{slide_index}.xml.rels", _slide_rels_xml(notes_index))
                archive.writestr(f"ppt/notesSlides/notesSlide{notes_index}.xml", _notes_slide_xml(slide["notes"]))


def _content_types_xml(slide_count: int, notes_count: int) -> str:
    slide_overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for index in range(1, slide_count + 1)
    )
    notes_overrides = "".join(
        f'<Override PartName="/ppt/notesSlides/notesSlide{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
        for index in range(1, notes_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        f"{slide_overrides}{notes_overrides}"
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="ppt/presentation.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _presentation_xml(slide_count: int) -> str:
    slide_ids = "".join(
        f'<p:sldId id="{255 + index}" r:id="rId{index}"/>'
        for index in range(1, slide_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<p:sldIdLst>{slide_ids}</p:sldIdLst>"
        '<p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    )


def _presentation_rels_xml(slide_count: int) -> str:
    slide_rels = "".join(
        f'<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        f'Target="slides/slide{index}.xml"/>'
        for index in range(1, slide_count + 1)
    )
    theme_id = slide_count + 1
    master_id = slide_count + 2
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{slide_rels}"
        f'<Relationship Id="rId{theme_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
        'Target="theme/theme1.xml"/>'
        f'<Relationship Id="rId{master_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
        'Target="slideMasters/slideMaster1.xml"/>'
        "</Relationships>"
    )


def _slide_rels_xml(notes_index: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdNotes1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" '
        f'Target="../notesSlides/notesSlide{notes_index}.xml"/>'
        "</Relationships>"
    )


def _slide_xml(slide: dict[str, Any]) -> str:
    body = "\n".join(str(line) for line in slide["body"])
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<p:cSld><p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        f'{_shape_xml(2, "Title", str(slide["title"]), placeholder="title")}'
        f'{_shape_xml(3, "Evidence", body, placeholder="body")}'
        "</p:spTree></p:cSld>"
        "</p:sld>"
    )


def _shape_xml(shape_id: int, name: str, text: str, *, placeholder: str) -> str:
    paragraphs = "".join(
        f"<a:p><a:r><a:t>{_xml_text(line)}</a:t></a:r></a:p>"
        for line in str(text).splitlines()
        if line
    ) or "<a:p/>"
    return (
        "<p:sp>"
        "<p:nvSpPr>"
        f'<p:cNvPr id="{shape_id}" name="{_xml_attr(name)}"/>'
        "<p:cNvSpPr/><p:nvPr>"
        f'<p:ph type="{_xml_attr(placeholder)}"/>'
        "</p:nvPr></p:nvSpPr>"
        "<p:spPr/>"
        f"<p:txBody><a:bodyPr/><a:lstStyle/>{paragraphs}</p:txBody>"
        "</p:sp>"
    )


def _notes_slide_xml(notes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:notes xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<p:cSld><p:spTree>"
        "<p:sp><p:txBody><a:bodyPr/><a:lstStyle/>"
        f"<a:p><a:r><a:t>{_xml_text(notes)}</a:t></a:r></a:p>"
        "</p:txBody></p:sp>"
        "</p:spTree></p:cSld>"
        "</p:notes>"
    )


def _theme_xml(style: dict[str, str]) -> str:
    theme_name = _xml_attr(style["theme_name"])
    primary = _xml_attr(style["primary_color"])
    accent = _xml_attr(style["accent_color"])
    font = _xml_attr(style["font_family"])
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="{theme_name}">'
        f'<a:themeElements><a:clrScheme name="{theme_name}">'
        f'<a:dk1><a:srgbClr val="{primary}"/></a:dk1>'
        '<a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        f'<a:accent1><a:srgbClr val="{accent}"/></a:accent1>'
        f'</a:clrScheme><a:fontScheme name="{theme_name}">'
        f'<a:majorFont><a:latin typeface="{font}"/></a:majorFont>'
        f'<a:minorFont><a:latin typeface="{font}"/></a:minorFont>'
        '</a:fontScheme><a:fmtScheme name="OKoffice"/></a:themeElements></a:theme>'
    )


def _slide_master_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree/>'
        "</p:cSld></p:sldMaster>"
    )


def _slide_layout_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" type="titleAndContent">'
        "<p:cSld><p:spTree/></p:cSld></p:sldLayout>"
    )


def _core_props_xml(title: str) -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{_xml_text(title)}</dc:title>"
        "<dc:creator>okoffice</dc:creator>"
        "<cp:lastModifiedBy>okoffice</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_props_xml(slide_count: int) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>okoffice</Application>"
        f"<Slides>{slide_count}</Slides>"
        "</Properties>"
    )


def _usage(
    data: dict[str, Any],
    output: Path,
    workbook: Path,
    profile: str,
    slides: list[dict[str, Any]],
    style: dict[str, str],
) -> dict[str, Any]:
    source_ref_count = len([row for row in data["source_map_rows"] if row.get("source_ref")])
    return {
        "summary": {
            "slide_count": len(slides),
            "row_count": len(data["rows"]),
            "field_count": len(data["headers"]),
            "source_ref_count": source_ref_count,
            "notes_slide_count": len([slide for slide in slides if slide["notes"]]),
        },
        "presentation_manifest": {
            "output_path": output.as_posix(),
            "format": "pptx",
            "profile": profile,
            "mutates_inputs": False,
            "package_type": "ooxml_pptx",
            "macro_enabled": False,
            "external_relationships": [],
            "source_workbook_path": workbook.as_posix(),
            "style": style,
        },
        "style": style,
        "slides": [
            {
                "slide_number": index,
                "slide_id": str(255 + index),
                "title": slide["title"],
                "row_id": slide["row_id"],
                "source_refs": slide["source_refs"],
            }
            for index, slide in enumerate(slides, start=1)
        ],
    }


def _validation_report(
    data: dict[str, Any],
    output: Path,
    inspected: ToolResult,
    warnings: list[str],
) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(
                name="evidence_workbook_loaded",
                status="passed",
                details={"row_count": len(data["rows"]), "field_count": len(data["headers"])},
            ),
            ValidationCheck(
                name="presentation_written",
                status="passed",
                details={"output_path": output.as_posix()},
            ),
            ValidationCheck(
                name="presentation_reopened_by_inspect",
                status="passed",
                details=inspected.usage.get("summary", {}),
            ),
            ValidationCheck(
                name="contact_sheet_preview",
                status="skipped",
                message="No local contact-sheet renderer is configured for PPTX creation.",
            ),
        ],
        warnings=warnings,
    )


def _warnings(data: dict[str, Any]) -> list[str]:
    warnings = []
    for row in data["rows"]:
        if not row["source_refs"]:
            warnings.append(f"Evidence row has no source refs: {row['row_id']}")
    return warnings


def _normalize_style(style: dict[str, Any] | None, *, profile: str) -> dict[str, str]:
    raw = style or {}
    return {
        "theme_name": str(raw.get("theme_name") or _default_theme_name(profile)),
        "primary_color": _color(raw.get("primary_color"), fallback="111827"),
        "accent_color": _color(raw.get("accent_color"), fallback="2563EB"),
        "font_family": str(raw.get("font_family") or "Aptos"),
    }


def _default_theme_name(profile: str) -> str:
    return {
        "board_review": "OKoffice Board Theme",
        "executive": "OKoffice Executive Theme",
    }.get(profile, "OKoffice Theme")


def _color(value: Any, *, fallback: str) -> str:
    candidate = str(value or fallback).strip().lstrip("#").upper()
    if not re.fullmatch(r"[0-9A-F]{6}", candidate):
        raise AgentPDFException("invalid_input", f"Invalid hex color: {value}")
    return candidate


def _ordered_row_ids(source_map_rows: list[dict[str, str]]) -> list[str]:
    return _unique([row.get("row_id", "") for row in source_map_rows])


def _unique(values: list[str]) -> list[str]:
    unique_values = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values


def _field_label(field: str) -> str:
    return field.replace("_", " ").capitalize()


def _first_non_empty(values: dict[str, str]) -> str | None:
    for value in values.values():
        if value:
            return value
    return None


def _default_title(workbook: Path) -> str:
    return workbook.stem.replace("-", " ").replace("_", " ").title()


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - 64
    return index


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
        else:
            parts.append(part)
    return "/".join(parts)


def _unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _xml_text(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=False)


def _xml_attr(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        error=error,
        warnings=[error.message],
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
