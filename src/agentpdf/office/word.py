from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.ooxml import WORD_NS, namespaced_attr, read_xml
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


INSPECT_TOOL_NAME = "word.inspect.document"
EXTRACT_TABLES_TOOL_NAME = "word.extract.tables"


def inspect_word_document(path: str | Path) -> ToolResult:
    resolved = Path(path)
    preflight = inspect_office_file(resolved)
    if preflight.status == "failed":
        return _failed(
            INSPECT_TOOL_NAME,
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Word inspect failed."),
        )
    if preflight.usage["format"]["detected_format"] != "docx":
        return _failed(
            INSPECT_TOOL_NAME,
            AgentPDFError(
                code="unsupported_file_type",
                message="word.inspect.document requires a DOCX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    document_root = read_xml(source_path, "word/document.xml")
    comments_root = read_xml(source_path, "word/comments.xml")
    styles_root = read_xml(source_path, "word/styles.xml")
    body = document_root.find(".//w:body", WORD_NS) if document_root is not None else None
    paragraphs = body.findall("./w:p", WORD_NS) if body is not None else []
    tables = body.findall("./w:tbl", WORD_NS) if body is not None else []
    sections = body.findall("./w:sectPr", WORD_NS) if body is not None else []
    heading_count = sum(1 for paragraph in paragraphs if _is_heading(paragraph))
    comment_count = len(comments_root.findall(".//w:comment", WORD_NS)) if comments_root is not None else 0
    style_count = len(styles_root.findall(".//w:style", WORD_NS)) if styles_root is not None else 0

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=INSPECT_TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="document_xml_present", status="passed"),
            ],
        ),
        usage={
            "document": {
                "path": source_path.as_posix(),
                "format": "docx",
                "package_type": preflight.usage["format"]["package_type"],
            },
            "structure": {
                "paragraph_count": len(paragraphs),
                "heading_count": heading_count,
                "table_count": len(tables),
                "section_count": len(sections),
            },
            "comments": {"comment_count": comment_count},
            "styles": {"style_count": style_count},
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
            preflight.error or AgentPDFError(code="unsupported_file_type", message="Word table extraction failed."),
        )
    if preflight.usage["format"]["detected_format"] != "docx":
        return _failed(
            EXTRACT_TABLES_TOOL_NAME,
            AgentPDFError(
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
            AgentPDFError(
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
        next_recommended_tools=["sheet.write.workbook", "office.workflow.extract_to_sheet", "office.context.build_packet"],
    )


def _is_heading(paragraph: object) -> bool:
    style = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
    if style is None:
        return False
    style_id = namespaced_attr(style, WORD_NS["w"], "val") or ""
    return style_id.lower().startswith("heading")


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


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=tool,
        warnings=[error.message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
