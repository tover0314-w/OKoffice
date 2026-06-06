"""Tests for deck.extract.* tools: text, notes, shapes, media, charts, theme."""

import zipfile
from pathlib import Path

import pytest


def _write_rich_pptx(path: Path) -> None:
    """Write a PPTX with two slides, speaker notes, shapes, and a theme."""
    ct = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        '<Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/notesSlides/notesSlide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        '</Relationships>'
    )
    pres_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/>'
        '</Relationships>'
    )
    presentation = (
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:sldIdLst>'
        '<p:sldId id="256" r:id="rId2"/>'
        '<p:sldId id="257" r:id="rId3"/>'
        '</p:sldIdLst>'
        '</p:presentation>'
    )
    slide1 = (
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Slide One Title</a:t></a:r></a:p></p:txBody></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content 2"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Body text here</a:t></a:r></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld></p:sld>'
    )
    slide2 = (
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Slide Two</a:t></a:r></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld></p:sld>'
    )
    slide1_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/>'
        '</Relationships>'
    )
    notes = (
        '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
        '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Speaker notes for slide 1</a:t></a:r></a:p></p:txBody></p:sp>'
        '</p:spTree></p:cSld></p:notes>'
    )
    theme = (
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">'
        '<a:themeElements>'
        '<a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1>'
        '<a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        '<a:accent1><a:srgbClr val="4472C4"/></a:accent1></a:clrScheme>'
        '<a:fontScheme name="Office"><a:majorFont><a:latin typeface="Calibri Light"/></a:majorFont>'
        '<a:minorFont><a:latin typeface="Calibri"/></a:minorFont></a:fontScheme>'
        '</a:themeElements></a:theme>'
    )
    master = (
        '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld/></p:sldMaster>'
    )
    layout = (
        '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld/></p:sldLayout>'
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("ppt/presentation.xml", presentation)
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        zf.writestr("ppt/slides/slide1.xml", slide1)
        zf.writestr("ppt/slides/slide2.xml", slide2)
        zf.writestr("ppt/slides/_rels/slide1.xml.rels", slide1_rels)
        zf.writestr("ppt/notesSlides/notesSlide1.xml", notes)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", master)
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", layout)
        zf.writestr("ppt/theme/theme1.xml", theme)


# ---------------------------------------------------------------------------
# 1. deck.extract.text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_extracts_text_with_slides(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_text

        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = extract_deck_text(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.extract.text"
        assert result.usage["summary"]["slide_count"] >= 2
        slides = result.usage["slides"]
        texts = [s["text"] for s in slides if s["text"]]
        assert any("Slide One Title" in t for t in texts)

    def test_rejects_non_pptx(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_text

        bad_path = tmp_path / "test.pdf"
        bad_path.write_text("not a pptx", encoding="utf-8")
        result = extract_deck_text(bad_path)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# 2. deck.extract.notes
# ---------------------------------------------------------------------------

class TestExtractNotes:
    def test_extracts_notes(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_notes

        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = extract_deck_notes(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.extract.notes"
        notes = result.usage["notes"]
        assert result.usage["summary"]["notes_count"] >= 1
        assert any("Speaker notes" in n["text"] for n in notes)

    def test_warns_when_no_notes(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_notes

        pptx_path = tmp_path / "bare.pptx"
        with zipfile.ZipFile(pptx_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml",
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
                '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                '</Types>')
            zf.writestr("_rels/.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
                '</Relationships>')
            zf.writestr("ppt/_rels/presentation.xml.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'
                '</Relationships>')
            zf.writestr("ppt/presentation.xml",
                '<p:presentation xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst></p:presentation>')
            zf.writestr("ppt/slides/slide1.xml",
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
                ' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
                '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
                '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>No notes slide</a:t></a:r></a:p></p:txBody></p:sp>'
                '</p:spTree></p:cSld></p:sld>')
        result = extract_deck_notes(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["notes_count"] == 0
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# 3. deck.extract.shapes
# ---------------------------------------------------------------------------

class TestExtractShapes:
    def test_extracts_shapes(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_shapes

        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = extract_deck_shapes(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.extract.shapes"
        shapes = result.usage["shapes"]
        assert len(shapes) > 0
        for shape in shapes:
            assert "locator" in shape
            assert "kind" in shape["locator"]


# ---------------------------------------------------------------------------
# 4. deck.extract.media
# ---------------------------------------------------------------------------

class TestExtractMedia:
    def test_extracts_media(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_media

        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = extract_deck_media(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.extract.media"

    def test_rejects_non_pptx(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_media

        bad_path = tmp_path / "test.txt"
        bad_path.write_text("not a pptx", encoding="utf-8")
        result = extract_deck_media(bad_path)
        assert result.status == "failed"


# ---------------------------------------------------------------------------
# 5. deck.extract.charts
# ---------------------------------------------------------------------------

class TestExtractCharts:
    def test_extracts_charts(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_charts

        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = extract_deck_charts(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.extract.charts"


# ---------------------------------------------------------------------------
# 6. deck.extract.theme
# ---------------------------------------------------------------------------

class TestExtractTheme:
    def test_extracts_theme(self, tmp_path: Path) -> None:
        from okoffice.office.deck_extract import extract_deck_theme

        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = extract_deck_theme(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.extract.theme"
        themes = result.usage["themes"]
        assert result.usage["summary"]["theme_count"] >= 1
        assert any(t.get("name") is not None for t in themes)
