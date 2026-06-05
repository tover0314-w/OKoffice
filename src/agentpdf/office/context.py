from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import inspect_pdf
from agentpdf.office.deck import inspect_deck_presentation
from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.sheet import inspect_sheet_workbook
from agentpdf.office.word import inspect_word_document
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


def build_office_context_packet(
    *,
    files: list[str | Path | dict[str, Any]] | None = None,
    context_items: list[dict[str, Any]] | None = None,
    output_path: str | Path | None = None,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    tool = "office.context.build_packet"
    try:
        paths = _paths_from_inputs(files or [], context_items or [])
        if not paths:
            raise AgentPDFException("invalid_input", "office.context.build_packet requires at least one file.")
        items, warnings = _build_items(paths)
        source_graph = _build_source_graph(items)
        packet = {
            "context_packet_version": "0.1",
            "context_packet_id": f"ctxpkt_{uuid4().hex[:16]}",
            "product": "okoffice",
            "title": title or "OKoffice Context Packet",
            "intent": intent or "",
            "items": items,
            "source_graph": source_graph,
        }
        artifacts = []
        if output_path is not None:
            packet_path = Path(output_path)
            packet_path.parent.mkdir(parents=True, exist_ok=True)
            packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
            artifacts.append(build_artifact(packet_path, source_tool=tool))

        domains = sorted({str(item["domain"]) for item in items})
        inspection_tools = [str(item["inspection"]["tool"]) for item in items]
        return ToolResult(
            job_id=f"job_{uuid4().hex[:16]}",
            status="succeeded",
            tool=tool,
            artifacts=artifacts,
            validation=_validation_report(paths, packet, warnings),
            warnings=warnings,
            usage={
                "context_packet_id": packet["context_packet_id"],
                "item_count": len(items),
                "domains": domains,
                "inspection_tools": inspection_tools,
                "context_packet": packet,
                "source_graph": source_graph,
            },
            next_recommended_tools=[
                "office.extract.schema",
                "office.workflow.extract_to_sheet",
                "office.workflow.source_to_deck",
            ],
        )
    except AgentPDFException as exc:
        return _failed(tool, exc.to_error())


def _paths_from_inputs(
    files: list[str | Path | dict[str, Any]],
    context_items: list[dict[str, Any]],
) -> list[Path]:
    paths: list[Path] = []
    for file_item in files:
        path = _path_from_input(file_item)
        if path is not None:
            paths.append(path)
    for context_item in context_items:
        path = _path_from_input(context_item)
        if path is not None:
            paths.append(path)
    return paths


def _path_from_input(value: str | Path | dict[str, Any]) -> Path | None:
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return Path(value)
    if isinstance(value, dict):
        raw_path = value.get("path") or value.get("input_path") or value.get("uri")
        return Path(str(raw_path)) if raw_path else None
    return None


def _build_items(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    items = []
    warnings: list[str] = []
    for index, path in enumerate(paths, start=1):
        office_result = inspect_office_file(path)
        if office_result.status == "failed":
            raise _exception_from_failed_result(office_result)
        domain = str(office_result.usage["format"]["domain"])
        structure = _structured_inspection(path, domain, str(office_result.usage["format"]["detected_format"]))
        warnings.extend(office_result.warnings)
        warnings.extend(structure.get("warnings", []))
        items.append(
            {
                "context_item_id": f"ctx_{index:03d}",
                "source_ref": f"ctx_{index:03d}",
                "label": path.name,
                "role": "source",
                "uri": office_result.usage["file"]["path"],
                "domain": domain,
                "format": office_result.usage["format"],
                "file": office_result.usage["file"],
                "safety": office_result.usage["safety"],
                "inspection": structure,
            }
        )
    return items, _dedupe(warnings)


def _structured_inspection(path: Path, domain: str, detected_format: str) -> dict[str, Any]:
    result: ToolResult | None = None
    if domain == "word" and detected_format == "docx":
        result = inspect_word_document(path)
    elif domain == "sheet" and detected_format == "xlsx":
        result = inspect_sheet_workbook(path)
    elif domain == "deck" and detected_format == "pptx":
        result = inspect_deck_presentation(path)
    elif domain == "pdf":
        info = inspect_pdf(path)
        return {
            "tool": "pdf.inspect.document",
            "status": "succeeded",
            "summary": {
                "page_count": info.get("page_count"),
                "encrypted": info.get("encrypted"),
            },
            "details": info,
            "warnings": [],
        }
    if result is None:
        return {
            "tool": "office.inspect.file",
            "status": "succeeded",
            "summary": {},
            "details": {},
            "warnings": [],
        }
    if result.status == "failed":
        raise _exception_from_failed_result(result)
    return {
        "tool": result.tool,
        "status": result.status,
        "summary": result.usage.get("summary", {}),
        "details": result.usage,
        "warnings": result.warnings,
    }


def _build_source_graph(items: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for item in items:
        root_id = f"src_{len(nodes) + 1:03d}"
        root_node = {
            "source_id": root_id,
            "source_type": _root_source_type(str(item["domain"])),
            "source_ref": item["source_ref"],
            "label": item["label"],
            "uri": item["uri"],
            "metadata": {
                "domain": item["domain"],
                "format": item["format"],
                "file": item["file"],
                "summary": item["inspection"]["summary"],
            },
        }
        nodes.append(root_node)
        for child in _child_nodes(item, parent_source_id=root_id):
            child_id = f"src_{len(nodes) + 1:03d}"
            child["source_id"] = child_id
            child["parent_source_id"] = root_id
            nodes.append(child)
            edges.append(
                {
                    "edge_id": f"edge_{len(edges) + 1:03d}",
                    "from_source_id": root_id,
                    "to_source_id": child_id,
                    "relation": "contains",
                }
            )
    return {
        "source_graph_id": f"srcgraph_{uuid4().hex[:16]}",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def _root_source_type(domain: str) -> str:
    return {
        "word": "word_document",
        "sheet": "workbook",
        "deck": "deck",
        "pdf": "pdf",
    }.get(domain, "text")


def _child_nodes(item: dict[str, Any], parent_source_id: str) -> list[dict[str, Any]]:
    details = item["inspection"].get("details", {})
    domain = str(item["domain"])
    if domain == "word":
        nodes = [
            _child_node(
                parent_source_id=parent_source_id,
                source_type="word_paragraph",
                source_ref=item["source_ref"],
                locator=paragraph.get("locator"),
                text=paragraph.get("text"),
                metadata={"paragraph_index": paragraph.get("paragraph_index")},
            )
            for paragraph in details.get("paragraphs", [])
        ]
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="word_table",
                source_ref=item["source_ref"],
                locator=table.get("locator"),
                text=f"Table {table.get('table_index')}",
                metadata={"row_count": table.get("row_count"), "column_count": table.get("column_count")},
            )
            for table in details.get("tables", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="word_comment",
                source_ref=item["source_ref"],
                locator=comment.get("locator"),
                text=comment.get("text"),
                metadata={"author": comment.get("author")},
            )
            for comment in details.get("comments", [])
        )
        return nodes
    if domain == "sheet":
        nodes = [
            _child_node(
                parent_source_id=parent_source_id,
                source_type="sheet",
                source_ref=item["source_ref"],
                locator=sheet.get("locator"),
                text=sheet.get("name"),
                metadata={"used_range": sheet.get("used_range")},
            )
            for sheet in details.get("sheets", [])
        ]
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="table",
                source_ref=item["source_ref"],
                locator=table.get("locator"),
                text=table.get("name"),
                metadata={"sheet": table.get("sheet"), "range": table.get("range")},
            )
            for table in details.get("tables", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="formula",
                source_ref=item["source_ref"],
                locator=formula.get("locator"),
                text=formula.get("formula"),
                metadata={"sheet": formula.get("sheet"), "cell": formula.get("cell")},
            )
            for formula in details.get("formulas", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="chart",
                source_ref=item["source_ref"],
                locator=chart.get("locator"),
                text=chart.get("title") or chart.get("chart_id"),
                metadata={
                    "sheet": chart.get("sheet"),
                    "chart_type": chart.get("chart_type"),
                    "planned": chart.get("planned"),
                },
            )
            for chart in details.get("charts", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="named_range",
                source_ref=item["source_ref"],
                locator=None,
                text=named_range.get("name"),
                metadata={"refers_to": named_range.get("refers_to"), "scope": named_range.get("scope")},
            )
            for named_range in details.get("named_ranges", [])
        )
        return nodes
    if domain == "deck":
        nodes = [
            _child_node(
                parent_source_id=parent_source_id,
                source_type="slide",
                source_ref=item["source_ref"],
                locator=slide.get("locator"),
                text=slide.get("title"),
                metadata={"slide_number": slide.get("slide_number")},
            )
            for slide in details.get("slides", [])
        ]
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="shape",
                source_ref=item["source_ref"],
                locator=shape.get("locator"),
                text=shape.get("text"),
                metadata={
                    "slide_number": shape.get("slide_number"),
                    "shape_id": shape.get("shape_id"),
                    "placeholder": shape.get("placeholder"),
                },
            )
            for shape in details.get("shapes", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="speaker_note",
                source_ref=item["source_ref"],
                locator=note.get("locator"),
                text=note.get("text"),
                metadata={"slide_number": note.get("slide_number")},
            )
            for note in details.get("notes", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="slide_chart",
                source_ref=item["source_ref"],
                locator=chart.get("locator"),
                text=chart.get("chart_id"),
                metadata={"slide_number": chart.get("slide_number"), "part": chart.get("part")},
            )
            for chart in details.get("charts", [])
        )
        nodes.extend(
            _child_node(
                parent_source_id=parent_source_id,
                source_type="media",
                source_ref=item["source_ref"],
                locator=media.get("locator"),
                text=media.get("media_id"),
                metadata={"slide_number": media.get("slide_number"), "kind": media.get("kind")},
            )
            for media in details.get("media", [])
        )
        return nodes
    return []


