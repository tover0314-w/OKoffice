from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.bundle import export_artifact_bundle, verify_artifact_bundle
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import AgentPDFError, ToolResult


EXPORT_TOOL = "office.bundle.export"
VERIFY_TOOL = "office.bundle.verify"


def export_office_bundle(
    *,
    artifact_paths: list[str | Path],
    output_path: str | Path,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ToolResult:
    try:
        okoffice_metadata = {"product": "okoffice", **(metadata or {})}
        okoffice_metadata["product"] = "okoffice"
        result = export_artifact_bundle(
            artifact_paths=artifact_paths,
            output_path=output_path,
            title=title or "OKoffice Artifact Bundle",
            metadata=okoffice_metadata,
        )
        return result.model_copy(
            update={
                "tool": EXPORT_TOOL,
                "next_recommended_tools": ["office.bundle.verify", "office.workflow.board_pack"],
            }
        )
    except AgentPDFException as exc:
        return _failed(EXPORT_TOOL, exc.to_error())


def verify_office_bundle(bundle_path: str | Path) -> ToolResult:
    try:
        result = verify_artifact_bundle(bundle_path)
        return result.model_copy(
            update={
                "tool": VERIFY_TOOL,
                "next_recommended_tools": ["office.bundle.export", "office.workflow.board_pack"],
            }
        )
    except AgentPDFException as exc:
        return _failed(VERIFY_TOOL, exc.to_error())


def _failed(tool: str, error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool=tool,
        error=error,
        warnings=[error.message],
    )
