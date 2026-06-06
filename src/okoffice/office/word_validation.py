from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from okoffice.office.shared import dedupe_strings, job_id
from okoffice.office.validation import validate_office_package
from okoffice.office.word import inspect_word_document
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


TOOL_NAME = "word.validation.document"
METADATA_TOOL_NAME = "word.validation.metadata"
ACCESSIBILITY_TOOL_NAME = "word.validation.accessibility"
RENDER_WORKER_WARNING = "DOCX render preview worker is not configured."


def validate_word_document(path: str | Path) -> ToolResult:
    package_result = validate_office_package(path)
    if package_result.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=TOOL_NAME,
            error=package_result.error
            or OKofficeError(
                code="output_validation_failed",
                message="Word package validation failed.",
            ),
            warnings=list(package_result.warnings),
        )

    inspected = inspect_word_document(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=TOOL_NAME,
            error=inspected.error
            or OKofficeError(
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
        job_id=job_id(),
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
    warnings = dedupe_strings([*package_warnings, *inspect_warnings])
    if comment_count:
        warnings.append(f"Document contains unresolved comments: {comment_count}.")
    if tracked_change_count:
        warnings.append(f"Document contains tracked changes: {tracked_change_count}.")
    if not metadata_title_present:
        warnings.append("Document metadata title is missing.")
    if not heading_count:
        warnings.append("Document has no heading structure.")
    return dedupe_strings(warnings)


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


_HEADING_LEVEL_RE = re.compile(r"heading\s*(\d+)", re.IGNORECASE)


def _extract_heading_level(style_id: str | None) -> int | None:
    """Extract the numeric heading level from a style_id like 'Heading1' or 'heading 3'."""
    if not style_id:
        return None
    low = style_id.lower()
    if low == "title":
        return 0
    match = _HEADING_LEVEL_RE.search(style_id)
    if match is None:
        return None
    return int(match.group(1))


def validate_word_metadata(path: str | Path) -> ToolResult:
    """Validate metadata completeness for a Word document.

    Tool name: ``word.validation.metadata``
    """
    inspected = inspect_word_document(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=METADATA_TOOL_NAME,
            error=inspected.error
            or OKofficeError(
                code="metadata_validation_failed",
                message="Word document could not be inspected for metadata validation.",
            ),
            warnings=list(inspected.warnings),
        )

    usage = inspected.usage
    summary = usage.get("summary", {})
    metadata = usage.get("metadata", {})
    structure = usage.get("structure", {})
    headings = [item for item in usage.get("headings", []) if isinstance(item, dict)]

    title_present = bool(metadata.get("title"))
    creator_present = bool(metadata.get("creator"))
    heading_count = len(headings)
    section_count = int(structure.get("section_count", summary.get("section_count", 0)))

    recommendations: list[str] = []
    if not title_present:
        recommendations.append("Add a descriptive title to the document metadata (File > Info > Title).")
    if not creator_present:
        recommendations.append("Set the creator/author field in document metadata.")
    if heading_count == 0:
        recommendations.append("Use heading styles to provide document structure.")

    meta_summary = {
        "title_present": title_present,
        "creator_present": creator_present,
        "heading_count": heading_count,
        "section_count": section_count,
    }

    meta_completeness = "passed" if (title_present and creator_present) else "warning"

    warnings: list[str] = []
    if not title_present:
        warnings.append("Document metadata title is missing.")
    if not creator_present:
        warnings.append("Document metadata creator is missing.")
    if heading_count == 0:
        warnings.append("Document has no heading structure.")

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=METADATA_TOOL_NAME,
        validation=ValidationReport(
            status=meta_completeness,
            checks=[
                ValidationCheck(
                    name="format_is_docx",
                    status="passed",
                    details=usage.get("document", {}),
                ),
                ValidationCheck(
                    name="metadata_completeness",
                    status=meta_completeness,
                    details=meta_summary,
                    message="Metadata is incomplete." if meta_completeness == "warning" else None,
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": meta_summary,
            "metadata": {
                "title": metadata.get("title"),
                "creator": metadata.get("creator"),
            },
            "recommendations": recommendations,
        },
        next_recommended_tools=["word.inspect.document", "word.validation.accessibility"],
    )


def validate_word_accessibility(path: str | Path) -> ToolResult:
    """Heuristic accessibility analysis for a Word document.

    Tool name: ``word.validation.accessibility``
    """
    inspected = inspect_word_document(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=ACCESSIBILITY_TOOL_NAME,
            error=inspected.error
            or OKofficeError(
                code="accessibility_validation_failed",
                message="Word document could not be inspected for accessibility validation.",
            ),
            warnings=list(inspected.warnings),
        )

    usage = inspected.usage
    summary = usage.get("summary", {})
    headings = [item for item in usage.get("headings", []) if isinstance(item, dict)]
    tables = [item for item in usage.get("tables", []) if isinstance(item, dict)]

    # --- heading hierarchy check ---
    heading_levels = []
    for h in headings:
        level = _extract_heading_level(h.get("style_id") or h.get("style"))
        if level is not None:
            heading_levels.append(level)

    heading_skip_count = 0
    skip_details: list[dict[str, Any]] = []
    for idx in range(1, len(heading_levels)):
        prev_level = heading_levels[idx - 1]
        curr_level = heading_levels[idx]
        if curr_level > prev_level + 1:
            heading_skip_count += 1
            skip_details.append({
                "previous_level": prev_level,
                "current_level": curr_level,
                "heading_index": idx,
            })

    # --- table header row check ---
    tables_without_headers = 0
    table_details: list[dict[str, Any]] = []
    for table in tables:
        cells = table.get("cells", [])
        rows = table.get("rows", [])
        first_row_cells = cells[0] if cells else []
        has_header_text = any(
            bool(cell.get("text", "").strip())
            for cell in first_row_cells
        ) if first_row_cells else False
        if not has_header_text:
            tables_without_headers += 1
        table_details.append({
            "table_index": table.get("table_index"),
            "row_count": table.get("row_count", len(rows)),
            "has_header_text": has_header_text,
        })

    # --- image alt text heuristic ---
    # Check if the document has media relationships that might indicate images
    document_info = usage.get("document", {})
    package = usage.get("package", {})
    has_media = bool(usage.get("structure", {}).get("image_count", 0)) or bool(
        summary.get("image_count", 0)
    )
    image_alt_flag = False
    if has_media:
        image_alt_flag = True  # flag for heuristic review when images are present

    # --- build accessibility checks ---
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []

    # heading hierarchy
    hierarchy_status = "passed" if heading_skip_count == 0 and len(heading_levels) > 0 else "warning"
    checks.append({
        "name": "heading_hierarchy",
        "status": hierarchy_status,
        "details": {
            "heading_count": len(heading_levels),
            "heading_skip_count": heading_skip_count,
            "skip_details": skip_details,
        },
    })
    if heading_skip_count > 0:
        warnings.append(
            f"Heading hierarchy has {heading_skip_count} level skip(s) (e.g. H1 -> H3)."
        )
    if len(heading_levels) == 0:
        warnings.append("No heading structure detected for accessibility review.")

    # image alt text
    alt_status = "warning" if image_alt_flag else "passed"
    checks.append({
        "name": "image_alt_text",
        "status": alt_status,
        "details": {
            "images_detected": has_media,
            "review_note": "Heuristic: images detected; verify alt text is set for each image."
            if image_alt_flag
            else "No images detected or images not flagged.",
        },
    })
    if image_alt_flag:
        warnings.append("Images detected; verify alt text is set for all images.")

    # table header rows
    table_status = "passed" if tables_without_headers == 0 else "warning"
    checks.append({
        "name": "table_header_rows",
        "status": table_status,
        "details": {
            "table_count": len(tables),
            "tables_without_headers": tables_without_headers,
            "table_details": table_details,
        },
    })
    if tables_without_headers > 0:
        warnings.append(
            f"{tables_without_headers} table(s) have empty first rows (possible missing headers)."
        )

    # document language (heuristic-only)
    checks.append({
        "name": "document_language",
        "status": "skipped",
        "details": {
            "note": "Language detection is not performed in heuristic accessibility review.",
        },
    })

    overall_status = "warning" if warnings else "passed"

    access_summary = {
        "heading_count": len(heading_levels),
        "heading_skip_count": heading_skip_count,
        "table_count": len(tables),
        "tables_without_headers": tables_without_headers,
    }

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=ACCESSIBILITY_TOOL_NAME,
        validation=ValidationReport(
            status=overall_status,
            checks=[
                ValidationCheck(
                    name="format_is_docx",
                    status="passed",
                    details=usage.get("document", {}),
                ),
                ValidationCheck(
                    name="accessibility_reviewed",
                    status=overall_status,
                    details=access_summary,
                    message="Accessibility issues detected." if overall_status == "warning" else None,
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": access_summary,
            "accessibility": {
                "checks": checks,
            },
        },
        next_recommended_tools=["word.inspect.document", "word.validation.metadata"],
    )
