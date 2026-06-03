from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.compose.context import DEFAULT_TARGET_PROFILES
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult


def classify_context(
    context_packet: dict[str, Any] | str | Path,
    target_profile: dict[str, Any] | str | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.context.classify"
    packet = _load_context_packet(context_packet)
    profile = _resolve_target_profile(target_profile)
    classifications = [_classify_item(item, profile) for item in packet["items"]]
    type_counts = dict(sorted(Counter(item["type"] for item in packet["items"]).items()))
    role_counts = dict(sorted(Counter(str(item.get("role") or "source") for item in packet["items"]).items()))
    report = {
        "classification_version": "0.1",
        "classification_id": f"ctxcls_{uuid4().hex[:16]}",
        "context_packet_id": packet["context_packet_id"],
        "target_profile": profile,
        "classification_count": len(classifications),
        "type_counts": type_counts,
        "role_counts": role_counts,
        "classifications": classifications,
        "recommended_target_profiles": _recommended_target_profiles(type_counts),
        "recommended_tools": _recommended_tools(classifications),
        "limitations": _report_limitations(classifications),
    }

    artifacts = []
    if output_path is not None:
        report_path = Path(output_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(report_path, source_tool=tool))

    warnings = _warnings_for_classifications(classifications)
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={
            "context_packet_id": packet["context_packet_id"],
            "classification_id": report["classification_id"],
            "classification_count": len(classifications),
            "type_counts": type_counts,
            "role_counts": role_counts,
            "target_profile": profile,
            "classifications": classifications,
            "recommended_target_profiles": report["recommended_target_profiles"],
            "limitations": report["limitations"],
            "context_classification": report,
        },
        next_recommended_tools=report["recommended_tools"],
    )


