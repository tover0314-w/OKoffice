import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_word_extract_tables_returns_normalized_cells(tmp_path: Path) -> None:
    from okoffice.office.word import extract_word_tables

    path = tmp_path / "memo.docx"
    _write_docx_with_table(path)

    result = extract_word_tables(path)

    assert result.status == "succeeded"
    assert result.tool == "word.extract.tables"
    assert result.usage["summary"] == {"table_count": 1, "row_count": 2, "cell_count": 4}
    table = result.usage["tables"][0]
    assert table["table_id"] == "word_table_1"
    assert table["source"]["document_path"] == path.as_posix()
    assert table["rows"][0]["cells"][0]["text"] == "Name"
    assert table["rows"][1]["cells"][1]["text"] == "42"
    assert table["rows"][1]["cells"][1]["source"] == {
        "document_path": path.as_posix(),
        "table_index": 1,
        "row_index": 2,
        "cell_index": 2,
    }
    assert "sheet.create.evidence_workbook" in result.next_recommended_tools
    assert "sheet.write.workbook" in result.next_recommended_tools


def test_sheet_extract_tables_returns_sheet_cell_refs(tmp_path: Path) -> None:
    from okoffice.office.sheet import extract_sheet_tables

    path = tmp_path / "model.xlsx"
    _write_xlsx_with_table(path)

    result = extract_sheet_tables(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.extract.tables"
    assert result.usage["summary"] == {"table_count": 1, "row_count": 2, "cell_count": 4}
    table = result.usage["tables"][0]
    assert table["table_id"] == "sheet_1_table_1"
    assert table["source"]["sheet_name"] == "Summary"
    assert table["source"]["range_ref"] == "A1:B2"
    assert table["rows"][0]["cells"][0]["value"] == "Name"
    assert table["rows"][1]["cells"][1]["value"] == "42"
    assert table["rows"][1]["cells"][1]["source"] == {
        "workbook_path": path.as_posix(),
        "sheet_name": "Summary",
        "sheet_index": 1,
        "cell_ref": "B2",
        "row_index": 2,
        "column_index": 2,
    }
    assert "sheet.create.evidence_workbook" in result.next_recommended_tools
    assert "office.workflow.extract_to_sheet" in result.next_recommended_tools


def test_okoffice_extract_table_cli_commands_return_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)

    runner = CliRunner()
    word = runner.invoke(app, ["word", "extract-tables", str(docx_path), "--json"])
    sheet = runner.invoke(app, ["sheet", "extract-tables", str(xlsx_path), "--json"])

    assert word.exit_code == 0
    assert json.loads(word.stdout)["tool"] == "word.extract.tables"
    assert sheet.exit_code == 0
    assert json.loads(sheet.stdout)["tool"] == "sheet.extract.tables"


def test_extract_table_tools_run_through_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import sheet_extract_tables
    from okoffice.workflows.runner import run_workflow

    docx_path = tmp_path / "memo.docx"
    xlsx_path = tmp_path / "model.xlsx"
    _write_docx_with_table(docx_path)
    _write_xlsx_with_table(xlsx_path)

    response = TestClient(create_app()).post(
        "/v1/tools/word.extract.tables/run",
        json={"path": str(docx_path)},
    )
    sheet_payload = json.loads(sheet_extract_tables(str(xlsx_path)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "sheet.extract.tables",
                    "input": {"path": str(xlsx_path)},
                }
            ]
        }
    )

    assert response.status_code == 200
    assert response.json()["tool"] == "word.extract.tables"
    assert response.json()["usage"]["summary"]["cell_count"] == 4
    assert sheet_payload["tool"] == "sheet.extract.tables"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.extract.tables"


def test_table_extract_manifest_and_mcp_catalog_mark_tools_beta() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target_tools = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target_tools["word.extract.tables"]["status"] == "beta"
    assert target_tools["word.extract.tables"]["implemented"] is True
    assert target_tools["sheet.extract.tables"]["status"] == "beta"
    assert target_tools["sheet.extract.tables"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    catalog_tools = {tool["name"]: tool for tool in catalog["tools"]}
    assert catalog_tools["word_extract_tables"]["maps_to"] == "word.extract.tables"
    assert catalog_tools["sheet_extract_tables"]["maps_to"] == "sheet.extract.tables"


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
