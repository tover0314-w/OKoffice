from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult


def map_sources(
    composition: dict[str, Any] | str | Path | None = None,
    blocks: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
    context_packet: dict[str, Any] | str | Path | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.evidence.map_sources"
    composition_payload = _load_optional_payload(composition, "Composition")
    packet = _load_optional_context_packet(context_packet)
    if packet is None and composition_payload is not None:
        packet = _load_optional_context_packet(composition_payload.get("context_packet"))

    source_index = _source_index(packet)
    composition_ir = _composition_ir(composition_payload)
    all_blocks = blocks if blocks is not None else _blocks_from_composition(composition_ir)
    all_claims = claims or []
    existing_source_map = _existing_source_map(composition_payload)

    if not all_blocks and not all_claims and not existing_source_map:
        raise OKofficeException(
            "invalid_input",
            "map_sources requires a composition with source_map or blocks, or explicit blocks/claims.",
        )

    block_index = {
        str(block.get("block_id")): block
        for block in all_blocks
        if isinstance(block, dict) and block.get("block_id") is not None
    }
    source_map: list[dict[str, Any]] = []
    unmapped_targets: list[dict[str, Any]] = []

    if existing_source_map:
        mapped_pairs: set[tuple[str, str]] = set()
        mapped_target_ids: set[str] = set()
        for mapping in existing_source_map:
            if not isinstance(mapping, dict):
                continue
            block_id = str(mapping.get("block_id") or "")
            source_ref = str(mapping.get("source_ref") or "").strip()
            if block_id:
                mapped_target_ids.add(block_id)
            if block_id and source_ref:
                mapped_pairs.add((block_id, source_ref))
            block = block_index.get(block_id)
            source_map.append(_source_mapping(mapping, block=block, source_index=source_index))
        for block in all_blocks:
            if not isinstance(block, dict):
                continue
            block_id = str(block.get("block_id") or "")
            refs = _source_refs(block)
            if not refs:
                if block_id not in mapped_target_ids:
                    unmapped_targets.append(_target_summary(block, target_kind="block"))
                continue
            for ref in refs:
                pair = (block_id, ref)
                if pair in mapped_pairs:
                    continue
                source_map.append(
                    _source_mapping(
                        {
                            "block_id": block.get("block_id"),
                            "source_ref": ref,
                            "block_type": block.get("type"),
                            "target_slot": block.get("target_slot"),
                        },
                        block=block,
                        source_index=source_index,
                    )
                )
                mapped_pairs.add(pair)
    else:
        for block in all_blocks:
            if not isinstance(block, dict):
                continue
            refs = _source_refs(block)
            if not refs:
                unmapped_targets.append(_target_summary(block, target_kind="block"))
                continue
            for ref in refs:
                source_map.append(
                    _source_mapping(
                        {
                            "block_id": block.get("block_id"),
                            "source_ref": ref,
                            "block_type": block.get("type"),
                            "target_slot": block.get("target_slot"),
                        },
                        block=block,
                        source_index=source_index,
                    )
                )

    for claim in all_claims:
        if not isinstance(claim, dict):
            continue
        refs = _source_refs(claim)
        if not refs:
            unmapped_targets.append(_target_summary(claim, target_kind="claim"))
            continue
        for ref in refs:
            source_map.append(
                _source_mapping(
                    {
                        "claim_id": claim.get("claim_id") or claim.get("id"),
                        "claim_text": claim.get("text") or claim.get("claim"),
                        "source_ref": ref,
                        "block_id": claim.get("block_id"),
                        "block_type": "claim",
                    },
                    block=claim,
                    source_index=source_index,
                )
            )

    unmatched_refs = sorted(
        {
            str(mapping["source_ref"])
            for mapping in source_map
            if mapping.get("source_ref") and mapping.get("source_match_status") == "unmatched"
        }
    )
    coverage = _coverage(
        source_map=source_map,
        blocks=all_blocks,
        claims=all_claims,
        unmapped_targets=unmapped_targets,
        context_packet=packet,
    )
    report = {
        "source_map_report_version": "0.1",
        "source_map_report_id": f"srcmap_{uuid4().hex[:16]}",
        "composition_id": composition_ir.get("composition_id") if composition_ir else None,
        "context_packet_id": _context_packet_id(packet, composition_ir),
        "source_map": source_map,
        "coverage": coverage,
        "unmatched_source_refs": unmatched_refs,
        "unmapped_targets": unmapped_targets,
        "source_graph": _source_graph_summary(packet),
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    warnings = []
    if packet is None:
        warnings.append("No Context Packet was provided; source refs could not be enriched from source graph evidence.")
    if unmatched_refs:
        warnings.append(f"{len(unmatched_refs)} source refs were not found in the provided Context Packet.")
    if unmapped_targets:
        warnings.append(f"{len(unmapped_targets)} blocks or claims did not include source_refs.")

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={
            "source_map_report": report,
            "source_map": source_map,
            "coverage": coverage,
            "source_ref_count": coverage["source_ref_count"],
            "matched_source_ref_count": coverage["matched_source_ref_count"],
            "unmatched_source_refs": unmatched_refs,
            "unmapped_targets": unmapped_targets,
        },
        next_recommended_tools=["pdf.evidence.coverage_report", "pdf.patch.plan", "pdf.artifacts.export_bundle"],
    )


def _load_optional_payload(value: dict[str, Any] | str | Path | None, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    path = Path(value)
    if not path.exists():
        raise OKofficeException("file_not_found", f"{label} JSON not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise OKofficeException("invalid_input", f"{label} JSON must be an object.")
    return payload


def _load_optional_context_packet(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    payload = _load_optional_payload(value, "Context Packet")
    if payload is None:
        return None
    if isinstance(payload.get("context_packet"), dict):
        return payload["context_packet"]
    if isinstance(payload.get("usage"), dict) and isinstance(payload["usage"].get("context_packet"), dict):
        return payload["usage"]["context_packet"]
    if isinstance(payload.get("items"), list):
        return payload
    return None


def _composition_ir(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload.get("composition_ir"), dict):
        return payload["composition_ir"]
    if isinstance(payload.get("usage"), dict) and isinstance(payload["usage"].get("composition_ir"), dict):
        return payload["usage"]["composition_ir"]
    if isinstance(payload.get("blocks"), list):
        return payload
    return {}


def _blocks_from_composition(composition_ir: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = composition_ir.get("blocks", [])
    if not isinstance(blocks, list):
        return []
    return [block for block in blocks if isinstance(block, dict)]


def _existing_source_map(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    source_map = payload.get("source_map")
    if source_map is None and isinstance(payload.get("usage"), dict):
        source_map = payload["usage"].get("source_map")
    if not isinstance(source_map, list):
        return []
    return [mapping for mapping in source_map if isinstance(mapping, dict)]


def _source_index(packet: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if packet is None:
        return {}
    index: dict[str, dict[str, Any]] = {}
    for item in packet.get("items", []):
        if not isinstance(item, dict):
            continue
        for key in ("source_ref", "context_item_id"):
            value = str(item.get(key) or "").strip()
            if value:
                index[value] = item
    return index


def _source_refs(value: dict[str, Any]) -> list[str]:
    refs = value.get("source_refs")
    if refs is None:
        refs = value.get("sources")
    if refs is None and value.get("source_ref") is not None:
        refs = [value.get("source_ref")]
    if isinstance(refs, str):
        return [refs]
    if isinstance(refs, list):
        return [str(ref) for ref in refs if str(ref).strip()]
    return []


def _source_mapping(
    mapping: dict[str, Any],
    block: dict[str, Any] | None,
    source_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_ref = str(mapping.get("source_ref") or "").strip()
    source_item = source_index.get(source_ref)
    metadata = source_item.get("metadata", {}) if source_item else {}
    content = source_item.get("content", {}) if source_item else {}
    evidence_kind = _evidence_kind(source_item)
    result = {
        "mapping_id": f"srcmap_entry_{uuid4().hex[:12]}",
        "block_id": mapping.get("block_id") or (block or {}).get("block_id"),
        "block_type": mapping.get("block_type") or (block or {}).get("type"),
        "target_slot": mapping.get("target_slot") or (block or {}).get("target_slot"),
        "claim_id": mapping.get("claim_id"),
        "claim_text_preview": _clip(str(mapping.get("claim_text") or ""), 240) if mapping.get("claim_text") else None,
        "source_ref": source_ref,
        "context_item_id": mapping.get("context_item_id") or (source_item or {}).get("context_item_id"),
        "source_kind": mapping.get("source_kind") or mapping.get("type") or (source_item or {}).get("type"),
        "source_label": mapping.get("label") or (source_item or {}).get("label"),
        "source_uri": (source_item or {}).get("uri"),
        "source_match_status": "matched" if source_item else "unmatched",
        "evidence_kind": evidence_kind,
        "evidence_summary": _evidence_summary(source_item, metadata, content),
    }
    for optional_key in ("page_number", "bbox", "timestamp", "row", "line_start", "line_end"):
        if mapping.get(optional_key) is not None:
            result[optional_key] = mapping[optional_key]
    return {key: value for key, value in result.items() if value is not None}


def _evidence_kind(source_item: dict[str, Any] | None) -> str | None:
    if not source_item:
        return None
    item_type = str(source_item.get("type") or "source")
    metadata = source_item.get("metadata", {}) if isinstance(source_item.get("metadata"), dict) else {}
    for key in (
        "code_snapshot_evidence",
        "code_evidence",
        "table_evidence",
        "pdf_evidence",
        "visual_evidence",
        "document_evidence",
        "citation_evidence",
        "media_evidence",
    ):
        if key in metadata:
            return key
    return f"{item_type}_evidence"


def _evidence_summary(
    source_item: dict[str, Any] | None,
    metadata: dict[str, Any],
    content: dict[str, Any],
) -> dict[str, Any]:
    if source_item is None:
        return {"available": False}
    item_type = str(source_item.get("type") or "source")
    summary: dict[str, Any] = {
        "available": True,
        "type": item_type,
        "role": source_item.get("role"),
        "preview": metadata.get("preview"),
    }
    for key in ("path", "filename", "mime_type", "size_bytes", "sha256", "page_count", "char_count", "row_count", "column_count"):
        if metadata.get(key) is not None:
            summary[key] = metadata[key]
    if item_type == "data" and isinstance(content.get("table"), dict):
        summary["table_columns"] = content["table"].get("columns", [])
    if item_type in {"audio", "video", "media"}:
        transcript = content.get("transcript") or content.get("transcript_excerpt")
        if transcript:
            summary["transcript_excerpt"] = _clip(str(transcript), 240)
    if item_type == "web_link":
        citation = metadata.get("citation_evidence")
        if isinstance(citation, dict):
            summary["domain"] = citation.get("domain")
            summary["fetch_status"] = citation.get("fetch_status")
    return summary


def _target_summary(target: dict[str, Any], target_kind: str) -> dict[str, Any]:
    return {
        "target_kind": target_kind,
        "block_id": target.get("block_id"),
        "claim_id": target.get("claim_id") or target.get("id"),
        "title": target.get("title"),
        "type": target.get("type"),
        "reason": "missing_source_refs",
    }


def _coverage(
    source_map: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    unmapped_targets: list[dict[str, Any]],
    context_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    target_count = len([block for block in blocks if isinstance(block, dict)]) + len(
        [claim for claim in claims if isinstance(claim, dict)]
    )
    mapped_target_ids = {
        str(mapping.get("block_id") or mapping.get("claim_id"))
        for mapping in source_map
        if mapping.get("block_id") or mapping.get("claim_id")
    }
    refs = {str(mapping.get("source_ref")) for mapping in source_map if mapping.get("source_ref")}
    matched_refs = {
        str(mapping.get("source_ref"))
        for mapping in source_map
        if mapping.get("source_ref") and mapping.get("source_match_status") == "matched"
    }
    context_item_count = len(context_packet.get("items", [])) if context_packet else None
    return {
        "target_count": target_count,
        "mapped_target_count": len(mapped_target_ids),
        "unmapped_target_count": len(unmapped_targets),
        "source_ref_count": len(refs),
        "matched_source_ref_count": len(matched_refs),
        "unmatched_source_ref_count": len(refs - matched_refs),
        "context_item_count": context_item_count,
        "coverage_ratio": 1.0 if target_count == 0 else round(len(mapped_target_ids) / target_count, 4),
        "source_ref_match_ratio": None if not refs else round(len(matched_refs) / len(refs), 4),
    }


def _context_packet_id(packet: dict[str, Any] | None, composition_ir: dict[str, Any]) -> str | None:
    if packet and packet.get("context_packet_id"):
        return str(packet["context_packet_id"])
    if composition_ir.get("context_packet_id"):
        return str(composition_ir["context_packet_id"])
    return None


def _source_graph_summary(packet: dict[str, Any] | None) -> dict[str, Any] | None:
    if packet is None or not isinstance(packet.get("source_graph"), dict):
        return None
    graph = packet["source_graph"]
    return {
        "source_graph_id": graph.get("source_graph_id"),
        "node_count": len(graph.get("nodes", [])) if isinstance(graph.get("nodes"), list) else 0,
        "edge_count": len(graph.get("edges", [])) if isinstance(graph.get("edges"), list) else 0,
    }


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."