def _load_context_packet(context_packet: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(context_packet, dict):
        packet = context_packet
    else:
        packet = json.loads(Path(context_packet).read_text(encoding="utf-8"))
    if not isinstance(packet, dict) or not packet.get("context_packet_id") or not isinstance(packet.get("items"), list):
        raise AgentPDFException("invalid_context_packet", "Context packet must include context_packet_id and items.")
    return packet


def _resolve_target_profile(target_profile: dict[str, Any] | str | None) -> dict[str, Any] | None:
    if target_profile is None:
        return None
    if isinstance(target_profile, dict):
        profile = dict(target_profile)
        profile.setdefault("profile_id", "custom")
        profile.setdefault("layout_slots", {})
        return profile
    profile_id = str(target_profile)
    if profile_id not in DEFAULT_TARGET_PROFILES:
        raise AgentPDFException("invalid_target_profile", f"Unknown target profile: {profile_id}")
    return DEFAULT_TARGET_PROFILES[profile_id]


def _classify_item(item: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, Any]:
    item_type = str(item.get("type") or "file")
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    suggested_block_type = _suggested_block_type(item_type, content, metadata)
    target_slots = _suggested_target_slots(suggested_block_type, profile)
    limitations = _limitations(item_type, metadata, content)
    safety_flags = _safety_flags(item_type, metadata, content)
    evidence_kind = _primary_evidence_kind(item_type, metadata)
    return {
        "context_item_id": str(item.get("context_item_id") or ""),
        "source_ref": str(item.get("source_ref") or item.get("context_item_id") or ""),
        "type": item_type,
        "role": str(item.get("role") or "source"),
        "label": str(item.get("label") or item.get("source_ref") or item_type),
        "primary_evidence_kind": evidence_kind,
        "evidence_methods": _evidence_methods(metadata),
        "suggested_block_type": suggested_block_type,
        "suggested_target_slots": target_slots,
        "likely_target_uses": _likely_target_uses(item_type, suggested_block_type, target_slots, item),
        "safety_flags": safety_flags,
        "limitations": limitations,
        "confidence": _confidence(item_type, metadata, content),
        "classification_method": "local_context_rules_v0",
    }


def _suggested_block_type(item_type: str, content: dict[str, Any], metadata: dict[str, Any]) -> str:
    if item_type == "code":
        return "code"
    if item_type == "data":
        if isinstance(content.get("table"), dict) or isinstance(metadata.get("table_evidence"), dict):
            return "table"
        return "data"
    if item_type == "image":
        return "image"
    if item_type == "pdf":
        return "pdf_reference"
    if item_type == "web_link":
        return "citation"
    if item_type == "audio":
        return "audio_reference"
    if item_type == "video":
        return "video_reference"
    if item_type == "media":
        return "media_reference"
    return "section"


def _suggested_target_slots(block_type: str, profile: dict[str, Any] | None) -> list[str]:
    if profile is None:
        return []
    slots = profile.get("layout_slots")
    if not isinstance(slots, dict):
        return []
    matches: list[str] = []
    for slot_id, slot in slots.items():
        accepts = slot.get("accepts") if isinstance(slot, dict) else None
        if isinstance(accepts, list) and block_type in {str(value) for value in accepts}:
            matches.append(str(slot_id))
    return matches


def _primary_evidence_kind(item_type: str, metadata: dict[str, Any]) -> str:
    for key in (
        "code_snapshot_evidence",
        "code_evidence",
        "data_profile_evidence",
        "table_evidence",
        "visual_evidence",
        "pdf_evidence",
        "document_evidence",
        "citation_evidence",
    ):
        if isinstance(metadata.get(key), dict):
            return key
    if item_type in {"audio", "video", "media"}:
        return "media_evidence"
    if item_type == "text":
        return "text"
    return "file_metadata"


def _evidence_methods(metadata: dict[str, Any]) -> list[str]:
    methods: list[str] = []
    for value in metadata.values():
        if isinstance(value, dict) and value.get("analysis_method"):
            methods.append(str(value["analysis_method"]))
    return sorted(set(methods))


def _likely_target_uses(
    item_type: str,
    block_type: str,
    target_slots: list[str],
    item: dict[str, Any],
) -> list[str]:
    uses = list(target_slots)
    role = str(item.get("role") or "").lower()
    if item_type == "text":
        uses.extend(["summary", "brief"])
    if block_type == "code":
        uses.extend(["code_review", "technical_appendix"])
    if block_type in {"table", "data"}:
        uses.extend(["evidence_table", "metrics"])
    if block_type == "image":
        uses.extend(["visual_evidence", "diagram"])
    if block_type == "citation":
        uses.extend(["citation", "source_map"])
    if block_type.endswith("_reference"):
        uses.extend(["source_appendix", "media_evidence"])
    if "brief" in role:
        uses.append("summary")
    if "citation" in role:
        uses.append("citation")
    return _dedupe(uses)


def _limitations(item_type: str, metadata: dict[str, Any], content: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    if item_type == "web_link":
        limitations.append("web_not_fetched")
    if item_type == "image":
        limitations.append("no_ocr_or_vision_model")
    if item_type == "code":
        limitations.append("static_scan_only")
        limitations.append("code_not_executed")
    if item_type == "data":
        limitations.append("local_schema_preview_only")
    if item_type == "pdf":
        pdf_evidence = metadata.get("pdf_evidence")
        if isinstance(pdf_evidence, dict) and not pdf_evidence.get("has_text_layer"):
            limitations.append("no_text_layer_detected")
        else:
            limitations.append("text_layer_preview_only")
    if item_type in {"audio", "video", "media"}:
        limitations.append("no_default_transcription")
        if isinstance(content.get("transcript"), dict):
            limitations.append("provided_transcript_only")
        else:
            limitations.append("no_transcript_available")
    return limitations


def _safety_flags(item_type: str, metadata: dict[str, Any], content: dict[str, Any]) -> list[str]:
    flags = ["local_only"]
    if item_type == "web_link":
        flags.append("network_not_used")
    if item_type in {"audio", "video", "media"} and isinstance(content.get("transcript"), dict):
        flags.append("provided_transcript")
    size_bytes = metadata.get("size_bytes")
    if isinstance(size_bytes, (int, float)) and size_bytes > 5_000_000:
        flags.append("large_context")
    return flags


def _confidence(item_type: str, metadata: dict[str, Any], content: dict[str, Any]) -> float:
    if item_type in {"code", "data", "image", "pdf", "web_link"}:
        return 0.92
    if item_type in {"audio", "video", "media"}:
        return 0.82 if isinstance(content.get("transcript"), dict) else 0.64
    if metadata or content:
        return 0.78
    return 0.5


def _warnings_for_classifications(classifications: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if any(item["type"] == "web_link" for item in classifications):
        warnings.append("Web links are not fetched by local classification.")
    if any(item["type"] in {"audio", "video", "media"} for item in classifications):
        warnings.append("Media transcripts are treated as provided evidence.")
    if any("no_ocr_or_vision_model" in item["limitations"] for item in classifications):
        warnings.append("Image classification does not perform OCR or vision-model interpretation.")
    return warnings


def _recommended_target_profiles(type_counts: dict[str, int]) -> list[str]:
    item_types = set(type_counts)
    scored: list[tuple[int, str]] = []
    for profile_id, profile in DEFAULT_TARGET_PROFILES.items():
        accepted = {str(value) for value in profile.get("accepted_context_types", [])}
        score = len(item_types & accepted)
        if profile.get("layout_mode") == "slides" and item_types & {"image", "audio", "video"}:
            score += 1
        if score:
            scored.append((score, profile_id))
    return [profile_id for _, profile_id in sorted(scored, key=lambda value: (-value[0], value[1]))[:5]]


def _recommended_tools(classifications: list[dict[str, Any]]) -> list[str]:
    tools = ["pdf.target.profiles", "pdf.compose.from_context", "pdf.evidence.context_packet_report"]
    if any(item["suggested_block_type"] == "code" for item in classifications):
        tools.append("pdf.compose.add_code_block")
    if any(item["suggested_block_type"] == "table" for item in classifications):
        tools.append("pdf.compose.add_table")
    if any(item["suggested_block_type"] == "image" for item in classifications):
        tools.append("pdf.compose.add_figure")
    if any(item["suggested_block_type"] == "citation" for item in classifications):
        tools.append("pdf.compose.add_citation")
    if any(
        item["suggested_block_type"] in {"audio_reference", "video_reference", "media_reference"}
        for item in classifications
    ):
        tools.append("pdf.compose.add_media_reference")
    return tools


def _report_limitations(classifications: list[dict[str, Any]]) -> list[str]:
    limitations: list[str] = []
    for item in classifications:
        limitations.extend(item["limitations"])
    return _dedupe(limitations)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
