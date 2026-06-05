from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from okoffice.office.deck import inspect_deck_presentation
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


CONTACT_SHEET_TOOL_NAME = "deck.validation.contact_sheet"
PRESENTATION_TOOL_NAME = "deck.validation.presentation"
WORKER_WARNING = "Contact-sheet render worker is not configured."


def validate_deck_contact_sheet(path: str | Path) -> ToolResult:
    inspected = inspect_deck_presentation(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=CONTACT_SHEET_TOOL_NAME,
            error=inspected.error
            or OKofficeError(
                code="output_validation_failed",
                message="Presentation could not be inspected before contact-sheet validation.",
            ),
            warnings=inspected.warnings,
        )

    summary = inspected.usage.get("summary", {})
    warnings = [WORKER_WARNING]
    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=CONTACT_SHEET_TOOL_NAME,
        validation=ValidationReport(
            status="skipped",
            checks=[
                ValidationCheck(
                    name="presentation_reopened_by_inspect",
                    status="passed",
                    details=summary,
                ),
                ValidationCheck(
                    name="contact_sheet_renderer",
                    status="skipped",
                    message=WORKER_WARNING,
                    details={"required_worker": "pptx_contact_sheet_renderer"},
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "slide_count": int(summary.get("slide_count", 0)),
                "rendered_contact_sheet": False,
                "worker_status": "not_configured",
            },
            "contact_sheet": {
                "preview_artifact_path": None,
                "render_backend": None,
                "render_evidence_available": False,
                "reason": WORKER_WARNING,
            },
            "deck_inspection": inspected.model_dump(mode="json"),
        },
        next_recommended_tools=["deck.inspect.presentation", "office.bundle.export"],
    )


def validate_deck_presentation(path: str | Path) -> ToolResult:
    inspected = inspect_deck_presentation(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=PRESENTATION_TOOL_NAME,
            error=inspected.error
            or OKofficeError(
                code="output_validation_failed",
                message="Presentation could not be inspected before validation.",
            ),
            warnings=inspected.warnings,
        )

    usage = inspected.usage
    summary = usage.get("summary", {})
    slides = [slide for slide in usage.get("slides", []) if isinstance(slide, dict)]
    package = usage.get("package", {})
    themes = [theme for theme in usage.get("themes", []) if isinstance(theme, dict)]
    media = [item for item in usage.get("media", []) if isinstance(item, dict)]
    missing_title_slides = [slide for slide in slides if not str(slide.get("title") or "").strip()]
    slides_without_notes = [slide for slide in slides if not slide.get("has_notes")]
    warnings = list(inspected.warnings)

    if not slides:
        warnings.append("Presentation contains no slides.")
    if missing_title_slides:
        warnings.append(f"Presentation has slides without title text: {len(missing_title_slides)}.")
    if slides_without_notes:
        warnings.append(f"Presentation has slides without speaker notes: {len(slides_without_notes)}.")
    if not themes:
        warnings.append("Presentation package does not include theme metadata.")

    validation_summary = {
        "slide_count": int(summary.get("slide_count", len(slides))),
        "missing_title_count": len(missing_title_slides),
        "slide_without_notes_count": len(slides_without_notes),
        "shape_count": int(summary.get("shape_count", 0)),
        "chart_count": int(summary.get("chart_count", 0)),
        "media_count": int(summary.get("media_count", 0)),
        "theme_count": int(summary.get("theme_count", len(themes))),
        "external_link_count": int(summary.get("external_link_count", 0)),
        "macro_enabled": bool(package.get("macro_enabled", False)),
    }
    render_evidence = {
        "status": "skipped",
        "rendered_contact_sheet": False,
        "required_worker": "pptx_contact_sheet_renderer",
        "reason": WORKER_WARNING,
    }
    placeholder_overflow = {
        "status": "structural_only",
        "checked_by": "text_inventory",
        "render_evidence_available": False,
        "reason": "Placeholder overflow requires a local render/layout worker.",
    }

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=PRESENTATION_TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(
                    name="presentation_reopened_by_inspect",
                    status="passed",
                    details=summary,
                ),
                ValidationCheck(
                    name="slide_count_nonzero",
                    status="passed" if slides else "warning",
                    details={"slide_count": validation_summary["slide_count"]},
                ),
                ValidationCheck(
                    name="slide_titles_present",
                    status="warning" if missing_title_slides else "passed",
                    details={"missing_title_slides": _slide_refs(missing_title_slides)},
                ),
                ValidationCheck(
                    name="notes_policy",
                    status="warning" if slides_without_notes else "passed",
                    message="Speaker notes are recommended for evidence-backed deck handoff.",
                    details={"slides_without_notes": _slide_refs(slides_without_notes)},
                ),
                ValidationCheck(
                    name="media_refs_resolved",
                    status="passed",
                    details={"media_count": len(media), "media_refs": media},
                ),
                ValidationCheck(
                    name="theme_metadata_present",
                    status="passed" if themes else "warning",
                    details={"theme_count": len(themes), "themes": themes},
                ),
                ValidationCheck(
                    name="package_safety_markers",
                    status="warning"
                    if package.get("macro_enabled") or package.get("has_external_relationships")
                    else "passed",
                    details=package if isinstance(package, dict) else {},
                ),
                ValidationCheck(
                    name="placeholder_overflow",
                    status="skipped",
                    message="Placeholder overflow requires a local render/layout worker.",
                    details=placeholder_overflow,
                ),
                ValidationCheck(
                    name="contact_sheet_render_evidence",
                    status="skipped",
                    message=WORKER_WARNING,
                    details=render_evidence,
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": validation_summary,
            "title_checks": {
                "missing_title_slides": _slide_refs(missing_title_slides),
            },
            "notes_policy": {
                "policy": "warn_when_notes_missing",
                "slides_without_notes": _slide_refs(slides_without_notes),
            },
            "media_refs": media,
            "theme_consistency": {
                "status": "passed" if themes else "warning",
                "theme_count": len(themes),
                "themes": themes,
            },
            "placeholder_overflow": placeholder_overflow,
            "render_evidence": render_evidence,
            "deck_inspection": inspected.model_dump(mode="json"),
        },
        next_recommended_tools=[
            "deck.inspect.presentation",
            "deck.validation.contact_sheet",
            "office.bundle.export",
        ],
    )


def _slide_refs(slides: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "slide_number": slide.get("slide_number"),
            "slide_id": slide.get("slide_id"),
            "locator": slide.get("locator"),
        }
        for slide in slides
    ]


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
