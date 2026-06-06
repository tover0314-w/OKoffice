"""Spec lock anti-drift mechanism for long deck generation.

Creates a frozen snapshot of the deck outline to detect visual drift
during generation.  Re-reading the spec lock before each page prevents
LLM context compression from causing color/font/layout drift.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SpecLock:
    fingerprint: str
    slide_count: int
    slide_titles: tuple[str, ...]
    slide_layouts: tuple[str, ...]
    rhythm_assignments: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "slide_count": self.slide_count,
            "slide_titles": list(self.slide_titles),
            "slide_layouts": list(self.slide_layouts),
            "rhythm_assignments": list(self.rhythm_assignments),
        }


def create_spec_lock(outline: dict[str, Any]) -> SpecLock:
    slides = _extract_slides(outline)
    titles = tuple(s.get("title", "") for s in slides)
    layouts = tuple(s.get("layout", "auto") for s in slides)
    rhythms = tuple(s.get("rhythm", "anchor") for s in slides)
    fingerprint = _compute_fingerprint(titles, layouts, rhythms)
    return SpecLock(
        fingerprint=fingerprint,
        slide_count=len(slides),
        slide_titles=titles,
        slide_layouts=layouts,
        rhythm_assignments=rhythms,
    )


def check_spec_drift(
    current_slides: list[dict[str, Any]],
    spec_lock: SpecLock,
) -> dict[str, Any]:
    deviations: list[dict[str, Any]] = []
    count_diff = len(current_slides) - spec_lock.slide_count
    if count_diff != 0:
        deviations.append({
            "type": "slide_count_drift",
            "expected": spec_lock.slide_count,
            "actual": len(current_slides),
            "severity": "high" if abs(count_diff) > 2 else "medium",
        })
    max_check = min(len(current_slides), spec_lock.slide_count)
    title_changes = 0
    layout_changes = 0
    for i in range(max_check):
        slide = current_slides[i]
        expected_title = spec_lock.slide_titles[i] if i < len(spec_lock.slide_titles) else ""
        actual_title = slide.get("title", "")
        if expected_title and actual_title != expected_title:
            title_changes += 1
        expected_layout = spec_lock.slide_layouts[i] if i < len(spec_lock.slide_layouts) else "auto"
        actual_layout = slide.get("layout", "auto")
        if expected_layout != "auto" and actual_layout != expected_layout:
            layout_changes += 1
    if title_changes > 0:
        deviations.append({
            "type": "title_drift",
            "changed_count": title_changes,
            "severity": "medium" if title_changes <= 2 else "high",
        })
    if layout_changes > 0:
        deviations.append({
            "type": "layout_drift",
            "changed_count": layout_changes,
            "severity": "low",
        })
    drift_score = _compute_drift_score(deviations, max_check)
    return {
        "has_drift": drift_score > 0.1,
        "drift_score": round(drift_score, 3),
        "deviations": deviations,
        "slide_count_match": count_diff == 0,
    }


def _extract_slides(outline: dict[str, Any]) -> list[dict[str, Any]]:
    slides = outline.get("slides", [])
    if not slides:
        slides = outline.get("pages", [])
    return slides


def _compute_fingerprint(
    titles: tuple[str, ...],
    layouts: tuple[str, ...],
    rhythms: tuple[str, ...],
) -> str:
    payload = json.dumps(
        {"t": list(titles), "l": list(layouts), "r": list(rhythms)},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _compute_drift_score(deviations: list[dict[str, Any]], total_slides: int) -> float:
    if not deviations or total_slides == 0:
        return 0.0
    score = 0.0
    for dev in deviations:
        severity = dev.get("severity", "low")
        weight = {"high": 0.4, "medium": 0.2, "low": 0.1}.get(severity, 0.1)
        count = dev.get("changed_count", 1)
        score += weight * (count / total_slides)
    return min(score, 1.0)
