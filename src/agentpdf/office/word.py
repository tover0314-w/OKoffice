from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree

from agentpdf.office.ir import WordLocator
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"
CORE_NS = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
WORD_DOCUMENT = "word/document.xml"


def inspect_word_document(path: str | Path) -> ToolResult:
    tool = "word.inspect.document"
    try:
        resolved = resolve_input_path(path)
        usage, warnings = _inspect_docx(resolved)
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=tool,
            validation=_validation_report(resolved, usage, warnings),
            warnings=warnings,
            usage=usage,
            next_recommended_tools=["office.context.build_packet", "word.validation.document"],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def _inspect_docx(path: Path) -> tuple[dict[str, Any], list[str]]:
    if path.suffix.lower() not in {".docx", ".docm"} or not zipfile.is_zipfile(path):
        raise AgentPDFException(
            "unsupported_file_type",
            f"Word inspect requires a readable DOCX/DOCM package: {path.name}",
            details={"path": path.as_posix()},
        )
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        if WORD_DOCUMENT not in names:
            raise AgentPDFException(
                "unsupported_file_type",
                "Word package is missing word/document.xml.",
                details={"path": path.as_posix()},
            )
        document = ElementTree.fromstring(archive.read(WORD_DOCUMENT))
        styles = _read_styles(archive, names)
        paragraphs, headings, section_count = _read_body_paragraphs(document, styles)
        tables = _read_tables(document)
        comments = _read_comments(archive, names)
        metadata = _read_core_metadata(archive, names)
        field_count = _field_count(document)
        tracked_change_count = _count(document, f".//{W_NS}ins") + _count(document, f".//{W_NS}del")
        package = _package_markers(path, archive, names)

    if package["macro_enabled"]:
        warnings.append("Macro-enabled Word package markers were detected; macros are not executed.")
    if package["has_external_relationships"]:
        warnings.append("External Word relationship targets were detected.")

    usage = {
        "file": {
            "path": path.as_posix(),
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        },
        "summary": {
            "paragraph_count": len(paragraphs),
            "heading_count": _heading_count(paragraphs),
            "table_count": len(tables),
            "comment_count": len(comments),
            "style_count": len(styles),
            "section_count": section_count,
            "field_count": field_count,
            "tracked_change_count": tracked_change_count,
        },
        "metadata": metadata,
        "package": package,
        "styles": list(styles.values()),
        "paragraphs": paragraphs,
        "headings": headings,
        "tables": tables,
        "comments": comments,
        "layout": {
            "rendered_layout_claimed": False,
            "render_evidence": "not_available_in_local_docx_inspect",
        },
    }
    return usage, warnings


