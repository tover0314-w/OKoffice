from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.office.deck import inspect_deck_presentation
from okoffice.office.shared import failed_result
from okoffice.office.inspect import inspect_office_file
from okoffice.office.sheet import extract_sheet_tables, inspect_sheet_workbook
from okoffice.office.word import extract_word_tables, inspect_word_document
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport
from okoffice.security.paths import resolve_output_path


TOOL_NAME = "office.context.build_packet"


def build_office_context_packet(
    files: list[str | Path],
    output_path: str | Path | None = None,
    *,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    if not files:
        return failed_result(
            TOOL_NAME,
            OKofficeError(
                code="unsafe_input_rejected",
                message="office.context.build_packet requires at least one input file.",
            ),
        )

    output: Path | None = None
    if output_path is not None:
        try:
            output = resolve_output_path(output_path)
        except OKofficeException as exc:
            return failed_result(TOOL_NAME, exc.to_error())

    items: list[dict[str, Any]] = []
    source_nodes: list[dict[str, Any]] = []
    source_edges: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, file_path in enumerate(files, start=1):
        inspect_result = inspect_office_file(file_path)
        if inspect_result.status == "failed":
            return failed_result(
                TOOL_NAME,
                inspect_result.error
                or OKofficeError(
                    code="unsupported_file_type",
                    message=f"Unable to inspect context source: {file_path}",
                ),
            )

        item, file_node, native_node, edge = _context_item_from_inspect(inspect_result, index)
        extra_nodes, extra_edges, extra_warnings = _enriched_source_nodes(inspect_result, index, native_node)
        items.append(item)
        source_nodes.extend([file_node, native_node, *extra_nodes])
        source_edges.extend([edge, *extra_edges])
        sources.append(_source_summary(inspect_result, item["context_item_id"]))
        warnings.extend([*inspect_result.warnings, *extra_warnings])

    source_graph = {
        "source_graph_version": "0.1",
        "source_graph_id": f"srcgraph_{uuid4().hex[:16]}",
        "nodes": source_nodes,
        "edges": source_edges,
    }
    _finalize_source_graph(source_graph)
    packet = {
        "product": "okoffice",
        "context_packet_version": "0.1",
        "context_packet_id": f"ctxpkt_{uuid4().hex[:16]}",
        "title": (title or "OKoffice Context Packet").strip(),
        "intent": (intent or "").strip(),
        "created_at": datetime.now(UTC).isoformat(),
        "items": items,
        "source_graph": {
            **source_graph,
            "node_count": len(source_nodes),
            "edge_count": len(source_edges),
        },
    }

    artifacts = []
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        artifacts.append(build_artifact(output, TOOL_NAME))

    formats = _counts(source["format"]["detected_format"] for source in sources)
    domains = _counts(source["format"]["domain"] for source in sources)
    checks = [
        ValidationCheck(
            name="input_files_scanned",
            status="passed",
            details={"input_count": len(files), "item_count": len(items)},
        ),
        ValidationCheck(
            name="source_graph_created",
            status="passed",
            details={"node_count": len(source_nodes), "edge_count": len(source_edges)},
        ),
        ValidationCheck(
            name="context_packet_written",
            status="passed" if output is not None else "skipped",
            details={"path": output.as_posix() if output is not None else None},
        ),
        ValidationCheck(
            name="source_warnings_collected",
            status="passed",
            message="Source warnings are reported without blocking context packet construction." if warnings else None,
            details={"warning_count": len(warnings)},
        ),
    ]

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=TOOL_NAME,
        artifacts=artifacts,
        validation=ValidationReport(
            status=_validation_status(checks),
            checks=checks,
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "input_count": len(files),
                "item_count": len(items),
                "source_node_count": len(source_nodes),
                "source_edge_count": len(source_edges),
                "native_node_count": len(source_nodes) - len(items),
                "formats": formats,
                "domains": domains,
                "warning_count": len(warnings),
                "output_path": output.as_posix() if output is not None else None,
            },
            "context_packet_id": packet["context_packet_id"],
            "context_packet": packet,
            "source_graph": {
                "source_graph_id": source_graph["source_graph_id"],
                "node_count": len(source_nodes),
                "edge_count": len(source_edges),
                "nodes": source_nodes,
                "edges": source_edges,
            },
            "sources": sources,
        },
        next_recommended_tools=[
            "office.workflow.extract_to_sheet",
            "office.extract.schema",
            "office.evidence.coverage",
            "office.workflow.sheet_to_deck",
        ],
    )


