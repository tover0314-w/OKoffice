import json
from pathlib import Path

from pypdf import PdfWriter

from okoffice.authoring.qa import run_visual_qa, visual_report
from okoffice.renderers.html_package import render_html_package
from okoffice.tools.runner import run_create_html_package


def _pdf(path: Path, page_count: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)


def test_run_visual_qa_combines_pdf_and_manifest_checks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "deck.pdf"
    manifest_path = tmp_path / "deck.html-manifest.json"
    html_path = tmp_path / "deck.html"
    _pdf(pdf_path, page_count=1)
    html_path.write_text("<!doctype html><html><body></body></html>", encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "renderer_contract": "authoring-html-package-v0",
                "html_path": str(html_path.resolve()),
                "javascript_enabled": False,
                "remote_assets_enabled": False,
                "page_count": 1,
            }
        ),
        encoding="utf-8",
    )

    result = visual_report(
        input_path=pdf_path,
        expected_page_count=1,
        html_package_manifest_path=manifest_path,
        pages="1",
    )

    qa = result.usage["visual_qa"]
    assert result.tool == "pdf.qa.visual_report"
    assert result.status == "succeeded"
    assert qa["expected_page_count"] == 1
    assert qa["checks"]["page_count"] == "passed"
    assert qa["checks"]["render_check"] == "passed"
    assert qa["checks"]["html_package_manifest"] == "passed"
    assert any(check.name == "html_package_manifest" for check in result.validation.checks)
    assert result.next_recommended_tools == ["pdf.artifacts.export_bundle", "pdf.workflow.report"]


def test_visual_qa_accepts_raw_html_package_contract(tmp_path: Path) -> None:
    html_package = run_create_html_package(
        page_document=None,
        html="<main><h1>HTML First</h1><p>Visual QA should accept this source package.</p></main>",
        html_output_path=tmp_path / "html-first.html",
        title="HTML First",
    )
    pdf_path = tmp_path / "html-first.pdf"
    rendered = render_html_package(html_package.usage["html_package_manifest_path"], pdf_path)

    result = visual_report(
        input_path=pdf_path,
        expected_page_count=rendered.validation.page_count if rendered.validation else None,
        html_package_manifest_path=html_package.usage["html_package_manifest_path"],
        pages="1",
    )

    qa = result.usage["visual_qa"]
    assert result.status == "succeeded"
    assert qa["checks"]["html_package_manifest"] == "passed"
    assert qa["html_package_manifest"]["renderer_contract"] == "html-package-v0"
    assert qa["html_package_manifest"]["source_format"] == "raw_html"


def test_run_visual_qa_delegates_to_visual_report(tmp_path: Path) -> None:
    pdf_path = tmp_path / "deck.pdf"
    _pdf(pdf_path, page_count=1)

    result = run_visual_qa(input_path=pdf_path, expected_page_count=1, pages="1")

    assert result.tool == "pdf.qa.visual_report"
    assert result.next_recommended_tools == ["pdf.artifacts.export_bundle", "pdf.workflow.report"]


def test_run_visual_qa_fails_for_unsafe_manifest(tmp_path: Path) -> None:
    pdf_path = tmp_path / "deck.pdf"
    manifest_path = tmp_path / "deck.html-manifest.json"
    _pdf(pdf_path)
    manifest_path.write_text(
        json.dumps(
            {
                "renderer_contract": "authoring-html-package-v0",
                "html_path": "https://example.com/deck.html",
                "javascript_enabled": False,
                "remote_assets_enabled": False,
                "page_count": 1,
            }
        ),
        encoding="utf-8",
    )

    result = visual_report(
        input_path=pdf_path,
        expected_page_count=1,
        html_package_manifest_path=manifest_path,
        pages="1",
    )

    qa = result.usage["visual_qa"]
    assert result.status == "failed"
    assert qa["checks"]["html_package_manifest"] == "failed"
    assert qa["issues"]
