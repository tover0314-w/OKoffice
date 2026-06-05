from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from typer.testing import CliRunner

from okoffice.api.app import create_app
from okoffice.cli.main import app
from okoffice.compose.blocks import (
    add_appendix_to_pdf,
    add_citation_to_pdf,
    add_code_block_to_pdf,
    add_figure_to_pdf,
    add_media_reference_to_pdf,
    add_slide_to_pdf,
    add_table_to_pdf,
)
from okoffice.core.pdf import create_text_pdf
from okoffice.mcp.server import (
    pdf_compose_add_citation,
    pdf_compose_add_code_block,
    pdf_compose_add_media_reference,
    pdf_compose_add_slide,
)
from okoffice.tools.registry import get_tool


runner = CliRunner()


def test_compose_block_tools_append_evidence_pages_and_keep_input_unchanged(tmp_path: Path) -> None:
    base_pdf = tmp_path / "base.pdf"
    create_text_pdf("Base PDF for agent composition.", base_pdf, title="Base")
    original_hash = _sha256(base_pdf)
    original_pages = _page_count(base_pdf)
    image_path = tmp_path / "diagram.png"
    Image.new("RGB", (96, 48), color=(31, 58, 95)).save(image_path)

    code_result = add_code_block_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-code.pdf",
        title="Risk Function",
        code="def risky_total(items):\n    return sum(items)\n",
        language="python",
        source_refs=["ctx_code"],
        block_id="blk_code",
        target_slot="code_review",
    )
    table_result = add_table_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-table.pdf",
        title="Runtime Metrics",
        columns=["metric", "value"],
        rows=[["latency_ms", "42"], ["error_rate", "0.01"]],
        source_refs=["ctx_metrics"],
        block_id="blk_metrics",
        target_slot="evidence_table",
    )
    figure_result = add_figure_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-figure.pdf",
        title="Architecture Figure",
        image_path=image_path,
        caption="Local visual evidence rendered into the composed PDF.",
        source_refs=["ctx_image"],
        block_id="blk_image",
        target_slot="visual_evidence",
    )
    appendix_result = add_appendix_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-appendix.pdf",
        title="Source Appendix",
        markdown="## Source Notes\n\n- Keep source refs explicit.\n- Validate every generated PDF.",
        source_refs=["ctx_code", "ctx_metrics", "ctx_image"],
        block_id="blk_appendix",
        target_slot="source_appendix",
    )

    for result, block_type, output_name, operation in [
        (code_result, "code", "with-code.pdf", "append_code_block"),
        (table_result, "table", "with-table.pdf", "append_table"),
        (figure_result, "image", "with-figure.pdf", "append_image"),
        (appendix_result, "appendix", "with-appendix.pdf", "append_markdown"),
    ]:
        assert result.status == "succeeded"
        assert result.tool.startswith("pdf.compose.add_")
        assert result.validation is not None
        assert result.validation.status == "passed"
        assert result.artifacts[0].path.name == output_name
        assert result.usage["compose_block"]["block_type"] == block_type
        assert result.usage["compose_block"]["operation"]["op"] == operation
        assert result.usage["verification"]["page_count_delta"] == 1
        assert result.usage["input_unchanged"] is True
        assert _page_count(tmp_path / output_name) == original_pages + 1
        assert (tmp_path / output_name).with_suffix(".compose-block.json").exists()

    assert _sha256(base_pdf) == original_hash


