import json
from pathlib import Path

from agentpdf.authoring.html_deck import write_authoring_html_package
from agentpdf.authoring.models import DesignTokens, PageDocument, PageSpec


def _page_document() -> PageDocument:
    return PageDocument(
        page_document_id="pages_html_test",
        page_count=2,
        pages=[
            PageSpec(
                page_number=1,
                layout="cover",
                title="AgentPDF Authoring",
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
                                "source_title": "AgentPDF Spec",
                            }
                        ],
                    },
                ],
                source_footer="Sources: AgentPDF Spec",
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
        title="AgentPDF Authoring",
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
    assert 'data-agentpdf-authoring-document' in html
    assert 'data-page-number="1"' in html
    assert "AgentPDF Authoring" in html
    assert "Sources: AgentPDF Spec" in html
    assert any(str(artifact.path) == str(output.resolve()) for artifact in result.artifacts)


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
