from __future__ import annotations

import re
from pathlib import Path
from okoffice.office.deck import inspect_deck_presentation
from okoffice.office.shared import job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport


CONTACT_SHEET_TOOL_NAME = "deck.validation.contact_sheet"
PRESENTATION_TOOL_NAME = "deck.validation.presentation"
NOTES_TOOL_NAME = "deck.validation.notes"
PLACEHOLDERS_TOOL_NAME = "deck.validation.placeholders"
WORKER_WARNING = "Contact-sheet render worker is not configured."

_PLACEHOLDER_RE = re.compile(
    r"\{\{.*?\}\}|\[\[.*?\]\]|<<.*?>>|\b(?:TODO|TBD|INSERT|PLACEHOLDER|FILL\s+IN)\b|lorem ipsum",
    re.IGNORECASE,
)


def validate_deck_contact_sheet(path: str | Path, *, html_preview_path: str | Path | None = None) -> ToolResult:
    inspected = inspect_deck_presentation(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
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
    resolved_path = Path(path).expanduser().resolve()
    html_path = _resolve_html_preview(html_preview_path, resolved_path)

    if html_path and html_path.exists():
        render_result = _render_contact_sheet(html_path, resolved_path)
        if render_result.status == "succeeded":
            render_summary = render_result.usage.get("summary", {})
            render_artifacts = render_result.artifacts
            render_checks = render_result.validation.checks if render_result.validation else []
            return ToolResult(
                job_id=job_id(),
                status="succeeded",
                tool=CONTACT_SHEET_TOOL_NAME,
                artifacts=render_artifacts,
                validation=ValidationReport(
                    status="passed",
                    checks=[
                        ValidationCheck(
                            name="presentation_reopened_by_inspect",
                            status="passed",
                            details=summary,
                        ),
                        *render_checks,
                    ],
                ),
                usage={
                    "summary": {
                        "slide_count": int(summary.get("slide_count", 0)),
                        "rendered_contact_sheet": render_summary.get("rendered_contact_sheet", True),
                        "worker_status": "available",
                    },
                    "contact_sheet": {
                        "contact_sheet_path": render_result.usage.get("contact_sheet", {}).get("path"),
                        "screenshot_count": len(render_result.usage.get("screenshots", [])),
                        "render_backend": "playwright_chromium",
                        "render_evidence_available": True,
                    },
                    "deck_inspection": inspected.model_dump(mode="json"),
                },
                next_recommended_tools=["deck.inspect.presentation", "office.bundle.export"],
            )

    warnings = [WORKER_WARNING]
    return ToolResult(
        job_id=job_id(),
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
                    details={
                        "required_worker": "pptx_contact_sheet_renderer",
                        "html_preview_found": html_path is not None and html_path.exists() if html_path else False,
                    },
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
            job_id=job_id(),
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
        job_id=job_id(),
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


def validate_deck_notes(path: str | Path) -> ToolResult:
    inspected = inspect_deck_presentation(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=NOTES_TOOL_NAME,
            error=inspected.error
            or OKofficeError(
                code="notes_validation_failed",
                message="Presentation could not be inspected before notes validation.",
            ),
            warnings=inspected.warnings,
        )

    slides = [slide for slide in inspected.usage.get("slides", []) if isinstance(slide, dict)]
    warnings: list[str] = list(inspected.warnings)

    notes_details: list[dict[str, object]] = []
    notes_count = 0
    empty_notes_count = 0
    placeholder_in_notes_count = 0

    for slide in slides:
        slide_number = slide.get("slide_number")
        has_notes = bool(slide.get("has_notes"))
        notes_text = str(slide.get("notes_text") or "").strip()
        notes_length = len(notes_text)

        placeholder_markers = _PLACEHOLDER_RE.findall(notes_text) if notes_text else []
        if placeholder_markers:
            placeholder_in_notes_count += 1

        if has_notes:
            notes_count += 1
            if not notes_text:
                empty_notes_count += 1
                warnings.append(f"Slide {slide_number} has notes but the text is empty.")

        if placeholder_markers:
            warnings.append(
                f"Slide {slide_number} notes contain placeholder markers: {placeholder_markers}."
            )

        notes_details.append({
            "slide_number": slide_number,
            "has_notes": has_notes,
            "notes_length": notes_length,
            "placeholder_markers_found": placeholder_markers,
        })

    slides_without_notes = [slide for slide in slides if not slide.get("has_notes")]
    if slides_without_notes:
        warnings.append(
            f"Speaker notes are missing on {len(slides_without_notes)} of {len(slides)} slides."
        )

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=NOTES_TOOL_NAME,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(
                    name="notes_completeness",
                    status="warning" if slides_without_notes else "passed",
                    details={
                        "notes_count": notes_count,
                        "slide_count": len(slides),
                        "fraction": notes_count / len(slides) if slides else 0.0,
                    },
                ),
                ValidationCheck(
                    name="empty_notes",
                    status="warning" if empty_notes_count else "passed",
                    details={"empty_notes_count": empty_notes_count},
                ),
                ValidationCheck(
                    name="placeholder_in_notes",
                    status="warning" if placeholder_in_notes_count else "passed",
                    details={"placeholder_in_notes_count": placeholder_in_notes_count},
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "slide_count": len(slides),
                "notes_count": notes_count,
                "empty_notes_count": empty_notes_count,
                "placeholder_in_notes_count": placeholder_in_notes_count,
            },
            "slides": notes_details,
        },
        next_recommended_tools=[
            "deck.validation.placeholders",
            "deck.validation.presentation",
        ],
    )


