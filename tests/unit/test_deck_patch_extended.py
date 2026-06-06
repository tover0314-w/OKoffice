"""Tests for Phase 6 deck patch extended operations: patch_slide, patch_shape, patch_notes, patch_chart."""

import zipfile
from pathlib import Path

from okoffice.office.deck_patch import apply_deck_patch


def _write_patchable_pptx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            '<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            '<Override PartName="/ppt/slides/slide2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            '<Override PartName="/ppt/notesSlides/notesSlide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
            "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "ppt/_rels/presentation.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "ppt/slides/slide1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Hello World</a:t></a:r></a:p></p:txBody></p:sp>'
            "</p:spTree></p:cSld></p:sld>",
        )
        z.writestr(
            "ppt/slides/slide2.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Second Slide</a:t></a:r></a:p></p:txBody></p:sp>'
            "</p:spTree></p:cSld></p:sld>",
        )
        z.writestr(
            "ppt/slides/_rels/slide1.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/>'
            "</Relationships>",
        )
        z.writestr(
            "ppt/notesSlides/notesSlide1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/>'
            '<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:t>Original notes</a:t></a:r></a:p></p:txBody></p:sp>'
            "</p:spTree></p:cSld></p:notes>",
        )
        z.writestr(
            "ppt/presentation.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:sldIdLst><p:sldId id="256" r:id="rId2"/><p:sldId id="257" r:id="rId3"/></p:sldIdLst></p:presentation>',
        )


class TestPatchSlide:
    def test_patches_specific_slide(self, tmp_path: Path) -> None:
        src = tmp_path / "input.pptx"
        out = tmp_path / "patched.pptx"
        _write_patchable_pptx(src)

        result = apply_deck_patch(
            input_path=src,
            output_path=out,
            operations=[{"op": "patch_slide", "slide": 1, "find": "Hello", "replace": "Hi"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["slide_patch_count"] >= 1


class TestPatchShape:
    def test_patches_shape_name(self, tmp_path: Path) -> None:
        src = tmp_path / "input.pptx"
        out = tmp_path / "patched.pptx"
        _write_patchable_pptx(src)

        result = apply_deck_patch(
            input_path=src,
            output_path=out,
            operations=[{"op": "patch_shape", "slide": 1, "shape_id": "2", "property": "name", "value": "New Title"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["shape_patch_count"] == 1


class TestPatchNotes:
    def test_patches_notes(self, tmp_path: Path) -> None:
        src = tmp_path / "input.pptx"
        out = tmp_path / "patched.pptx"
        _write_patchable_pptx(src)

        result = apply_deck_patch(
            input_path=src,
            output_path=out,
            operations=[{"op": "patch_notes", "slide": 1, "find": "Original", "replace": "Updated"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["notes_patch_count"] == 1


class TestPatchChart:
    def test_handles_no_charts(self, tmp_path: Path) -> None:
        src = tmp_path / "input.pptx"
        out = tmp_path / "patched.pptx"
        _write_patchable_pptx(src)

        result = apply_deck_patch(
            input_path=src,
            output_path=out,
            operations=[{"op": "patch_chart", "chart_id": "1", "title": "Revenue"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["chart_patch_count"] == 0


class TestExistingOpsStillWork:
    def test_replace_text_still_works(self, tmp_path: Path) -> None:
        src = tmp_path / "input.pptx"
        out = tmp_path / "patched.pptx"
        _write_patchable_pptx(src)

        result = apply_deck_patch(
            input_path=src,
            output_path=out,
            operations=[{"op": "replace_text", "find": "Hello", "replace": "Greetings"}],
        )

        assert result.status == "succeeded"
        assert result.usage["summary"]["text_replacement_count"] >= 1
