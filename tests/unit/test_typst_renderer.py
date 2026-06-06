"""Unit tests for the Typst rendering backend."""

from __future__ import annotations

import pytest
from pathlib import Path

from okoffice.renderers import is_typst_available
from okoffice.schemas.resume import ResumeData
from okoffice.schemas.resume_design_tokens import (
    RESUME_TOKEN_PRESETS,
    resolve_resume_tokens_from_source,
)

# Skip all tests that require typst if not installed
typst_installed = is_typst_available()
requires_typst = pytest.mark.skipif(
    not typst_installed,
    reason="typst package not installed",
)

SAMPLE_RESUME_DATA = {
    "name": "Jane Smith",
    "headline": "Senior Software Engineer",
    "contact": {
        "email": "jane@example.com",
        "phone": "+1 (555) 123-4567",
        "location": "San Francisco, CA",
    },
    "sections": [
        {
            "section_id": "summary",
            "title": "Professional Summary",
            "entry_type": "text",
            "entries": [
                {
                    "entry_type": "text",
                    "content": "Experienced software engineer with 10+ years building scalable systems.",
                }
            ],
            "order": 0,
        },
        {
            "section_id": "experience",
            "title": "Work Experience",
            "entry_type": "experience",
            "entries": [
                {
                    "entry_type": "experience",
                    "title": "Senior Engineer",
                    "organization": "Acme Corp",
                    "location": "San Francisco, CA",
                    "date_range": {"start": "January 2020", "end": "Present"},
                    "highlights": [
                        "Led team of 8 engineers",
                        "Reduced latency by 40%",
                        "Migrated monolith to microservices",
                    ],
                },
                {
                    "entry_type": "experience",
                    "title": "Software Engineer",
                    "organization": "StartupXYZ",
                    "date_range": {"start": "June 2017", "end": "December 2019"},
                    "highlights": [
                        "Built real-time data pipeline",
                    ],
                },
            ],
            "order": 1,
        },
        {
            "section_id": "education",
            "title": "Education",
            "entry_type": "education",
            "entries": [
                {
                    "entry_type": "education",
                    "title": "B.S. Computer Science",
                    "organization": "MIT",
                    "date_range": {"start": "September 2013", "end": "June 2017"},
                    "gpa": "3.9/4.0",
                    "honors": ["Summa Cum Laude", "Dean's List"],
                },
            ],
            "order": 2,
        },
        {
            "section_id": "certifications",
            "title": "Certifications",
            "entry_type": "one_line",
            "entries": [
                {"entry_type": "one_line", "title": "AWS Solutions Architect", "detail": "2021"},
                {"entry_type": "one_line", "title": "Kubernetes Administrator", "detail": "2022"},
            ],
            "order": 3,
        },
        {
            "section_id": "skills",
            "title": "Skills",
            "entry_type": "bullet",
            "entries": [
                {
                    "entry_type": "bullet",
                    "highlights": [
                        "Languages: Python, Go, TypeScript",
                        "Platforms: AWS, GCP, Kubernetes",
                    ],
                },
            ],
            "order": 4,
        },
    ],
}


class TestTypstMarkupGeneration:
    def test_build_typst_markup_returns_string(self):
        from okoffice.renderers.typst_renderer import _build_typst_markup

        resume = ResumeData.model_validate(SAMPLE_RESUME_DATA)
        tokens = resolve_resume_tokens_from_source("resume_modern")
        markup = _build_typst_markup(resume, tokens, ats_mode=True)

        assert isinstance(markup, str)
        assert len(markup) > 100

    def test_markup_contains_name(self):
        from okoffice.renderers.typst_renderer import _build_typst_markup

        resume = ResumeData.model_validate(SAMPLE_RESUME_DATA)
        tokens = resolve_resume_tokens_from_source("resume_modern")
        markup = _build_typst_markup(resume, tokens, ats_mode=True)

        assert "Jane Smith" in markup

    def test_markup_contains_page_setup(self):
        from okoffice.renderers.typst_renderer import _build_typst_markup

        resume = ResumeData.model_validate(SAMPLE_RESUME_DATA)
        tokens = resolve_resume_tokens_from_source("resume_modern")
        markup = _build_typst_markup(resume, tokens, ats_mode=True)

        assert '#set page(' in markup
        assert '#set text(' in markup


class TestTokenMapping:
    def test_tokens_appear_as_typst_variables(self):
        from okoffice.renderers.typst_renderer import _build_typst_markup

        resume = ResumeData.model_validate(SAMPLE_RESUME_DATA)
        tokens = resolve_resume_tokens_from_source("resume_modern")
        markup = _build_typst_markup(resume, tokens, ats_mode=True)

        assert "#let name-size" in markup
        assert "#let name-color" in markup
        assert "#let section-color" in markup
        assert "#let date-size" in markup

    def test_ats_mode_overrides_margins(self):
        from okoffice.renderers.typst_renderer import _build_typst_markup

        resume = ResumeData.model_validate(SAMPLE_RESUME_DATA)
        tokens = resolve_resume_tokens_from_source("resume_modern")
        markup = _build_typst_markup(resume, tokens, ats_mode=True)

        # ATS mode with ats_standard_margins=True should set 72pt margins
        assert "72pt" in markup

    def test_all_presets_produce_valid_markup(self):
        from okoffice.renderers.typst_renderer import _build_typst_markup

        resume = ResumeData.model_validate(SAMPLE_RESUME_DATA)
        for preset_name in RESUME_TOKEN_PRESETS:
            tokens = resolve_resume_tokens_from_source(preset_name)
            markup = _build_typst_markup(resume, tokens, ats_mode=False)
            assert "#set page(" in markup, f"Preset {preset_name} missing page setup"


