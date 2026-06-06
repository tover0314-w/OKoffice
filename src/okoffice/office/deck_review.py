from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from okoffice.office.deck import inspect_deck_presentation
from okoffice.office.shared import failed_result, job_id
from okoffice.schemas.models import OKofficeError, ToolResult, ValidationCheck, ValidationReport

STORY_TOOL = "deck.review.story"
CLAIMS_TOOL = "deck.review.claims"

CLAIM_PATTERNS: dict[str, re.Pattern[str]] = {
    "percentage": re.compile(r"\d+\.?\d*\s*%"),
    "dollar_amount": re.compile(r"\$\s*[\d,.]+"),
    "superlative": re.compile(
        r"\b(?:largest|smallest|best|worst|first|last|most|least|highest|lowest|biggest|fastest)\b",
        re.IGNORECASE,
    ),
    "comparative": re.compile(
        r"\b(?:more|less|higher|lower|greater|fewer|better|worse|faster|slower)\s+than\b",
        re.IGNORECASE,
    ),
    "strong_claim": re.compile(
        r"\b(?:will|guarantee|ensure|proven|demonstrated)\b",
        re.IGNORECASE,
    ),
}

SECTION_RE = re.compile(r"[:–—]")


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def _preflight(path: str | Path, tool: str) -> tuple[list[dict[str, Any]], ToolResult | None]:
    inspected = inspect_deck_presentation(Path(path))
    if inspected.status == "failed":
        return [], failed_result(
            tool,
            inspected.error or OKofficeError(code="unsupported_file_type", message="Preflight failed."),
        )
    if inspected.usage["presentation"]["format"] != "pptx":
        return [], failed_result(
            tool,
            OKofficeError(
                code="unsupported_file_type",
                message=f"{tool} requires a PPTX file.",
                details={"detected_format": inspected.usage["presentation"]["format"]},
            ),
        )
    slides = inspected.usage["slides"]
    return slides, None


# ---------------------------------------------------------------------------
# 1. deck.review.story
# ---------------------------------------------------------------------------

def review_deck_story(path: str | Path) -> ToolResult:
    slides, err = _preflight(path, STORY_TOOL)
    if err is not None:
        return err

    title_flow = [slide["title"] for slide in slides]
    lengths = [len(title) for title in title_flow]

    title_length_variation = _title_length_range(lengths)
    section_balance = _section_balance(title_flow)
    repetition_score = _repetition_score(title_flow)

    warnings: list[str] = []
    if all(not t for t in title_flow):
        warnings.append("All slide titles are empty.")
    elif len(slides) < 2:
        warnings.append("Story review is more useful with 2 or more slides.")

    section_count = len(section_balance)
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=STORY_TOOL,
        validation=ValidationReport(
            status="warning" if warnings else "passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="story_reviewed",
                    status="passed",
                    details={"slide_count": len(slides)},
                ),
            ],
            warnings=warnings,
        ),
        warnings=warnings,
        usage={
            "summary": {
                "slide_count": len(slides),
                "section_count": section_count,
                "repetition_score": repetition_score,
            },
            "story": {
                "title_flow": title_flow,
                "section_balance": section_balance,
                "title_length_variation": title_length_variation,
            },
        },
        next_recommended_tools=["deck.review.claims", "deck.extract.text"],
    )


# ---------------------------------------------------------------------------
# 2. deck.review.claims
# ---------------------------------------------------------------------------

def review_deck_claims(path: str | Path) -> ToolResult:
    slides, err = _preflight(path, CLAIMS_TOOL)
    if err is not None:
        return err

    claims: list[dict[str, Any]] = []
    for slide in slides:
        text = slide.get("text", "")
        slide_number = slide["slide_number"]
        locator = slide.get("locator", {})
        for match_type, pattern in CLAIM_PATTERNS.items():
            for match in pattern.finditer(text):
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                snippet = text[start:end].strip()
                claims.append({
                    "slide_number": slide_number,
                    "text_snippet": snippet,
                    "claim_type": match_type,
                    "locator": locator,
                })

    slides_with_claims = len({c["slide_number"] for c in claims})
    return ToolResult(
        job_id=job_id(),
        status="succeeded",
        tool=CLAIMS_TOOL,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed"),
                ValidationCheck(
                    name="claims_reviewed",
                    status="passed",
                    details={"slide_count": len(slides), "total_claims": len(claims)},
                ),
            ],
        ),
        usage={
            "summary": {
                "slide_count": len(slides),
                "slides_with_claims": slides_with_claims,
                "total_claims": len(claims),
            },
            "claims": claims,
        },
        next_recommended_tools=["deck.review.story", "deck.extract.text"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _title_length_range(lengths: list[int]) -> dict[str, int | float]:
    if not lengths:
        return {"min": 0, "max": 0, "range": 0}
    mn, mx = min(lengths), max(lengths)
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    return {"min": mn, "max": mx, "range": mx - mn, "stdev": round(math.sqrt(variance), 2)}


def _section_balance(titles: list[str]) -> dict[str, int]:
    sections: dict[str, list[int]] = {}
    current = "intro"
    for index, title in enumerate(titles):
        if SECTION_RE.search(title):
            current = title.strip()
        sections.setdefault(current, []).append(index)
    return {name: len(indices) for name, indices in sections.items()}


def _repetition_score(titles: list[str]) -> int:
    seen: dict[str, int] = {}
    for title in titles:
        normalized = title.strip().lower()
        if normalized:
            seen[normalized] = seen.get(normalized, 0) + 1
    return sum(count - 1 for count in seen.values() if count > 1)
