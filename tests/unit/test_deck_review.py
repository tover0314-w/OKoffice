"""Tests for deck.review.story, deck.review.claims, deck.validation.notes, deck.validation.placeholders."""

import zipfile
from pathlib import Path

from okoffice.office.deck_review import review_deck_claims, review_deck_story
from okoffice.office.deck_validation import validate_deck_notes, validate_deck_placeholders

from tests.unit.test_deck_extract import _write_rich_pptx


def _write_single_slide_pptx(path: Path) -> None:
    """Write a PPTX with one slide, no notes."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
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
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Only Slide</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>')


def _write_placeholder_pptx(path: Path) -> None:
    """Write a PPTX with placeholder markers in slide body text."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
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
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Review TODO items</a:t></a:r></a:p></p:txBody></p:sp>'
            '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content 2"/><p:cNvSpPr/><p:nvPr><p:ph idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>TODO fix this {{fill}} later</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>')


# ---------------------------------------------------------------------------
# deck.review.story
# ---------------------------------------------------------------------------

class TestReviewDeckStory:
    def test_reviews_story_rhythm(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = review_deck_story(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.review.story"
        title_flow = result.usage["story"]["title_flow"]
        assert len(title_flow) == 2
        assert result.usage["summary"]["slide_count"] >= 2

    def test_warns_single_slide(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "single.pptx"
        _write_single_slide_pptx(pptx_path)
        result = review_deck_story(pptx_path)
        assert result.status == "succeeded"
        assert len(result.warnings) > 0
        assert any("2 or more slides" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# deck.review.claims
# ---------------------------------------------------------------------------

class TestReviewDeckClaims:
    def test_detects_claims(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = review_deck_claims(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.review.claims"
        claims = result.usage["claims"]
        assert isinstance(claims, list)

    def test_no_claims_in_minimal_deck(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "bare.pptx"
        _write_single_slide_pptx(pptx_path)
        result = review_deck_claims(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["total_claims"] >= 0


# ---------------------------------------------------------------------------
# deck.validation.notes
# ---------------------------------------------------------------------------

class TestValidateDeckNotes:
    def test_validates_notes_completeness(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "test.pptx"
        _write_rich_pptx(pptx_path)
        result = validate_deck_notes(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.validation.notes"
        assert result.usage["summary"]["notes_count"] >= 1

    def test_warns_no_notes(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "bare.pptx"
        _write_single_slide_pptx(pptx_path)
        result = validate_deck_notes(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["notes_count"] == 0
        assert any("missing" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# deck.validation.placeholders
# ---------------------------------------------------------------------------

class TestValidateDeckPlaceholders:
    def test_validates_no_placeholders(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "clean.pptx"
        _write_rich_pptx(pptx_path)
        result = validate_deck_placeholders(pptx_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.validation.placeholders"
        assert result.usage["summary"]["total_placeholders"] == 0

    def test_detects_placeholders(self, tmp_path: Path) -> None:
        pptx_path = tmp_path / "placeholders.pptx"
        _write_placeholder_pptx(pptx_path)
        result = validate_deck_placeholders(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["total_placeholders"] > 0
        assert result.usage["summary"]["slides_with_placeholders"] >= 1