def test_compose_add_citation_appends_traceable_citation_page(tmp_path: Path) -> None:
    base_pdf = tmp_path / "base.pdf"
    create_text_pdf("Base PDF for citation composition.", base_pdf, title="Base")
    original_hash = _sha256(base_pdf)
    original_pages = _page_count(base_pdf)

    result = add_citation_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-citation.pdf",
        title="Source Citation",
        quote="OKoffice keeps citation source refs auditable.",
        source="https://example.com/research?ref=agent#evidence",
        page="section 2",
        source_refs=["ctx_web"],
        block_id="blk_citation",
        target_slot="citations",
    )

    manifest_path = tmp_path / "with-citation.compose-block.json"
    patch_path = tmp_path / "with-citation.compose-block.patch.json"
    text = "\n".join(page.extract_text() or "" for page in PdfReader(tmp_path / "with-citation.pdf").pages)

    assert result.status == "succeeded"
    assert result.tool == "pdf.compose.add_citation"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.artifacts[0].path.name == "with-citation.pdf"
    assert result.usage["compose_block"]["block_type"] == "citation"
    assert result.usage["compose_block"]["source_refs"] == ["ctx_web"]
    assert result.usage["compose_block"]["operation"]["op"] == "append_citation"
    assert result.usage["compose_block"]["operation"]["quote"].startswith("OKoffice keeps")
    assert result.usage["compose_block"]["operation"]["source"] == "https://example.com/research?ref=agent#evidence"
    assert result.usage["compose_block"]["operation"]["page"] == "section 2"
    assert result.usage["compose_block"]["operation"]["citation_evidence"]["domain"] == "example.com"
    assert result.usage["compose_block"]["operation"]["citation_evidence"]["fetch_status"] == "not_fetched"
    assert result.usage["verification"]["page_count_delta"] == 1
    assert result.usage["input_unchanged"] is True
    assert _page_count(tmp_path / "with-citation.pdf") == original_pages + 1
    assert _sha256(base_pdf) == original_hash
    assert manifest_path.exists()
    assert patch_path.exists()
    assert "Source Citation" in text
    assert "OKoffice keeps citation source refs auditable." in text
    assert "https://example.com/research?ref=agent#evidence" in text


def test_compose_add_media_reference_appends_traceable_media_page(tmp_path: Path) -> None:
    base_pdf = tmp_path / "base.pdf"
    media_path = tmp_path / "meeting.mp3"
    create_text_pdf("Base PDF for media reference composition.", base_pdf, title="Base")
    media_path.write_bytes(b"ID3\x04\x00\x00\x00\x00\x00\x21okoffice local media fixture")
    original_hash = _sha256(base_pdf)
    original_pages = _page_count(base_pdf)
    media_hash = _sha256(media_path)

    result = add_media_reference_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-media.pdf",
        title="Meeting Audio",
        media_path=media_path,
        media_kind="audio",
        transcript_excerpt="00:00 Kickoff\n00:12 Decision: keep provenance explicit.",
        duration_seconds=42.5,
        chapter_count=1,
        source_refs=["ctx_audio"],
        block_id="blk_audio",
        target_slot="media_evidence",
    )

    manifest_path = tmp_path / "with-media.compose-block.json"
    patch_path = tmp_path / "with-media.compose-block.patch.json"
    operation = result.usage["compose_block"]["operation"]
    evidence = operation["media_evidence"]
    text = "\n".join(page.extract_text() or "" for page in PdfReader(tmp_path / "with-media.pdf").pages)

    assert result.status == "succeeded"
    assert result.tool == "pdf.compose.add_media_reference"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.artifacts[0].path.name == "with-media.pdf"
    assert result.usage["compose_block"]["block_type"] == "audio_reference"
    assert result.usage["compose_block"]["source_refs"] == ["ctx_audio"]
    assert operation["op"] == "append_media_reference"
    assert operation["media_kind"] == "audio"
    assert operation["media_path"].endswith("meeting.mp3")
    assert operation["transcript_excerpt"].startswith("00:00 Kickoff")
    assert operation["duration_seconds"] == 42.5
    assert operation["chapter_count"] == 1
    assert evidence["exists"] is True
    assert evidence["filename"] == "meeting.mp3"
    assert evidence["mime_type"] == "audio/mpeg"
    assert evidence["sha256"] == media_hash
    assert evidence["analysis_method"] == "local_media_reference_metadata_v0"
    assert result.usage["verification"]["page_count_delta"] == 1
    assert result.usage["input_unchanged"] is True
    assert _page_count(tmp_path / "with-media.pdf") == original_pages + 1
    assert _sha256(base_pdf) == original_hash
    assert manifest_path.exists()
    assert patch_path.exists()
    assert "Meeting Audio" in text
    assert "meeting.mp3" in text
    assert "00:12 Decision: keep provenance explicit." in text


