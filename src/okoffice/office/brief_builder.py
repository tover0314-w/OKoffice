from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.office.inspect import inspect_office_file
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_input_path, resolve_output_path

TOOL_NAME = "office.workflow.multi_format_brief"


def build_multi_format_brief(
    *,
    files: list[str | Path],
    output_path: str | Path | None = None,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    try:
        sources = []
        warnings: list[str] = []
        format_counts: dict[str, int] = {}
        key_content: list[dict[str, Any]] = []

        for file_path in files:
            resolved = resolve_input_path(file_path)
            inspect_result = inspect_office_file(resolved)
            source_info: dict[str, Any] = {
                "path": resolved.as_posix(),
                "name": resolved.name,
                "size_bytes": resolved.stat().st_size,
            }
            if inspect_result.status == "succeeded" and inspect_result.usage:
                fmt = inspect_result.usage.get("format", {})
                detected = fmt.get("detected_format", "unknown")
                domain = fmt.get("domain", "unknown")
                source_info["format"] = detected
                source_info["domain"] = domain
                format_counts[detected] = format_counts.get(detected, 0) + 1
                key_content.append(_extract_key_content(resolved, detected))
            else:
                source_info["format"] = "unknown"
                source_info["domain"] = "unknown"
                source_info["inspect_error"] = inspect_result.error.message if inspect_result.error else "unknown"
                warnings.append(f"Could not inspect {resolved.name}")
            sources.append(source_info)

        brief: dict[str, Any] = {
            "title": title or "Multi-Format Brief",
            "intent": intent or "Aggregate multi-format source evidence for downstream workflows.",
            "source_count": len(files),
            "format_distribution": format_counts,
            "sources": sources,
            "key_content": key_content,
            "recommended_workflows": _recommend_workflows(format_counts),
        }

        artifacts = []
        if output_path is not None:
            destination = resolve_output_path(output_path)
            destination.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            from okoffice.artifacts.store import build_artifact
            artifacts.append(build_artifact(destination, source_tool=TOOL_NAME))

        checks = [
            ValidationCheck(
                name="sources_inspected",
                status="passed",
                details={"total": len(files), "successful": sum(1 for s in sources if s.get("format") != "unknown")},
            ),
            ValidationCheck(
                name="format_distribution",
                status="passed",
                details=format_counts,
            ),
        ]
        return ToolResult(
            job_id=f"job_{uuid4().hex[:12]}",
            status="succeeded",
            tool=TOOL_NAME,
            artifacts=artifacts,
            validation=ValidationReport(
                status="warning" if warnings else "passed",
                checks=checks,
                warnings=warnings,
            ),
            warnings=warnings,
            usage={
                "brief_title": brief["title"],
                "source_count": len(files),
                "format_distribution": format_counts,
                "recommended_workflows": brief["recommended_workflows"],
            },
            next_recommended_tools=brief["recommended_workflows"],
        )
    except OKofficeException as exc:
        return ToolResult(
            job_id=f"job_{uuid4().hex[:12]}",
            status="failed",
            tool=TOOL_NAME,
            error=exc.to_error(),
            warnings=[exc.message],
        )


def _extract_key_content(path: Path, detected_format: str) -> dict[str, Any]:
    content: dict[str, Any] = {"path": path.as_posix(), "format": detected_format}
    try:
        if detected_format == "pdf":
            content["summary"] = _pdf_key_content(path)
        elif detected_format in ("docx", "word"):
            content["summary"] = _docx_key_content(path)
        elif detected_format in ("xlsx", "sheet"):
            content["summary"] = _xlsx_key_content(path)
        elif detected_format in ("pptx", "deck"):
            content["summary"] = _pptx_key_content(path)
        else:
            content["summary"] = {"text_preview": path.read_text(encoding="utf-8", errors="replace")[:500]}
    except Exception:
        content["summary"] = {"note": "Content extraction skipped"}
    return content


def _pdf_key_content(path: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return {
            "page_count": len(reader.pages),
            "metadata": {k: v for k, v in (reader.metadata or {}).items() if v},
        }
    except Exception:
        return {"note": "PDF read skipped"}


def _docx_key_content(path: Path) -> dict[str, Any]:
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            doc_xml = z.read("word/document.xml")
            root = ET.fromstring(doc_xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            headings = [
                p.text for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                if p.text
            ]
            return {
                "text_preview": " ".join(headings[:20])[:500],
                "heading_count": len([p for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")
                                      if p.find(".//w:pStyle[@w:val]", ns) is not None]),
            }
    except Exception:
        return {"note": "DOCX read skipped"}


def _xlsx_key_content(path: Path) -> dict[str, Any]:
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            sheets_xml = z.read("xl/workbook.xml")
            root = ET.fromstring(sheets_xml)
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            sheets = [
                s.get("name", "") for s in root.findall(".//s:sheet", ns)
            ]
            return {"sheet_names": sheets, "sheet_count": len(sheets)}
    except Exception:
        return {"note": "XLSX read skipped"}


def _pptx_key_content(path: Path) -> dict[str, Any]:
    import xml.etree.ElementTree as ET
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            slides = [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
            titles = []
            for slide_name in slides:
                slide_xml = z.read(slide_name)
                root = ET.fromstring(slide_xml)
                for ph in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t"):
                    if ph.text and ph.text.strip():
                        titles.append(ph.text.strip())
                        break
            return {"slide_count": len(slides), "slide_titles": titles[:10]}
    except Exception:
        return {"note": "PPTX read skipped"}


def _recommend_workflows(format_counts: dict[str, int]) -> list[str]:
    workflows = []
    has_doc = format_counts.get("docx", 0) + format_counts.get("word", 0) > 0
    has_sheet = format_counts.get("xlsx", 0) + format_counts.get("sheet", 0) > 0
    has_deck = format_counts.get("pptx", 0) + format_counts.get("deck", 0) > 0
    has_pdf = format_counts.get("pdf", 0) > 0
    if has_doc or has_pdf:
        workflows.append("office.workflow.source_to_doc")
    if has_doc or has_pdf or has_sheet:
        workflows.append("office.workflow.source_to_deck")
    if sum(format_counts.values()) >= 2:
        workflows.append("office.workflow.source_to_board_pack")
    if not workflows:
        workflows.append("office.context.build_packet")
    return workflows
