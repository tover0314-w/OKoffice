from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.office.inspect import inspect_office_file
from okoffice.office.ooxml import WORD_NS, namespaced_attr, read_xml
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


INSPECT_TOOL_NAME = "word.inspect.document"
EXTRACT_TABLES_TOOL_NAME = "word.extract.tables"
WORD_DOCUMENT = "word/document.xml"
W_URI = WORD_NS["w"]
W_NS = f"{{{W_URI}}}"
CORE_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def inspect_word_document(path: str | Path) -> ToolResult:
    resolved = Path(path)
    preflight = inspect_office_file(resolved)
    if preflight.status == "failed":
        return _failed(
            INSPECT_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Word inspect failed."),
        )
    if preflight.usage["format"]["detected_format"] != "docx":
        return _failed(
            INSPECT_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="word.inspect.document requires a DOCX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    document_root = read_xml(source_path, WORD_DOCUMENT)
    if document_root is None:
        return _failed(
            INSPECT_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="word.inspect.document requires word/document.xml in the DOCX package.",
                details={"path": source_path.as_posix()},
            ),
        )
    comments_root = read_xml(source_path, "word/comments.xml")
    styles_root = read_xml(source_path, "word/styles.xml")
    core_root = read_xml(source_path, "docProps/core.xml")
    body = document_root.find(".//w:body", WORD_NS) if document_root is not None else None
    paragraphs = body.findall("./w:p", WORD_NS) if body is not None else []
    tables = body.findall("./w:tbl", WORD_NS) if body is not None else []
    sections = body.findall(".//w:sectPr", WORD_NS) if body is not None else []
    styles = _styles(styles_root)
    paragraph_payloads = [_paragraph_payload(source_path, paragraph, index, styles) for index, paragraph in enumerate(paragraphs)]
    heading_payloads = [item for item in paragraph_payloads if str(item.get("style_id", "")).lower().startswith("heading")]
    title_payloads = [item for item in paragraph_payloads if str(item.get("style_id", "")).lower() == "title"]
    table_payloads = [_rich_table_payload(source_path, table, index) for index, table in enumerate(tables, start=1)]
    comments = _comments(comments_root)
    field_count = max(
        len(document_root.findall(".//w:fldChar", WORD_NS)),
        len(document_root.findall(".//w:instrText", WORD_NS)),
    )
    tracked_change_count = len(document_root.findall(".//w:ins", WORD_NS)) + len(document_root.findall(".//w:del", WORD_NS))
    metadata = _core_metadata(core_root)
    package = {
        "macro_enabled": bool(preflight.usage["safety"].get("macro_enabled", False)),
        "has_external_relationships": bool(preflight.usage["safety"].get("has_external_relationships", False)),
        "zip_entry_count": preflight.usage["safety"].get("zip_entry_count", 0),
    }
    warnings = _word_warnings(preflight.warnings, package=package)
    summary = {
        "paragraph_count": len(paragraphs),
        "heading_count": len(heading_payloads) + len(title_payloads),
        "table_count": len(table_payloads),
        "comment_count": len(comments),
        "field_count": field_count,
        "tracked_change_count": tracked_change_count,
        "section_count": len(sections),
        "style_count": len(styles),
    }

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=INSPECT_TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="document_xml_present", status="passed"),
                ValidationCheck(name="paragraph_inventory", status="passed", details={"paragraph_count": len(paragraphs)}),
                ValidationCheck(
                    name="package_safety_markers",
                    status="warning" if warnings else "passed",
                    details=package,
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "document": {
                "path": source_path.as_posix(),
                "format": "docx",
                "package_type": preflight.usage["format"]["package_type"],
            },
            "summary": summary,
            "structure": {
                "paragraph_count": len(paragraphs),
                "heading_count": summary["heading_count"],
                "table_count": len(table_payloads),
                "section_count": len(sections),
            },
            "paragraphs": paragraph_payloads,
            "headings": heading_payloads + title_payloads,
            "tables": table_payloads,
            "comments": _CountedList(comments, comment_count=len(comments)),
            "styles": _CountedList(styles, style_count=len(styles)),
            "metadata": metadata,
            "package": package,
            "layout": {
                "rendered_layout_claimed": False,
                "preview_available": False,
                "render_worker_required": "docx_render_preview_worker",
            },
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=["word.extract.structure", "word.extract.tables", "office.context.build_packet"],
    )


