from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.core.pdf import create_markdown_pdf
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.validation.pdf import validate_pdf


def create_context_packet_report(
    context_packet: dict[str, Any] | str | Path,
    output_path: str | Path,
    report_output_path: str | Path | None = None,
    title: str | None = None,
    style_pack: str = "paper_ink",
) -> ToolResult:
    tool = "pdf.evidence.context_packet_report"
    packet = _load_context_packet(context_packet)
    report = _build_report_payload(packet)
    markdown = _report_markdown(report, title=title)
    rendered = create_markdown_pdf(
        markdown,
        output_path=output_path,
        title=title or "OKoffice Context Packet Report",
        style_pack=style_pack,
    )
    pdf_path = rendered.artifacts[0].path if rendered.artifacts else Path(output_path).resolve()
    validation = validate_pdf(pdf_path)

    json_path = Path(report_output_path) if report_output_path is not None else Path(output_path).with_suffix(".context-report.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    artifacts = [
        build_artifact(pdf_path, source_tool=tool),
        build_artifact(json_path, source_tool=tool),
    ]
    warnings = [*validation.warnings, *_report_warnings(report)]
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=artifacts,
        validation=validation,
        warnings=warnings,
        usage={
            "context_packet_id": report["context_packet_id"],
            "context_packet_report_id": report["context_packet_report_id"],
            "source_graph_id": report["source_graph"]["source_graph_id"],
            "source_ref_count": report["source_ref_count"],
            "context_packet_report": report,
            "generated_markdown": markdown,
        },
        next_recommended_tools=[
            "pdf.compose.from_context",
            "pdf.evidence.coverage_report",
            "pdf.artifacts.export_bundle",
        ],
    )


