from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult


def create_coverage_report(
    composition: dict[str, Any] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.evidence.coverage_report"
    payload = _load_composition_payload(composition)
    composition_ir = payload.get("composition_ir", {})
    coverage = payload.get("evidence_coverage", {})
    source_map = payload.get("source_map", [])
    blocks = composition_ir.get("blocks", [])
    block_evidence = []
    uncovered_blocks = []

    for block in blocks:
        source_refs = list(block.get("source_refs") or [])
        block_report = {
            "block_id": block.get("block_id"),
            "title": block.get("title"),
            "type": block.get("type"),
            "source_refs": source_refs,
            "covered": bool(source_refs),
        }
        block_evidence.append(block_report)
        if not source_refs:
            uncovered_blocks.append(block_report)

    source_refs = sorted({mapping.get("source_ref") for mapping in source_map if mapping.get("source_ref")})
    report = {
        "coverage_report_version": "0.1",
        "coverage_report_id": f"cov_{uuid4().hex[:16]}",
        "composition_id": composition_ir.get("composition_id"),
        "context_packet_id": payload.get("context_packet_id") or composition_ir.get("context_packet_id"),
        "target_profile": payload.get("target_profile", {}),
        "coverage": coverage,
        "block_evidence": block_evidence,
        "uncovered_blocks": uncovered_blocks,
        "source_ref_count": len(source_refs),
        "source_refs": source_refs,
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage={
            "coverage_report": report,
            "coverage": coverage,
            "covered_blocks": len(blocks) - len(uncovered_blocks),
            "uncovered_blocks": uncovered_blocks,
            "source_ref_count": len(source_refs),
            "source_refs": source_refs,
        },
        next_recommended_tools=["pdf.patch.plan", "pdf.validation.validate_output"],
    )


def _load_composition_payload(composition: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(composition, dict):
        payload = composition
    else:
        path = Path(composition)
        if not path.exists():
            raise AgentPDFException("file_not_found", f"Composition artifact not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
    if "composition_ir" not in payload:
        raise AgentPDFException("invalid_composition_ir", "Composition payload must include composition_ir.")
    return payload