class TestExperienceEntry:
    def test_experience_entry_uses_grid(self):
        from okoffice.renderers.typst_renderer import _render_experience_entry
        from okoffice.schemas.resume import ExperienceEntry

        entry = ExperienceEntry.model_validate({
            "entry_type": "experience",
            "title": "Senior Engineer",
            "organization": "Acme Corp",
            "location": "NYC",
            "date_range": {"start": "Jan 2020", "end": "Present"},
            "highlights": ["Led team of 5"],
        })

        result = _render_experience_entry(entry)
        assert "grid(" in result
        assert "columns: (1fr, auto)" in result
        assert "Senior Engineer" in result
        assert "Jan 2020" in result

    def test_experience_entry_without_date(self):
        from okoffice.renderers.typst_renderer import _render_experience_entry
        from okoffice.schemas.resume import ExperienceEntry

        entry = ExperienceEntry.model_validate({
            "entry_type": "experience",
            "title": "Consultant",
            "organization": "Freelance",
            "highlights": [],
        })

        result = _render_experience_entry(entry)
        assert "Consultant" in result
        assert "grid(" not in result or "columns" not in result


class TestEducationEntry:
    def test_education_entry_has_gpa(self):
        from okoffice.renderers.typst_renderer import _render_education_entry
        from okoffice.schemas.resume import EducationEntry

        entry = EducationEntry.model_validate({
            "entry_type": "education",
            "title": "B.S. CS",
            "organization": "MIT",
            "date_range": {"start": "Sep 2016", "end": "Jun 2020"},
            "gpa": "3.9/4.0",
            "honors": ["Summa Cum Laude"],
        })

        result = _render_education_entry(entry)
        assert "GPA" in result
        assert "3.9" in result
        assert "MIT" in result


class TestEntryRenderers:
    def test_text_entry(self):
        from okoffice.renderers.typst_renderer import _render_text_entry
        from okoffice.schemas.resume import TextEntry

        entry = TextEntry.model_validate({
            "entry_type": "text",
            "content": "A professional summary paragraph.",
        })
        result = _render_text_entry(entry)
        assert "professional summary" in result

    def test_one_line_entry(self):
        from okoffice.renderers.typst_renderer import _render_one_line_entry
        from okoffice.schemas.resume import OneLineEntry

        entry = OneLineEntry.model_validate({
            "entry_type": "one_line",
            "title": "AWS Certified",
            "detail": "2021",
        })
        result = _render_one_line_entry(entry)
        assert "AWS Certified" in result
        assert "2021" in result

    def test_bullet_entry(self):
        from okoffice.renderers.typst_renderer import _render_bullet_entry
        from okoffice.schemas.resume import BulletEntry

        entry = BulletEntry.model_validate({
            "entry_type": "bullet",
            "highlights": ["Python", "Go", "TypeScript"],
        })
        result = _render_bullet_entry(entry)
        assert "- Python" in result
        assert "- Go" in result


class TestSpecialCharacterEscaping:
    def test_escapes_brackets(self):
        from okoffice.renderers.typst_renderer import _esc

        assert "\\[" in _esc("test [value]")
        assert "\\]" in _esc("test [value]")

    def test_escapes_hash(self):
        from okoffice.renderers.typst_renderer import _esc

        assert "\\#" in _esc("C# developer")

    def test_escapes_dollar(self):
        from okoffice.renderers.typst_renderer import _esc

        assert "\\$" in _esc("$100K salary")


class TestRendererFallback:
    def test_reportlab_renderer_always_works(self):
        from okoffice.core.pdf import create_resume_pdf

        result = create_resume_pdf(
            SAMPLE_RESUME_DATA,
            ".okoffice-out/test-reportlab-fallback.pdf",
            renderer="reportlab",
        )
        assert result.status == "succeeded"
        assert result.usage.get("renderer") != "typst"

    @requires_typst
    def test_auto_renderer_picks_typst(self):
        from okoffice.core.pdf import create_resume_pdf

        result = create_resume_pdf(
            SAMPLE_RESUME_DATA,
            ".okoffice-out/test-auto-pick.pdf",
            renderer="auto",
        )
        assert result.status == "succeeded"
        assert result.usage.get("renderer") == "typst"


class TestTypstNotInstalled:
    def test_typst_renderer_raises_when_missing(self, monkeypatch):
        from okoffice.renderers.typst_renderer import _require_typst
        from okoffice.schemas.errors import OKofficeException

        monkeypatch.setitem(
            __import__("sys").modules, "typst", None
        )
        # Force re-import to trigger ImportError
        import importlib
        import okoffice.renderers.typst_renderer as mod
        # Just test the error message directly
        with pytest.raises(OKofficeException) as exc_info:
            # Simulate typst not being available
            import builtins
            real_import = builtins.__import__

            def fake_import(name, *args, **kwargs):
                if name == "typst":
                    raise ImportError("No module named 'typst'")
                return real_import(name, *args, **kwargs)

            monkeypatch.setattr(builtins, "__import__", fake_import)
            _require_typst()

        assert "typst_not_installed" in str(exc_info.value.code)