def extract_word_tables(path: str | Path) -> ToolResult:
    resolved = Path(path)
    preflight = inspect_office_file(resolved)
    if preflight.status == "failed":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            preflight.error or OKofficeError(code="unsupported_file_type", message="Word table extraction failed."),
        )
    if preflight.usage["format"]["detected_format"] != "docx":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="word.extract.tables requires a DOCX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            ),
        )

    source_path = Path(preflight.usage["file"]["path"])
    document_root = read_xml(source_path, "word/document.xml")
    if document_root is None:
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            OKofficeError(
                code="unsupported_file_type",
                message="word.extract.tables requires word/document.xml in the DOCX package.",
                details={"path": source_path.as_posix()},
            ),
        )

    body = document_root.find(".//w:body", WORD_NS)
    table_elements = body.findall("./w:tbl", WORD_NS) if body is not None else []
    tables = [_table_payload(source_path, table, index) for index, table in enumerate(table_elements, start=1)]
    row_count = sum(len(table["rows"]) for table in tables)
    cell_count = sum(len(row["cells"]) for table in tables for row in table["rows"])

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=EXTRACT_TABLES_TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="document_xml_present", status="passed"),
                ValidationCheck(
                    name="tables_extracted",
                    status="passed",
                    details={"table_count": len(tables), "row_count": row_count, "cell_count": cell_count},
                ),
            ],
        ),
        usage={
            "document": {
                "path": source_path.as_posix(),
                "format": "docx",
                "package_type": preflight.usage["format"]["package_type"],
            },
            "summary": {"table_count": len(tables), "row_count": row_count, "cell_count": cell_count},
            "tables": tables,
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=[
            "sheet.create.evidence_workbook",
            "sheet.write.workbook",
            "office.workflow.extract_to_sheet",
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


def _is_heading(paragraph: object) -> bool:
    style = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
    if style is None:
        return False
    style_id = namespaced_attr(style, WORD_NS["w"], "val") or ""
    return style_id.lower().startswith("heading") or style_id.lower() == "title"


def _paragraph_payload(
    source_path: Path,
    paragraph: object,
    paragraph_index: int,
    styles: list[dict[str, Any]],
) -> dict[str, Any]:
    style_id = _paragraph_style_id(paragraph)
    style_name = _style_name(style_id, styles)
    return {
        "paragraph_id": f"p_{paragraph_index + 1:04d}",
        "paragraph_index": paragraph_index,
        "text": _word_text(paragraph),
        "style_id": style_id,
        "style": style_name,
        "is_heading": _is_heading(paragraph),
        "locator": _word_locator(source_path, paragraph_index=paragraph_index),
    }


def _paragraph_style_id(paragraph: object) -> str | None:
    style = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
    if style is None:
        return None
    return namespaced_attr(style, W_URI, "val")


def _style_name(style_id: str | None, styles: list[dict[str, Any]]) -> str | None:
    if style_id is None:
        return None
    for style in styles:
        if style.get("style_id") == style_id:
            return str(style.get("name") or style_id)
    return style_id


def _styles(root: object | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    results = []
    for style in root.findall(".//w:style", WORD_NS):
        style_id = namespaced_attr(style, W_URI, "styleId")
        name_node = style.find("./w:name", WORD_NS)
        name = namespaced_attr(name_node, W_URI, "val") if name_node is not None else style_id
        results.append(
            {
                "style_id": style_id,
                "name": name,
                "type": namespaced_attr(style, W_URI, "type"),
            }
        )
    return results


def _comments(root: object | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    results = []
    for comment in root.findall(".//w:comment", WORD_NS):
        results.append(
            {
                "comment_id": namespaced_attr(comment, W_URI, "id"),
                "author": namespaced_attr(comment, W_URI, "author"),
                "text": _word_text(comment),
            }
        )
    return results


def _core_metadata(root: object | None) -> dict[str, Any]:
    if root is None:
        return {"title": None, "creator": None}
    title = root.findtext("./dc:title", default=None, namespaces=CORE_NS)
    creator = root.findtext("./dc:creator", default=None, namespaces=CORE_NS)
    return {"title": title, "creator": creator}


def _rich_table_payload(source_path: Path, table: object, table_index: int) -> dict[str, Any]:
    table_payload = _table_payload(source_path, table, table_index)
    rows = table_payload["rows"]
    cell_grid = [
        [
            {
                "row_index": row["row_index"],
                "cell_index": cell["cell_index"],
                "text": cell["text"],
                "locator": {
                    "kind": "word",
                    "document_path": source_path.as_posix(),
                    "table_index": table_index,
                    "row_index": row["row_index"],
                    "cell_index": cell["cell_index"],
                },
            }
            for cell in row["cells"]
        ]
        for row in rows
    ]
    column_count = max((len(row) for row in cell_grid), default=0)
    return {
        **table_payload,
        "row_count": len(cell_grid),
        "column_count": column_count,
        "cells": cell_grid,
        "locator": _word_locator(source_path, table_index=table_index),
    }


def _word_locator(
    source_path: Path,
    *,
    paragraph_index: int | None = None,
    table_index: int | None = None,
) -> dict[str, Any]:
    locator: dict[str, Any] = {
        "kind": "word",
        "document_path": source_path.as_posix(),
        "package_part": WORD_DOCUMENT,
    }
    if paragraph_index is not None:
        locator["paragraph_index"] = paragraph_index
    if table_index is not None:
        locator["table_index"] = table_index
    return locator


def _word_warnings(preflight_warnings: list[str], *, package: dict[str, Any]) -> list[str]:
    warnings = list(preflight_warnings)
    if package.get("has_external_relationships"):
        warnings.append("External Word relationship targets were detected.")
    return _dedupe(warnings)


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _table_payload(source_path: Path, table: object, table_index: int) -> dict[str, object]:
    rows = []
    for row_index, row in enumerate(table.findall("./w:tr", WORD_NS), start=1):
        cells = []
        for cell_index, cell in enumerate(row.findall("./w:tc", WORD_NS), start=1):
            source = {
                "document_path": source_path.as_posix(),
                "table_index": table_index,
                "row_index": row_index,
                "cell_index": cell_index,
            }
            cells.append(
                {
                    "cell_index": cell_index,
                    "text": _word_text(cell),
                    "source": source,
                }
            )
        rows.append({"row_index": row_index, "cells": cells})
    return {
        "table_id": f"word_table_{table_index}",
        "table_index": table_index,
        "source": {"document_path": source_path.as_posix(), "table_index": table_index},
        "rows": rows,
    }


def _word_text(element: object) -> str:
    parts = [node.text or "" for node in element.findall(".//w:t", WORD_NS)]
    return "".join(parts).strip()


def _failed(tool: str, error: OKofficeError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[error.message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
