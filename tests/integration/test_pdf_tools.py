from pathlib import Path

from pypdf import PdfReader

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import (
    create_markdown_pdf,
    create_text_pdf,
    extract_pages_pdf,
    extract_text_pdf,
    inspect_pdf,
    merge_pdfs,
    read_metadata_pdf,
    remove_pages_pdf,
    remove_metadata_pdf,
    render_pdf,
    rotate_pages_pdf,
    split_pdf,
    update_metadata_pdf,
)
from agentpdf.validation.pdf import validate_pdf


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


def test_inspect_pdf_returns_agent_readable_details(two_page_pdf: Path) -> None:
    info = inspect_pdf(two_page_pdf)

    assert info["page_count"] == 2
    assert info["encrypted"] is False
    assert info["pages"][0]["width"] == 612
    assert info["pages"][0]["height"] == 792


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


def test_render_pdf_writes_png_artifact(simple_pdf: Path, tmp_path: Path) -> None:
    result = render_pdf(simple_pdf, pages="1", image_format="png", out_dir=tmp_path)

    assert result.status == "succeeded"
    assert result.tool == "pdf.convert.pdf_to_images"
    assert result.artifacts[0].mime_type == "image/png"
    assert result.artifacts[0].path.exists()
    assert result.artifacts[0].size_bytes > 0


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
