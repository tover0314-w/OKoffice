from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.office.inspect import inspect_office_file
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_output_path


TOOL_NAME = "office.context.build_packet"


def build_office_context_packet(
    files: list[str | Path],
    output_path: str | Path | None = None,
    *,
    title: str | None = None,
    intent: str | None = None,
) -> ToolResult:
    if not files:
        return _failed(
            AgentPDFError(
                code="unsafe_input_rejected",
                message="office.context.build_packet requires at least one input file.",
            )
        )

    output: Path | None = None
    if output_path is not None:
        try:
            output = resolve_output_path(output_path)
        except AgentPDFException as exc:
            return _failed(exc.to_error())

    items: list[dict[str, Any]] = []
    source_nodes: list[dict[str, Any]] = []
    source_edges: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, file_path in enumerate(files, start=1):
        inspect_result = inspect_office_file(file_path)
        if inspect_result.status == "failed":
            return _failed(
                inspect_result.error
                or AgentPDFError(
                    code="unsupported_file_type",
                    message=f"Unable to inspect context source: {file_path}",
                )
            )

        item, file_node, native_node, edge = _context_item_from_inspect(inspect_result, index)
        items.append(item)
        source_nodes.extend([file_node, native_node])
        source_edges.append(edge)
        sources.append(_source_summary(inspect_result, item["context_item_id"]))
        warnings.extend(inspect_result.warnings)

    source_graph = {
        "source_graph_version": "0.1",
        "source_graph_id": f"srcgraph_{uuid4().hex[:16]}",
        "nodes": source_nodes,
        "edges": source_edges,
    }
    packet = {
        "product": "okoffice",
        "context_packet_version": "0.1",
        "context_packet_id": f"ctxpkt_{uuid4().hex[:16]}",
        "title": (title or "OKoffice Context Packet").strip(),
        "intent": (intent or "").strip(),
        "created_at": datetime.now(UTC).isoformat(),
        "items": items,
        "source_graph": source_graph,
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
            status="warning" if warnings else "passed",
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


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool=TOOL_NAME,
        error=error,
        warnings=[error.message],
    )
