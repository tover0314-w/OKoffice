import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from fastapi.testclient import TestClient
from typer.testing import CliRunner


SHEET_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def test_extract_to_sheet_builds_evidence_workbook_from_docx_and_xlsx(tmp_path: Path) -> None:
    from okoffice.office.workflows import extract_to_sheet

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    output_path = tmp_path / "evidence.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)

    result = extract_to_sheet([docx_path, xlsx_path], output_path)

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.extract_to_sheet"
    assert output_path.exists()
    assert result.artifacts[0].path == output_path.resolve()
    assert result.usage["summary"] == {
        "source_count": 2,
        "supported_source_count": 2,
        "table_count": 2,
        "row_count": 4,
        "cell_count": 8,
    }
    assert result.usage["evidence_workbook"]["path"] == output_path.resolve().as_posix()
    assert result.usage["records"][0]["source_format"] == "docx"
    assert result.usage["records"][0]["values"] == ["Name", "Value"]
    assert result.usage["records"][2]["source_format"] == "xlsx"
    assert result.usage["records"][3]["source_refs"][1]["cell_ref"] == "B2"
    assert "office.workflow.sheet_to_deck" in result.next_recommended_tools
    assert _sheet_names(output_path) == ["Tables", "Cells"]


def test_extract_to_sheet_can_start_from_context_packet_source_graph(tmp_path: Path) -> None:
    from okoffice.office.context import build_office_context_packet
    from okoffice.office.workflows import extract_to_sheet

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    context_path = tmp_path / "context.packet.json"
    output_path = tmp_path / "evidence-from-context.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)
    context_result = build_office_context_packet(
        [docx_path, xlsx_path],
        context_path,
        title="Evidence Context",
        intent="Create a source-mapped evidence workbook",
    )
    context_packet = context_result.usage["context_packet"]

    result = extract_to_sheet([], output_path, context_packet_path=context_path)

    assert result.status == "succeeded"
    assert output_path.exists()
    assert result.usage["summary"]["source_count"] == 2
    assert result.usage["summary"]["context_packet_id"] == context_packet["context_packet_id"]
    assert result.usage["source_graph"]["source_graph_id"] == context_packet["source_graph"]["source_graph_id"]
    assert result.usage["source_graph"]["node_type_counts"]["word.table"] == 1
    assert result.usage["source_graph"]["node_type_counts"]["sheet.table"] == 1
    assert result.usage["records"][0]["context_packet_id"] == context_packet["context_packet_id"]
    assert result.usage["records"][0]["source_graph_id"] == context_packet["source_graph"]["source_graph_id"]
    assert any(ref["type"] == "word.table" for ref in result.usage["records"][0]["source_node_refs"])
    assert _sheet_names(output_path) == ["Tables", "Cells", "SourceGraph"]


def test_extract_to_sheet_cli_returns_json_and_workbook(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    output_path = tmp_path / "evidence.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)

    result = CliRunner().invoke(
        app,
        [
            "workflow",
            "extract-to-sheet",
            str(docx_path),
            str(xlsx_path),
            "--output",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.workflow.extract_to_sheet"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["table_count"] == 2
    assert output_path.exists()


def test_extract_to_sheet_runs_through_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_workflow_extract_to_sheet
    from okoffice.workflows.runner import run_workflow

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    api_output = tmp_path / "api-evidence.xlsx"
    mcp_output = tmp_path / "mcp-evidence.xlsx"
    workflow_output = tmp_path / "workflow-evidence.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)

    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.extract_to_sheet/run",
        json={"input_paths": [str(docx_path), str(xlsx_path)], "output_path": str(api_output)},
    )
    mcp_payload = json.loads(
        office_workflow_extract_to_sheet([str(docx_path), str(xlsx_path)], str(mcp_output))
    )
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.extract_to_sheet",
                    "input": {
                        "input_paths": [str(docx_path), str(xlsx_path)],
                        "output_path": str(workflow_output),
                    },
                }
            ]
        }
    )

    assert response.status_code == 200
    assert response.json()["tool"] == "office.workflow.extract_to_sheet"
    assert api_output.exists()
    assert mcp_payload["tool"] == "office.workflow.extract_to_sheet"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "office.workflow.extract_to_sheet"


def test_extract_to_sheet_context_packet_runs_through_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import office_workflow_extract_to_sheet
    from okoffice.office.context import build_office_context_packet
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    context_path = tmp_path / "context.packet.json"
    api_output = tmp_path / "api-context-evidence.xlsx"
    mcp_output = tmp_path / "mcp-context-evidence.xlsx"
    workflow_output = tmp_path / "workflow-context-evidence.xlsx"
    cli_output = tmp_path / "cli-context-evidence.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)
    build_office_context_packet([docx_path, xlsx_path], context_path)

    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.extract_to_sheet/run",
        json={"context_packet_path": str(context_path), "output_path": str(api_output)},
    )
    mcp_payload = json.loads(
        office_workflow_extract_to_sheet([], str(mcp_output), context_packet_path=str(context_path))
    )
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.extract_to_sheet",
                    "input": {
                        "context_packet_path": str(context_path),
                        "output_path": str(workflow_output),
                    },
                }
            ]
        }
    )
    cli_result = CliRunner().invoke(
        app,
        [
            "workflow",
            "extract-to-sheet",
            "--context-packet",
            str(context_path),
            "--output",
            str(cli_output),
            "--json",
        ],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["usage"]["summary"]["source_count"] == 2
    assert api_output.exists()
    assert mcp_payload["status"] == "succeeded"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["status"] == "succeeded"
    assert cli_output.exists()


def test_extract_to_sheet_manifest_and_mcp_catalog_mark_tool_beta() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target_tools = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target_tools["office.workflow.extract_to_sheet"]["status"] == "beta"
    assert target_tools["office.workflow.extract_to_sheet"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    catalog_tools = {tool["name"]: tool for tool in catalog["tools"]}
    assert catalog_tools["office_workflow_extract_to_sheet"]["maps_to"] == "office.workflow.extract_to_sheet"


def _write_docx_with_table(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body>
                <w:tbl>
                  <w:tr>
                    <w:tc><w:p><w:r><w:t>Name</w:t></w:r></w:p></w:tc>
                    <w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc>
                  </w:tr>
                  <w:tr>
                    <w:tc><w:p><w:r><w:t>Alpha</w:t></w:r></w:p></w:tc>
                    <w:tc><w:p><w:r><w:t>42</w:t></w:r></w:p></w:tc>
                  </w:tr>
                </w:tbl>
              </w:body>
            </w:document>
            """,
        )


def _write_xlsx_with_table(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets><sheet name="Summary" sheetId="1" r:id="rId1"/></sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:B2"/>
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>Name</t></is></c>
                  <c r="B1" t="inlineStr"><is><t>Value</t></is></c>
                </row>
                <row r="2">
                  <c r="A2" t="inlineStr"><is><t>Alpha</t></is></c>
                  <c r="B2"><v>42</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )


def _sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    return [str(sheet.get("name")) for sheet in workbook.findall(".//main:sheet", SHEET_NS)]
