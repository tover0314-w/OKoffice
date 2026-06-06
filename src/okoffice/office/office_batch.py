"""Batch inspection tool for multiple Office files."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from okoffice.office.inspect import inspect_office_file
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


BATCH_TOOL = "office.inspect.batch"


def inspect_office_batch(paths: list[str | Path]) -> ToolResult:
    """Inspect multiple Office files and return aggregated per-file results."""
    if not paths:
        return failed_result(
            BATCH_TOOL,
            OKofficeError(code="unsafe_input_rejected", message="office.inspect.batch requires at least one file path."),
        )

    file_results: list[dict[str, Any]] = []
    format_counts: dict[str, int] = {}
    total_warnings = 0

    for raw_path in paths:
        try:
            result = inspect_office_file(raw_path)
        except Exception as exc:
            file_results.append({
                "path": str(raw_path),
                "format": None,
                "status": "failed",
                "summary": {"error": str(exc)},
            })
            continue

        if result.status == "failed":
            error_msg = result.error.message if result.error else "Inspection failed"
            file_results.append({
                "path": str(raw_path),
                "format": None,
                "status": "failed",
                "summary": {"error": error_msg},
            })
            continue

        detected = result.usage["format"]["detected_format"]
        warning_count = len(result.warnings)
        total_warnings += warning_count
        format_counts[detected] = format_counts.get(detected, 0) + 1

        file_results.append({
            "path": result.usage["file"]["path"],
            "format": detected,
            "status": "succeeded",
            "summary": {
                "extension": result.usage["file"]["extension"],
                "size_bytes": result.usage["file"]["size_bytes"],
                "warning_count": warning_count,
                "macro_enabled": result.usage["safety"].get("macro_enabled", False),
            },
        })

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=BATCH_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(
                    name="batch_inspected",
                    status="passed",
                    details={"file_count": len(paths), "succeeded": sum(1 for f in file_results if f["status"] == "succeeded")},
                ),
            ],
        ),
        warnings=[],
        usage={
            "summary": {
                "file_count": len(paths),
                "formats": format_counts,
                "total_warnings": total_warnings,
            },
            "files": file_results,
        },
        next_recommended_tools=[
            "office.extract.claims",
            "office.extract.entities",
            "office.context.build_packet",
        ],
    )