def _read_body_paragraphs(root: ElementTree.Element, styles: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    body = root.find(f"{W_NS}body")
    if body is None:
        return [], [], 0
    paragraphs: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    section_count = 0
    paragraph_index = 0
    for child in list(body):
        if child.tag != f"{W_NS}p":
            continue
        style_id = _paragraph_style_id(child)
        style_name = styles.get(style_id or "", style_id or "Normal")
        text = _text_content(child)
        locator = WordLocator(paragraph_id=f"p_{paragraph_index + 1:04d}", paragraph_index=paragraph_index).model_dump(mode="json")
        entry = {
            "paragraph_id": f"p_{paragraph_index + 1:04d}",
            "paragraph_index": paragraph_index,
            "style": style_name,
            "text": text,
            "is_heading": _is_heading_style(style_name),
            "locator": locator,
        }
        paragraphs.append(entry)
        if _is_heading_style(style_name):
            headings.append(entry)
        if child.find(f".//{W_NS}sectPr") is not None:
            section_count += 1
        paragraph_index += 1
    if body.find(f"{W_NS}sectPr") is not None:
        section_count += 1
    return paragraphs, headings, section_count


def _read_tables(root: ElementTree.Element) -> list[dict[str, Any]]:
    body = root.find(f"{W_NS}body")
    if body is None:
        return []
    tables: list[dict[str, Any]] = []
    table_index = 0
    for child in list(body):
        if child.tag != f"{W_NS}tbl":
            continue
        rows = []
        max_columns = 0
        for row_index, row in enumerate(child.findall(f"{W_NS}tr")):
            cells = []
            table_cells = row.findall(f"{W_NS}tc")
            max_columns = max(max_columns, len(table_cells))
            for column_index, cell in enumerate(table_cells):
                cells.append(
                    {
                        "text": _text_content(cell),
                        "locator": WordLocator(
                            table_id=f"t_{table_index + 1:04d}",
                            table_index=table_index,
                            row_index=row_index,
                            column_index=column_index,
                        ).model_dump(mode="json"),
                    }
                )
            rows.append(cells)
        tables.append(
            {
                "table_id": f"t_{table_index + 1:04d}",
                "table_index": table_index,
                "row_count": len(rows),
                "column_count": max_columns,
                "cells": rows,
                "locator": WordLocator(table_id=f"t_{table_index + 1:04d}", table_index=table_index).model_dump(mode="json"),
            }
        )
        table_index += 1
    return tables


def _read_styles(archive: zipfile.ZipFile, names: set[str]) -> dict[str, str]:
    if "word/styles.xml" not in names:
        return {}
    root = ElementTree.fromstring(archive.read("word/styles.xml"))
    styles: dict[str, str] = {}
    for style in root.findall(f"{W_NS}style"):
        style_id = style.attrib.get(f"{W_NS}styleId")
        name = style.find(f"{W_NS}name")
        style_name = name.attrib.get(f"{W_NS}val") if name is not None else None
        if style_id:
            styles[style_id] = style_name or style_id
    return styles


def _read_comments(archive: zipfile.ZipFile, names: set[str]) -> list[dict[str, Any]]:
    if "word/comments.xml" not in names:
        return []
    root = ElementTree.fromstring(archive.read("word/comments.xml"))
    comments = []
    for comment in root.findall(f"{W_NS}comment"):
        comment_id = comment.attrib.get(f"{W_NS}id", "")
        comments.append(
            {
                "comment_id": comment_id,
                "author": comment.attrib.get(f"{W_NS}author"),
                "text": _text_content(comment),
                "locator": WordLocator(comment_id=comment_id).model_dump(mode="json"),
            }
        )
    return comments


def _read_core_metadata(archive: zipfile.ZipFile, names: set[str]) -> dict[str, Any]:
    if "docProps/core.xml" not in names:
        return {}
    root = ElementTree.fromstring(archive.read("docProps/core.xml"))
    return {
        "title": _first_text(root, f"{DC_NS}title"),
        "creator": _first_text(root, f"{DC_NS}creator"),
        "last_modified_by": _first_text(root, f"{CORE_NS}lastModifiedBy"),
    }


def _package_markers(path: Path, archive: zipfile.ZipFile, names: set[str]) -> dict[str, Any]:
    return {
        "package_type": "ooxml_docx",
        "zip_entry_count": len(names),
        "macro_enabled": path.suffix.lower() == ".docm" or any(name.lower().endswith("vbaproject.bin") for name in names),
        "has_external_relationships": _has_external_relationships(archive, names),
        "unsafe_package_entries": [name for name in names if _unsafe_zip_entry(name)],
    }


def _has_external_relationships(archive: zipfile.ZipFile, names: set[str]) -> bool:
    for name in sorted(names):
        if not name.endswith(".rels"):
            continue
        raw = archive.read(name)
        if b'TargetMode="External"' in raw or b"TargetMode='External'" in raw:
            return True
    return False


def _unsafe_zip_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _paragraph_style_id(paragraph: ElementTree.Element) -> str | None:
    style = paragraph.find(f"{W_NS}pPr/{W_NS}pStyle")
    if style is None:
        return None
    return style.attrib.get(f"{W_NS}val")


def _text_content(element: ElementTree.Element) -> str:
    values = []
    for node in element.iter():
        if node.tag in {f"{W_NS}t", f"{W_NS}instrText"} and node.text:
            values.append(node.text)
    return "".join(values).strip()


def _first_text(root: ElementTree.Element, tag: str) -> str | None:
    node = root.find(tag)
    return node.text if node is not None else None


def _count(root: ElementTree.Element, path: str) -> int:
    return len(root.findall(path))


def _field_count(root: ElementTree.Element) -> int:
    begin_markers = [
        node
        for node in root.findall(f".//{W_NS}fldChar")
        if node.attrib.get(f"{W_NS}fldCharType") == "begin"
    ]
    if begin_markers:
        return len(begin_markers)
    return _count(root, f".//{W_NS}instrText")


def _is_heading_style(style_name: str) -> bool:
    normalized = style_name.lower().replace(" ", "")
    return normalized.startswith("heading")


def _heading_count(paragraphs: list[dict[str, Any]]) -> int:
    return sum(1 for paragraph in paragraphs if paragraph["style"] == "Title" or paragraph["is_heading"])


def _validation_report(path: Path, usage: dict[str, Any], warnings: list[str]) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(name="input_path_safe", status="passed", message="Input path passed local safety checks."),
            ValidationCheck(name="document_xml_present", status="passed", details={"path": path.as_posix()}),
            ValidationCheck(name="structure_extracted", status="passed", details=usage["summary"]),
            ValidationCheck(
                name="rendered_layout_not_claimed",
                status="passed",
                message="DOCX inspect reports structure only; it does not claim rendered layout fit.",
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
