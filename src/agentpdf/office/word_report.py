from __future__ import annotations

import html
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.deck_writer import _load_evidence_workbook
from agentpdf.office.word import inspect_word_document
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path, resolve_output_path


TOOL_NAME = "word.create.report"


def create_word_report(
    *,
    workbook_path: str | Path,
    output_path: str | Path,
    title: str | None = None,
    profile: str = "executive_memo",
) -> ToolResult:
    try:
        workbook = resolve_input_path(workbook_path)
        output = resolve_output_path(output_path)
        if output.suffix.lower() != ".docx":
            raise AgentPDFException(
                "unsupported_file_type",
                "word.create.report writes .docx output files.",
                details={"output_path": output.as_posix()},
            )

        data = _load_evidence_workbook(workbook)
        report_title = title or _default_title(workbook)
        paragraphs = _compose_paragraphs(data=data, title=report_title)
        _write_docx_package(output, paragraphs, title=report_title)

        inspected = inspect_word_document(output)
        if inspected.status != "succeeded":
            raise AgentPDFException(
                "output_validation_failed",
                "Generated Word report could not be inspected.",
                details=inspected.error.model_dump(mode="json") if inspected.error else {},
            )

        artifacts = [build_artifact(output, source_tool=TOOL_NAME)]
        return ToolResult(
            job_id=_job_id(),
            status="succeeded",
            tool=TOOL_NAME,
            artifacts=artifacts,
            validation=_validation_report(data, output, inspected, paragraphs),
            usage=_usage(data, output, workbook, profile, paragraphs),
            next_recommended_tools=["word.inspect.document", "office.bundle.export", "office.workflow.board_pack"],
        )
    except AgentPDFException as exc:
        return _failed(exc.to_error())
    except (ValueError, zipfile.BadZipFile) as exc:
        return _failed(AgentPDFError(code="invalid_input", message=str(exc)))


def _compose_paragraphs(data: dict[str, Any], title: str) -> list[str]:
    paragraphs = [title]
    for row in data["rows"]:
        values = row["values"]
        for field, value in values.items():
            if value:
                paragraphs.append(f"{_field_label(field)}: {value}")
        source_refs = row["source_refs"]
        paragraphs.append(f"Sources: {', '.join(source_refs)}" if source_refs else "Sources: none")
    return paragraphs


def _write_docx_package(path: Path, paragraphs: list[str], title: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("docProps/core.xml", _core_props_xml(title))
        archive.writestr("docProps/app.xml", _app_props_xml())
        archive.writestr("word/document.xml", _document_xml(paragraphs))


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
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
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _document_xml(paragraphs: list[str]) -> str:
    body = "".join(f"<w:p><w:r><w:t>{_xml_text(paragraph)}</w:t></w:r></w:p>" for paragraph in paragraphs)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}<w:sectPr/></w:body></w:document>"
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


def _app_props_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        "<Application>okoffice</Application>"
        "</Properties>"
    )


def _usage(
    data: dict[str, Any],
    output: Path,
    workbook: Path,
    profile: str,
    paragraphs: list[str],
) -> dict[str, Any]:
    source_ref_count = len([row for row in data["source_map_rows"] if row.get("source_ref")])
    return {
        "summary": {
            "paragraph_count": len(paragraphs),
            "row_count": len(data["rows"]),
            "field_count": len(data["headers"]),
            "source_ref_count": source_ref_count,
        },
        "report_manifest": {
            "output_path": output.as_posix(),
            "format": "docx",
            "profile": profile,
            "mutates_inputs": False,
            "package_type": "ooxml_docx",
            "macro_enabled": False,
            "external_relationships": [],
            "source_workbook_path": workbook.as_posix(),
        },
        "rows": [
            {
                "row_id": row["row_id"],
                "source_refs": row["source_refs"],
                "field_count": len([value for value in row["values"].values() if value]),
            }
            for row in data["rows"]
        ],
    }


def _validation_report(
    data: dict[str, Any],
    output: Path,
    inspected: ToolResult,
    paragraphs: list[str],
) -> ValidationReport:
    return ValidationReport(
        status="passed",
        checks=[
            ValidationCheck(
                name="evidence_workbook_loaded",
                status="passed",
                details={"row_count": len(data["rows"]), "field_count": len(data["headers"])},
            ),
            ValidationCheck(
                name="word_report_written",
                status="passed",
                details={"output_path": output.as_posix(), "paragraph_count": len(paragraphs)},
            ),
            ValidationCheck(
                name="word_report_reopened_by_inspect",
                status="passed",
                details=inspected.usage.get("summary", {}),
            ),
        ],
    )


def _field_label(field: str) -> str:
    return field.replace("_", " ").capitalize()


def _default_title(workbook: Path) -> str:
    return f"{workbook.stem.replace('-', ' ').replace('_', ' ').title()} Memo"


def _xml_text(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=False)


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
