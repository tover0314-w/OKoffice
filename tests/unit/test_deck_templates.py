"""Unit tests for deck template loading and selection."""
from __future__ import annotations

import pytest

from okoffice.authoring.models import TemplateMetadata
from okoffice.office.deck_templates import (
    load_template_index,
    preview_template_ids,
    select_template,
    _esc,
)

# Clear lru_cache before tests
load_template_index.cache_clear()


class TestLoadTemplateIndex:
    def test_returns_list(self):
        result = load_template_index()
        assert isinstance(result, list)

    def test_index_has_templates(self):
        result = load_template_index()
        assert len(result) >= 16

    def test_all_entries_have_required_fields(self):
        result = load_template_index()
        for entry in result:
            assert entry.template_id
            assert entry.name
            assert entry.track in ("html", "svg", "both")


class TestSelectTemplate:
    def test_returns_none_for_empty_list(self):
        result = select_template([], mood="professional")
        assert result is None

    def test_selects_by_template_id(self):
        meta = [TemplateMetadata(template_id="test_1", name="Test One")]
        result = select_template(meta, template_id="test_1")
        assert result is not None
        assert result.template_id == "test_1"

    def test_returns_none_for_unknown_id(self):
        meta = [TemplateMetadata(template_id="test_1", name="Test One")]
        result = select_template(meta, template_id="nonexistent")
        assert result is None

    def test_selects_by_mood(self):
        meta = [
            TemplateMetadata(template_id="a", name="A", mood=["professional", "clean"]),
            TemplateMetadata(template_id="b", name="B", mood=["creative", "bold"]),
        ]
        result = select_template(meta, mood="creative")
        assert result is not None
        assert result.template_id == "b"

    def test_returns_first_when_no_match(self):
        meta = [
            TemplateMetadata(template_id="a", name="A", mood=["professional"]),
            TemplateMetadata(template_id="b", name="B", mood=["bold"]),
        ]
        result = select_template(meta, mood="nonexistent")
        assert result is not None


class TestPreviewTemplateIds:
    def test_returns_empty_for_no_templates(self):
        result = preview_template_ids()
        assert isinstance(result, list)


class TestEsc:
    def test_escapes_html(self):
        assert _esc("<script>") == "&lt;script&gt;"

    def test_escapes_quotes(self):
        assert _esc('"hello"') == "&quot;hello&quot;"