def test_compose_add_slide_appends_traceable_slide_page(tmp_path: Path) -> None:
    base_pdf = tmp_path / "base.pdf"
    create_text_pdf("Base PDF for slide composition.", base_pdf, title="Base")
    original_hash = _sha256(base_pdf)
    original_pages = _page_count(base_pdf)

    result = add_slide_to_pdf(
        base_pdf,
        output_path=tmp_path / "with-slide.pdf",
        title="Agent Review Slide",
        subtitle="Decision evidence",
        body=[
            "Patch transactions can append slide-like evidence pages.",
            "Input PDFs are never mutated.",
        ],
        code="risk_score = 42",
        source_refs=["ctx_slide"],
        block_id="blk_slide",
        target_slot="evidence_slide",
    )

    manifest_path = tmp_path / "with-slide.compose-block.json"
    patch_path = tmp_path / "with-slide.compose-block.patch.json"
    operation = result.usage["compose_block"]["operation"]
    text = "\n".join(page.extract_text() or "" for page in PdfReader(tmp_path / "with-slide.pdf").pages)

    assert result.status == "succeeded"
    assert result.tool == "pdf.compose.add_slide"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.artifacts[0].path.name == "with-slide.pdf"
    assert result.usage["compose_block"]["block_type"] == "slide"
    assert result.usage["compose_block"]["source_refs"] == ["ctx_slide"]
    assert operation["op"] == "append_slide"
    assert operation["subtitle"] == "Decision evidence"
    assert operation["body"] == [
        "Patch transactions can append slide-like evidence pages.",
        "Input PDFs are never mutated.",
    ]
    assert operation["code"] == "risk_score = 42"
    assert result.usage["verification"]["page_count_delta"] == 1
    assert result.usage["input_unchanged"] is True
    assert _page_count(tmp_path / "with-slide.pdf") == original_pages + 1
    assert _sha256(base_pdf) == original_hash
    assert manifest_path.exists()
    assert patch_path.exists()
    assert "Agent Review Slide" in text
    assert "Patch transactions can append slide-like evidence pages." in text
    assert "risk_score = 42" in text


