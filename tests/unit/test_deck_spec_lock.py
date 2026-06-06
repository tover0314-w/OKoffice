"""Unit tests for spec lock anti-drift mechanism."""
from __future__ import annotations

import pytest

from okoffice.office.deck_spec_lock import (
    SpecLock,
    check_spec_drift,
    create_spec_lock,
)


def _outline(**overrides) -> dict:
    base = {
        "slides": [
            {"title": "Cover", "layout": "cover", "rhythm": "anchor"},
            {"title": "Agenda", "layout": "agenda", "rhythm": "dense"},
            {"title": "Summary", "layout": "text", "rhythm": "breathing"},
        ]
    }
    base.update(overrides)
    return base


class TestCreateSpecLock:
    def test_returns_spec_lock(self):
        lock = create_spec_lock(_outline())
        assert isinstance(lock, SpecLock)

    def test_slide_count(self):
        lock = create_spec_lock(_outline())
        assert lock.slide_count == 3

    def test_titles(self):
        lock = create_spec_lock(_outline())
        assert lock.slide_titles == ("Cover", "Agenda", "Summary")

    def test_layouts(self):
        lock = create_spec_lock(_outline())
        assert lock.slide_layouts == ("cover", "agenda", "text")

    def test_rhythms(self):
        lock = create_spec_lock(_outline())
        assert lock.rhythm_assignments == ("anchor", "dense", "breathing")

    def test_fingerprint_is_stable(self):
        lock1 = create_spec_lock(_outline())
        lock2 = create_spec_lock(_outline())
        assert lock1.fingerprint == lock2.fingerprint

    def test_fingerprint_changes_with_content(self):
        lock1 = create_spec_lock(_outline())
        lock2 = create_spec_lock(_outline(slides=[{"title": "Different"}]))
        assert lock1.fingerprint != lock2.fingerprint

    def test_uses_pages_key_as_fallback(self):
        lock = create_spec_lock({"pages": [{"title": "A", "layout": "cover"}]})
        assert lock.slide_count == 1


class TestCheckSpecDrift:
    def test_no_drift(self):
        lock = create_spec_lock(_outline())
        slides = [
            {"title": "Cover", "layout": "cover"},
            {"title": "Agenda", "layout": "agenda"},
            {"title": "Summary", "layout": "text"},
        ]
        result = check_spec_drift(slides, lock)
        assert result["has_drift"] is False
        assert result["drift_score"] == 0.0
        assert result["slide_count_match"] is True

    def test_count_drift_high(self):
        lock = create_spec_lock(_outline())
        slides = [{"title": f"S{i}"} for i in range(10)]
        result = check_spec_drift(slides, lock)
        assert result["has_drift"] is True
        assert result["slide_count_match"] is False
        assert any(d["type"] == "slide_count_drift" for d in result["deviations"])

    def test_title_drift(self):
        lock = create_spec_lock(_outline())
        slides = [
            {"title": "Different Cover", "layout": "cover"},
            {"title": "Different Agenda", "layout": "agenda"},
            {"title": "Summary", "layout": "text"},
        ]
        result = check_spec_drift(slides, lock)
        title_devs = [d for d in result["deviations"] if d["type"] == "title_drift"]
        assert len(title_devs) == 1
        assert title_devs[0]["changed_count"] == 2

    def test_layout_drift(self):
        lock = create_spec_lock(_outline())
        slides = [
            {"title": "Cover", "layout": "cover"},
            {"title": "Agenda", "layout": "text"},
            {"title": "Summary", "layout": "quote"},
        ]
        result = check_spec_drift(slides, lock)
        layout_devs = [d for d in result["deviations"] if d["type"] == "layout_drift"]
        assert len(layout_devs) == 1


class TestSpecLockToDict:
    def test_roundtrip(self):
        lock = create_spec_lock(_outline())
        d = lock.to_dict()
        assert d["slide_count"] == 3
        assert isinstance(d["slide_titles"], list)
        assert isinstance(d["slide_layouts"], list)
        assert isinstance(d["rhythm_assignments"], list)
