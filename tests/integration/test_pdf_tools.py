from pathlib import Path

from pypdf import PdfReader
from PIL import Image
from reportlab.pdfgen import canvas

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import (
    add_page_numbers_pdf,
    add_text_watermark_pdf,
    compress_pdf,
    create_markdown_pdf,
    create_text_pdf,
    extract_images_pdf,
    extract_pages_pdf,
    extract_text_pdf,
    image_to_pdf,
    inspect_pdf,
    inspect_pdf_pages,
    merge_pdfs,
    page_info_pdf,
    read_metadata_pdf,
    remove_pages_pdf,
    remove_metadata_pdf,
    repair_pdf,
    insert_blank_pages_pdf,
    reorder_pages_pdf,
    render_pdf,
    rotate_pages_pdf,
    split_pdf,
    update_metadata_pdf,
)
from agentpdf.tools.runner import run_page_count_check, run_security_remove_metadata
from agentpdf.validation.pdf import blank_page_check_pdf, render_check_pdf, validate_pdf


def test_build_artifact_records_pdf_metadata(simple_pdf: Path) -> None:
    artifact = build_artifact(simple_pdf, source_tool="pdf.inspect.document")

    assert artifact.mime_type == "application/pdf"
    assert artifact.size_bytes > 0
    assert artifact.sha256
    assert artifact.page_count == 1


def test_validate_pdf_reports_page_count(simple_pdf: Path) -> None:
    report = validate_pdf(simple_pdf, expected_pages=1)

    assert report.status == "passed"
    assert report.page_count == 1
    assert report.checks[0].status == "passed"


def test_render_check_pdf_reports_renderable_pages(simple_pdf: Path) -> None:
    report, usage = render_check_pdf(simple_pdf, pages="1")

    assert report.status == "passed"
    assert report.page_count == 1
    assert report.checks[0].name == "render_page"
    assert usage["rendered_pages"] == [1]


def test_blank_page_check_pdf_reports_blank_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    with_blank = tmp_path / "with-blank.pdf"
    _write_labeled_pages(source, ["First page", "Second page"])
    insert_blank_pages_pdf(source, after_page=1, count=1, output_path=with_blank)

    report, usage = blank_page_check_pdf(with_blank, pages="all")

    assert report.status == "warning"
    assert usage["blank_pages"] == [2]
    assert usage["non_blank_pages"] == [1, 3]
    assert report.checks[1].status == "warning"


def test_inspect_pdf_returns_agent_readable_details(two_page_pdf: Path) -> None:
    info = inspect_pdf(two_page_pdf)

    assert info["page_count"] == 2
    assert info["encrypted"] is False
    assert info["pages"][0]["width"] == 612
    assert info["pages"][0]["height"] == 792


def test_inspect_pdf_pages_reports_page_level_agent_facts(tmp_path: Path) -> None:
    source = tmp_path / "page-facts.pdf"
    _write_page_inspection_fixture(source, tmp_path / "embedded.png")

    info = inspect_pdf_pages(source, pages="all")

    assert info["page_count"] == 2
    assert info["selected_pages"] == [1, 2]
    first_page = info["pages"][0]
    assert first_page["page_number"] == 1
    assert first_page["width"] == 612
    assert first_page["height"] == 792
    assert first_page["has_text_layer"] is True
    assert first_page["text_char_count"] > 0
    assert first_page["image_count"] == 1
    assert info["pages"][1]["has_text_layer"] is False


def test_page_info_pdf_returns_metadata_page_geometry(two_page_pdf: Path) -> None:
    result = page_info_pdf(two_page_pdf, pages="2")

    assert result.status == "succeeded"
    assert result.tool == "pdf.metadata.page_info"
    assert result.usage["page_count"] == 2
    assert result.usage["selected_pages"] == [2]
    assert result.usage["pages"][0]["page_number"] == 2
    assert result.usage["pages"][0]["width"] == 612


