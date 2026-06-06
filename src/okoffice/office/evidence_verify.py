from __future__ import annotations

from typing import Any
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


TOOL_NAME = "office.evidence.verify_citations"


def verify_office_evidence_citations(
    claims: list[dict[str, Any]],
    context_packet: dict[str, Any],
    source_map: dict[str, Any] | None = None,
) -> ToolResult:
    if not claims:
        return failed_result(
            TOOL_NAME, OKofficeError(code="invalid_input", message="claims must be a non-empty list."))
    if not isinstance(context_packet, dict) or not context_packet.get("items"):
        return failed_result(
            TOOL_NAME, OKofficeError(code="invalid_input", message="context_packet must contain items."))

    context_source_refs = _context_source_ref_index(context_packet)
    source_map_index = _source_map_block_index(source_map) if source_map else {}
    verifications: list[dict[str, Any]] = []
    verified_count = 0
    for claim in claims:
        verification = _verify_claim(claim, context_source_refs, source_map_index)
        verifications.append(verification)
        if verification["verification_status"] == "verified":
            verified_count += 1
    unverified_count = len(claims) - verified_count
    integrity_score = round(verified_count / len(claims), 3) if claims else 0.0
    warnings: list[str] = []
    if unverified_count:
        warnings.append(f"{unverified_count} claim(s) could not be fully verified against context sources.")
    checks = [
        ValidationCheck(name="claims_provided", status="passed", details={"claim_count": len(claims)}),
        ValidationCheck(name="context_packet_items_present", status="passed",
                        details={"item_count": len(context_packet.get("items", []))}),
        ValidationCheck(name="source_refs_resolved", status="passed" if verified_count else "warning",
                        details={"verified_count": verified_count, "unverified_count": unverified_count}),
    ]
    return ToolResult(
        job_id=job_id(), status="succeeded", tool=TOOL_NAME,
        validation=ValidationReport(status="warning" if unverified_count else "passed", checks=checks, warnings=warnings),
        warnings=warnings,
        usage={
            "summary": {"claim_count": len(claims), "verified_count": verified_count,
                        "unverified_count": unverified_count, "integrity_score": integrity_score},
            "verifications": verifications,
        },
        next_recommended_tools=["office.evidence.coverage", "office.bundle.report", "office.validate.output"],
    )


def _context_source_ref_index(context_packet: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for item in context_packet.get("items", []):
        if not isinstance(item, dict):
            continue
        source_ref = str(item.get("source_ref") or "").strip()
        if source_ref:
            content = item.get("content")
            text = str(content.get("text", "") if isinstance(content, dict) else "").strip()
            index[source_ref] = text
        for ref in item.get("metadata", {}).get("source_refs", []):
            if isinstance(ref, str) and ref.strip() and ref.strip() not in index:
                index[ref.strip()] = ""
    return index


def _source_map_block_index(source_map: dict[str, Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    entries = source_map if isinstance(source_map, list) else source_map.get("source_map", [])
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        block_id = str(entry.get("block_id") or "").strip()
        source_ref = str(entry.get("source_ref") or "").strip()
        if block_id and source_ref:
            index.setdefault(block_id, [])
            if source_ref not in index[block_id]:
                index[block_id].append(source_ref)
    return index


def _verify_claim(
    claim: dict[str, Any],
    context_source_refs: dict[str, str],
    source_map_index: dict[str, list[str]],
) -> dict[str, Any]:
    claim_text = str(claim.get("text") or "").strip()
    source_refs = claim.get("source_refs") or []
    if isinstance(source_refs, str):
        source_refs = [source_refs]
    if not source_refs:
        return {"claim_text": claim_text[:200], "has_source_refs": False,
                "refs_found_in_context": False, "verification_status": "unverified"}
    refs_found = [str(ref).strip() for ref in source_refs if str(ref).strip() in context_source_refs]
    refs_found_in_context = len(refs_found) == len(source_refs)
    content_matches = all(
        _has_content_overlap(claim_text, context_source_refs.get(ref, "")) for ref in refs_found)
    if refs_found_in_context and content_matches:
        status = "verified"
    elif refs_found:
        status = "partial"
    else:
        status = "unverified"
    return {"claim_text": claim_text[:200], "has_source_refs": True,
            "refs_found_in_context": refs_found_in_context, "refs_found": refs_found,
            "content_overlap": content_matches if refs_found else False, "verification_status": status}


def _has_content_overlap(claim_text: str, source_text: str) -> bool:
    if not claim_text or not source_text:
        return not claim_text
    claim_words = set(claim_text.lower().split())
    source_words = set(source_text.lower().split())
    if not claim_words:
        return True
    overlap = claim_words & source_words
    return len(overlap) / len(claim_words) >= 0.2