def _finalize_source_graph(source_graph: dict[str, Any]) -> None:
    for node in source_graph.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type") or "")
        node.setdefault("source_type", _compact_source_type(node_type))
        locators = node.get("locators")
        if "locator" not in node and isinstance(locators, list) and locators and isinstance(locators[0], dict):
            node["locator"] = locators[0]
        if "text" not in node:
            node["text"] = _node_text(node)
    for edge in source_graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        relationship = str(edge.get("relationship") or "contains")
        edge.setdefault("relation", "contains" if relationship.startswith("contains") else relationship)


def _compact_source_type(node_type: str) -> str:
    mapping = {
        "file": "file",
        "word.document": "document",
        "word.paragraph": "word_paragraph",
        "word.table": "table",
        "sheet.workbook": "workbook",
        "sheet.sheet": "sheet",
        "sheet.table": "table",
        "sheet.chart": "chart",
        "sheet.formula_summary": "formula",
        "deck.presentation": "deck",
        "deck.slide": "slide",
        "deck.shape": "shape",
        "deck.speaker_note": "speaker_note",
        "pdf.document": "pdf",
    }
    return mapping.get(node_type, node_type.rsplit(".", 1)[-1] if "." in node_type else node_type)


def _node_text(node: dict[str, Any]) -> str:
    for key in ("label", "evidence_text"):
        value = str(node.get(key) or "").strip()
        if value:
            return value
    evidence = node.get("evidence")
    if isinstance(evidence, dict):
        for key in ("text", "summary", "excerpt"):
            value = str(evidence.get(key) or "").strip()
            if value:
                return value
    return ""


