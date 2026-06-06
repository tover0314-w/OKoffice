"""Word document creation tools: word.create.document and word.create.memo."""
from __future__ import annotations

import html
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from okoffice.artifacts.store import build_artifact
from okoffice.office.shared import failed_result, job_id
from okoffice.office.word import inspect_word_document
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_output_path

DOCUMENT_TOOL = "word.create.document"
MEMO_TOOL = "word.create.memo"


def create_word_document(*, output_path: str | Path, document_ir: dict[str, Any]) -> ToolResult:
    """Create a DOCX from a document IR schema."""
    try:
        output = resolve_output_path(output_path)
        _require_docx(output)
        title = document_ir.get("title", "Untitled")
        metadata = document_ir.get("metadata", {})
        sections = document_ir.get("sections", [])
        _write_docx_package(output, title, metadata, sections)
        return _build_result(DOCUMENT_TOOL, output, title, sections)
    except OKofficeException as exc:
        return failed_result(DOCUMENT_TOOL, exc.to_error())
    except (ValueError, zipfile.BadZipFile) as exc:
        return failed_result(DOCUMENT_TOOL, OKofficeError(code="invalid_input", message=str(exc)))


def create_word_memo(*, output_path: str | Path, memo_ir: dict[str, Any]) -> ToolResult:
    """Create a DOCX memo (specialised template wrapping create_word_document)."""
    try:
        output = resolve_output_path(output_path)
        _require_docx(output)
        document_ir = _memo_to_document_ir(memo_ir)
        title = document_ir["title"]
        metadata = document_ir.get("metadata", {})
        sections = document_ir.get("sections", [])
        _write_docx_package(output, title, metadata, sections)
        return _build_result(MEMO_TOOL, output, title, sections)
    except OKofficeException as exc:
        return failed_result(MEMO_TOOL, exc.to_error())
    except (ValueError, zipfile.BadZipFile) as exc:
        return failed_result(MEMO_TOOL, OKofficeError(code="invalid_input", message=str(exc)))


def _build_result(tool: str, output: Path, title: str, sections: list[dict[str, Any]]) -> ToolResult:
    inspected = inspect_word_document(output)
    if inspected.status != "succeeded":
        raise OKofficeException(
            "output_validation_failed",
            f"Generated Word document could not be inspected.",
            details=inspected.error.model_dump(mode="json") if inspected.error else {},
        )
    counts = _section_counts(sections)
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=tool,
        artifacts=[build_artifact(output, source_tool=tool)],
        validation=_validation(output, counts, inspected),
        usage=_usage_payload(tool, output, title, counts),
        next_recommended_tools=["word.inspect.document", "word.patch.apply", "office.bundle.export"],
    )


def _memo_to_document_ir(memo_ir: dict[str, Any]) -> dict[str, Any]:
    to_val, from_val = memo_ir.get("to", ""), memo_ir.get("from", "")
    date_val, subject_val = memo_ir.get("date", ""), memo_ir.get("subject", "")
    body, metadata = memo_ir.get("body", []), memo_ir.get("metadata", {})
    header_paragraphs = [
        *(["To: " + to_val] if to_val else []),
        *(["From: " + from_val] if from_val else []),
        *(["Date: " + date_val] if date_val else []),
        *(["Subject: " + subject_val] if subject_val else []),
        "---",
    ]
    return {
        "title": subject_val or "Memo",
        "metadata": metadata,
        "sections": [
            {"heading": "", "level": 0, "paragraphs": header_paragraphs, "tables": []},
            {"heading": "", "level": 0, "paragraphs": list(body), "tables": []},
        ],
    }


def _write_docx_package(path: Path, title: str, metadata: dict[str, Any], sections: list[dict[str, Any]]) -> None:
    creator = metadata.get("creator", "okoffice")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml())
        zf.writestr("_rels/.rels", _root_rels_xml())
        zf.writestr("docProps/core.xml", _core_props_xml(title, creator))
        zf.writestr("docProps/app.xml", _app_props_xml())
        zf.writestr("word/_rels/document.xml.rels", _document_rels_xml())
        zf.writestr("word/document.xml", _document_xml(sections, title))
        zf.writestr("word/styles.xml", _styles_xml())


# -- XML builders --


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/></Relationships>'
    )


