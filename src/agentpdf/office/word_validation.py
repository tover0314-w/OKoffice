from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.office.validation import validate_office_package
from agentpdf.office.word import inspect_word_document
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


TOOL_NAME = "word.validation.document"
RENDER_WORKER_WARNING = "DOCX render preview worker is not configured."


def validate_word_document(path: str | Path) -> ToolResult:
    package_result = validate_office_package(path)
    if package_result.status != "succeeded":
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=TOOL_NAME,
            error=package_result.error
            or AgentPDFError(
                code="output_validation_failed",
                message="Word package validation failed.",
            ),
            warnings=list(package_result.warnings),
        )

    inspected = inspect_word_document(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=TOOL_NAME,
            error=inspected.error
            or AgentPDFError(
                code="output_validation_failed",
                message="Word document could not be inspected before validation.",
            ),
            warnings=list(inspected.warnings),
        )

    usage = inspected.usage
    summary = usage.get("summary", {})
    metadata = usage.get("metadata", {})
    package = usage.get("package", {})
    paragraphs = [item for item in usage.get("paragraphs", []) if isinstance(item, dict)]
    headings = [item for item in usage.get("headings", []) if isinstance(item, dict)]
    tables = [item for item in usage.get("tables", []) if isinstance(item, dict)]
    comments = [item for item in usage.get("comments", []) if isinstance(item, dict)]
    tracked_change_count = int(summary.get("tracked_change_count", 0))
    warnings = _warnings(
        package_warnings=list(package_result.warnings),
        inspect_warnings=list(inspected.warnings),
        comment_count=len(comments),
        tracked_change_count=tracked_change_count,
        metadata_title_present=bool(metadata.get("title")),
        heading_count=len(headings),
    )
    validation_summary = {
        "paragraph_count": int(summary.get("paragraph_count", len(paragraphs))),
        "heading_count": int(summary.get("heading_count", len(headings))),
        "table_count": int(summary.get("table_count", len(tables))),
        "comment_count": int(summary.get("comment_count", len(comments))),
        "tracked_change_count": tracked_change_count,
        "field_count": int(summary.get("field_count", 0)),
        "style_count": int(summary.get("style_count", 0)),
        "section_count": int(summary.get("section_count", 0)),
        "metadata_title_present": bool(metadata.get("title")),
        "macro_enabled": bool(package.get("macro_enabled", False)),
        "has_external_relationships": bool(package.get("has_external_relationships", False)),
    }
    render_evidence = {
        "status": "skipped",
        "rendered_preview": False,
        "required_worker": "docx_render_preview_worker",
        "reason": RENDER_WORKER_WARNING,
    }
    accessibility_hints = _accessibility_hints(validation_summary, headings, tables)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(
                    name="package_validation",
                    status=package_result.validation.status if package_result.validation else "passed",
                    details=package_result.usage.get("summary", {}),
                ),
                ValidationCheck(
                    name="document_reopened_by_inspect",
                    status="passed",
                    details=summary,
                ),
                ValidationCheck(
                    name="styles_inventory",
                    status="passed" if validation_summary["style_count"] else "warning",
                    details={"style_count": validation_summary["style_count"]},
                ),
                ValidationCheck(
                    name="comments_policy",
                    status="warning" if comments else "passed",
                    details={"comment_count": len(comments), "comments": comments},
                    message="Unresolved comments should be reviewed before delivery." if comments else None,
                ),
                ValidationCheck(
                    name="tracked_changes_policy",
                    status="warning" if tracked_change_count else "passed",
                    details={"tracked_change_count": tracked_change_count},
                    message="Tracked changes should be accepted or rejected before delivery."
                    if tracked_change_count
                    else None,
                ),
                ValidationCheck(
                    name="metadata_title_present",
                    status="passed" if validation_summary["metadata_title_present"] else "warning",
                    details={"metadata": metadata},
                ),
                ValidationCheck(
                    name="accessibility_hints",
                    status=accessibility_hints["status"],
                    details=accessibility_hints,
                ),
                ValidationCheck(
                    name="render_preview_evidence",
                    status="skipped",
                    message=RENDER_WORKER_WARNING,
                    details=render_evidence,
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": validation_summary,
            "comments_policy": {
                "policy": "warn_if_comments_present",
                "comments": comments,
            },
            "tracked_changes_policy": {
                "policy": "warn_if_tracked_changes_present",
                "tracked_change_count": tracked_change_count,
            },
            "metadata": metadata,
            "styles": usage.get("styles", []),
            "accessibility_hints": accessibility_hints,
            "render_evidence": render_evidence,
            "package_validation": package_result.model_dump(mode="json"),
            "word_inspection": inspected.model_dump(mode="json"),
        },
        next_recommended_tools=["word.inspect.document", "office.context.build_packet", "office.bundle.export"],
    )


def _warnings(
    *,
    package_warnings: list[str],
    inspect_warnings: list[str],
    comment_count: int,
    tracked_change_count: int,
    metadata_title_present: bool,
    heading_count: int,
) -> list[str]:
    warnings = _dedupe([*package_warnings, *inspect_warnings])
    if comment_count:
        warnings.append(f"Document contains unresolved comments: {comment_count}.")
    if tracked_change_count:
        warnings.append(f"Document contains tracked changes: {tracked_change_count}.")
    if not metadata_title_present:
        warnings.append("Document metadata title is missing.")
    if not heading_count:
        warnings.append("Document has no heading structure.")
    return _dedupe(warnings)


def _accessibility_hints(
    summary: dict[str, Any],
    headings: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> dict[str, Any]:
    hints: list[str] = []
    if not headings:
        hints.append("No heading paragraphs detected.")
    if tables:
        hints.append("Table accessibility requires visual/layout review for header semantics.")
    if not summary["metadata_title_present"]:
        hints.append("Metadata title is missing.")
    return {
        "status": "warning" if hints else "passed",
        "hints": hints,
        "heading_count": len(headings),
        "table_count": len(tables),
        "metadata_title_present": summary["metadata_title_present"],
        "render_evidence_available": False,
    }


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