def _load_context_packet(context_packet: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(context_packet, dict):
        packet = context_packet
    else:
        path = Path(context_packet)
        if not path.exists():
            raise OKofficeException("file_not_found", f"Context packet not found: {path}")
        packet = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(packet, dict) or not packet.get("context_packet_id") or not isinstance(packet.get("items"), list):
        raise OKofficeException("invalid_context_packet", "Context packet must include context_packet_id and items.")
    if not isinstance(packet.get("source_graph"), dict):
        raise OKofficeException("invalid_context_packet", "Context packet must include source_graph.")
    return packet


def _build_report_payload(packet: dict[str, Any]) -> dict[str, Any]:
    items = [_item_report(item) for item in packet.get("items", []) if isinstance(item, dict)]
    source_graph = packet.get("source_graph", {})
    nodes = source_graph.get("nodes") if isinstance(source_graph.get("nodes"), list) else []
    return {
        "context_packet_report_version": "0.1",
        "context_packet_report_id": f"ctxrpt_{uuid4().hex[:16]}",
        "context_packet_id": packet["context_packet_id"],
        "title": packet.get("title") or "OKoffice Context Packet",
        "intent": packet.get("intent") or "",
        "item_count": len(items),
        "item_types": sorted({item["type"] for item in items}),
        "source_ref_count": len({item["source_ref"] for item in items if item.get("source_ref")}),
        "items": items,
        "source_graph": {
            "source_graph_id": source_graph.get("source_graph_id"),
            "source_graph_version": source_graph.get("source_graph_version"),
            "node_count": len(nodes),
            "edge_count": len(source_graph.get("edges", [])) if isinstance(source_graph.get("edges"), list) else 0,
            "nodes": nodes,
        },
        "limitations": {
            "web_fetch": "not_performed",
            "ocr": "not_performed",
            "vision_model": "not_performed",
            "audio_transcription": "provided_transcripts_only",
            "video_keyframes": "provided_keyframes_only",
        },
    }


def _item_report(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    evidence_kind, evidence = _primary_evidence(item, metadata)
    report = {
        "context_item_id": item.get("context_item_id"),
        "source_ref": item.get("source_ref"),
        "type": item.get("type"),
        "role": item.get("role"),
        "label": item.get("label"),
        "uri": item.get("uri"),
        "evidence_kind": evidence_kind,
        "evidence": evidence,
        "summary": _item_summary(item, metadata, content, evidence_kind),
    }
    transcript = content.get("transcript") if isinstance(content.get("transcript"), dict) else {}
    if transcript.get("text"):
        report["transcript_excerpt"] = str(transcript["text"])[:1200]
    return report


def _primary_evidence(item: dict[str, Any], metadata: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    item_type = str(item.get("type") or "")
    if isinstance(metadata.get("code_evidence"), dict):
        return "code_evidence", metadata["code_evidence"]
    if isinstance(metadata.get("table_evidence"), dict):
        return "table_evidence", metadata["table_evidence"]
    if isinstance(metadata.get("visual_evidence"), dict):
        return "visual_evidence", metadata["visual_evidence"]
    if isinstance(metadata.get("pdf_evidence"), dict):
        return "pdf_evidence", metadata["pdf_evidence"]
    if isinstance(metadata.get("citation_evidence"), dict):
        return "citation_evidence", metadata["citation_evidence"]
    if item_type in {"audio", "video", "media"}:
        keys = {
            "path",
            "sha256",
            "media_kind",
            "duration_seconds",
            "transcript_char_count",
            "chapter_count",
            "keyframe_count",
            "mime_type",
            "size_bytes",
        }
        return "media_evidence", {key: metadata[key] for key in keys if key in metadata}
    keys = {"path", "sha256", "line_count", "char_count", "size_bytes", "mime_type"}
    generic = {key: metadata[key] for key in keys if key in metadata}
    if item_type == "text":
        generic["char_count"] = metadata.get("char_count", 0)
    return "source_metadata", generic


def _item_summary(
    item: dict[str, Any],
    metadata: dict[str, Any],
    content: dict[str, Any],
    evidence_kind: str,
) -> str:
    item_type = str(item.get("type") or "source")
    if evidence_kind == "code_evidence":
        evidence = metadata.get("code_evidence", {})
        return f"{evidence.get('language', 'code')} code, {evidence.get('line_count', 0)} lines, {evidence.get('symbol_count', 0)} symbols"
    if evidence_kind == "table_evidence":
        evidence = metadata.get("table_evidence", {})
        return f"{evidence.get('row_count', 0)} rows, {evidence.get('column_count', 0)} columns"
    if evidence_kind == "visual_evidence":
        evidence = metadata.get("visual_evidence", {})
        return f"{evidence.get('width')}x{evidence.get('height')} image, blank={str(evidence.get('is_blank')).lower()}"
    if evidence_kind == "pdf_evidence":
        evidence = metadata.get("pdf_evidence", {})
        return f"{evidence.get('page_count', 0)} PDF page(s), text layer={str(evidence.get('has_text_layer')).lower()}"
    if evidence_kind == "citation_evidence":
        evidence = metadata.get("citation_evidence", {})
        return f"{evidence.get('domain', '')} citation, fetch={evidence.get('fetch_status', 'not_fetched')}"
    if evidence_kind == "media_evidence":
        transcript = content.get("transcript") if isinstance(content.get("transcript"), dict) else {}
        suffix = " with transcript" if transcript.get("text") else ""
        return f"{item_type} file{suffix}"
    return f"{item_type} source metadata"


def _report_markdown(report: dict[str, Any], title: str | None = None) -> str:
    lines = [
        f"# {title or 'OKoffice Context Packet Report'}",
        "",
        "## Packet",
        "",
        f"- Context Packet: `{report['context_packet_id']}`",
        f"- Source Graph: `{report['source_graph']['source_graph_id']}`",
        f"- Items: {report['item_count']}",
        f"- Source refs: {report['source_ref_count']}",
    ]
    if report.get("intent"):
        lines.extend(["", "## Intent", "", str(report["intent"])])

    lines.extend(
        [
            "",
            "## Items",
            "",
            "| Source Ref | Type | Label | Evidence | Summary |",
            "|---|---|---|---|---|",
        ]
    )
    for item in report["items"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item.get('source_ref', '')}`",
                    _table_cell(str(item.get("type", ""))),
                    _table_cell(str(item.get("label", ""))),
                    _table_cell(str(item.get("evidence_kind", ""))),
                    _table_cell(str(item.get("summary", ""))),
                ]
            )
            + " |"
        )

    lines.extend(["", "## Source Graph", ""])
    for node in report["source_graph"]["nodes"]:
        if not isinstance(node, dict):
            continue
        lines.append(
            f"- `{node.get('node_id')}` -> `{node.get('source_ref')}` ({node.get('type')}, {node.get('role')})"
        )

    lines.extend(["", "## Evidence Details", ""])
    for item in report["items"]:
        lines.extend(_item_detail_lines(item))

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Web links are recorded but not fetched by this local report tool.",
            "- OCR and vision-model interpretation are not performed by this local report tool.",
            "- Media transcripts, chapters, and keyframes are treated as provided evidence.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _item_detail_lines(item: dict[str, Any]) -> list[str]:
    label = str(item.get("label") or item.get("source_ref") or "Source")
    evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    lines = [f"### {label}", "", f"Source ref: `{item.get('source_ref', '')}`", ""]
    if item.get("uri"):
        lines.extend([f"URI: `{item['uri']}`", ""])
    if item.get("evidence_kind") == "citation_evidence":
        lines.append(f"Title: {evidence.get('title', label)}")
        lines.append(f"Fetch status: `{evidence.get('fetch_status', 'not_fetched')}`")
        if evidence.get("snippet"):
            lines.extend(["", str(evidence["snippet"])])
    elif item.get("evidence_kind") == "media_evidence":
        lines.append(str(item.get("summary", "")))
        if evidence.get("duration_seconds") is not None:
            lines.append(f"Duration: {evidence['duration_seconds']} second(s)")
        if item.get("transcript_excerpt"):
            lines.extend(["", "Transcript excerpt:", "", str(item["transcript_excerpt"])])
    elif item.get("evidence_kind") == "code_evidence":
        symbols = evidence.get("symbols") if isinstance(evidence.get("symbols"), list) else []
        lines.append(f"Code hash: `{evidence.get('code_hash', '')}`")
        if symbols:
            lines.append("Symbols: " + ", ".join(str(symbol.get("name")) for symbol in symbols[:12] if isinstance(symbol, dict)))
    elif item.get("evidence_kind") == "pdf_evidence":
        for page in evidence.get("pages", [])[:3]:
            if isinstance(page, dict) and page.get("text_preview"):
                lines.extend(["", f"Page {page.get('page_number')}: {page.get('text_preview')}"])
    else:
        lines.append(str(item.get("summary", "")))
    lines.append("")
    return lines


def _report_warnings(report: dict[str, Any]) -> list[str]:
    item_types = set(report.get("item_types", []))
    warnings: list[str] = []
    if "web_link" in item_types:
        warnings.append("Web links are not fetched by the local report tool.")
    if item_types & {"audio", "video", "media"}:
        warnings.append("Media transcripts are treated as provided evidence.")
    return warnings


def _table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
