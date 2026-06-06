from __future__ import annotations

from pathlib import Path
from typing import Any

from okoffice.office.inspect import inspect_office_file
from okoffice.office.ooxml import WORD_NS, namespaced_attr, read_xml
from okoffice.office.shared import failed_result, job_id
from okoffice.office.word import (
    _comments,
    _core_metadata,
    _is_heading,
    _paragraph_payload,
    _paragraph_style_id,
    _styles,
    _word_locator,
    _word_text,
)
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport

EXTRACT_TEXT_TOOL = "word.extract.text"
EXTRACT_OUTLINE_TOOL = "word.extract.outline"
EXTRACT_COMMENTS_TOOL = "word.extract.comments"
EXTRACT_REVISIONS_TOOL = "word.extract.revisions"
EXTRACT_FIELDS_TOOL = "word.extract.fields"
EXTRACT_STYLES_TOOL = "word.extract.styles"
WORD_DOCUMENT = "word/document.xml"
W_URI = WORD_NS["w"]
W_NS = f"{{{W_URI}}}"


def _preflight(path: str | Path, tool: str) -> tuple[Path, Any, Any] | ToolResult:
    preflight = inspect_office_file(Path(path))
    if preflight.status == "failed":
        return failed_result(tool, preflight.error or OKofficeError(code="unsupported_file_type", message="Preflight failed."))
    if preflight.usage["format"]["detected_format"] != "docx":
        return failed_result(
            tool,
            OKofficeError(code="unsupported_file_type", message=f"{tool} requires a DOCX file.", details={"detected_format": preflight.usage["format"]["detected_format"]}),
        )
    source_path = Path(preflight.usage["file"]["path"])
    document_root = read_xml(source_path, WORD_DOCUMENT)
    if document_root is None:
        return failed_result(tool, OKofficeError(code="unsupported_file_type", message=f"{tool} requires {WORD_DOCUMENT} in the package."))
    return source_path, document_root, preflight


def extract_word_text(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_TEXT_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, document_root, preflight = result
    body = document_root.find(".//w:body", WORD_NS)
    paragraphs = body.findall("./w:p", WORD_NS) if body is not None else []
    styles_root = read_xml(source_path, "word/styles.xml")
    styles = _styles(styles_root)
    text_items = []
    for index, para in enumerate(paragraphs):
        text = _word_text(para)
        if text:
            text_items.append({
                "paragraph_id": f"p_{index + 1:04d}",
                "paragraph_index": index,
                "text": text,
                "style_id": _paragraph_style_id(para),
                "is_heading": _is_heading(para),
                "locator": _word_locator(source_path, paragraph_index=index),
            })
    full_text = "\n\n".join(item["text"] for item in text_items)
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_TEXT_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="text_extracted", status="passed", details={"paragraph_count": len(text_items)}),
            ],
        ),
        usage={
            "summary": {"paragraph_count": len(text_items), "character_count": len(full_text)},
            "text": full_text,
            "paragraphs": text_items,
        },
        next_recommended_tools=["word.extract.outline", "word.extract.tables", "office.context.build_packet"],
    )


def extract_word_outline(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_OUTLINE_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, document_root, preflight = result
    body = document_root.find(".//w:body", WORD_NS)
    paragraphs = body.findall("./w:p", WORD_NS) if body is not None else []
    styles_root = read_xml(source_path, "word/styles.xml")
    styles = _styles(styles_root)
    headings = []
    for index, para in enumerate(paragraphs):
        if not _is_heading(para):
            continue
        style_id = _paragraph_style_id(para) or ""
        level = _heading_level(style_id)
        headings.append({
            "paragraph_index": index,
            "level": level,
            "text": _word_text(para),
            "style_id": style_id,
            "locator": _word_locator(source_path, paragraph_index=index),
        })
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_OUTLINE_TOOL,
        validation=ValidationReport(
            status="warning" if not headings else "passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="headings_found", status="passed" if headings else "warning", details={"heading_count": len(headings)}),
            ],
            warnings=[] if headings else ["No headings found in document."],
        ),
        warnings=[] if headings else ["No headings found in document."],
        usage={
            "summary": {"heading_count": len(headings), "max_depth": max((h["level"] for h in headings), default=0)},
            "headings": headings,
        },
        next_recommended_tools=["word.extract.text", "word.extract.tables"],
    )


def extract_word_comments(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_COMMENTS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, document_root, preflight = result
    comments_root = read_xml(source_path, "word/comments.xml")
    comments = _comments(comments_root)
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_COMMENTS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="comments_extracted", status="passed", details={"comment_count": len(comments)}),
            ],
        ),
        usage={
            "summary": {"comment_count": len(comments)},
            "comments": comments,
        },
        next_recommended_tools=["word.extract.text", "word.extract.revisions"],
    )