def _context_item_from_inspect(
    inspect_result: ToolResult,
    index: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    usage = inspect_result.usage
    file_info = dict(usage["file"])
    format_info = dict(usage["format"])
    safety = dict(usage["safety"])
    context_item_id = f"ctx_{index:03d}"
    detected_format = str(format_info["detected_format"])
    domain = str(format_info["domain"])
    item_type = _context_item_type(detected_format, domain)
    source_ref = f"{context_item_id}:file"
    native_ref = f"{context_item_id}:{detected_format}"
    label = str(file_info["name"])

    item = {
        "context_item_id": context_item_id,
        "type": item_type,
        "role": "source",
        "label": label,
        "source_ref": source_ref,
        "uri": str(file_info["path"]),
        "metadata": {
            "office": {
                "file": file_info,
                "format": format_info,
                "safety": safety,
            },
            "source_refs": [source_ref, native_ref],
            "warnings": list(inspect_result.warnings),
        },
        "content": {
            "text": _content_preview(format_info, file_info),
            "office": {
                "detected_format": detected_format,
                "domain": domain,
                "package_type": format_info.get("package_type"),
                "source_ref": native_ref,
            },
        },
    }
    file_node = {
        "node_id": f"src_{index:03d}_file",
        "context_item_id": context_item_id,
        "source_ref": source_ref,
        "type": "file",
        "role": "source_file",
        "label": label,
        "uri": str(file_info["path"]),
        "locators": [{"kind": "file", "path": str(file_info["path"])}],
        "evidence": {
            "file": file_info,
            "format": format_info,
            "safety": safety,
        },
    }
    native_node = {
        "node_id": f"src_{index:03d}_{detected_format}",
        "context_item_id": context_item_id,
        "source_ref": native_ref,
        "type": _native_node_type(detected_format, domain),
        "role": "native_artifact",
        "label": label,
        "uri": str(file_info["path"]),
        "locators": [_native_locator(detected_format, file_info)],
        "evidence": {
            "format": format_info,
            "safety": safety,
            "warnings": list(inspect_result.warnings),
        },
    }
    edge = {
        "edge_id": f"edge_{index:03d}_file_to_native",
        "from": file_node["node_id"],
        "to": native_node["node_id"],
        "relationship": "contains",
    }
    return item, file_node, native_node, edge


def _enriched_source_nodes(
    inspect_result: ToolResult,
    index: int,
    native_node: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    detected_format = str(inspect_result.usage["format"]["detected_format"])
    path = Path(str(inspect_result.usage["file"]["path"]))
    try:
        if detected_format == "docx":
            return _word_source_nodes(path, index, native_node)
        if detected_format == "xlsx":
            return _sheet_source_nodes(path, index, native_node)
        if detected_format == "pptx":
            return _deck_source_nodes(path, index, native_node)
    except Exception as exc:
        return [], [], [f"{detected_format} source enrichment skipped: {exc}"]
    return [], [], []


def _word_source_nodes(
    path: Path,
    index: int,
    native_node: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    nodes: list[dict[str, Any]] = []
    inspect_result = inspect_word_document(path)
    if inspect_result.status == "failed":
        return [], [], _tool_warnings(inspect_result, "word.inspect.document")

    table_result = extract_word_tables(path)
    if table_result.status == "failed":
        warnings.extend(_tool_warnings(table_result, "word.extract.tables"))
        tables: list[dict[str, Any]] = []
    else:
        tables = [table for table in table_result.usage.get("tables", []) if isinstance(table, dict)]

    structure = inspect_result.usage.get("structure", {})
    paragraphs = [paragraph for paragraph in inspect_result.usage.get("paragraphs", []) if isinstance(paragraph, dict)]
    for paragraph in paragraphs:
        paragraph_index = int(paragraph.get("paragraph_index", len(nodes)))
        text = str(paragraph.get("text") or "").strip()
        if not text:
            continue
        locator = paragraph.get("locator") if isinstance(paragraph.get("locator"), dict) else {
            "kind": "word",
            "path": path.as_posix(),
            "paragraph_index": paragraph_index,
        }
        nodes.append(
            {
                "node_id": f"src_{index:03d}_word_paragraph_{paragraph_index + 1}",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:paragraph:{paragraph_index + 1}",
                "type": "word.paragraph",
                "role": "paragraph",
                "label": f"{path.name} paragraph {paragraph_index + 1}",
                "uri": path.as_posix(),
                "locators": [locator],
                "text": text,
                "evidence": {
                    "text": text,
                    "style": paragraph.get("style"),
                    "paragraph_id": paragraph.get("paragraph_id"),
                    "document_structure": structure,
                },
            }
        )
    for table in tables:
        table_index = int(table.get("table_index", len(nodes) + 1))
        row_count = len(table.get("rows", [])) if isinstance(table.get("rows"), list) else 0
        cell_count = sum(
            len(row.get("cells", []))
            for row in table.get("rows", [])
            if isinstance(row, dict) and isinstance(row.get("cells"), list)
        )
        nodes.append(
            {
                "node_id": f"src_{index:03d}_word_table_{table_index}",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:table:{table_index}",
                "type": "word.table",
                "role": "source_table",
                "label": f"{path.name} table {table_index}",
                "uri": path.as_posix(),
                "locators": [{"kind": "word_table", "path": path.as_posix(), "table_index": table_index}],
                "evidence": {
                    "table_id": table.get("table_id"),
                    "row_count": row_count,
                    "cell_count": cell_count,
                    "document_structure": structure,
                },
            }
        )
    return nodes, _contains_edges(native_node, nodes), warnings


def _sheet_source_nodes(
    path: Path,
    index: int,
    native_node: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    nodes: list[dict[str, Any]] = []
    inspect_result = inspect_sheet_workbook(path)
    if inspect_result.status == "failed":
        return [], [], _tool_warnings(inspect_result, "sheet.inspect.workbook")

    sheets = [sheet for sheet in inspect_result.usage.get("sheets", []) if isinstance(sheet, dict)]
    for sheet in sheets:
        sheet_index = int(sheet.get("sheet_index", len(nodes) + 1))
        sheet_name = str(sheet.get("name") or f"Sheet{sheet_index}")
        nodes.append(
            {
                "node_id": f"src_{index:03d}_sheet_{sheet_index}",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:sheet:{sheet_index}",
                "type": "sheet.sheet",
                "role": "worksheet",
                "label": f"{path.name} {sheet_name}",
                "uri": path.as_posix(),
                "locators": [{"kind": "worksheet", "path": path.as_posix(), "sheet_name": sheet_name}],
                "evidence": sheet,
            }
        )

    table_result = extract_sheet_tables(path)
    if table_result.status == "failed":
        warnings.extend(_tool_warnings(table_result, "sheet.extract.tables"))
        tables: list[dict[str, Any]] = []
    else:
        tables = [table for table in table_result.usage.get("tables", []) if isinstance(table, dict)]

    for table in tables:
        source = table.get("source") if isinstance(table.get("source"), dict) else {}
        table_index = int(table.get("table_index", len(nodes) + 1))
        sheet_name = str(source.get("sheet_name") or f"Sheet{source.get('sheet_index', 1)}")
        range_ref = str(source.get("range_ref") or "")
        row_count = len(table.get("rows", [])) if isinstance(table.get("rows"), list) else 0
        cell_count = sum(
            len(row.get("cells", []))
            for row in table.get("rows", [])
            if isinstance(row, dict) and isinstance(row.get("cells"), list)
        )
        nodes.append(
            {
                "node_id": f"src_{index:03d}_sheet_table_{table_index}",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:table:{table_index}",
                "type": "sheet.table",
                "role": "source_table",
                "label": f"{path.name} {sheet_name} {range_ref}",
                "uri": path.as_posix(),
                "locators": [
                    {
                        "kind": "sheet_range",
                        "path": path.as_posix(),
                        "sheet_name": sheet_name,
                        "range_ref": range_ref,
                    }
                ],
                "evidence": {
                    "table_id": table.get("table_id"),
                    "row_count": row_count,
                    "cell_count": cell_count,
                    "source": source,
                },
            }
        )

    charts = [chart for chart in inspect_result.usage.get("charts", []) if isinstance(chart, dict)]
    for chart_index, chart in enumerate(charts, start=1):
        locator = chart.get("locator") if isinstance(chart.get("locator"), dict) else {}
        nodes.append(
            {
                "node_id": f"src_{index:03d}_sheet_chart_{chart_index}",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:chart:{chart_index}",
                "type": "sheet.chart",
                "role": "chart",
                "label": str(chart.get("title") or chart.get("chart_id") or f"{path.name} chart {chart_index}"),
                "uri": path.as_posix(),
                "locators": [locator or {"kind": "sheet", "path": path.as_posix()}],
                "evidence": chart,
            }
        )

    formula_usage = inspect_result.usage.get("formulas", [])
    formula_count = len(formula_usage) if isinstance(formula_usage, list) else int(formula_usage.get("formula_count", 0))
    if formula_count:
        nodes.append(
            {
                "node_id": f"src_{index:03d}_sheet_formula_summary",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:formulas",
                "type": "sheet.formula_summary",
                "role": "formula_evidence",
                "label": f"{path.name} formulas",
                "uri": path.as_posix(),
                "locators": [{"kind": "workbook_formulas", "path": path.as_posix()}],
                "evidence": {"formula_count": formula_count},
            }
        )
    return nodes, _contains_edges(native_node, nodes), warnings


def _deck_source_nodes(
    path: Path,
    index: int,
    native_node: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    inspect_result = inspect_deck_presentation(path)
    if inspect_result.status == "failed":
        return [], [], _tool_warnings(inspect_result, "deck.inspect.presentation")

    presentation = inspect_result.usage.get("presentation", {})
    slide_count = int(presentation.get("slide_count", 0))
    text_run_count = int(presentation.get("text_run_count", 0))
    slide_texts, note_texts = _deck_text_parts(path)
    nodes: list[dict[str, Any]] = []
    for slide_index in range(1, slide_count + 1):
        slide_part = f"ppt/slides/slide{slide_index}.xml"
        slide_text = slide_texts.get(slide_part, "")
        nodes.append(
            {
                "node_id": f"src_{index:03d}_deck_slide_{slide_index}",
                "context_item_id": str(native_node["context_item_id"]),
                "source_ref": f"{native_node['source_ref']}:slide:{slide_index}",
                "type": "deck.slide",
                "role": "slide",
                "label": f"{path.name} slide {slide_index}",
                "uri": path.as_posix(),
                "locators": [
                    {
                        "kind": "deck_slide",
                        "path": path.as_posix(),
                        "slide_index": slide_index,
                        "package_part": slide_part,
                    }
                ],
                "text": slide_text,
                "evidence": {
                    "slide_index": slide_index,
                    "package_part": slide_part,
                    "presentation_text_run_count": text_run_count,
                },
            }
        )
        if slide_text:
            nodes.append(
                {
                    "node_id": f"src_{index:03d}_deck_slide_{slide_index}_shape_1",
                    "context_item_id": str(native_node["context_item_id"]),
                    "source_ref": f"{native_node['source_ref']}:slide:{slide_index}:shape:1",
                    "type": "deck.shape",
                    "role": "shape_text",
                    "label": f"{path.name} slide {slide_index} text",
                    "uri": path.as_posix(),
                    "locators": [
                        {
                            "kind": "deck_shape",
                            "path": path.as_posix(),
                            "slide_index": slide_index,
                            "shape_index": 1,
                            "package_part": slide_part,
                        }
                    ],
                    "text": slide_text,
                    "evidence": {"text": slide_text},
                }
            )
        note_text = note_texts.get(slide_index, "")
        if note_text:
            nodes.append(
                {
                    "node_id": f"src_{index:03d}_deck_slide_{slide_index}_speaker_note",
                    "context_item_id": str(native_node["context_item_id"]),
                    "source_ref": f"{native_node['source_ref']}:slide:{slide_index}:speaker_note",
                    "type": "deck.speaker_note",
                    "role": "speaker_note",
                    "label": f"{path.name} slide {slide_index} speaker notes",
                    "uri": path.as_posix(),
                    "locators": [
                        {
                            "kind": "deck_notes",
                            "path": path.as_posix(),
                            "slide_index": slide_index,
                            "package_part": f"ppt/notesSlides/notesSlide{slide_index - 1}.xml",
                        }
                    ],
                    "text": note_text,
                    "evidence": {"text": note_text},
                }
            )
    return nodes, _contains_edges(native_node, nodes), []


def _deck_text_parts(path: Path) -> tuple[dict[str, str], dict[int, str]]:
    slide_texts: dict[str, str] = {}
    note_texts: dict[int, str] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            names = {name.replace("\\", "/") for name in archive.namelist()}
            slide_members = sorted(
                [name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
                key=_deck_part_index,
            )
            for slide_index, slide_part in enumerate(slide_members, start=1):
                slide_texts[slide_part] = _ooxml_text(archive.read(slide_part))
                rels_part = _deck_rels_part(slide_part)
                if rels_part not in names:
                    continue
                rels_root = ElementTree.fromstring(archive.read(rels_part))
                for relationship in rels_root:
                    rel_type = str(relationship.attrib.get("Type") or "")
                    if not rel_type.endswith("/notesSlide"):
                        continue
                    target = _deck_resolve_target(slide_part, str(relationship.attrib.get("Target") or ""))
                    if target in names:
                        note_texts[slide_index] = _ooxml_text(archive.read(target))
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError):
        return slide_texts, note_texts
    return slide_texts, note_texts


def _ooxml_text(data: bytes) -> str:
    root = ElementTree.fromstring(data)
    values = [node.text or "" for node in root.iter() if str(node.tag).endswith("}t")]
    return "\n".join(value for value in values if value).strip()


def _deck_rels_part(part: str) -> str:
    path = PurePosixPath(part)
    return str(path.parent / "_rels" / f"{path.name}.rels")


def _deck_resolve_target(source_part: str, target: str) -> str:
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
        else:
            parts.append(part)
    return "/".join(parts)


def _deck_part_index(part: str) -> int:
    stem = PurePosixPath(part).stem
    digits = "".join(char for char in stem if char.isdigit())
    return int(digits or "0")


def _contains_edges(parent_node: dict[str, Any], child_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": f"edge_{parent_node['node_id']}_to_{child['node_id']}",
            "from": str(parent_node["node_id"]),
            "to": str(child["node_id"]),
            "relationship": "contains_source_node",
        }
        for child in child_nodes
    ]


def _tool_warnings(result: ToolResult, tool_name: str) -> list[str]:
    if result.warnings:
        return [f"{tool_name}: {warning}" for warning in result.warnings]
    if result.error is not None:
        return [f"{tool_name}: {result.error.message}"]
    return [f"{tool_name}: source enrichment was skipped."]


def _context_item_type(detected_format: str, domain: str) -> str:
    if detected_format == "pdf":
        return "pdf"
    if domain == "sheet":
        return "data"
    if domain in {"word", "deck", "office"}:
        return "document"
    return "file"


def _native_node_type(detected_format: str, domain: str) -> str:
    if domain == "word":
        return "word.document"
    if domain == "sheet":
        return "sheet.workbook"
    if domain == "deck":
        return "deck.presentation"
    if detected_format == "pdf":
        return "pdf.document"
    return f"office.{detected_format}"


def _native_locator(detected_format: str, file_info: dict[str, Any]) -> dict[str, Any]:
    if detected_format == "docx":
        return {"kind": "word_document", "path": file_info["path"], "package_part": "word/document.xml"}
    if detected_format == "xlsx":
        return {"kind": "sheet_workbook", "path": file_info["path"], "package_part": "xl/workbook.xml"}
    if detected_format == "pptx":
        return {"kind": "deck_presentation", "path": file_info["path"], "package_part": "ppt/presentation.xml"}
    if detected_format == "pdf":
        return {"kind": "pdf_document", "path": file_info["path"]}
    return {"kind": detected_format, "path": file_info["path"]}


def _content_preview(format_info: dict[str, Any], file_info: dict[str, Any]) -> str:
    detected_format = format_info.get("detected_format", "file")
    return f"{file_info['name']} ({detected_format}) inspected for OKoffice context packet."


def _source_summary(inspect_result: ToolResult, context_item_id: str) -> dict[str, Any]:
    return {
        "context_item_id": context_item_id,
        "file": inspect_result.usage["file"],
        "format": inspect_result.usage["format"],
        "safety": inspect_result.usage["safety"],
        "warnings": list(inspect_result.warnings),
    }


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _validation_status(checks: list[ValidationCheck]) -> str:
    statuses = [check.status for check in checks]
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    return "passed"
