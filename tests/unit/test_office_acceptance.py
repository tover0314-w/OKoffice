"""Office acceptance tests covering inspect, validate, workflow, and bundle tools."""

import json
import zipfile
from pathlib import Path

import pytest


def _write_minimal_pptx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            '<Override PartName="/ppt/slides/slide1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            '</Types>'
        )
        archive.writestr("_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="ppt/presentation.xml"/></Relationships>'
        )
        archive.writestr("ppt/presentation.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>'
            '<p:sldSz cx="12192000" cy="6858000" type="wide"/>'
            '<p:notesSz cx="6858000" cy="9144000"/></p:presentation>'
        )
        archive.writestr("ppt/_rels/presentation.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            'Target="slides/slide1.xml"/></Relationships>'
        )
        archive.writestr("ppt/slides/slide1.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name="Group"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="650000" y="520000"/><a:ext cx="10900000" cy="700000"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            '<p:txBody><a:bodyPr/><a:lstStyle/>'
            '<a:p><a:r><a:rPr lang="en-US" sz="2700" dirty="0"><a:latin typeface="Arial"/>'
            '<a:solidFill><a:srgbClr val="111827"/></a:solidFill></a:rPr>'
            '<a:t>Test Slide</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>'
        )
        archive.writestr("ppt/slides/_rels/slide1.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        )


def _write_minimal_docx(path: Path, content: str = "Test content") -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body><w:p><w:r><w:t>{content}</w:t></w:r></w:p></w:body></w:document>',
        )


def _write_minimal_xlsx(path: Path) -> None:
    from okoffice.office.xlsx import write_xlsx

    write_xlsx(path, [("Sheet1", [["A", "B"], ["1", "2"]])])


class TestInspectTools:
    def test_inspect_office_file_docx(self, tmp_path: Path) -> None:
        from okoffice.office.inspect import inspect_office_file

        docx_path = tmp_path / "doc.docx"
        _write_minimal_docx(docx_path)
        result = inspect_office_file(docx_path)
        assert result.status == "succeeded"
        assert result.usage["format"]["detected_format"] == "docx"

    def test_inspect_office_file_pptx(self, tmp_path: Path) -> None:
        from okoffice.office.inspect import inspect_office_file

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)
        result = inspect_office_file(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["format"]["detected_format"] == "pptx"

    def test_inspect_office_file_xlsx(self, tmp_path: Path) -> None:
        from okoffice.office.inspect import inspect_office_file

        xlsx_path = tmp_path / "data.xlsx"
        _write_minimal_xlsx(xlsx_path)
        result = inspect_office_file(xlsx_path)
        assert result.status == "succeeded"
        assert result.usage["format"]["detected_format"] == "xlsx"

    def test_inspect_office_file_rejects_missing(self, tmp_path: Path) -> None:
        from okoffice.office.inspect import inspect_office_file

        result = inspect_office_file(tmp_path / "missing.docx")
        assert result.status == "failed"


class TestValidateTools:
    def test_validate_pptx(self, tmp_path: Path) -> None:
        from okoffice.office.deck_validation import validate_deck_presentation

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)
        result = validate_deck_presentation(pptx_path)
        assert result.status == "succeeded"
        assert result.validation is not None

    def test_validate_xlsx(self, tmp_path: Path) -> None:
        from okoffice.office.sheet import validate_sheet_workbook

        xlsx_path = tmp_path / "data.xlsx"
        _write_minimal_xlsx(xlsx_path)
        result = validate_sheet_workbook(xlsx_path)
        assert result.status == "succeeded"

    def test_validate_docx(self, tmp_path: Path) -> None:
        from okoffice.office.word_validation import validate_word_document

        docx_path = tmp_path / "doc.docx"
        _write_minimal_docx(docx_path)
        result = validate_word_document(docx_path)
        assert result.status == "succeeded"


class TestDeckTools:
    def test_inspect_deck(self, tmp_path: Path) -> None:
        from okoffice.office.deck import inspect_deck_presentation

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)
        result = inspect_deck_presentation(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["slide_count"] == 1

    def test_deck_taste_review(self, tmp_path: Path) -> None:
        from okoffice.office.deck_taste_qa import review_deck_taste

        html_path = tmp_path / "deck.html"
        manifest_path = tmp_path / "deck.html-manifest.json"
        slides_html = (
            '<section class="okoffice-slide" id="slide-1">'
            '<div class="slide-content"><h1>Test</h1></div></section>'
        )
        html_path.write_text(
            f"<html><head><style>:root {{ --color-primary: #2563EB; }}</style></head>"
            f"<body><main class='okoffice-deck'>{slides_html}</main></body></html>",
            encoding="utf-8",
        )
        manifest_path.write_text(json.dumps({
            "tool": "deck.render.html",
            "outline": {"title": "Test", "slides": [{"title": "Test"}]},
            "summary": {"slide_count": 1},
        }), encoding="utf-8")

        result = review_deck_taste(html_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.review.taste"

    def test_revise_deck(self, tmp_path: Path) -> None:
        from okoffice.office.deck_patch import revise_deck

        input_path = tmp_path / "input.pptx"
        output_path = tmp_path / "output.pptx"
        _write_minimal_pptx(input_path)
        result = revise_deck(
            input_path=input_path,
            output_path=output_path,
            operations=[{"op": "replace_text", "find": "Test Slide", "replace": "Revised"}],
        )
        assert result.status == "succeeded"
        assert result.tool == "deck.revise"
        assert output_path.exists()


class TestBundleTools:
    def test_board_pack_creates_zip(self, tmp_path: Path) -> None:
        from okoffice.office.workflows import board_pack

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)
        output = tmp_path / "pack.zip"
        result = board_pack(files=[pptx_path], output_path=output, title="Acceptance Pack")
        assert result.status == "succeeded"
        assert output.exists()
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist())
            assert "okoffice-manifest.json" in names
            assert "okoffice-validation.json" in names

    def test_verify_board_pack(self, tmp_path: Path) -> None:
        from okoffice.office.workflows import board_pack, verify_board_pack

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)
        pack_path = tmp_path / "pack.zip"
        board_pack(files=[pptx_path], output_path=pack_path)
        result = verify_board_pack(pack_path)
        assert result.status == "succeeded"
        assert result.validation is not None


class TestSheetTools:
    def test_write_and_read_workbook(self, tmp_path: Path) -> None:
        from okoffice.office.sheet import read_sheet_workbook
        from okoffice.office.xlsx import write_xlsx

        path = tmp_path / "test.xlsx"
        write_xlsx(path, [("Data", [["Name", "Value"], ["a", "1"]])])
        result = read_sheet_workbook(path)
        assert result.status == "succeeded"

    def test_profile_data(self, tmp_path: Path) -> None:
        from okoffice.office.sheet import profile_sheet_data

        path = tmp_path / "data.xlsx"
        _write_minimal_xlsx(path)
        result = profile_sheet_data(path)
        assert result.status == "succeeded"


class TestManifestAndRegistry:
    def test_okoffice_tool_manifest_loads(self) -> None:
        from okoffice.office.manifest import load_office_tool_manifest

        manifest = load_office_tool_manifest()
        assert manifest.product == "okoffice"
        assert manifest.tool_count > 0
        assert len(manifest.tools) > 0

    def test_workers_status(self) -> None:
        from okoffice.office.workers import inspect_office_workers

        result = inspect_office_workers()
        assert result.status == "succeeded"
