"""Cross-format evidence mapping, coverage, and context classification tools."""
from __future__ import annotations

from typing import Any

from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


_ITEM_TYPE_SLOT_MAP: dict[str, list[str]] = {
    "text_evidence": ["body", "title", "appendix"],
    "data_evidence": ["table", "body", "appendix"],
    "code_evidence": ["appendix", "body"],
    "citation": ["appendix", "body"],
    "image_evidence": ["figure", "appendix"],
}
_SLOT_KEYWORDS: dict[str, list[str]] = {
    "title": ["title", "heading", "headline", "name"],
    "figure": ["figure", "image", "diagram", "chart", "graph", "screenshot"],
    "table": ["table", "data", "metrics", "statistics", "spreadsheet"],
    "appendix": ["appendix", "supplementary", "reference", "footnote", "citation", "source"],
}


# -- 1. office.evidence.map_sources ------------------------------------------

def map_office_evidence_sources(context_packet: dict[str, Any], composition: dict[str, Any] | None = None) -> ToolResult:
    """Map composition blocks back to context packet source refs."""
    try:
        if not isinstance(context_packet, dict) or not context_packet.get("context_packet_id"):
            return failed_result("office.evidence.map_sources", OKofficeError(code="invalid_input", message="context_packet must include context_packet_id."))
        source_refs = _collect_source_refs(context_packet)
        block_refs = _collect_block_refs(composition) if composition else {}
        source_map, mapped = [], 0
        for ref in sorted(source_refs):
            blocks = block_refs.get(ref, [])
            if blocks:
                mapped += 1
            source_map.append({"source_ref": ref, "blocks": blocks, "coverage": "covered" if blocks else "unmapped"})
        return ToolResult(job_id=job_id(), status="succeeded", tool="office.evidence.map_sources",
            validation=ValidationReport(status="passed", checks=[
                ValidationCheck(name="source_refs_collected", status="passed", details={"count": len(source_refs)}),
                ValidationCheck(name="sources_mapped", status="passed", details={"mapped": mapped, "unmapped": len(source_refs) - mapped}),
            ]), usage={"summary": {"source_count": len(source_refs), "mapped_count": mapped, "unmapped_count": len(source_refs) - mapped}, "source_map": source_map},
            next_recommended_tools=["office.evidence.coverage"])
    except Exception as exc:
        return failed_result("office.evidence.map_sources", OKofficeError(code="mapping_failed", message=str(exc)))


