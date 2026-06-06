from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from okoffice.office.shared import failed_result, job_id
from okoffice.office.word import inspect_word_document
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport

REVIEW_STYLE_TOOL = "word.review.style"


def review_word_style(path: str | Path) -> ToolResult:
    """Analyse style consistency in a Word document (no model calls)."""
    doc = inspect_word_document(path)
    if doc.status == "failed":
        return failed_result(
            REVIEW_STYLE_TOOL,
            doc.error or OKofficeError(code="inspect_failed", message="Word inspect failed."),
        )
    if doc.usage.get("document", {}).get("format") != "docx":
        return failed_result(
            REVIEW_STYLE_TOOL,
            OKofficeError(code="unsupported_file_type", message="word.review.style requires a DOCX file."),
        )

    paragraphs: list[dict[str, Any]] = doc.usage.get("paragraphs", [])
    styles_catalog: list[dict[str, Any]] = doc.usage.get("styles", [])
    headings: list[dict[str, Any]] = doc.usage.get("headings", [])

    defined_ids = {s["style_id"] for s in styles_catalog if s.get("style_id")}
    used_ids: set[str] = set()
    style_counter: Counter[str] = Counter()
    direct_formatting_count = 0

    for para in paragraphs:
        sid = para.get("style_id")
        if sid is None:
            direct_formatting_count += 1
            continue
        used_ids.add(sid)
        style_counter[sid] += 1

    unused_styles = sorted(defined_ids - used_ids)
    undefined_styles = sorted(used_ids - defined_ids)
    style_frequency = dict(style_counter.most_common())

    heading_hierarchy = _heading_levels(headings)
    heading_skips = _detect_heading_skips(heading_hierarchy)

    warnings: list[str] = []
    if undefined_styles:
        warnings.append(f"Undefined styles used in paragraphs: {', '.join(undefined_styles)}.")
    if heading_skips:
        warnings.append(f"Heading level skips detected: {heading_skips}.")
    if direct_formatting_count > len(paragraphs) * 0.3:
        warnings.append(f"High direct-formatting ratio: {direct_formatting_count}/{len(paragraphs)} paragraphs have no style.")

    summary = {
        "used_style_count": len(used_ids),
        "defined_style_count": len(defined_ids),
        "unused_style_count": len(unused_styles),
        "undefined_style_count": len(undefined_styles),
        "heading_skips": heading_skips,
    }
    style_report = {
        "used_styles": sorted(used_ids),
        "defined_styles": sorted(defined_ids),
        "unused_styles": unused_styles,
        "undefined_styles": undefined_styles,
        "style_frequency": style_frequency,
        "heading_hierarchy": heading_hierarchy,
        "direct_formatting_count": direct_formatting_count,
    }

    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=REVIEW_STYLE_TOOL,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(name="format_is_docx", status="passed"),
                ValidationCheck(name="style_reviewed", status="passed", details=summary),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={"summary": summary, "style_report": style_report},
        next_recommended_tools=["word.extract.styles", "word.extract.outline", "office.context.build_packet"],
    )


def _heading_levels(headings: list[dict[str, Any]]) -> list[int]:
    levels: list[int] = []
    for h in headings:
        sid = str(h.get("style_id", ""))
        low = sid.lower()
        if low == "title":
            levels.append(0)
        elif low.startswith("heading"):
            suffix = low[len("heading"):]
            m = re.match(r"(\d+)", suffix)
            levels.append(int(m.group(1)) if m else 1)
    return levels


def _detect_heading_skips(levels: list[int]) -> list[str]:
    skips: list[str] = []
    for i in range(1, len(levels)):
        prev, cur = levels[i - 1], levels[i]
        if cur > prev + 1:
            skips.append(f"{prev}->{cur}")
    return skips
