import hashlib
import importlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.context.packet import (
    build_reusable_context_packet,
    create_code_snapshot,
    ingest_context_item,
    profile_data_source,
)
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.mcp.server import (
    pdf_context_code_snapshot,
    pdf_context_data_profile,
    pdf_context_ingest,
    pdf_context_packet,
)
from agentpdf.tools.registry import get_tool


runner = CliRunner()


def test_context_ingest_normalizes_single_code_item_and_writes_artifact(tmp_path: Path) -> None:
    source = tmp_path / "risk.ts"
    source.write_text(
        "\n".join(
            [
                "export function scoreRisk(value: number) {",
                "  return value * 2;",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    item_path = tmp_path / "risk.context-item.json"

    result = ingest_context_item(
        {
            "path": str(source),
            "role": "code_evidence",
            "label": "Risk Scoring Source",
        },
        output_path=item_path,
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.ingest"
    assert result.artifacts[0].source_tool == "pdf.context.ingest"
    assert result.usage["item_type"] == "code"
    assert result.usage["source_ref"] == "ctx_001"
    assert result.usage["context_item"]["metadata"]["code_evidence"]["language"] == "typescript"
    assert result.usage["context_item"]["metadata"]["code_evidence"]["symbol_count"] == 1
    assert result.usage["source_graph_node"]["evidence"]["code_evidence"]["code_hash"]
    assert "pdf.context.packet" in result.next_recommended_tools

    written = json.loads(item_path.read_text(encoding="utf-8"))
    assert written["context_item"]["context_item_id"] == "ctx_001"
    assert written["context_item"]["source_ref"] == "ctx_001"
    assert written["source_graph_node"]["type"] == "code"


def test_context_packet_accepts_preingested_items_and_validates_schema(tmp_path: Path) -> None:
    code = tmp_path / "service.py"
    code.write_text("def score(value):\n    return value * 2\n", encoding="utf-8")
    packet_path = tmp_path / "agent.packet.json"

    ingested = ingest_context_item(
        {"path": str(code), "role": "code_evidence", "label": "Scoring Code"}
    ).usage["context_item"]

    result = build_reusable_context_packet(
        [
            ingested,
            {
                "url": "https://okpdf.dev/docs/context",
                "role": "citation",
                "label": "Context Docs",
                "snippet": "Source refs and packet evidence for PDF agents.",
            },
        ],
        output_path=packet_path,
        title="Agent Packet",
        intent="Combine pre-ingested and raw agent context.",
    )

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.packet"
    assert result.artifacts[0].source_tool == "pdf.context.packet"
    assert result.usage["item_count"] == 2
    assert result.usage["item_types"] == ["code", "web_link"]
    assert result.usage["context_packet"]["items"][0]["source_ref"] == ingested["source_ref"]
    assert result.usage["context_packet"]["items"][1]["metadata"]["citation_evidence"]["fetch_status"] == "not_fetched"
    assert "pdf.compose.from_context" in result.next_recommended_tools

    schema = json.loads(Path("schemas/context-packet.schema.json").read_text(encoding="utf-8"))
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []


def test_context_web_link_normalizes_bare_domain_without_fetching() -> None:
    result = ingest_context_item(
        {
            "url": "OKPDF.dev/docs/context?ref=agent#source",
            "label": "Context Docs",
            "snippet": "Traceable PDF context packets for agents.",
        }
    )
    item = result.usage["context_item"]
    citation = item["metadata"]["citation_evidence"]

    assert item["type"] == "web_link"
    assert item["uri"] == "https://okpdf.dev/docs/context?ref=agent#source"
    assert citation["normalized_url"] == "https://okpdf.dev/docs/context?ref=agent#source"
    assert citation["domain"] == "okpdf.dev"
    assert citation["fetch_status"] == "not_fetched"
    assert citation["analysis_method"] == "local_url_metadata_v0"
    assert result.usage["source_graph_node"]["evidence"]["citation_evidence"]["domain"] == "okpdf.dev"


def test_context_web_link_rejects_unsafe_schemes() -> None:
    for url in ("javascript:alert(1)", "file:///etc/passwd", "ftp://example.com/source"):
        try:
            ingest_context_item({"url": url, "label": "Unsafe link"})
        except AgentPDFException as exc:
            assert exc.code == "unsafe_input_rejected"
        else:  # pragma: no cover - defensive assertion for clearer test failures
            raise AssertionError(f"Expected unsafe_input_rejected for {url}")


def test_context_web_capture_fetches_html_into_auditable_context_item(tmp_path: Path, monkeypatch) -> None:
    context_web = importlib.import_module("agentpdf.context.web")
    html = (
        b"<!doctype html><html><head><title>AgentPDF Context</title></head>"
        b"<body><h1>AgentPDF Context</h1><p>Traceable web evidence for target PDFs.</p></body></html>"
    )

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}
        url = "https://okpdf.dev/docs/context"

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return html[:size] if size >= 0 else html

    monkeypatch.setattr(context_web, "urlopen", lambda request, timeout: FakeResponse())
    monkeypatch.setattr(context_web, "_validate_public_url_host", lambda hostname, allow_private_hosts: None)

    result = context_web.capture_web_context(
        "OKPDF.dev/docs/context",
        output_path=tmp_path / "context-web.json",
        label="Context Docs",
        role="citation",
        context_item_id="ctx_web",
        max_bytes=4096,
    )
    item = result.usage["context_item"]
    evidence = item["metadata"]["citation_evidence"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.web_capture"
    assert result.artifacts[0].source_tool == "pdf.context.web_capture"
    assert item["type"] == "web_link"
    assert item["context_item_id"] == "ctx_web"
    assert item["uri"] == "https://okpdf.dev/docs/context"
    assert "Traceable web evidence" in item["content"]["text"]
    assert evidence["fetch_status"] == "fetched"
    assert evidence["status_code"] == 200
    assert evidence["content_type"] == "text/html; charset=utf-8"
    assert evidence["sha256"] == hashlib.sha256(html).hexdigest()
    assert evidence["bytes_read"] == len(html)
    assert evidence["max_bytes"] == 4096
    assert evidence["ssrf_policy"]["allow_private_hosts"] is False
    assert evidence["analysis_method"] == "local_http_fetch_text_v0"
    assert result.usage["source_graph_node"]["evidence"]["citation_evidence"]["fetch_status"] == "fetched"


def test_context_web_capture_is_exposed_to_cli_rest_mcp_and_registry(tmp_path: Path, monkeypatch) -> None:
    context_web = importlib.import_module("agentpdf.context.web")
    mcp_server = importlib.import_module("agentpdf.mcp.server")
    html = b"<html><body><h1>AgentPDF Web Capture</h1><p>Captured for context packets.</p></body></html>"

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "text/html"}
        url = "https://okpdf.dev/docs/context"

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return html[:size] if size >= 0 else html

    monkeypatch.setattr(context_web, "urlopen", lambda request, timeout: FakeResponse())
    monkeypatch.setattr(context_web, "_validate_public_url_host", lambda hostname, allow_private_hosts: None)

    cli_output = tmp_path / "cli-web.context-item.json"
    cli_result = runner.invoke(
        app,
        [
            "context",
            "web-capture",
            "OKPDF.dev/docs/context",
            "--label",
            "CLI Web Capture",
            "--context-item-id",
            "ctx_cli_web",
            "-o",
            str(cli_output),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.context.web_capture/run",
        json={
            "url": "OKPDF.dev/docs/context",
            "label": "API Web Capture",
            "context_item_id": "ctx_api_web",
            "output_path": str(tmp_path / "api-web.context-item.json"),
        },
    )
    mcp_result = json.loads(
        mcp_server.pdf_context_web_capture(
            "OKPDF.dev/docs/context",
            output_path=str(tmp_path / "mcp-web.context-item.json"),
            label="MCP Web Capture",
            context_item_id="ctx_mcp_web",
        )
    )

    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["tool"] == "pdf.context.web_capture"
    assert cli_output.exists()
    assert api_response.status_code == 200
    assert api_response.json()["usage"]["context_item"]["context_item_id"] == "ctx_api_web"
    assert mcp_result["usage"]["context_item"]["metadata"]["citation_evidence"]["fetch_status"] == "fetched"
    assert get_tool("pdf.context.web_capture").implemented is True


def test_context_web_capture_validates_final_redirect_host(monkeypatch) -> None:
    context_web = importlib.import_module("agentpdf.context.web")
    html = b"<html><body><p>Redirected content</p></body></html>"
    checked_hosts: list[str | None] = []

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "text/html"}
        url = "https://cdn.okpdf.dev/context"

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return html[:size] if size >= 0 else html

    def record_host(hostname: str | None, allow_private_hosts: bool) -> None:
        checked_hosts.append(hostname)

    monkeypatch.setattr(context_web, "urlopen", lambda request, timeout: FakeResponse())
    monkeypatch.setattr(context_web, "_validate_public_url_host", record_host)

    result = context_web.capture_web_context("okpdf.dev/docs/context")

    assert result.status == "succeeded"
    assert checked_hosts == ["okpdf.dev", "cdn.okpdf.dev"]
    assert result.usage["web_capture"]["final_url"] == "https://cdn.okpdf.dev/context"


def test_context_ingest_extracts_docx_text_evidence_for_packets(tmp_path: Path) -> None:
    docx_path = tmp_path / "field-notes.docx"
    _write_minimal_docx(
        docx_path,
        [
            "DOCX Field Notes",
            "Margin pressure is the largest risk.",
        ],
    )
    item_path = tmp_path / "field-notes.context-item.json"
    packet_path = tmp_path / "field-notes.packet.json"

    ingested = ingest_context_item(
        {
            "path": str(docx_path),
            "role": "source_document",
            "label": "Field Notes",
        },
        output_path=item_path,
    )
    item = ingested.usage["context_item"]
    packet = build_reusable_context_packet(
        [item],
        output_path=packet_path,
        title="DOCX Packet",
        intent="Compose a target PDF from Office document context.",
    )

    assert ingested.status == "succeeded"
    assert ingested.usage["item_type"] == "document"
    assert item["content"]["text"] == "DOCX Field Notes\nMargin pressure is the largest risk."
    assert item["metadata"]["document_evidence"]["format"] == "docx"
    assert item["metadata"]["document_evidence"]["paragraph_count"] == 2
    assert item["metadata"]["document_evidence"]["analysis_method"] == "local_docx_xml_text_v0"
    assert item["metadata"]["char_count"] == len(item["content"]["text"])
    assert "PK" not in item["content"]["text"]
    assert ingested.usage["source_graph_node"]["evidence"]["document_evidence"]["paragraph_count"] == 2
    assert item_path.exists()
    assert packet.status == "succeeded"
    assert packet.usage["context_packet"]["items"][0]["content"]["text"].startswith("DOCX Field Notes")
    assert packet.usage["source_graph"]["nodes"][0]["evidence"]["document_evidence"]["format"] == "docx"
    assert packet_path.exists()


def test_context_code_snapshot_creates_range_evidence_and_interfaces(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text(
        "\n".join(
            [
                "import math",
                "def score(value):",
                "    return math.ceil(value * 2)",
                "",
                "class RiskModel:",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )
    snapshot_path = tmp_path / "service.snapshot.json"
    cli_snapshot_path = tmp_path / "service.cli.snapshot.json"
    mcp_snapshot_path = tmp_path / "service.mcp.snapshot.json"

    result = create_code_snapshot(
        source,
        output_path=snapshot_path,
        label="Scoring Function",
        role="code_evidence",
        line_start=2,
        line_end=3,
        repository_root=tmp_path,
    )
    item = result.usage["context_item"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.code_snapshot"
    assert result.artifacts[0].source_tool == "pdf.context.code_snapshot"
    assert item["type"] == "code"
    assert item["content"]["code"]["text"] == "def score(value):\n    return math.ceil(value * 2)"
    assert item["metadata"]["code_evidence"]["symbol_count"] == 1
    assert item["metadata"]["code_snapshot_evidence"]["line_start"] == 2
    assert item["metadata"]["code_snapshot_evidence"]["line_end"] == 3
    assert item["metadata"]["code_snapshot_evidence"]["file_line_count"] == 6
    assert item["metadata"]["code_snapshot_evidence"]["repository_relative_path"] == "service.py"
    assert result.usage["source_graph_node"]["evidence"]["code_snapshot_evidence"]["selected_line_count"] == 2
    assert "pdf.compose.add_code_block" in result.next_recommended_tools
    assert snapshot_path.exists()

    cli_result = runner.invoke(
        app,
        [
            "context",
            "code-snapshot",
            str(source),
            "--line-start",
            "2",
            "--line-end",
            "3",
            "--repository-root",
            str(tmp_path),
            "-o",
            str(cli_snapshot_path),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.context.code_snapshot/run",
        json={
            "path": str(source),
            "output_path": str(tmp_path / "service.api.snapshot.json"),
            "line_start": 2,
            "line_end": 3,
            "repository_root": str(tmp_path),
        },
    )
    mcp_result = json.loads(
        pdf_context_code_snapshot(
            str(source),
            output_path=str(mcp_snapshot_path),
            line_start=2,
            line_end=3,
            repository_root=str(tmp_path),
        )
    )

    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["tool"] == "pdf.context.code_snapshot"
    assert cli_snapshot_path.exists()
    assert api_response.status_code == 200
    assert api_response.json()["tool"] == "pdf.context.code_snapshot"
    assert mcp_result["tool"] == "pdf.context.code_snapshot"
    assert mcp_snapshot_path.exists()
    assert get_tool("pdf.context.code_snapshot").implemented is True


def test_context_data_profile_profiles_csv_and_interfaces(tmp_path: Path) -> None:
    source = tmp_path / "metrics.csv"
    source.write_text("metric,value\nlatency_ms,42\nerror_rate,0.01\n", encoding="utf-8")
    profile_path = tmp_path / "metrics.profile.json"
    cli_profile_path = tmp_path / "metrics.cli.profile.json"
    mcp_profile_path = tmp_path / "metrics.mcp.profile.json"

    result = profile_data_source(
        source,
        output_path=profile_path,
        label="Runtime Metrics",
        role="data_evidence",
    )
    item = result.usage["context_item"]

    assert result.status == "succeeded"
    assert result.tool == "pdf.context.data_profile"
    assert result.artifacts[0].source_tool == "pdf.context.data_profile"
    assert item["type"] == "data"
    assert item["content"]["table"]["columns"] == ["metric", "value"]
    assert item["metadata"]["table_evidence"]["row_count"] == 2
    assert item["metadata"]["table_evidence"]["column_types"] == {"metric": "string", "value": "number"}
    assert item["metadata"]["data_profile_evidence"]["format"] == "csv"
    assert item["metadata"]["data_profile_evidence"]["has_table"] is True
    assert result.usage["source_graph_node"]["evidence"]["data_profile_evidence"]["row_count"] == 2
    assert "pdf.compose.add_table" in result.next_recommended_tools
    assert profile_path.exists()

    cli_result = runner.invoke(
        app,
        [
            "context",
            "data-profile",
            str(source),
            "--label",
            "CLI Metrics",
            "-o",
            str(cli_profile_path),
            "--json",
        ],
    )
    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.context.data_profile/run",
        json={
            "path": str(source),
            "output_path": str(tmp_path / "metrics.api.profile.json"),
            "label": "API Metrics",
        },
    )
    mcp_result = json.loads(
        pdf_context_data_profile(
            str(source),
            output_path=str(mcp_profile_path),
            label="MCP Metrics",
        )
    )

    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["tool"] == "pdf.context.data_profile"
    assert cli_profile_path.exists()
    assert api_response.status_code == 200
    assert api_response.json()["tool"] == "pdf.context.data_profile"
    assert mcp_result["tool"] == "pdf.context.data_profile"
    assert mcp_profile_path.exists()
    assert get_tool("pdf.context.data_profile").implemented is True


def test_context_data_profile_extracts_xlsx_sheet_table(tmp_path: Path) -> None:
    source = tmp_path / "metrics.xlsx"
    _write_minimal_xlsx(
        source,
        [
            ["metric", "value"],
            ["latency_ms", "42"],
            ["error_rate", "0.01"],
        ],
    )

    result = profile_data_source(source, label="Workbook Metrics")
    item = result.usage["context_item"]

    assert item["content"]["table"]["columns"] == ["metric", "value"]
    assert item["content"]["table"]["rows"] == [["latency_ms", "42"], ["error_rate", "0.01"]]
    assert item["metadata"]["data_profile_evidence"]["format"] == "xlsx"
    assert item["metadata"]["data_profile_evidence"]["sheet_name"] == "Sheet1"
    assert item["metadata"]["data_profile_evidence"]["sheet_count"] == 1
    assert item["metadata"]["data_profile_evidence"]["analysis_method"] == "local_xlsx_sheet_profile_v0"
    assert "PK" not in item["content"]["text"]


def test_context_ingest_and_packet_are_exposed_to_cli_rest_mcp_and_registry(tmp_path: Path) -> None:
    source = tmp_path / "notes.md"
    source.write_text("# Notes\n\nKeep context provenance explicit.\n", encoding="utf-8")
    item_path = tmp_path / "notes.context-item.json"
    packet_path = tmp_path / "notes.packet.json"
    api_item = tmp_path / "api.context-item.json"
    mcp_packet = tmp_path / "mcp.packet.json"

    cli_result = runner.invoke(
        app,
        [
            "context",
            "ingest",
            "--file",
            str(source),
            "--label",
            "Design Notes",
            "--role",
            "source_document",
            "-o",
            str(item_path),
            "--json",
        ],
    )
    cli_packet_result = runner.invoke(
        app,
        [
            "context",
            "packet",
            "--item-json",
            str(item_path),
            "--text",
            "Combine the pre-ingested notes with an inline brief.",
            "-o",
            str(packet_path),
            "--title",
            "CLI Packet",
            "--json",
        ],
    )

    client = TestClient(create_app())
    api_response = client.post(
        "/v1/tools/pdf.context.ingest/run",
        json={
            "context_item": {
                "path": str(source),
                "role": "source_document",
                "label": "API Design Notes",
            },
            "output_path": str(api_item),
        },
    )
    mcp_result = json.loads(
        pdf_context_packet(
            [
                {"text": "Create a packet from MCP.", "role": "brief"},
                {"path": str(source), "role": "source_document", "label": "MCP Design Notes"},
            ],
            str(mcp_packet),
            title="MCP Packet",
        )
    )

    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["tool"] == "pdf.context.ingest"
    assert item_path.exists()
    assert cli_packet_result.exit_code == 0
    cli_packet_payload = json.loads(cli_packet_result.stdout)
    assert cli_packet_payload["tool"] == "pdf.context.packet"
    packet_refs = [item["source_ref"] for item in cli_packet_payload["usage"]["context_packet"]["items"]]
    assert len(packet_refs) == len(set(packet_refs))
    assert packet_path.exists()
    assert api_response.status_code == 200
    assert api_response.json()["tool"] == "pdf.context.ingest"
    assert api_item.exists()
    assert json.loads(pdf_context_ingest({"text": "MCP inline note"}, output_path=None))["tool"] == "pdf.context.ingest"
    assert mcp_result["tool"] == "pdf.context.packet"
    assert mcp_result["usage"]["item_count"] == 2
    assert mcp_packet.exists()
    assert get_tool("pdf.context.ingest").implemented is True
    assert get_tool("pdf.context.packet").implemented is True


def test_context_ingest_cli_accepts_media_transcript_sidecar_path(tmp_path: Path) -> None:
    audio = tmp_path / "meeting.mp3"
    audio.write_bytes(b"ID3 local audio fixture")
    transcript = tmp_path / "meeting.transcript.txt"
    transcript.write_text("00:00 Kickoff\n00:11 Keep sidecar provenance.", encoding="utf-8")
    output_path = tmp_path / "meeting.context-item.json"

    result = runner.invoke(
        app,
        [
            "context",
            "ingest",
            "--file",
            str(audio),
            "--role",
            "audio_context",
            "--label",
            "Meeting Audio",
            "--transcript-path",
            str(transcript),
            "-o",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    context_item = payload["usage"]["context_item"]
    expected_hash = hashlib.sha256(transcript.read_bytes()).hexdigest()
    assert context_item["content"]["transcript"]["source"] == "sidecar_file"
    assert context_item["metadata"]["transcript_source_path"] == transcript.resolve().as_posix()
    assert context_item["metadata"]["transcript_sha256"] == expected_hash
    assert payload["usage"]["source_graph"]["edge_count"] == 1
    assert payload["usage"]["source_graph"]["edges"][0]["relation"] == "provides_transcript_for"
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["source_graph_node"]["evidence"]["transcript_source_path"] == transcript.resolve().as_posix()
    assert written["source_graph"]["nodes"][1]["type"] == "transcript"
    assert written["source_graph"]["edges"][0]["sidecar_source_ref"] == "ctx_001#transcript"


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    def xml_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    body = "".join(
        f"<w:p><w:r><w:t>{xml_escape(paragraph)}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr("word/document.xml", document_xml)


def _write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    def xml_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    worksheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_xlsx_column(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{xml_escape(value)}</t></is></c>'
            )
        worksheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(worksheet_rows)}</sheetData></worksheet>'
    )

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
            ),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)


def _xlsx_column(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