def extract_word_revisions(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_REVISIONS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, document_root, preflight = result
    revisions: list[dict[str, Any]] = []
    body = document_root.find(".//w:body", WORD_NS)
    if body is None:
        return _empty_revisions(source_path)
    for para_index, para in enumerate(body.findall(".//w:p", WORD_NS)):
        for ins in para.findall(".//w:ins", WORD_NS):
            revisions.append(_revision_payload(source_path, para_index, "insertion", ins))
        for de in para.findall(".//w:del", WORD_NS):
            revisions.append(_revision_payload(source_path, para_index, "deletion", de))
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_REVISIONS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="revisions_extracted", status="passed", details={"revision_count": len(revisions)}),
            ],
        ),
        usage={
            "summary": {"revision_count": len(revisions), "insertion_count": sum(1 for r in revisions if r["type"] == "insertion"), "deletion_count": sum(1 for r in revisions if r["type"] == "deletion")},
            "revisions": revisions,
        },
        next_recommended_tools=["word.extract.text", "word.extract.comments"],
    )


def extract_word_fields(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_FIELDS_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, document_root, preflight = result
    fields: list[dict[str, Any]] = []
    body = document_root.find(".//w:body", WORD_NS)
    if body is not None:
        for instr in body.findall(".//w:instrText", WORD_NS):
            fields.append({
                "field_code": (instr.text or "").strip(),
                "locator": {"kind": "word", "document_path": source_path.as_posix(), "package_part": WORD_DOCUMENT},
            })
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_FIELDS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="fields_extracted", status="passed", details={"field_count": len(fields)}),
            ],
        ),
        usage={
            "summary": {"field_count": len(fields)},
            "fields": fields,
        },
        next_recommended_tools=["word.extract.text", "word.extract.styles"],
    )


def extract_word_styles(path: str | Path) -> ToolResult:
    result = _preflight(path, EXTRACT_STYLES_TOOL)
    if isinstance(result, ToolResult):
        return result
    source_path, document_root, preflight = result
    styles_root = read_xml(source_path, "word/styles.xml")
    styles = _rich_styles(styles_root)
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_STYLES_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="styles_extracted", status="passed", details={"style_count": len(styles)}),
            ],
        ),
        usage={
            "summary": {"style_count": len(styles)},
            "styles": styles,
        },
        next_recommended_tools=["word.extract.text", "word.validation.document"],
    )


def _heading_level(style_id: str) -> int:
    lower = style_id.lower()
    if lower == "title":
        return 0
    if lower.startswith("heading"):
        suffix = lower[len("heading"):]
        try:
            return int(suffix)
        except ValueError:
            return 1
    return 1


def _revision_payload(source_path: Path, para_index: int, rev_type: str, element: Any) -> dict[str, Any]:
    return {
        "type": rev_type,
        "author": namespaced_attr(element, W_URI, "author") or "",
        "date": namespaced_attr(element, W_URI, "date") or "",
        "text": _word_text(element),
        "paragraph_index": para_index,
        "revision_id": namespaced_attr(element, W_URI, "id") or "",
        "locator": _word_locator(source_path, paragraph_index=para_index),
    }


def _rich_styles(root: Any) -> list[dict[str, Any]]:
    if root is None:
        return []
    results = []
    for style in root.findall(".//w:style", WORD_NS):
        style_id = namespaced_attr(style, W_URI, "styleId")
        name_node = style.find("./w:name", WORD_NS)
        name = namespaced_attr(name_node, W_URI, "val") if name_node is not None else style_id
        based_on_node = style.find("./w:basedOn", WORD_NS)
        based_on = namespaced_attr(based_on_node, W_URI, "val") if based_on_node is not None else None
        results.append({
            "style_id": style_id,
            "name": name,
            "type": namespaced_attr(style, W_URI, "type"),
            "based_on": based_on,
            "is_custom": namespaced_attr(style, W_URI, "customStyle") == "1",
        })
    return results


def _empty_revisions(source_path: Path) -> ToolResult:
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=EXTRACT_REVISIONS_TOOL,
        validation=ValidationReport(status="passed", checks=[ValidationCheck(name="format_is_docx", status="passed"), ValidationCheck(name="revisions_extracted", status="passed", details={"revision_count": 0})]),
        usage={"summary": {"revision_count": 0, "insertion_count": 0, "deletion_count": 0}, "revisions": []},
        next_recommended_tools=["word.extract.text", "word.extract.comments"],
    )