def test_merge_pdfs_writes_new_validated_output(simple_pdf: Path, two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "merged.pdf"

    result = merge_pdfs([simple_pdf, two_page_pdf], output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.merge"
    assert result.artifacts[0].page_count == 3
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert len(PdfReader(output).pages) == 3


def test_split_pdf_writes_selected_pages(simple_pdf: Path, two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "page-2.pdf"

    result = split_pdf(two_page_pdf, pages="2", output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.split"
    assert result.artifacts[0].page_count == 1
    assert len(PdfReader(output).pages) == 1
    assert len(PdfReader(simple_pdf).pages) == 1


def test_extract_pages_pdf_uses_stable_tool_name(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "extracted.pdf"

    result = extract_pages_pdf(two_page_pdf, pages="2", output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.extract_pages"
    assert result.artifacts[0].page_count == 1


def test_remove_pages_pdf_writes_remaining_pages(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "removed.pdf"

    result = remove_pages_pdf(two_page_pdf, pages="1", output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.remove_pages"
    assert result.artifacts[0].page_count == 1
    assert len(PdfReader(output).pages) == 1


def test_rotate_pages_pdf_rotates_selected_pages(two_page_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "rotated.pdf"

    result = rotate_pages_pdf(two_page_pdf, pages="1", degrees=90, output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.rotate_pages"
    reader = PdfReader(output)
    assert int(reader.pages[0].get("/Rotate", 0)) == 90
    assert int(reader.pages[1].get("/Rotate", 0)) == 0


def test_reorder_pages_pdf_writes_requested_page_order(tmp_path: Path) -> None:
    source = tmp_path / "ordered.pdf"
    output = tmp_path / "reordered.pdf"
    _write_labeled_pages(source, ["First page", "Second page", "Third page"])

    result = reorder_pages_pdf(source, order="3,1,2", output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.reorder_pages"
    assert result.artifacts[0].page_count == 3
    reader = PdfReader(output)
    assert "Third page" in (reader.pages[0].extract_text() or "")
    assert "First page" in (reader.pages[1].extract_text() or "")
    assert "Second page" in (reader.pages[2].extract_text() or "")


def test_insert_blank_pages_pdf_adds_blank_pages_after_target(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "with-blanks.pdf"
    _write_labeled_pages(source, ["First page", "Second page"])

    result = insert_blank_pages_pdf(source, after_page=1, count=2, output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.organize.insert_blank_pages"
    assert result.artifacts[0].page_count == 4
    reader = PdfReader(output)
    assert len(reader.pages) == 4
    assert "First page" in (reader.pages[0].extract_text() or "")
    assert (reader.pages[1].extract_text() or "").strip() == ""
    assert (reader.pages[2].extract_text() or "").strip() == ""
    assert "Second page" in (reader.pages[3].extract_text() or "")


def test_compress_pdf_rewrites_streams_and_reports_savings(tmp_path: Path) -> None:
    source = tmp_path / "uncompressed.pdf"
    output = tmp_path / "compressed.pdf"
    _write_uncompressed_text_pdf(source)

    result = compress_pdf(source, output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.optimize.compress"
    assert result.artifacts[0].page_count == len(PdfReader(source).pages)
    assert result.usage["original_size_bytes"] > result.usage["output_size_bytes"]
    assert result.usage["bytes_saved"] > 0
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert "compressible content" in (PdfReader(output).pages[0].extract_text() or "")


def test_repair_pdf_rewrites_parseable_output(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "repaired.pdf"
    _write_labeled_pages(source, ["Repairable PDF"])

    result = repair_pdf(source, output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.optimize.repair"
    assert result.artifacts[0].page_count == 1
    assert result.usage["input"] == str(source.resolve())
    assert result.usage["repair_strategy"] == "pypdf_read_rewrite"
    assert "Repairable PDF" in (PdfReader(output).pages[0].extract_text() or "")


def test_render_pdf_writes_png_artifact(simple_pdf: Path, tmp_path: Path) -> None:
    result = render_pdf(simple_pdf, pages="1", image_format="png", out_dir=tmp_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.pdf_to_images"
    assert result.artifacts[0].mime_type == "image/png"
    assert result.artifacts[0].path.exists()
    assert result.artifacts[0].size_bytes > 0


def test_extract_images_pdf_writes_image_artifacts_with_page_evidence(tmp_path: Path) -> None:
    source = tmp_path / "images.pdf"
    out_dir = tmp_path / "extracted"
    _write_page_inspection_fixture(source, tmp_path / "embedded.png")

    result = extract_images_pdf(source, pages="1", out_dir=out_dir)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.extract_images"
    assert result.artifacts
    assert result.artifacts[0].mime_type == "image/png"
    assert result.artifacts[0].path.exists()
    assert result.usage["image_count"] == 1
    first_image = result.usage["images"][0]
    assert first_image["page_number"] == 1
    assert first_image["image_index"] == 1
    assert first_image["width"] == 24
    assert first_image["height"] == 24


def test_extract_text_pdf_returns_page_text(text_pdf: Path) -> None:
    result = extract_text_pdf(text_pdf, pages="1")

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.pdf_to_text"
    assert "AgentPDF local text layer" in result.usage["text"]
    assert result.usage["pages"][0]["page_number"] == 1


def test_read_metadata_pdf_returns_document_info(metadata_pdf: Path) -> None:
    result = read_metadata_pdf(metadata_pdf)

    assert result.status == "succeeded"
    assert result.tool == "pdf.metadata.read"
    assert result.usage["metadata"]["Title"] == "Original Title"
    assert result.usage["metadata"]["Author"] == "AgentPDF Tests"


def test_update_metadata_pdf_writes_new_validated_output(metadata_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "updated.pdf"

    result = update_metadata_pdf(metadata_pdf, {"Title": "Updated Title"}, output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.metadata.update"
    assert result.artifacts[0].page_count == 1
    assert read_metadata_pdf(output).usage["metadata"]["Title"] == "Updated Title"
    assert read_metadata_pdf(metadata_pdf).usage["metadata"]["Title"] == "Original Title"


def test_remove_metadata_pdf_removes_custom_document_info(metadata_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "clean.pdf"

    result = remove_metadata_pdf(metadata_pdf, output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.metadata.remove"
    cleaned_metadata = read_metadata_pdf(output).usage["metadata"]
    assert "Title" not in cleaned_metadata
    assert "Author" not in cleaned_metadata


def test_security_remove_metadata_uses_security_tool_name(metadata_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "security-clean.pdf"

    result = run_security_remove_metadata(metadata_pdf, output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.security.remove_metadata"
    assert result.artifacts[0].source_tool == "pdf.security.remove_metadata"
    assert "Title" not in read_metadata_pdf(output).usage["metadata"]


def test_page_count_check_returns_validation_evidence(two_page_pdf: Path) -> None:
    result = run_page_count_check(two_page_pdf, expected_pages=2)

    assert result.status == "succeeded"
    assert result.tool == "pdf.validation.page_count_check"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["expected_pages"] == 2
    assert result.usage["actual_pages"] == 2


def test_create_text_pdf_writes_valid_pdf(tmp_path: Path) -> None:
    output = tmp_path / "text-output.pdf"

    result = create_text_pdf("Hello from okpdf\nLocal PDF creation works.", output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.text_to_pdf"
    assert result.artifacts[0].page_count == 1
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert "Hello from okpdf" in extract_text_pdf(output).usage["text"]


def test_create_markdown_pdf_writes_headings_and_bullets(tmp_path: Path) -> None:
    output = tmp_path / "report.pdf"
    markdown = "# Agent Report\n\n## Summary\n\n- Local first\n- Agent ready\n"

    result = create_markdown_pdf(markdown, output, title="Agent Report")

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.markdown_to_pdf"
    assert result.artifacts[0].page_count == 1
    extracted = extract_text_pdf(output).usage["text"]
    assert "Agent Report" in extracted
    assert "Local first" in extracted


def test_create_markdown_pdf_applies_builtin_style_pack_page_and_palette(tmp_path: Path) -> None:
    output = tmp_path / "styled-report.pdf"
    markdown = "# Board Report\n\n## Summary\n\n- Local first\n- Agent ready\n"

    result = create_markdown_pdf(
        markdown,
        output,
        title="Board Report",
        style_pack="business_report_modern",
    )

    page = PdfReader(output).pages[0]
    assert result.status == "succeeded"
    assert result.usage["style_pack"] == "business_report_modern"
    assert result.usage["style_pack_name"] == "Business Report Modern"
    assert result.usage["style_pack_source"] == "builtin"
    assert result.usage["colors"]["primary"] == "#1f3a5f"
    assert round(float(page.mediabox.width)) == 595
    assert round(float(page.mediabox.height)) == 842


def test_create_markdown_pdf_loads_local_json_style_pack(tmp_path: Path) -> None:
    output = tmp_path / "custom-report.pdf"
    style_pack = tmp_path / "custom-style.json"
    style_pack.write_text(
        """{
  "style_id": "custom_agent_report",
  "name": "Custom Agent Report",
  "page": {
    "size": "A4",
    "orientation": "landscape",
    "margins": {"top": 40, "right": 42, "bottom": 44, "left": 46}
  },
  "typography": {"base_size": 11},
  "colors": {"primary": "#0f766e", "accent": "#f59e0b", "text": "#0f172a"},
  "components": ["section_header"]
}""",
        encoding="utf-8",
    )

    result = create_markdown_pdf(
        "# Custom\n\nLocal template colors work.",
        output,
        style_pack=str(style_pack),
    )

    page = PdfReader(output).pages[0]
    assert result.status == "succeeded"
    assert result.usage["style_pack"] == "custom_agent_report"
    assert result.usage["style_pack_name"] == "Custom Agent Report"
    assert result.usage["style_pack_source"] == str(style_pack.resolve())
    assert result.usage["colors"]["accent"] == "#f59e0b"
    assert round(float(page.mediabox.width)) == 842
    assert round(float(page.mediabox.height)) == 595


def test_image_to_pdf_creates_valid_pdf_from_local_images(tmp_path: Path) -> None:
    image = tmp_path / "cover.png"
    output = tmp_path / "cover.pdf"
    Image.new("RGB", (320, 180), color=(18, 52, 86)).save(image)

    result = image_to_pdf([image], output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.image_to_pdf"
    assert result.artifacts[0].page_count == 1
    assert result.validation is not None
    assert result.validation.status == "passed"


def test_add_text_watermark_writes_validated_overlay(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "watermarked.pdf"
    create_text_pdf("Watermark source", source)

    result = add_text_watermark_pdf(source, text="CONFIDENTIAL", output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "pdf.edit.watermark"
    assert result.artifacts[0].page_count == 1
    assert "CONFIDENTIAL" in extract_text_pdf(output).usage["text"]


def test_add_page_numbers_writes_page_labels(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "numbered.pdf"
    create_markdown_pdf("# Page One\n\n" + ("Body\n\n" * 90), source)

    result = add_page_numbers_pdf(source, output_path=output, template="Page {page} of {total}")

    assert result.status == "succeeded"
    assert result.tool == "pdf.edit.page_numbers"
    extracted = extract_text_pdf(output).usage["text"]
    assert "Page 1 of" in extracted


def _write_labeled_pages(path: Path, labels: list[str]) -> None:
    document = canvas.Canvas(str(path))
    for label in labels:
        document.drawString(72, 720, label)
        document.showPage()
    document.save()


def _write_uncompressed_text_pdf(path: Path) -> None:
    document = canvas.Canvas(str(path), pageCompression=0)
    for index in range(160):
        document.drawString(72, 760 - (index % 45) * 14, "compressible content " * 8)
        if index % 45 == 44:
            document.showPage()
    document.save()


def _write_page_inspection_fixture(path: Path, image_path: Path) -> None:
    Image.new("RGB", (24, 24), color=(80, 120, 160)).save(image_path)
    document = canvas.Canvas(str(path), pagesize=(612, 792))
    document.drawString(72, 720, "Page facts with text and image")
    document.drawImage(str(image_path), 72, 650, width=24, height=24)
    document.showPage()
    document.showPage()
    document.save()
