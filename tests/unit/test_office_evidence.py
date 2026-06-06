"""Tests for evidence tools: map_sources, coverage, classify, verify_citations, validate.output."""

import zipfile
from pathlib import Path

import pytest

from tests.unit.test_word_extract import _write_rich_docx


# ---------------------------------------------------------------------------
# 1. office.evidence.map_sources
# ---------------------------------------------------------------------------

class TestMapEvidenceSources:
    def test_maps_sources(self) -> None:
        from okoffice.office.evidence import map_office_evidence_sources

        context_packet = {
            "context_packet_id": "pkt_001",
            "items": [
                {"context_item_id": "ci_1", "source_ref": "src_a", "role": "text_evidence"},
                {"context_item_id": "ci_2", "source_ref": "src_b", "role": "data_evidence"},
            ],
        }
        composition = {
            "blocks": [
                {"block_id": "b1", "source_refs": ["src_a"]},
            ],
        }
        result = map_office_evidence_sources(context_packet, composition)
        assert result.status == "succeeded"
        assert result.tool == "office.evidence.map_sources"
        assert result.usage["summary"]["mapped_count"] >= 1


# ---------------------------------------------------------------------------
# 2. office.evidence.coverage
# ---------------------------------------------------------------------------

class TestReportEvidenceCoverage:
    def test_reports_coverage(self) -> None:
        from okoffice.office.evidence import report_office_evidence_coverage

        composition = {
            "blocks": [
                {"block_id": "b1", "source_refs": ["src_a", "src_b"]},
                {"block_id": "b2", "source_refs": ["src_a"]},
            ],
        }
        result = report_office_evidence_coverage(composition)
        assert result.status == "succeeded"
        assert result.tool == "office.evidence.coverage"
        ratio = result.usage["summary"]["coverage_ratio"]
        assert 0.0 <= ratio <= 1.0


# ---------------------------------------------------------------------------
# 3. office.context.classify
# ---------------------------------------------------------------------------

class TestClassifyOfficeContext:
    def test_classifies_items(self) -> None:
        from okoffice.office.evidence import classify_office_context

        context_packet = {
            "context_packet_id": "pkt_002",
            "items": [
                {"context_item_id": "ci_1", "role": "text_evidence", "label": "Introduction"},
                {"context_item_id": "ci_2", "type": "data_table", "label": "Metrics table"},
            ],
        }
        result = classify_office_context(context_packet)
        assert result.status == "succeeded"
        assert result.tool == "office.context.classify"
        classifications = result.usage["classifications"]
        assert len(classifications) >= 2


# ---------------------------------------------------------------------------
# 4. office.evidence.verify_citations
# ---------------------------------------------------------------------------

class TestVerifyEvidenceCitations:
    def test_verifies_citations(self) -> None:
        from okoffice.office.evidence_verify import verify_office_evidence_citations

        context_packet = {
            "items": [
                {"source_ref": "src_a", "content": {"text": "Revenue grew 25% this quarter."}},
            ],
        }
        claims = [
            {"text": "Revenue grew 25% this quarter.", "source_refs": ["src_a"]},
        ]
        result = verify_office_evidence_citations(claims, context_packet)
        assert result.status == "succeeded"
        assert result.usage["summary"]["verified_count"] > 0

    def test_flags_unverified_claims(self) -> None:
        from okoffice.office.evidence_verify import verify_office_evidence_citations

        context_packet = {
            "items": [
                {"source_ref": "src_a", "content": {"text": "Some source text."}},
            ],
        }
        claims = [
            {"text": "Unsourced claim with no references."},
        ]
        result = verify_office_evidence_citations(claims, context_packet)
        assert result.status == "succeeded"
        assert result.usage["summary"]["unverified_count"] > 0


# ---------------------------------------------------------------------------
# 5. office.validate.output
# ---------------------------------------------------------------------------

class TestValidateOfficeOutput:
    def test_validates_docx(self, tmp_path: Path) -> None:
        from okoffice.office.bundle_report import validate_office_output

        docx_path = tmp_path / "output.docx"
        _write_rich_docx(docx_path)
        result = validate_office_output(docx_path, "docx")
        assert result.status == "succeeded"
        assert result.tool == "office.validate.output"

    def test_validates_unknown_format(self, tmp_path: Path) -> None:
        from okoffice.office.bundle_report import validate_office_output

        txt_path = tmp_path / "data.txt"
        txt_path.write_text("hello", encoding="utf-8")
        result = validate_office_output(txt_path, "txt")
        assert result.status == "failed"
