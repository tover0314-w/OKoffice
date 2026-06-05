import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_read_sheet_workbook_returns_cells_formulas_and_source_refs(tmp_path: Path) -> None:
    from okoffice.office.sheet import read_sheet_workbook

    path = tmp_path / "formula-model.xlsx"
    _write_formula_xlsx(path)

    result = read_sheet_workbook(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.read.workbook"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["sheet_count"] == 2
    assert result.usage["summary"]["row_count"] == 3
    assert result.usage["summary"]["cell_count"] == 6
    assert result.usage["summary"]["formula_count"] == 1
    assert result.usage["summary"]["source_refs_sheet_present"] is True
    assert result.usage["sheets"][0]["name"] == "Model"
    first_row = result.usage["sheets"][0]["rows"][0]
    assert first_row["cells"][0]["value"] == "Revenue"
    assert first_row["cells"][0]["data_type"] == "s"
    assert first_row["cells"][1]["value"] == "10"
    assert first_row["cells"][2]["formula"] == "SUM(B1:B2)"
    assert first_row["cells"][2]["source"]["cell_ref"] == "C1"
    assert "sheet.profile.data" in result.next_recommended_tools


def test_read_sheet_workbook_applies_row_limit_with_warning(tmp_path: Path) -> None:
    from okoffice.office.sheet import read_sheet_workbook

    path = tmp_path / "formula-model.xlsx"
    _write_formula_xlsx(path)

    result = read_sheet_workbook(path, max_rows_per_sheet=1)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"]["truncated"] is True
    assert result.usage["summary"]["returned_row_count"] == 2
    assert result.usage["sheets"][0]["row_count"] == 2
    assert result.usage["sheets"][0]["returned_row_count"] == 1
    assert result.usage["sheets"][0]["truncated"] is True
    assert any("truncated" in warning.lower() for warning in result.warnings)


def test_read_sheet_workbook_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import sheet_read_workbook
    from okoffice.office.sheet import write_sheet_workbook
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    path = tmp_path / "model.xlsx"
    write_sheet_workbook([{"values": ["Metric", "42"], "source_refs": [{"cell_ref": "A1"}]}], path)

    runner = CliRunner()
    cli = runner.invoke(app, ["sheet", "read", str(path), "--max-rows", "5", "--json"])
    response = TestClient(create_app()).post(
        "/v1/tools/sheet.read.workbook/run",
        json={"path": str(path), "max_rows_per_sheet": 5},
    )
    mcp_payload = json.loads(sheet_read_workbook(str(path), max_rows_per_sheet=5))
    workflow = run_workflow(
        {"steps": [{"tool": "sheet.read.workbook", "input": {"path": str(path), "max_rows_per_sheet": 5}}]}
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "sheet.read.workbook"
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["source_refs_sheet_present"] is True
    assert mcp_payload["tool"] == "sheet.read.workbook"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.read.workbook"


def test_sheet_read_workbook_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["sheet.read.workbook"]["status"] == "beta"
    assert target["sheet.read.workbook"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["sheet_read_workbook"]["maps_to"] == "sheet.read.workbook"


def _write_formula_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Model" sheetId="1" r:id="rId1"/>
                <sheet name="SourceRefs" sheetId="2" r:id="rId2"/>
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            """
            <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <si><t>Revenue</t></si>
              <si><t>source_refs_json</t></si>
            </sst>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:C2"/>
              <sheetData>
                <row r="1">
                  <c r="A1" t="s"><v>0</v></c>
                  <c r="B1"><v>10</v></c>
                  <c r="C1"><f>SUM(B1:B2)</f><v>30</v></c>
                </row>
                <row r="2">
                  <c r="A2" t="inlineStr"><is><t>Bookings</t></is></c>
                  <c r="B2"><v>20</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet2.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:A1"/>
              <sheetData>
                <row r="1"><c r="A1" t="s"><v>1</v></c></row>
              </sheetData>
            </worksheet>
            """,
        )
