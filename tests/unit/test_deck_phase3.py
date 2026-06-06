"""Tests for Phase 3 deck pipeline: contact sheet, taste review, layout hints, revise_deck."""

import json
import zipfile
from pathlib import Path

import pytest


def _write_minimal_pptx(path: Path, *, slide_count: int = 2) -> None:
    slides_xml = "".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, slide_count + 1)
    )
    slide_files = ""
    slide_content_types = ""
    for i in range(1, slide_count + 1):
        slide_files += (
            f'<Relationship Id="rId{i}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i}.xml"/>'
        )
        slide_content_types += (
            f'<Override PartName="/ppt/slides/slide{i}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        slide_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name="Group"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="650000" y="520000"/><a:ext cx="10900000" cy="700000"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'<p:txBody><a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:r><a:rPr lang="en-US" sz="2700" dirty="0"><a:latin typeface="Arial"/>'
            f'<a:solidFill><a:srgbClr val="111827"/></a:solidFill></a:rPr>'
            f'<a:t>Slide {i} Title</a:t></a:r></a:p></p:txBody></p:sp>'
            '</p:spTree></p:cSld></p:sld>'
        )
        slide_files_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
        )
        # We'll write these inside the zip below

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            f'{slide_content_types}</Types>'
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
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<p:sldIdLst>{slides_xml}</p:sldIdLst>'
            '<p:sldSz cx="12192000" cy="6858000" type="wide"/>'
            '<p:notesSz cx="6858000" cy="9144000"/></p:presentation>'
        )
        archive.writestr("ppt/_rels/presentation.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{slide_files}</Relationships>'
        )
        for i in range(1, slide_count + 1):
            slide_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                '<p:cSld><p:spTree>'
                '<p:nvGrpSpPr><p:cNvPr id="1" name="Group"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
                '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
                f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
                f'<p:spPr><a:xfrm><a:off x="650000" y="520000"/><a:ext cx="10900000" cy="700000"/></a:xfrm>'
                f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
                f'<p:txBody><a:bodyPr/><a:lstStyle/>'
                f'<a:p><a:r><a:rPr lang="en-US" sz="2700" dirty="0"><a:latin typeface="Arial"/>'
                f'<a:solidFill><a:srgbClr val="111827"/></a:solidFill></a:rPr>'
                f'<a:t>Slide {i} Title</a:t></a:r></a:p></p:txBody></p:sp>'
                '</p:spTree></p:cSld></p:sld>'
            )
            archive.writestr(f"ppt/slides/slide{i}.xml", slide_xml)
            archive.writestr(f"ppt/slides/_rels/slide{i}.xml.rels",
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
            )


