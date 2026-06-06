from __future__ import annotations

from pathlib import Path
from typing import Any
from okoffice.artifacts.bundle import export_artifact_bundle, verify_artifact_bundle
from okoffice.office.shared import failed_result
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import OKofficeError, ToolResult


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
    except OKofficeException as exc:
        return failed_result(EXPORT_TOOL, exc.to_error())


def verify_office_bundle(bundle_path: str | Path) -> ToolResult:
    try:
        result = verify_artifact_bundle(bundle_path)
        return result.model_copy(
            update={
                "tool": VERIFY_TOOL,
                "next_recommended_tools": ["office.bundle.export", "office.workflow.board_pack"],
            }
        )
    except OKofficeException as exc:
        return failed_result(VERIFY_TOOL, exc.to_error())