def _document_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/></Relationships>'
    )


def _document_xml(sections: list[dict[str, Any]], title: str) -> str:
    parts = [_heading_para(title, 0)]
    for section in sections:
        heading = section.get("heading", "")
        level = section.get("level", 1)
        if heading:
            parts.append(_heading_para(heading, level))
        for text in section.get("paragraphs", []):
            parts.append(_separator_para() if text == "---" else _text_para(text))
        for table in section.get("tables", []):
            parts.append(_table_xml(table))
    body = "".join(parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
    )


def _heading_para(text: str, level: int) -> str:
    style = "Title" if level == 0 else f"Heading{min(level, 4)}"
    return (
        f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
        f"<w:r><w:t>{_xml_text(text)}</w:t></w:r></w:p>"
    )


def _text_para(text: str) -> str:
    return f"<w:p><w:r><w:t>{_xml_text(text)}</w:t></w:r></w:p>"


def _separator_para() -> str:
    return "<w:p><w:pPr><w:pBdr/></w:pPr><w:r><w:t> </w:t></w:r></w:p>"


def _table_xml(table: dict[str, Any]) -> str:
    columns, rows = table.get("columns", []), table.get("rows", [])
    parts = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/></w:tblPr>']
    if columns:
        cells = "".join(
            f"<w:tc><w:p><w:r><w:rPr><w:b/></w:rPr>"
            f"<w:t>{_xml_text(c)}</w:t></w:r></w:p></w:tc>"
            for c in columns
        )
        parts.append(f"<w:tr>{cells}</w:tr>")
    for ri, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            raise OKofficeException("invalid_input", f"Table row {ri} must be a list, got {type(row).__name__}.")
        cells = "".join(
            f"<w:tc><w:p><w:r><w:t>{_xml_text(c)}</w:t></w:r></w:p></w:tc>"
            for c in row
        )
        parts.append(f"<w:tr>{cells}</w:tr>")
    parts.append("</w:tbl>")
    return "".join(parts)


def _styles_xml() -> str:
    entries = "".join(
        f'<w:style w:type="paragraph" w:styleId="{sid}">'
        f'<w:name w:val="{_xml_text(name)}"/></w:style>'
        for sid, name in [
            ("Title", "Title"), ("Heading1", "heading 1"), ("Heading2", "heading 2"),
            ("Heading3", "heading 3"), ("Heading4", "heading 4"), ("Normal", "Normal"),
        ]
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"{entries}</w:styles>"
    )


def _core_props_xml(title: str, creator: str) -> str:
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{_xml_text(title)}</dc:title>"
        f"<dc:creator>{_xml_text(creator)}</dc:creator>"
        f"<cp:lastModifiedBy>{_xml_text(creator)}</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{ts}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{ts}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_props_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        "<Application>okoffice</Application></Properties>"
    )


# -- Helpers --


def _xml_text(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=False)


def _require_docx(path: Path) -> None:
    if path.suffix.lower() != ".docx":
        raise OKofficeException(
            "unsupported_file_type",
            "Word create tools write .docx output files.",
            details={"output_path": path.as_posix()},
        )


def _section_counts(sections: list[dict[str, Any]]) -> dict[str, int]:
    headings = sum(1 for s in sections if s.get("heading"))
    paras = sum(len(s.get("paragraphs", [])) for s in sections)
    tables = sum(len(s.get("tables", [])) for s in sections)
    return {"paragraph_count": paras, "heading_count": headings, "table_count": tables, "section_count": len(sections)}


def _validation(output: Path, counts: dict[str, int], inspected: ToolResult) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(name="docx_package_written", status="passed", details={"output_path": output.as_posix()}),
            ValidationCheck(name="document_structure", status="passed", details=counts),
            ValidationCheck(name="docx_reopened_by_inspect", status="passed", details=inspected.usage.get("summary", {})),
        ],
    )


def _usage_payload(tool: str, output: Path, title: str, counts: dict[str, int]) -> dict[str, Any]:
    return {
        "summary": counts,
        "report_manifest": {
            "output_path": output.as_posix(), "format": "docx", "tool": tool, "title": title,
            "mutates_inputs": False, "package_type": "ooxml_docx", "macro_enabled": False,
            "external_relationships": [],
        },
    }
