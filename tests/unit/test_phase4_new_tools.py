"""Unit tests for Phase 4 new tool implementations."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from okoffice.office.brief_builder import build_multi_format_brief
from okoffice.office.word_comments import review_word_comments
from okoffice.office.apply_theme import apply_deck_theme
from okoffice.office.pdf_tables import extract_pdf_tables


def _make_minimal_docx(path: Path) -> Path:
    """Create a minimal DOCX with comments.xml for testing."""
    nsmap = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    W = f"{{{nsmap['w']}}}"

    doc_xml = f'<?xml version="1.0" encoding="UTF-8"?>'
    doc_xml += f'<w:document xmlns:w="{nsmap["w"]}"><w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body></w:document>'

    comments_xml = f'<?xml version="1.0" encoding="UTF-8"?>'
    comments_xml += f'<w:comments xmlns:w="{nsmap["w"]}">'
    comments_xml += f'<w:comment w:id="0" w:author="Alice" w:date="2024-01-01T00:00:00Z" w:initials="A">'
    comments_xml += f'<w:p><w:r><w:t>Fix this</w:t></w:r></w:p></w:comment>'
    comments_xml += f'<w:comment w:id="1" w:author="Bob" w:date="2024-01-02T00:00:00Z" w:initials="B">'
    comments_xml += f'<w:p><w:r><w:t>Looks good</w:t></w:r></w:p></w:comment>'
    comments_xml += f'</w:comments>'

    content_types = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    word_rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/></Relationships>'

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", word_rels)
        z.writestr("word/document.xml", doc_xml)
        z.writestr("word/comments.xml", comments_xml)
    return path


def _make_minimal_pptx(path: Path) -> Path:
    """Create a minimal PPTX with theme1.xml for testing."""
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    P = "http://schemas.openxmlformats.org/presentationml/2006/main"

    theme_xml = f'<?xml version="1.0" encoding="UTF-8"?>'
    theme_xml += f'<a:theme xmlns:a="{A}" name="Test">'
    theme_xml += f'<a:themeElements>'
    theme_xml += f'<a:clrScheme name="Office">'
    theme_xml += f'<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
    theme_xml += f'<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
    theme_xml += f'<a:dk2><a:srgbClr val="1F2937"/></a:dk2>'
    theme_xml += f'<a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>'
    theme_xml += f'<a:accent1><a:srgbClr val="2563EB"/></a:accent1>'
    theme_xml += f'<a:accent2><a:srgbClr val="7C3AED"/></a:accent2>'
    theme_xml += f'<a:accent3><a:srgbClr val="059669"/></a:accent3>'
    theme_xml += f'<a:accent4><a:srgbClr val="D97706"/></a:accent4>'
    theme_xml += f'<a:accent5><a:srgbClr val="DC2626"/></a:accent5>'
    theme_xml += f'<a:accent6><a:srgbClr val="0891B2"/></a:accent6>'
    theme_xml += f'<a:hlink><a:srgbClr val="2563EB"/></a:hlink>'
    theme_xml += f'<a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink>'
    theme_xml += f'</a:clrScheme>'
    theme_xml += f'</a:themeElements>'
    theme_xml += f'</a:theme>'

    slide_xml = f'<?xml version="1.0" encoding="UTF-8"?>'
    slide_xml += f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}">'
    slide_xml += f'<p:cSld><p:spTree><p:nvGrpSpPr/><p:grpSpPr/></p:spTree></p:cSld>'
    slide_xml += f'</p:sld>'

    content_types = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>'
    pres_xml = f'<?xml version="1.0" encoding="UTF-8"?><p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="1" r:id="rId1"/></p:sldIdLst></p:presentation>'
    pres_rels = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/></Relationships>'

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("ppt/presentation.xml", pres_xml)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slides/slide1.xml", slide_xml)
        z.writestr("ppt/theme/theme1.xml", theme_xml)
    return path


def _make_minimal_xlsx(path: Path) -> Path:
    """Create a minimal XLSX for testing."""
    workbook_xml = '<?xml version="1.0" encoding="UTF-8"?><s:workbook xmlns:s="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><s:sheets><s:sheet name="Sheet1" sheetId="1"/></s:sheets></s:workbook>'
    content_types = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook_xml)
    return path


class TestWordCommentReview:
    def test_review_extracts_comments(self, tmp_path: Path) -> None:
        docx_path = _make_minimal_docx(tmp_path / "test.docx")
        result = review_word_comments(input_path=docx_path)
        assert result.status == "succeeded"
        assert result.tool == "word.comment.review"
        assert result.usage["total_comments"] == 2
        assert result.usage["comments"][0]["author"] == "Alice"
        assert result.usage["comments"][1]["author"] == "Bob"

    def test_review_resolve_comments(self, tmp_path: Path) -> None:
        docx_path = _make_minimal_docx(tmp_path / "input.docx")
        output_path = tmp_path / "resolved.docx"
        result = review_word_comments(
            input_path=docx_path,
            output_path=output_path,
            resolve_ids=["0"],
        )
        assert result.status == "succeeded"
        assert result.usage["resolved_count"] == 1
        assert output_path.exists()

        with zipfile.ZipFile(output_path) as z:
            patched = z.read("word/comments.xml").decode("utf-8")
            assert 'w:resolved="1"' in patched or 'resolved="1"' in patched


class TestDeckApplyTheme:
    def test_apply_named_theme(self, tmp_path: Path) -> None:
        pptx_path = _make_minimal_pptx(tmp_path / "input.pptx")
        output_path = tmp_path / "themed.pptx"
        result = apply_deck_theme(
            input_path=pptx_path,
            output_path=output_path,
            theme_name="nature_green",
        )
        assert result.status == "succeeded"
        assert result.tool == "deck.edit.apply_theme"
        assert output_path.exists()

        with zipfile.ZipFile(output_path) as z:
            theme_data = z.read("ppt/theme/theme1.xml").decode("utf-8")
            assert "059669" in theme_data

    def test_apply_custom_colors(self, tmp_path: Path) -> None:
        pptx_path = _make_minimal_pptx(tmp_path / "input.pptx")
        output_path = tmp_path / "custom.pptx"
        result = apply_deck_theme(
            input_path=pptx_path,
            output_path=output_path,
            colors={"accent1": "FF0000"},
        )
        assert result.status == "succeeded"
        with zipfile.ZipFile(output_path) as z:
            theme_data = z.read("ppt/theme/theme1.xml").decode("utf-8")
            assert "FF0000" in theme_data

    def test_reject_unknown_theme(self, tmp_path: Path) -> None:
        pptx_path = _make_minimal_pptx(tmp_path / "input.pptx")
        result = apply_deck_theme(
            input_path=pptx_path,
            output_path=tmp_path / "out.pptx",
            theme_name="nonexistent",
        )
        assert result.status == "failed"


class TestPdfExtractTables:
    def test_returns_tool_result(self) -> None:
        result = extract_pdf_tables(input_path="nonexistent.pdf")
        # Should fail on missing file, but be a valid ToolResult
        assert result.tool == "pdf.extract.tables"


class TestMultiFormatBrief:
    def test_brief_from_mixed_files(self, tmp_path: Path) -> None:
        docx_path = _make_minimal_docx(tmp_path / "doc.docx")
        xlsx_path = _make_minimal_xlsx(tmp_path / "sheet.xlsx")
        output_path = tmp_path / "brief.json"

        result = build_multi_format_brief(
            files=[docx_path, xlsx_path],
            output_path=output_path,
            title="Test Brief",
        )
        assert result.status == "succeeded"
        assert result.tool == "office.workflow.multi_format_brief"
        assert result.usage["source_count"] == 2
        assert output_path.exists()

        brief = json.loads(output_path.read_text(encoding="utf-8"))
        assert brief["title"] == "Test Brief"
        assert len(brief["sources"]) == 2

    def test_brief_without_output(self, tmp_path: Path) -> None:
        docx_path = _make_minimal_docx(tmp_path / "doc.docx")
        result = build_multi_format_brief(files=[docx_path])
        assert result.status == "succeeded"
        assert result.artifacts == []
