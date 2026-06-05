import json
from pathlib import Path

import pytest

from okoffice.renderers.html_package import render_html_package
from okoffice.tools.runner import run_create_html_package
from okoffice.authoring.html_deck import write_authoring_html_package
from okoffice.authoring.models import DesignTokens, PageDocument, PageSpec


def _page_document() -> PageDocument:
    return PageDocument(
        page_document_id="pages_html_test",
        page_count=2,
        pages=[
            PageSpec(
                page_number=1,
                layout="cover",
                title="OKoffice Authoring",
                subtitle="A local-first deck",
                blocks=[{"type": "hero", "text": "A local-first deck"}],
            ),
            PageSpec(
                page_number=2,
                layout="three_cards",
                title="The point",
                subtitle="One idea per page",
                blocks=[
                    {"type": "claim", "text": "One idea per page"},
                    {
                        "type": "evidence_cards",
                        "items": [
                            {
                                "claim": "Evidence-backed pages are clearer.",
                                "evidence": "Cards keep source claims visible.",
                                "source_title": "OKoffice Spec",
                            }
                        ],
                    },
                ],
                source_footer="Sources: OKoffice Spec",
                evidence_refs=["ev_1"],
            ),
        ],
        design_tokens=DesignTokens(theme="business_tech"),
    )


def test_write_authoring_html_package_writes_html_and_manifest(tmp_path: Path) -> None:
    output = tmp_path / "deck.html"

    result = write_authoring_html_package(
        page_document=_page_document(),
        html_output_path=output,
        title="OKoffice Authoring",
    )

    manifest_path = output.with_suffix(".html-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    html = output.read_text(encoding="utf-8")

    assert result.status == "succeeded"
    assert result.tool == "pdf.create.html_package"
    assert result.usage["html_package_manifest"]["renderer_contract"] == "authoring-html-package-v0"
    assert manifest["page_count"] == 2
    assert manifest["javascript_enabled"] is False
    assert manifest["remote_assets_enabled"] is False
    assert manifest["render_profile"]["profile_id"] == "browser_print_deck_16x9_v0"
    assert manifest["render_profile"]["page_size"] == "1280px 720px"
    assert manifest["render_profile"]["margin"] == {"top": "0", "right": "0", "bottom": "0", "left": "0"}
    assert manifest["renderer_constraints"]["javascript"] == "blocked"
    assert 'data-agentpdf-authoring-document' in html
    assert 'data-page-number="1"' in html
    assert "OKoffice Authoring" in html
    assert "Sources: OKoffice Spec" in html
    assert any(str(artifact.path) == str(output.resolve()) for artifact in result.artifacts)


def test_create_html_package_accepts_raw_html_then_renders_pdf(tmp_path: Path) -> None:
    html_output = tmp_path / "brief.html"
    pdf_output = tmp_path / "brief.pdf"

    result = run_create_html_package(
        page_document=None,
        html="<html><body><main><h1>HTML First</h1><p>Auditable source package.</p></main></body></html>",
        html_output_path=html_output,
        title="HTML First",
    )

    manifest_path = html_output.with_suffix(".html-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result.status == "succeeded"
    assert result.tool == "pdf.create.html_package"
    assert html_output.exists()
    assert manifest["source_format"] == "raw_html"
    assert manifest["renderer_contract"] == "html-package-v0"
    assert manifest["remote_assets_enabled"] is False
    assert manifest["javascript_enabled"] is False
    assert manifest["render_profile"]["profile_id"] == "browser_print_a4_v0"
    assert manifest["renderer_constraints"]["asset_policy"] == "local_packaged_assets_only"
    assert result.usage["source_format"] == "raw_html"
    assert result.next_recommended_tools == ["pdf.render.html_package", "pdf.qa.visual_report"]

    rendered = render_html_package(manifest_path, pdf_output)

    assert rendered.status == "succeeded"
    assert pdf_output.exists()
    assert rendered.usage["html_package_manifest"]["source_format"] == "raw_html"
    assert rendered.usage["render_profile"]["prefer_css_page_size"] is True


@pytest.mark.parametrize(
    "raw_html",
    [
        "<main><script>alert('no')</script></main>",
        '<main><img src="https://example.com/remote.png" /></main>',
    ],
)
def test_create_html_package_rejects_unsafe_raw_html(tmp_path: Path, raw_html: str) -> None:
    result = run_create_html_package(
        page_document=None,
        html=raw_html,
        html_output_path=tmp_path / "unsafe.html",
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    assert not (tmp_path / "unsafe.html").exists()
    assert not (tmp_path / "unsafe.html-manifest.json").exists()


def test_write_authoring_html_package_rejects_remote_assets(tmp_path: Path) -> None:
    document = _page_document()
    document.pages[1].blocks.append(
        {
            "type": "image",
            "src": "https://example.com/unsafe.png",
            "alt": "Remote asset",
        }
    )

    result = write_authoring_html_package(
        page_document=document,
        html_output_path=tmp_path / "deck.html",
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"


def test_write_authoring_html_package_returns_stable_error_code_for_invalid_page_document(
    tmp_path: Path,
) -> None:
    result = write_authoring_html_package(
        page_document={"page_document_id": "pages_bad", "page_count": 1, "pages": []},
        html_output_path=tmp_path / "deck.html",
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_page_document"


def test_write_authoring_html_package_rejects_malicious_design_tokens(tmp_path: Path) -> None:
    output = tmp_path / "deck.html"
    result = write_authoring_html_package(
        page_document={
            "page_document_id": "pages_bad_tokens",
            "page_count": 1,
            "pages": [{"page_number": 1, "layout": "cover", "title": "Bad"}],
            "design_tokens": {
                "primary_color": "#fff; background: url(https://example.com/x)",
                "font_family": "Arial; @import url(https://example.com/x.css)",
            },
        },
        html_output_path=output,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    assert not output.exists()
    assert not output.with_suffix(".html-manifest.json").exists()


def test_write_authoring_html_package_rejects_bad_page_document_payload(tmp_path: Path) -> None:
    result = write_authoring_html_package(
        page_document={"page_document_id": "pages_bad", "page_count": 2, "pages": []},
        html_output_path=tmp_path / "deck.html",
    )

    assert result.status == "failed"
    assert result.tool == "pdf.create.html_package"
    assert result.error is not None
    assert result.error.code == "authoring_invalid_page_document"
    assert result.error.details["payload"] == "page_document"
