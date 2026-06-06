"""Tests for word.review.style, word.validation.metadata, word.validation.accessibility."""

import zipfile
from pathlib import Path

from okoffice.office.word_review import review_word_style
from okoffice.office.word_validation import validate_word_accessibility, validate_word_metadata

from tests.unit.test_word_extract import _write_rich_docx


def _write_plain_docx(path: Path) -> None:
    """Write a DOCX with only unstyled paragraphs for direct-formatting detection."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '</Types>')
        zf.writestr("_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zf.writestr("word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
        zf.writestr("word/styles.xml",
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
            '</w:styles>')
        zf.writestr("word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            '<w:p><w:r><w:t>Plain paragraph one</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Plain paragraph two</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Plain paragraph three</w:t></w:r></w:p>'
            '</w:body></w:document>')


def _write_heading_skip_docx(path: Path) -> None:
    """Write a DOCX with Heading1 followed by Heading3 (skipping Heading2)."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '</Types>')
        zf.writestr("_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zf.writestr("word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
        zf.writestr("word/styles.xml",
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
            '</w:styles>')
        zf.writestr("word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Main Section</w:t></w:r></w:p>'
            '<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Skipped Level</w:t></w:r></w:p>'
            '</w:body></w:document>')


# ---------------------------------------------------------------------------
# word.review.style
# ---------------------------------------------------------------------------

class TestReviewWordStyle:
    def test_reviews_style_consistency(self, tmp_path: Path) -> None:
        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = review_word_style(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.review.style"
        report = result.usage["style_report"]
        assert "used_styles" in report
        assert "defined_styles" in report

    def test_detects_direct_formatting(self, tmp_path: Path) -> None:
        docx_path = tmp_path / "plain.docx"
        _write_plain_docx(docx_path)
        result = review_word_style(docx_path)
        assert result.status == "succeeded"
        assert result.usage["style_report"]["direct_formatting_count"] > 0


# ---------------------------------------------------------------------------
# word.validation.metadata
# ---------------------------------------------------------------------------

class TestValidateWordMetadata:
    def test_validates_metadata(self, tmp_path: Path) -> None:
        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = validate_word_metadata(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.validation.metadata"
        assert isinstance(result.usage["metadata"], dict)

    def test_warns_missing_title(self, tmp_path: Path) -> None:
        docx_path = tmp_path / "notitle.docx"
        _write_plain_docx(docx_path)
        result = validate_word_metadata(docx_path)
        assert result.status == "succeeded"
        recs = result.usage.get("recommendations", [])
        has_title_rec = any("title" in r.lower() for r in recs)
        assert has_title_rec or len(result.warnings) > 0


# ---------------------------------------------------------------------------
# word.validation.accessibility
# ---------------------------------------------------------------------------

class TestValidateWordAccessibility:
    def test_validates_accessibility(self, tmp_path: Path) -> None:
        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = validate_word_accessibility(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.validation.accessibility"
        checks = result.usage["accessibility"]["checks"]
        assert isinstance(checks, list)
        assert len(checks) > 0

    def test_detects_heading_skips(self, tmp_path: Path) -> None:
        docx_path = tmp_path / "skip.docx"
        _write_heading_skip_docx(docx_path)
        result = validate_word_accessibility(docx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["heading_skip_count"] > 0