def test_compose_block_cli_api_mcp_and_registry_are_exposed(tmp_path: Path) -> None:
    base_pdf = tmp_path / "base.pdf"
    media_path = tmp_path / "clip.mp4"
    create_text_pdf("Base PDF for compose block surfaces.", base_pdf, title="Base")
    media_path.write_bytes(b"\x00\x00\x00\x18ftypmp42okoffice local media fixture")

    tool = get_tool("pdf.compose.add_code_block")
    assert tool.implemented is True
    citation_tool = get_tool("pdf.compose.add_citation")
    assert citation_tool.implemented is True
    media_tool = get_tool("pdf.compose.add_media_reference")
    assert media_tool.implemented is True
    slide_tool = get_tool("pdf.compose.add_slide")
    assert slide_tool.implemented is True

    cli = runner.invoke(
        app,
        [
            "compose",
            "add-code-block",
            str(base_pdf),
            "--title",
            "CLI Risk Function",
            "--code",
            "def cli_total(items):\n    return sum(items)\n",
            "--language",
            "python",
            "--source-ref",
            "ctx_cli_code",
            "--block-id",
            "blk_cli_code",
            "--target-slot",
            "code_review",
            "-o",
            str(tmp_path / "cli-code.pdf"),
            "--json",
        ],
    )

    assert cli.exit_code == 0
    cli_payload = json.loads(cli.stdout)
    assert cli_payload["tool"] == "pdf.compose.add_code_block"
    assert cli_payload["usage"]["compose_block"]["source_refs"] == ["ctx_cli_code"]
    assert cli_payload["usage"]["verification"]["page_count_delta"] == 1

    cli_citation = runner.invoke(
        app,
        [
            "compose",
            "add-citation",
            str(base_pdf),
            "--title",
            "CLI Citation",
            "--quote",
            "CLI route keeps source refs.",
            "--source",
            "https://example.com/cli",
            "--page",
            "C1",
            "--source-ref",
            "ctx_cli_citation",
            "--block-id",
            "blk_cli_citation",
            "--target-slot",
            "citations",
            "-o",
            str(tmp_path / "cli-citation.pdf"),
            "--json",
        ],
    )

    assert cli_citation.exit_code == 0
    cli_citation_payload = json.loads(cli_citation.stdout)
    assert cli_citation_payload["tool"] == "pdf.compose.add_citation"
    assert cli_citation_payload["usage"]["compose_block"]["source_refs"] == ["ctx_cli_citation"]
    assert cli_citation_payload["usage"]["verification"]["page_count_delta"] == 1

    cli_media = runner.invoke(
        app,
        [
            "compose",
            "add-media-reference",
            str(base_pdf),
            "--title",
            "CLI Media",
            "--media",
            str(media_path),
            "--media-kind",
            "video",
            "--transcript-excerpt",
            "00:00 visual evidence frame.",
            "--duration-seconds",
            "12.75",
            "--keyframe-count",
            "1",
            "--source-ref",
            "ctx_cli_media",
            "--block-id",
            "blk_cli_media",
            "--target-slot",
            "media_evidence",
            "-o",
            str(tmp_path / "cli-media.pdf"),
            "--json",
        ],
    )

    assert cli_media.exit_code == 0
    cli_media_payload = json.loads(cli_media.stdout)
    assert cli_media_payload["tool"] == "pdf.compose.add_media_reference"
    assert cli_media_payload["usage"]["compose_block"]["block_type"] == "video_reference"
    assert cli_media_payload["usage"]["compose_block"]["source_refs"] == ["ctx_cli_media"]
    assert cli_media_payload["usage"]["compose_block"]["operation"]["duration_seconds"] == 12.75
    assert cli_media_payload["usage"]["verification"]["page_count_delta"] == 1

    cli_slide = runner.invoke(
        app,
        [
            "compose",
            "add-slide",
            str(base_pdf),
            "--title",
            "CLI Slide",
            "--subtitle",
            "CLI evidence",
            "--body",
            "First CLI slide bullet.",
            "--body",
            "Second CLI slide bullet.",
            "--code",
            "cli_score = 42",
            "--source-ref",
            "ctx_cli_slide",
            "--block-id",
            "blk_cli_slide",
            "--target-slot",
            "evidence_slide",
            "-o",
            str(tmp_path / "cli-slide.pdf"),
            "--json",
        ],
    )

    assert cli_slide.exit_code == 0
    cli_slide_payload = json.loads(cli_slide.stdout)
    assert cli_slide_payload["tool"] == "pdf.compose.add_slide"
    assert cli_slide_payload["usage"]["compose_block"]["block_type"] == "slide"
    assert cli_slide_payload["usage"]["compose_block"]["source_refs"] == ["ctx_cli_slide"]
    assert cli_slide_payload["usage"]["compose_block"]["operation"]["body"] == [
        "First CLI slide bullet.",
        "Second CLI slide bullet.",
    ]
    assert cli_slide_payload["usage"]["verification"]["page_count_delta"] == 1

    api = TestClient(create_app())
    api_result = api.post(
        "/v1/tools/pdf.compose.add_code_block/run",
        json={
            "input_path": str(base_pdf),
            "output_path": str(tmp_path / "api-code.pdf"),
            "title": "API Risk Function",
            "code": "def api_total(items):\n    return sum(items)\n",
            "language": "python",
            "source_refs": ["ctx_api_code"],
            "block_id": "blk_api_code",
            "target_slot": "code_review",
        },
    )

    assert api_result.status_code == 200
    assert api_result.json()["tool"] == "pdf.compose.add_code_block"
    assert api_result.json()["usage"]["compose_block"]["source_refs"] == ["ctx_api_code"]
    assert api_result.json()["usage"]["verification"]["page_count_delta"] == 1

    api_citation_result = api.post(
        "/v1/tools/pdf.compose.add_citation/run",
        json={
            "input_path": str(base_pdf),
            "output_path": str(tmp_path / "api-citation.pdf"),
            "title": "API Citation",
            "quote": "API route keeps source refs.",
            "source": "https://example.com/api",
            "page": "A1",
            "source_refs": ["ctx_api_citation"],
            "block_id": "blk_api_citation",
            "target_slot": "citations",
        },
    )

    assert api_citation_result.status_code == 200
    assert api_citation_result.json()["tool"] == "pdf.compose.add_citation"
    assert api_citation_result.json()["usage"]["compose_block"]["source_refs"] == ["ctx_api_citation"]
    assert api_citation_result.json()["usage"]["verification"]["page_count_delta"] == 1

    api_media_result = api.post(
        "/v1/tools/pdf.compose.add_media_reference/run",
        json={
            "input_path": str(base_pdf),
            "output_path": str(tmp_path / "api-media.pdf"),
            "title": "API Media",
            "media_path": str(media_path),
            "media_kind": "video",
            "transcript_excerpt": "00:01 API evidence frame.",
            "duration_seconds": 13.5,
            "keyframe_count": 1,
            "source_refs": ["ctx_api_media"],
            "block_id": "blk_api_media",
            "target_slot": "media_evidence",
        },
    )

    assert api_media_result.status_code == 200
    assert api_media_result.json()["tool"] == "pdf.compose.add_media_reference"
    assert api_media_result.json()["usage"]["compose_block"]["block_type"] == "video_reference"
    assert api_media_result.json()["usage"]["compose_block"]["source_refs"] == ["ctx_api_media"]
    assert api_media_result.json()["usage"]["verification"]["page_count_delta"] == 1

    api_slide_result = api.post(
        "/v1/tools/pdf.compose.add_slide/run",
        json={
            "input_path": str(base_pdf),
            "output_path": str(tmp_path / "api-slide.pdf"),
            "title": "API Slide",
            "subtitle": "API evidence",
            "body": ["API slide bullet."],
            "code": "api_score = 42",
            "source_refs": ["ctx_api_slide"],
            "block_id": "blk_api_slide",
            "target_slot": "evidence_slide",
        },
    )

    assert api_slide_result.status_code == 200
    assert api_slide_result.json()["tool"] == "pdf.compose.add_slide"
    assert api_slide_result.json()["usage"]["compose_block"]["block_type"] == "slide"
    assert api_slide_result.json()["usage"]["compose_block"]["source_refs"] == ["ctx_api_slide"]
    assert api_slide_result.json()["usage"]["verification"]["page_count_delta"] == 1

    mcp_payload = json.loads(
        pdf_compose_add_code_block(
            str(base_pdf),
            output_path=str(tmp_path / "mcp-code.pdf"),
            title="MCP Risk Function",
            code="def mcp_total(items):\n    return sum(items)\n",
            language="python",
            source_refs=["ctx_mcp_code"],
            block_id="blk_mcp_code",
            target_slot="code_review",
        )
    )

    assert mcp_payload["tool"] == "pdf.compose.add_code_block"
    assert mcp_payload["usage"]["compose_block"]["source_refs"] == ["ctx_mcp_code"]
    assert mcp_payload["usage"]["verification"]["page_count_delta"] == 1

    mcp_citation_payload = json.loads(
        pdf_compose_add_citation(
            str(base_pdf),
            output_path=str(tmp_path / "mcp-citation.pdf"),
            title="MCP Citation",
            quote="MCP route keeps source refs.",
            source="https://example.com/mcp",
            page="M1",
            source_refs=["ctx_mcp_citation"],
            block_id="blk_mcp_citation",
            target_slot="citations",
        )
    )

    assert mcp_citation_payload["tool"] == "pdf.compose.add_citation"
    assert mcp_citation_payload["usage"]["compose_block"]["source_refs"] == ["ctx_mcp_citation"]
    assert mcp_citation_payload["usage"]["verification"]["page_count_delta"] == 1

    mcp_media_payload = json.loads(
        pdf_compose_add_media_reference(
            str(base_pdf),
            output_path=str(tmp_path / "mcp-media.pdf"),
            title="MCP Media",
            media_path=str(media_path),
            media_kind="video",
            transcript_excerpt="00:02 MCP evidence frame.",
            duration_seconds=14.25,
            keyframe_count=1,
            source_refs=["ctx_mcp_media"],
            block_id="blk_mcp_media",
            target_slot="media_evidence",
        )
    )

    assert mcp_media_payload["tool"] == "pdf.compose.add_media_reference"
    assert mcp_media_payload["usage"]["compose_block"]["block_type"] == "video_reference"
    assert mcp_media_payload["usage"]["compose_block"]["source_refs"] == ["ctx_mcp_media"]
    assert mcp_media_payload["usage"]["verification"]["page_count_delta"] == 1

    mcp_slide_payload = json.loads(
        pdf_compose_add_slide(
            str(base_pdf),
            output_path=str(tmp_path / "mcp-slide.pdf"),
            title="MCP Slide",
            subtitle="MCP evidence",
            body=["MCP slide bullet."],
            code="mcp_score = 42",
            source_refs=["ctx_mcp_slide"],
            block_id="blk_mcp_slide",
            target_slot="evidence_slide",
        )
    )

    assert mcp_slide_payload["tool"] == "pdf.compose.add_slide"
    assert mcp_slide_payload["usage"]["compose_block"]["block_type"] == "slide"
    assert mcp_slide_payload["usage"]["compose_block"]["source_refs"] == ["ctx_mcp_slide"]
    assert mcp_slide_payload["usage"]["verification"]["page_count_delta"] == 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _page_count(path: Path) -> int:
    return len(PdfReader(path).pages)
