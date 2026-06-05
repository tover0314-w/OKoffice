import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_build_context_packet_from_office_sources_writes_source_graph(tmp_path: Path) -> None:
    from okoffice.office.context import build_office_context_packet

    docx_path, xlsx_path, pptx_path = _write_context_sources(tmp_path)
    output_path = tmp_path / "context.packet.json"

    result = build_office_context_packet(
        [docx_path, xlsx_path, pptx_path],
        output_path,
        title="Vendor Context",
        intent="Prepare board review",
    )

    assert result.status == "succeeded"
    assert result.tool == "office.context.build_packet"
    assert output_path.exists()
    assert result.artifacts[0].path == output_path
    assert result.artifacts[0].source_tool == "office.context.build_packet"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["input_count"] == 3
    assert result.usage["summary"]["item_count"] == 3
    assert result.usage["summary"]["source_node_count"] >= 6
    assert result.usage["summary"]["formats"] == {"docx": 1, "pptx": 1, "xlsx": 1}
    assert "office.workflow.extract_to_sheet" in result.next_recommended_tools

    packet = json.loads(output_path.read_text(encoding="utf-8"))
    assert packet["product"] == "okoffice"
    assert packet["context_packet_id"].startswith("ctxpkt_")
    assert packet["title"] == "Vendor Context"
    assert [item["type"] for item in packet["items"]] == ["document", "data", "document"]
    assert packet["items"][0]["metadata"]["office"]["format"]["detected_format"] == "docx"
    assert packet["items"][1]["metadata"]["office"]["format"]["domain"] == "sheet"
    assert packet["source_graph"]["source_graph_id"].startswith("srcgraph_")
    node_types = {node["type"] for node in packet["source_graph"]["nodes"]}
    assert {"file", "word.document", "sheet.workbook", "deck.presentation"} <= node_types
    first_file_node = packet["source_graph"]["nodes"][0]
    assert first_file_node["evidence"]["file"]["sha256"]
    assert first_file_node["locators"][0]["kind"] == "file"


def test_build_context_packet_rejects_empty_inputs(tmp_path: Path) -> None:
    from okoffice.office.context import build_office_context_packet

    result = build_office_context_packet([], tmp_path / "empty.json")

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"


def test_context_packet_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_context_build_packet
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    docx_path, xlsx_path, _ = _write_context_sources(tmp_path)
    cli_output = tmp_path / "cli.context.json"
    api_output = tmp_path / "api.context.json"
    mcp_output = tmp_path / "mcp.context.json"
    workflow_output = tmp_path / "workflow.context.json"

    runner = CliRunner()
    cli = runner.invoke(
        app,
        [
            "context",
            "build",
            "--file",
            str(docx_path),
            "--file",
            str(xlsx_path),
            "-o",
            str(cli_output),
            "--title",
            "Vendor Context",
            "--intent",
            "Prepare board review",
            "--json",
        ],
    )
    response = TestClient(create_app()).post(
        "/v1/tools/office.context.build_packet/run",
        json={
            "files": [str(docx_path), str(xlsx_path)],
            "output_path": str(api_output),
            "title": "Vendor Context",
            "intent": "Prepare board review",
        },
    )
    mcp_payload = json.loads(
        office_context_build_packet(
            [str(docx_path), str(xlsx_path)],
            str(mcp_output),
            title="Vendor Context",
            intent="Prepare board review",
        )
    )
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.context.build_packet",
                    "input": {
                        "files": [str(docx_path), str(xlsx_path)],
                        "output_path": str(workflow_output),
                        "title": "Vendor Context",
                    },
                }
            ]
        }
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "office.context.build_packet"
    assert cli_output.exists()
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["item_count"] == 2
    assert api_output.exists()
    assert mcp_payload["tool"] == "office.context.build_packet"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "office.context.build_packet"


def test_context_packet_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["office.context.build_packet"]["status"] == "beta"
    assert target["office.context.build_packet"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["office_context_build_packet"]["maps_to"] == "office.context.build_packet"


def _write_context_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    pptx_path = tmp_path / "deck.pptx"
    _write_ooxml(docx_path, "word/document.xml", "<w:document/>")
    _write_ooxml(xlsx_path, "xl/workbook.xml", "<workbook/>")
    _write_ooxml(pptx_path, "ppt/presentation.xml", "<p:presentation/>")
    return docx_path, xlsx_path, pptx_path


def _write_ooxml(path: Path, primary_member: str, body: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>",
        )
        archive.writestr(primary_member, body)
