"""Tests for cross-format tools: office.extract.claims/entities/obligations, office.inspect.batch."""

import zipfile
from pathlib import Path

import pytest

from tests.unit.test_word_extract import _write_rich_docx
from tests.unit.test_sheet_extract import _write_rich_xlsx


def _write_docx_with_text(path: Path, text: str) -> None:
    """Write a minimal DOCX containing the given body text."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>')
        zf.writestr("_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zf.writestr("word/document.xml",
            f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')


# ---------------------------------------------------------------------------
# 1. office.extract.claims
# ---------------------------------------------------------------------------

class TestExtractOfficeClaims:
    def test_extracts_claims_from_docx(self, tmp_path: Path) -> None:
        from okoffice.office.office_extract import extract_office_claims

        docx_path = tmp_path / "claims.docx"
        _write_docx_with_text(docx_path, "Revenue grew 25% and costs exceeded $1.5 million.")
        result = extract_office_claims(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "office.extract.claims"
        assert result.usage["summary"]["claim_count"] > 0
        claim_types = result.usage["summary"]["claim_types"]
        assert "percentage" in claim_types

    def test_rejects_unsupported_format(self, tmp_path: Path) -> None:
        from okoffice.office.office_extract import extract_office_claims

        txt_path = tmp_path / "data.txt"
        txt_path.write_text("Some text.", encoding="utf-8")
        result = extract_office_claims(txt_path)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# 2. office.extract.entities
# ---------------------------------------------------------------------------

class TestExtractOfficeEntities:
    def test_extracts_entities_from_docx(self, tmp_path: Path) -> None:
        from okoffice.office.office_extract import extract_office_entities

        docx_path = tmp_path / "entities.docx"
        _write_docx_with_text(docx_path, "John Smith and Acme Corporation signed on 01/15/2024.")
        result = extract_office_entities(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "office.extract.entities"
        assert result.usage["summary"]["entity_count"] > 0

    def test_rejects_unsupported_format(self, tmp_path: Path) -> None:
        from okoffice.office.office_extract import extract_office_entities

        txt_path = tmp_path / "data.txt"
        txt_path.write_text("Some text.", encoding="utf-8")
        result = extract_office_entities(txt_path)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# 3. office.extract.obligations
# ---------------------------------------------------------------------------

class TestExtractOfficeObligations:
    def test_extracts_obligations_from_docx(self, tmp_path: Path) -> None:
        from okoffice.office.office_extract import extract_office_obligations

        docx_path = tmp_path / "obligations.docx"
        _write_docx_with_text(docx_path, "The vendor shall provide quarterly reports.")
        result = extract_office_obligations(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "office.extract.obligations"
        assert result.usage["summary"]["obligation_count"] > 0


# ---------------------------------------------------------------------------
# 4. office.inspect.batch
# ---------------------------------------------------------------------------

class TestInspectOfficeBatch:
    def test_inspects_multiple_files(self, tmp_path: Path) -> None:
        from okoffice.office.office_batch import inspect_office_batch

        docx_path = tmp_path / "doc.docx"
        xlsx_path = tmp_path / "sheet.xlsx"
        _write_rich_docx(docx_path)
        _write_rich_xlsx(xlsx_path)
        result = inspect_office_batch([docx_path, xlsx_path])
        assert result.status == "succeeded"
        assert result.tool == "office.inspect.batch"
        assert result.usage["summary"]["file_count"] == 2
        formats = result.usage["summary"]["formats"]
        assert "docx" in formats
        assert "xlsx" in formats

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        from okoffice.office.office_batch import inspect_office_batch

        missing = tmp_path / "nonexistent.docx"
        result = inspect_office_batch([missing])
        assert result.status == "succeeded"  # batch itself succeeds
        files = result.usage["files"]
        assert len(files) == 1
        assert files[0]["status"] == "failed"
