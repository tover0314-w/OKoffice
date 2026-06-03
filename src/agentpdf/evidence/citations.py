from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.evidence.source_map import map_sources
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult


def cite_claims(
    claims: list[dict[str, Any]],
    composition: dict[str, Any] | str | Path | None = None,
    source_map: dict[str, Any] | list[dict[str, Any]] | str | Path | None = None,
    context_packet: dict[str, Any] | str | Path | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.evidence.cite_claims"
    normalized_claims = _normalize_claims(claims)
    if not normalized_claims:
        raise AgentPDFException("invalid_input", "claims must include at least one claim object.")

    mapped = _mapped_source_entries(
        claims=normalized_claims,
        composition=composition,
        source_map=source_map,
        context_packet=context_packet,
    )
    source_map_entries = mapped["source_map"]
    citations: list[dict[str, Any]] = []
    uncited_claims: list[dict[str, Any]] = []

    for claim in normalized_claims:
        refs = _source_refs(claim)
        claim_citations: list[dict[str, Any]] = []
        if refs:
            for ref in refs:
                entry = _best_source_entry(
                    source_map_entries,
                    claim_id=str(claim["claim_id"]),
                    source_ref=ref,
                    block_id=str(claim.get("block_id") or ""),
                )
                claim_citations.append(_citation(claim=claim, source_ref=ref, source_entry=entry))
        if not claim_citations:
            uncited_claims.append(
                {
                    "claim_id": claim["claim_id"],
                    "claim_text_preview": _clip(str(claim.get("text") or ""), 240),
                    "reason": "missing_source_refs",
                }
            )
        citations.extend(claim_citations)

    matched_citations = [
        citation for citation in citations if citation.get("source_match_status") == "matched"
    ]
    report = {
        "citation_report_version": "0.1",
        "citation_report_id": f"cite_{uuid4().hex[:16]}",
        "claims": normalized_claims,
        "citations": citations,
        "uncited_claims": uncited_claims,
        "coverage": {
            "claim_count": len(normalized_claims),
            "cited_claim_count": len({citation["claim_id"] for citation in citations}),
            "uncited_claim_count": len(uncited_claims),
            "citation_count": len(citations),
            "matched_citation_count": len(matched_citations),
            "source_ref_count": len({citation["source_ref"] for citation in citations}),
            "claim_citation_ratio": round(
                len({citation["claim_id"] for citation in citations}) / len(normalized_claims),
                4,
            ),
            "source_match_ratio": None
            if not citations
            else round(len(matched_citations) / len(citations), 4),
        },
        "source_map_summary": {
            "source_map_entry_count": len(source_map_entries),
            "unmatched_source_refs": mapped.get("unmatched_source_refs", []),
        },
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    warnings = list(mapped.get("warnings", []))
    if uncited_claims:
        warnings.append(f"{len(uncited_claims)} claims did not include source refs.")
    unmatched = sorted(
        {
            citation["source_ref"]
            for citation in citations
            if citation.get("source_match_status") == "unmatched"
        }
    )
    if unmatched:
        warnings.append(f"{len(unmatched)} cited source refs were not matched to local context evidence.")

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={
            "citation_report": report,
            "claims": normalized_claims,
            "citations": citations,
            "citation_count": len(citations),
            "uncited_claims": uncited_claims,
            "coverage": report["coverage"],
        },
        next_recommended_tools=[
            "pdf.compose.add_citation",
            "pdf.evidence.map_sources",
            "pdf.evidence.coverage_report",
        ],
    )


def _mapped_source_entries(
    claims: list[dict[str, Any]],
    composition: dict[str, Any] | str | Path | None,
    source_map: dict[str, Any] | list[dict[str, Any]] | str | Path | None,
    context_packet: dict[str, Any] | str | Path | None,
) -> dict[str, Any]:
    composition_payload: dict[str, Any] | str | Path | None = composition
    if source_map is not None:
        source_map_entries = _load_source_map_entries(source_map)
        if context_packet is None and composition is None:
            unmatched_refs = sorted(
                {
                    str(entry.get("source_ref"))
                    for entry in source_map_entries
                    if entry.get("source_ref") and entry.get("source_match_status") == "unmatched"
                }
            )
            return {"source_map": source_map_entries, "warnings": [], "unmatched_source_refs": unmatched_refs}
        composition_payload = {
            "composition_ir": {"composition_version": "0.1", "blocks": []},
            "source_map": source_map_entries,
        }
    result = map_sources(
        composition=composition_payload,
        claims=claims,
        context_packet=context_packet,
    )
    return {
        "source_map": list(result.usage.get("source_map", [])),
        "warnings": list(result.warnings),
        "unmatched_source_refs": list(result.usage.get("unmatched_source_refs", [])),
    }


def _load_source_map_entries(value: dict[str, Any] | list[dict[str, Any]] | str | Path) -> list[dict[str, Any]]:
    payload: Any
    if isinstance(value, list):
        payload = value
    elif isinstance(value, dict):
        payload = value
    else:
        path = Path(value)
        if not path.exists():
            raise AgentPDFException("file_not_found", f"Source map JSON not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if isinstance(payload.get("source_map"), list):
            payload = payload["source_map"]
        elif isinstance(payload.get("source_map_report"), dict) and isinstance(
            payload["source_map_report"].get("source_map"),
            list,
        ):
            payload = payload["source_map_report"]["source_map"]
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise AgentPDFException("invalid_input", "source_map must be a JSON array or object containing source_map.")
    return payload


def _normalize_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw_claim in enumerate(claims, start=1):
        if not isinstance(raw_claim, dict):
            raise AgentPDFException("invalid_input", "claims entries must be JSON objects.")
        claim_id = str(raw_claim.get("claim_id") or raw_claim.get("id") or f"claim_{index:03d}")
        text = str(raw_claim.get("text") or raw_claim.get("claim") or raw_claim.get("quote") or "")
        if not text:
            raise AgentPDFException("invalid_input", "Each claim must include text, claim, or quote.")
        normalized_claim = dict(raw_claim)
        normalized_claim["claim_id"] = claim_id
        normalized_claim["text"] = text
        normalized_claim["source_refs"] = _source_refs(raw_claim)
        normalized.append(normalized_claim)
    return normalized


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


def _best_source_entry(
    source_map_entries: list[dict[str, Any]],
    claim_id: str,
    source_ref: str,
    block_id: str,
) -> dict[str, Any] | None:
    candidates = [
        entry
        for entry in source_map_entries
        if isinstance(entry, dict) and str(entry.get("source_ref") or "") == source_ref
    ]
    if not candidates:
        return None
    for entry in candidates:
        if str(entry.get("claim_id") or "") == claim_id:
            return entry
    if block_id:
        for entry in candidates:
            if str(entry.get("block_id") or "") == block_id:
                return entry
    return candidates[0]


def _citation(
    claim: dict[str, Any],
    source_ref: str,
    source_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    entry = source_entry or {"source_ref": source_ref, "source_match_status": "unmatched"}
    source_match_status = str(entry.get("source_match_status") or ("matched" if source_entry else "unmatched"))
    citation = {
        "citation_id": _citation_id(str(claim["claim_id"]), source_ref),
        "claim_id": claim["claim_id"],
        "claim_text": claim["text"],
        "claim_text_preview": _clip(str(claim["text"]), 240),
        "source_ref": source_ref,
        "source_match_status": source_match_status,
        "source_kind": entry.get("source_kind"),
        "source_label": entry.get("source_label"),
        "source_uri": entry.get("source_uri"),
        "context_item_id": entry.get("context_item_id"),
        "block_id": claim.get("block_id") or entry.get("block_id"),
        "evidence_kind": entry.get("evidence_kind"),
        "evidence_summary": entry.get("evidence_summary", {"available": False}),
        "locator": _locator(claim, entry),
        "support_status": "cited" if source_match_status == "matched" else "source_ref_unmatched",
    }
    return {key: value for key, value in citation.items() if value is not None}


def _locator(claim: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    locator: dict[str, Any] = {}
    for key in ("page_number", "bbox", "timestamp", "timestamp_seconds", "row", "line_start", "line_end"):
        value = entry.get(key)
        if value is None:
            value = claim.get(key)
        if value is not None:
            locator[key] = value
    if not locator:
        summary = entry.get("evidence_summary")
        if isinstance(summary, dict):
            for key in ("path", "filename", "page_count", "row_count", "column_count"):
                if summary.get(key) is not None:
                    locator[key] = summary[key]
    locator["locator_precision"] = "provided_source_ref"
    if "bbox" in locator:
        locator["locator_precision"] = "page_bbox"
    elif "timestamp_seconds" in locator or "timestamp" in locator:
        locator["locator_precision"] = "timestamp"
    elif "row" in locator:
        locator["locator_precision"] = "row"
    elif "line_start" in locator:
        locator["locator_precision"] = "line_range"
    return locator


def _citation_id(claim_id: str, source_ref: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", f"{claim_id}_{source_ref}").strip("_").lower()
    return f"cit_{value[:80] or uuid4().hex[:12]}"


def _clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."