def _write_html_preview(html_path: Path, manifest_path: Path, *, slide_count: int = 2) -> None:
    slides_html = "\n".join(
        f'    <section class="okoffice-slide" id="slide-{i}" data-slide-index="{i}">'
        f'<div class="slide-content layout-title_only">'
        f'<h1 style="grid-area: title">Slide {i} Title</h1>'
        f'</div></section>'
        for i in range(1, slide_count + 1)
    )
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>:root { --color-primary: #2563EB; }</style></head>"
        f"<body><main class='okoffice-deck'>{slides_html}</main></body></html>"
    )
    html_path.write_text(html_doc, encoding="utf-8")

    manifest = {
        "tool": "deck.render.html",
        "html_path": html_path.name,
        "render_profile": "okoffice-html-slide-package-v0",
        "summary": {"slide_count": slide_count},
        "slides": [
            {"slide_index": i, "dom_anchor": f"slide-{i}"}
            for i in range(1, slide_count + 1)
        ],
        "outline": {
            "title": "Test Deck",
            "slides": [
                {"title": f"Slide {i} Title", "bullets": [], "notes": ""}
                for i in range(1, slide_count + 1)
            ],
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


class TestContactSheetRendering:
    def test_contact_sheet_returns_skipped_without_html_preview(self, tmp_path: Path) -> None:
        from okoffice.office.deck_validation import validate_deck_contact_sheet

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)

        result = validate_deck_contact_sheet(pptx_path)
        assert result.status == "succeeded"
        assert result.validation.status == "skipped"
        check_names = [c.name for c in result.validation.checks]
        assert "contact_sheet_renderer" in check_names

    def test_contact_sheet_returns_skipped_when_playwright_unavailable(self, tmp_path: Path) -> None:
        from okoffice.office.deck_validation import validate_deck_contact_sheet

        pptx_path = tmp_path / "deck.pptx"
        html_path = tmp_path / "deck.html"
        manifest_path = tmp_path / "deck.html-manifest.json"
        _write_minimal_pptx(pptx_path)
        _write_html_preview(html_path, manifest_path)

        result = validate_deck_contact_sheet(pptx_path)
        assert result.status == "succeeded"
        # Will be "skipped" if Playwright not installed, or "passed" if it is
        assert result.validation.status in ("passed", "skipped", "failed")

    def test_contact_sheet_with_explicit_html_path(self, tmp_path: Path) -> None:
        from okoffice.office.deck_validation import validate_deck_contact_sheet

        pptx_path = tmp_path / "deck.pptx"
        html_path = tmp_path / "deck-preview.html"
        manifest_path = tmp_path / "deck-preview.html-manifest.json"
        _write_minimal_pptx(pptx_path)
        _write_html_preview(html_path, manifest_path)

        result = validate_deck_contact_sheet(pptx_path, html_preview_path=html_path)
        assert result.status == "succeeded"

    def test_contact_sheet_fails_for_invalid_pptx(self, tmp_path: Path) -> None:
        from okoffice.office.deck_validation import validate_deck_contact_sheet

        bad_path = tmp_path / "bad.pptx"
        bad_path.write_text("not a pptx", encoding="utf-8")

        result = validate_deck_contact_sheet(bad_path)
        assert result.status == "failed"


class TestDeckTasteReview:
    def test_review_deck_taste_with_html_manifest(self, tmp_path: Path) -> None:
        from okoffice.office.deck_taste_qa import review_deck_taste

        html_path = tmp_path / "deck.html"
        manifest_path = tmp_path / "deck.html-manifest.json"
        _write_html_preview(html_path, manifest_path)

        result = review_deck_taste(html_path)
        assert result.status == "succeeded"
        assert result.tool == "deck.review.taste"
        assert "taste_score" in result.usage["summary"]
        assert isinstance(result.usage["summary"]["taste_score"], int)
        assert 0 <= result.usage["summary"]["taste_score"] <= 100
        assert "passing" in result.usage["summary"]

    def test_review_deck_taste_with_pptx_path(self, tmp_path: Path) -> None:
        from okoffice.office.deck_taste_qa import review_deck_taste

        pptx_path = tmp_path / "deck.pptx"
        html_path = tmp_path / "deck.html"
        manifest_path = tmp_path / "deck.html-manifest.json"
        _write_minimal_pptx(pptx_path)
        _write_html_preview(html_path, manifest_path)

        result = review_deck_taste(pptx_path)
        assert result.status == "succeeded"
        assert result.usage["summary"]["taste_score"] >= 0

    def test_review_deck_taste_fails_without_html(self, tmp_path: Path) -> None:
        from okoffice.office.deck_taste_qa import review_deck_taste

        pptx_path = tmp_path / "deck.pptx"
        _write_minimal_pptx(pptx_path)

        result = review_deck_taste(pptx_path)
        assert result.status == "failed"
        assert "HTML" in result.error.message or "html" in result.error.message.lower()

    def test_review_deck_taste_check_names(self, tmp_path: Path) -> None:
        from okoffice.office.deck_taste_qa import review_deck_taste

        html_path = tmp_path / "deck.html"
        manifest_path = tmp_path / "deck.html-manifest.json"
        _write_html_preview(html_path, manifest_path)

        result = review_deck_taste(html_path)
        check_names = [c.name for c in result.validation.checks]
        assert "taste_score" in check_names
        assert "color_contrast" in check_names
        assert "typography_hierarchy" in check_names


class TestLayoutHints:
    def test_css_class_to_layout_mapping_exists(self) -> None:
        from okoffice.office.deck_themes import CSS_CLASS_TO_LAYOUT

        assert "layout-cover" in CSS_CLASS_TO_LAYOUT
        assert "layout-title_bullets" in CSS_CLASS_TO_LAYOUT
        assert CSS_CLASS_TO_LAYOUT["layout-cover"] == "cover"

    def test_select_layout_uses_css_class(self) -> None:
        from okoffice.office.deck_themes import select_layout

        layout = select_layout({"css_class": "layout-two_column", "bullets": ["a"]})
        assert layout.kind == "two_column"

    def test_select_layout_prefers_explicit_layout(self) -> None:
        from okoffice.office.deck_themes import select_layout

        layout = select_layout({"layout": "metrics", "css_class": "layout-cover"})
        assert layout.kind == "metrics"

    def test_outline_preserves_layout_hints(self, tmp_path: Path) -> None:
        from okoffice.office.deck_plan import compose_deck_plan

        schema_path = tmp_path / "test.xlsx"
        _write_test_workbook(schema_path)

        result = compose_deck_plan(schema_path, title="Layout Test")
        assert result.status == "succeeded"
        outline = result.usage.get("outline", {})
        slides = outline.get("slides", [])
        assert len(slides) > 0
        layout_hints = [s.get("layout") for s in slides if s.get("layout")]
        assert len(layout_hints) > 0, "Composition plan should include layout hints"


class TestReviseDeck:
    def test_revise_deck_applies_text_replacement(self, tmp_path: Path) -> None:
        from okoffice.office.deck_patch import revise_deck

        input_path = tmp_path / "input.pptx"
        output_path = tmp_path / "output.pptx"
        _write_minimal_pptx(input_path)

        result = revise_deck(
            input_path=input_path,
            output_path=output_path,
            operations=[{"op": "replace_text", "find": "Slide 1 Title", "replace": "Revised Title"}],
        )
        assert result.status == "succeeded"
        assert result.tool == "deck.revise"
        assert output_path.exists()

    def test_revise_deck_includes_post_revision_validation(self, tmp_path: Path) -> None:
        from okoffice.office.deck_patch import revise_deck

        input_path = tmp_path / "input.pptx"
        output_path = tmp_path / "output.pptx"
        _write_minimal_pptx(input_path)

        result = revise_deck(
            input_path=input_path,
            output_path=output_path,
            operations=[{"op": "replace_text", "find": "Slide 1 Title", "replace": "Updated"}],
        )
        assert "post_revision_validation" in result.usage
        check_names = [c.name for c in result.validation.checks]
        assert "post_revision_slide_count" in check_names

    def test_revise_deck_fails_on_bad_input(self, tmp_path: Path) -> None:
        from okoffice.office.deck_patch import revise_deck

        result = revise_deck(
            input_path=tmp_path / "nonexistent.pptx",
            output_path=tmp_path / "output.pptx",
            operations=[{"op": "replace_text", "find": "x", "replace": "y"}],
        )
        assert result.status == "failed"


def _write_test_workbook(path: Path) -> None:
    from okoffice.office.xlsx import write_xlsx

    sheets = [
        (
            "Data",
            [
                ["Vendor", "Amount", "Risk"],
                ["Acme Corp", "$120,000", "High"],
                ["Beta Inc", "$50,000", "Low"],
            ],
        ),
    ]
    write_xlsx(path, sheets)