def _child_node(
    *,
    parent_source_id: str,
    source_type: str,
    source_ref: str,
    locator: dict[str, Any] | None,
    text: Any,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_id": "",
        "source_type": source_type,
        "parent_source_id": parent_source_id,
        "source_ref": source_ref,
        "locator": locator,
        "text": str(text or ""),
        "metadata": {key: value for key, value in metadata.items() if value is not None},
    }


def _validation_report(paths: list[Path], packet: dict[str, Any], warnings: list[str]) -> ValidationReport:
    return ValidationReport(
        status="warning" if warnings else "passed",
        checks=[
            ValidationCheck(
                name="inputs_declared",
                status="passed",
                details={"input_count": len(paths)},
            ),
            ValidationCheck(
                name="items_built",
                status="passed",
                details={"item_count": len(packet["items"])},
            ),
            ValidationCheck(
                name="source_graph_built",
                status="passed",
                details={
                    "node_count": packet["source_graph"]["node_count"],
                    "edge_count": packet["source_graph"]["edge_count"],
                },
            ),
        ],
        warnings=warnings,
    )


def _exception_from_failed_result(result: ToolResult) -> AgentPDFException:
    if result.error is None:
        return AgentPDFException("output_validation_failed", f"{result.tool} failed.")
    return AgentPDFException(result.error.code, result.error.message, details=result.error.details)


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )
