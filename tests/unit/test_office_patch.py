"""Tests for unified office patch and workflow tools."""

from __future__ import annotations

from pathlib import Path

from tests.unit.test_deck_extract import _write_rich_pptx
from tests.unit.test_word_extract import _write_rich_docx

import pytest


# -- TestPlanOfficePatch --


class TestPlanOfficePatch:
    def test_plans_patch_for_docx(self, tmp_path: Path) -> None:
        from okoffice.office.office_patch import plan_office_patch

        docx_path = tmp_path / "plan.docx"
        _write_rich_docx(docx_path)
        result = plan_office_patch(path=docx_path, operations=[{"op": "replace_text", "replace": "foo"}])
        assert result.status == "succeeded"
        assert result.usage["plan"]["format"] == "docx"
        assert len(result.usage["plan"]["supported"]) >= 1

    def test_rejects_unsupported_format(self, tmp_path: Path) -> None:
        from okoffice.office.office_patch import plan_office_patch

        txt_path = tmp_path / "plain.txt"
        txt_path.write_text("hello", encoding="utf-8")
        result = plan_office_patch(path=txt_path, operations=[{"op": "replace_text"}])
        assert result.status == "failed"


# -- TestPreviewOfficePatch --


class TestPreviewOfficePatch:
    def test_previews_patch(self, tmp_path: Path) -> None:
        from okoffice.office.office_patch import preview_office_patch

        docx_path = tmp_path / "preview.docx"
        _write_rich_docx(docx_path)
        result = preview_office_patch(path=docx_path, operations=[{"op": "replace_text", "replace": "bar"}])
        assert result.status == "succeeded"
        assert result.usage["summary"]["estimated_replacements"] >= 0


# -- TestVerifyOfficePatch --


class TestVerifyOfficePatch:
    def test_verifies_unchanged_file(self, tmp_path: Path) -> None:
        from okoffice.office.office_patch import verify_office_patch

        docx_path = tmp_path / "verify.docx"
        _write_rich_docx(docx_path)
        result = verify_office_patch(input_path=docx_path, output_path=docx_path)
        assert result.status == "succeeded"
        assert result.usage["verification"]["format_match"] is True


# -- TestReviewAndPatchWorkflow --


class TestReviewAndPatchWorkflow:
    def test_workflow_rejects_bad_format(self, tmp_path: Path) -> None:
        from okoffice.office.workflows_extended import review_and_patch_workflow

        txt_path = tmp_path / "bad.txt"
        txt_path.write_text("nope", encoding="utf-8")
        out_path = tmp_path / "out.txt"
        result = review_and_patch_workflow(path=txt_path, output_path=out_path, operations=[{"op": "replace_text"}])
        assert result.status == "failed"

    def test_workflow_processes_docx(self, tmp_path: Path) -> None:
        from okoffice.office.workflows_extended import review_and_patch_workflow

        docx_path = tmp_path / "wf.docx"
        _write_rich_docx(docx_path)
        out_path = tmp_path / "wf_out.docx"
        result = review_and_patch_workflow(
            path=docx_path, output_path=out_path,
            operations=[{"op": "replace_text", "paragraph_index": 0, "replace": "Updated"}],
        )
        assert result.status == "succeeded"
        assert out_path.exists()


# -- TestBuildRedactionPacket --


class TestBuildRedactionPacket:
    def test_builds_redaction_packet(self, tmp_path: Path) -> None:
        from okoffice.office.workflows_extended import build_redaction_packet

        docx_path = tmp_path / "redact.docx"
        _write_rich_docx(docx_path)
        result = build_redaction_packet(path=docx_path, search_terms=["Introduction"])
        assert result.status == "succeeded"
        assert result.usage["summary"]["occurrence_count"] > 0


# -- TestBuildArtifactGraph --


class TestBuildArtifactGraph:
    def test_builds_graph(self, tmp_path: Path) -> None:
        from okoffice.office.workflows_extended import build_artifact_graph

        docx_a = tmp_path / "a.docx"
        docx_b = tmp_path / "b.docx"
        _write_rich_docx(docx_a)
        _write_rich_docx(docx_b)
        result = build_artifact_graph(artifact_paths=[docx_a, docx_b])
        assert result.status == "succeeded"
        assert result.usage["summary"]["artifact_count"] == 2
        assert result.usage["summary"]["edge_count"] >= 1
