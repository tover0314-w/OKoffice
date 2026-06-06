"""Tests for word.extract.* tools: text, outline, comments, revisions, fields, styles."""

import json
import zipfile
from pathlib import Path

import pytest


def _write_rich_docx(path: Path) -> None:
    """Write a DOCX with headings, comments, fields, styles, and tracked changes."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>'
            '</Types>'
        )
        archive.writestr("_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>'
        )
        archive.writestr("word/_rels/document.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>'
            '</Relationships>'
        )
        archive.writestr("word/styles.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
            '<w:style w:type="paragraph" w:styleId="CustomBody" w:customStyle="1"><w:name w:val="Custom Body"/><w:basedOn w:val="Normal"/></w:style>'
            '</w:styles>'
        )
        archive.writestr("word/comments.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:comment w:id="0" w:author="Alice"><w:p><w:r><w:t>Review this section</w:t></w:r></w:p></w:comment>'
            '<w:comment w:id="1" w:author="Bob"><w:p><w:r><w:t>Needs citation</w:t></w:r></w:p></w:comment>'
            '</w:comments>'
        )
        archive.writestr("word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            '<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Test Document</w:t></w:r></w:p>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Introduction</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>This is a paragraph with some text.</w:t></w:r></w:p>'
            '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Details</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>More content here.</w:t></w:r></w:p>'
            '<w:p><w:ins w:id="100" w:author="Charlie" w:date="2024-01-15T10:00:00Z">'
            '<w:r><w:t>Inserted text</w:t></w:r></w:ins></w:p>'
            '<w:p><w:del w:id="101" w:author="Diana" w:date="2024-01-15T11:00:00Z">'
            '<w:r><w:delText>Deleted text</w:delText></w:r></w:del></w:p>'
            '</w:body></w:document>'
        )


class TestExtractText:
    def test_extracts_text_with_paragraphs(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_text

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_text(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.extract.text"
        assert result.usage["summary"]["paragraph_count"] > 0
        assert "Test Document" in result.usage["text"]
        assert "Introduction" in result.usage["text"]

    def test_text_items_have_locators(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_text

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_text(docx_path)
        for item in result.usage["paragraphs"]:
            assert "locator" in item
            assert item["locator"]["kind"] == "word"

    def test_rejects_non_docx(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_text

        bad_path = tmp_path / "test.pdf"
        bad_path.write_text("not a docx", encoding="utf-8")
        result = extract_word_text(bad_path)
        assert result.status == "failed"


class TestExtractOutline:
    def test_extracts_heading_hierarchy(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_outline

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_outline(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.extract.outline"
        headings = result.usage["headings"]
        assert len(headings) >= 3
        assert headings[0]["text"] == "Test Document"
        assert headings[0]["level"] == 0  # title
        assert headings[1]["text"] == "Introduction"
        assert headings[1]["level"] == 1
        assert headings[2]["text"] == "Details"
        assert headings[2]["level"] == 2

    def test_outline_warns_when_no_headings(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_outline

        docx_path = tmp_path / "flat.docx"
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            archive.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            archive.writestr("word/document.xml", '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Just text</w:t></w:r></w:p></w:body></w:document>')
        result = extract_word_outline(docx_path)
        assert result.status == "succeeded"
        assert len(result.warnings) > 0


class TestExtractComments:
    def test_extracts_comments(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_comments

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_comments(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.extract.comments"
        comments = result.usage["comments"]
        assert len(comments) == 2
        assert comments[0]["author"] == "Alice"
        assert comments[1]["author"] == "Bob"

    def test_handles_no_comments(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_comments

        docx_path = tmp_path / "nocomments.docx"
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            archive.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            archive.writestr("word/document.xml", '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>No comments</w:t></w:r></w:p></w:body></w:document>')
        result = extract_word_comments(docx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["comment_count"] == 0


class TestExtractRevisions:
    def test_extracts_insertions_and_deletions(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_revisions

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_revisions(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.extract.revisions"
        revisions = result.usage["revisions"]
        assert len(revisions) == 2
        insertions = [r for r in revisions if r["type"] == "insertion"]
        deletions = [r for r in revisions if r["type"] == "deletion"]
        assert len(insertions) == 1
        assert len(deletions) == 1
        assert insertions[0]["author"] == "Charlie"
        assert deletions[0]["author"] == "Diana"

    def test_revisions_have_locators(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_revisions

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_revisions(docx_path)
        for rev in result.usage["revisions"]:
            assert "locator" in rev
            assert rev["locator"]["kind"] == "word"


class TestExtractFields:
    def test_extracts_field_codes(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_fields

        docx_path = tmp_path / "fields.docx"
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml",
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                '</Types>'
            )
            archive.writestr("_rels/.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '</Relationships>'
            )
            archive.writestr("word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:instrText> DATE </w:instrText></w:r></w:p>'
                '<w:p><w:r><w:instrText> PAGE </w:instrText></w:r></w:p>'
                '</w:body></w:document>'
            )
        result = extract_word_fields(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.extract.fields"
        fields = result.usage["fields"]
        assert len(fields) == 2
        assert any("DATE" in f["field_code"] for f in fields)


class TestExtractStyles:
    def test_extracts_style_catalog(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_styles

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_styles(docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.extract.styles"
        styles = result.usage["styles"]
        assert len(styles) >= 4
        style_ids = {s["style_id"] for s in styles}
        assert "Title" in style_ids
        assert "Heading1" in style_ids

    def test_styles_include_inheritance(self, tmp_path: Path) -> None:
        from okoffice.office.word_extract import extract_word_styles

        docx_path = tmp_path / "test.docx"
        _write_rich_docx(docx_path)
        result = extract_word_styles(docx_path)
        custom = [s for s in result.usage["styles"] if s["style_id"] == "CustomBody"]
        assert len(custom) == 1
        assert custom[0]["based_on"] == "Normal"
        assert custom[0]["is_custom"] is True