def validate_deck_placeholders(path: str | Path) -> ToolResult:
    inspected = inspect_deck_presentation(path)
    if inspected.status != "succeeded":
        return ToolResult(
            job_id=job_id(),
            status="failed",
            tool=PLACEHOLDERS_TOOL_NAME,
            error=inspected.error
            or OKofficeError(
                code="placeholder_validation_failed",
                message="Presentation could not be inspected before placeholder validation.",
            ),
            warnings=inspected.warnings,
        )

    slides = [slide for slide in inspected.usage.get("slides", []) if isinstance(slide, dict)]
    warnings: list[str] = list(inspected.warnings)

    placeholder_entries: list[dict[str, object]] = []
    slides_with_placeholders = 0
    total_placeholders = 0

    for slide in slides:
        slide_number = slide.get("slide_number")
        locator = slide.get("locator")
        slide_text = str(slide.get("text") or "")
        title_text = str(slide.get("title") or "")
        body_text = str(slide.get("body") or "")
        combined_text = "\n".join(part for part in [title_text, body_text, slide_text] if part)

        matches = _PLACEHOLDER_RE.findall(combined_text)
        if matches:
            slides_with_placeholders += 1
            total_placeholders += len(matches)
            warnings.append(
                f"Slide {slide_number} contains {len(matches)} placeholder marker(s): {matches}."
            )

        placeholder_entries.append({
            "slide_number": slide_number,
            "text": combined_text[:500] if matches else "",
            "matches": matches,
            "locator": locator,
        })

    if slides_with_placeholders:
        warnings.append(
            f"Placeholder markers detected on {slides_with_placeholders} slide(s) "
            f"({total_placeholders} total)."
        )

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=PLACEHOLDERS_TOOL_NAME,
        validation=ValidationReport(
            status="warning" if slides_with_placeholders else "passed",
            checks=[
                ValidationCheck(
                    name="placeholder_markers",
                    status="warning" if slides_with_placeholders else "passed",
                    details={
                        "slides_with_placeholders": slides_with_placeholders,
                        "total_placeholders": total_placeholders,
                    },
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "slide_count": len(slides),
                "slides_with_placeholders": slides_with_placeholders,
                "total_placeholders": total_placeholders,
            },
            "placeholders": placeholder_entries,
        },
        next_recommended_tools=[
            "deck.validation.notes",
            "deck.validation.presentation",
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



def _resolve_html_preview(
    html_preview_path: str | Path | None,
    pptx_path: Path,
) -> Path | None:
    if html_preview_path is not None:
        candidate = Path(html_preview_path).expanduser().resolve()
        return candidate if candidate.exists() else None
    sibling = pptx_path.with_suffix(".html")
    return sibling if sibling.exists() else None


def _render_contact_sheet(html_path: Path, pptx_path: Path) -> ToolResult:
    from okoffice.renderers.contact_sheet import render_contact_sheet

    output_dir = pptx_path.parent / f"{pptx_path.stem}-contact-sheet"
    return render_contact_sheet(html_path, output_dir)