def _collect_source_refs(packet: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for item in packet.get("items", []):
        if isinstance(item, dict) and item.get("source_ref"):
            refs.add(str(item["source_ref"]))
    graph = packet.get("source_graph")
    if isinstance(graph, dict):
        for node in graph.get("nodes", []):
            if isinstance(node, dict) and node.get("source_ref"):
                refs.add(str(node["source_ref"]))
    return refs


def _collect_block_refs(composition: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for block in composition.get("blocks", []):
        if not isinstance(block, dict):
            continue
        bid = str(block.get("block_id", ""))
        for ref in block.get("source_refs", []):
            mapping.setdefault(str(ref), []).append(bid)
    return mapping


# -- 2. office.evidence.coverage ---------------------------------------------

def report_office_evidence_coverage(composition: dict[str, Any]) -> ToolResult:
    """Coverage report from a composition artifact."""
    try:
        if not isinstance(composition, dict):
            return failed_result("office.evidence.coverage", OKofficeError(code="invalid_input", message="composition must be a dict."))
        blocks = composition.get("blocks", [])
        if not isinstance(blocks, list):
            return failed_result("office.evidence.coverage", OKofficeError(code="invalid_input", message="composition.blocks must be a list."))
        all_sources: set[str] = set()
        covered: set[str] = set()
        for block in blocks:
            if isinstance(block, dict):
                refs = [str(r) for r in block.get("source_refs", [])]
                all_sources.update(refs)
                if refs:
                    covered.update(refs)
        total = len(all_sources) if all_sources else 0
        ratio = round(len(covered) / total, 4) if total else 0.0
        gaps = sorted(all_sources - covered)
        return ToolResult(job_id=job_id(), status="succeeded", tool="office.evidence.coverage",
            validation=ValidationReport(status="passed", checks=[
                ValidationCheck(name="composition_parsed", status="passed", details={"block_count": len(blocks)}),
                ValidationCheck(name="coverage_computed", status="passed", details={"ratio": ratio}),
            ]), usage={"summary": {"total_sources": total, "covered_sources": len(covered), "coverage_ratio": ratio, "gaps": len(gaps)},
                "coverage_report": {"covered": sorted(covered), "gaps": gaps}},
            next_recommended_tools=["office.evidence.map_sources", "office.context.classify"])
    except Exception as exc:
        return failed_result("office.evidence.coverage", OKofficeError(code="coverage_failed", message=str(exc)))


# -- 3. office.context.classify ----------------------------------------------

def classify_office_context(context_packet: dict[str, Any], target_profile: dict[str, Any] | None = None) -> ToolResult:
    """Classify context items for agent routing into target blocks and slots."""
    try:
        if not isinstance(context_packet, dict) or not context_packet.get("context_packet_id"):
            return failed_result("office.context.classify", OKofficeError(code="invalid_input", message="context_packet must include context_packet_id."))
        profile_slots = _profile_slots(target_profile)
        items = context_packet.get("items", []) if isinstance(context_packet.get("items"), list) else []
        classifications, slot_counts = [], {}
        for item in items:
            if not isinstance(item, dict):
                continue
            iid = str(item.get("context_item_id", ""))
            itype = _detect_item_type(item)
            slot = _best_slot(item, itype, profile_slots)
            classifications.append({"item_id": iid, "item_type": itype, "target_slot": slot, "confidence": _confidence(item, itype, slot)})
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
        return ToolResult(job_id=job_id(), status="succeeded", tool="office.context.classify",
            validation=ValidationReport(status="passed", checks=[
                ValidationCheck(name="context_parsed", status="passed", details={"item_count": len(items)}),
                ValidationCheck(name="items_classified", status="passed", details={"classified": len(classifications)}),
            ]), usage={"summary": {"item_count": len(classifications), "slot_count": len(slot_counts)}, "classifications": classifications},
            next_recommended_tools=["office.evidence.map_sources", "office.evidence.coverage"])
    except Exception as exc:
        return failed_result("office.context.classify", OKofficeError(code="classification_failed", message=str(exc)))


def _detect_item_type(item: dict[str, Any]) -> str:
    role, itype = str(item.get("role", "")).lower(), str(item.get("type", "")).lower()
    content = item.get("content")
    if isinstance(content, dict):
        if content.get("code") or content.get("language"):
            return "code_evidence"
        if content.get("image_path") or content.get("media_path"):
            return "image_evidence"
    if any(k in itype for k in ("data", "table", "sheet")):
        return "data_evidence"
    if "code" in itype or "snippet" in itype:
        return "code_evidence"
    if "citation" in role or "citation" in itype or "reference" in itype:
        return "citation"
    return "text_evidence"


def _best_slot(item: dict[str, Any], item_type: str, profile_slots: list[str]) -> str:
    label = str(item.get("label", "")).lower()
    for slot, keywords in _SLOT_KEYWORDS.items():
        if any(kw in label for kw in keywords) and slot in profile_slots:
            return slot
    for candidate in _ITEM_TYPE_SLOT_MAP.get(item_type, ["body"]):
        if candidate in profile_slots:
            return candidate
    return profile_slots[0] if profile_slots else "body"


def _confidence(item: dict[str, Any], item_type: str, slot: str) -> float:
    label = str(item.get("label", "")).lower()
    if any(kw in label for kw in _SLOT_KEYWORDS.get(slot, [])):
        return 0.9
    if slot in _ITEM_TYPE_SLOT_MAP.get(item_type, []):
        return 0.7
    return 0.5


def _profile_slots(target_profile: dict[str, Any] | None) -> list[str]:
    default = ["title", "body", "appendix", "figure", "table"]
    if not isinstance(target_profile, dict):
        return default
    slots = target_profile.get("slots")
    return [str(s) for s in slots] if isinstance(slots, list) and slots else default
