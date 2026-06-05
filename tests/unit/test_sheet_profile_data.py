import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_profile_sheet_data_reports_headers_types_missing_and_coverage(tmp_path: Path) -> None:
    from okoffice.office.sheet import profile_sheet_data

    path = tmp_path / "profile.xlsx"
    _write_profile_xlsx(path)

    result = profile_sheet_data(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.profile.data"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"]["sheet_count"] == 2
    assert result.usage["summary"]["profiled_sheet_count"] == 1
    assert result.usage["summary"]["column_count"] == 3
    assert result.usage["summary"]["data_row_count"] == 3
    assert result.usage["summary"]["missing_cell_count"] == 2
    assert result.usage["summary"]["formula_cell_count"] == 1
    assert result.usage["summary"]["source_ref_row_count"] == 2
    assert result.usage["summary"]["source_coverage"]["status"] == "partial"

    model = result.usage["profiles"][0]
    assert model["sheet_name"] == "Model"
    assert model["header_row_index"] == 1
    assert model["data_row_count"] == 3
    assert model["headers"] == ["Region", "Revenue", "Score"]
    columns = {column["header"]: column for column in model["columns"]}
    assert columns["Region"]["semantic_type"] == "text"
    assert columns["Revenue"]["semantic_type"] == "number"
    assert columns["Revenue"]["missing_count"] == 1
    assert columns["Revenue"]["nonempty_count"] == 2
    assert columns["Score"]["formula_count"] == 1
    assert columns["Score"]["missing_count"] == 1
    assert "sheet.create.evidence_workbook" in result.next_recommended_tools
    assert "sheet.write.workbook" in result.next_recommended_tools
    assert any("missing cells" in warning.lower() for warning in result.warnings)


def test_profile_sheet_data_can_include_source_refs_sheet(tmp_path: Path) -> None:
    from okoffice.office.sheet import profile_sheet_data

    path = tmp_path / "profile.xlsx"
    _write_profile_xlsx(path)

    result = profile_sheet_data(path, include_source_refs=True)

    assert result.status == "succeeded"
    assert [profile["sheet_name"] for profile in result.usage["profiles"]] == ["Model", "SourceRefs"]
    assert result.usage["summary"]["profiled_sheet_count"] == 2


def test_profile_sheet_data_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import sheet_profile_data
    from okoffice.office.sheet import write_sheet_workbook
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    path = tmp_path / "model.xlsx"
    write_sheet_workbook(
        [
            {"values": ["Metric", "Value"], "source_refs": [{"cell_ref": "A1"}]},
            {"values": ["Revenue", "42"], "source_refs": [{"cell_ref": "A2"}]},
        ],
        path,
    )

    runner = CliRunner()
    cli = runner.invoke(app, ["sheet", "profile", str(path), "--json"])
    response = TestClient(create_app()).post("/v1/tools/sheet.profile.data/run", json={"path": str(path)})
    mcp_payload = json.loads(sheet_profile_data(str(path)))
    workflow = run_workflow({"steps": [{"tool": "sheet.profile.data", "input": {"path": str(path)}}]})

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "sheet.profile.data"
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["profiled_sheet_count"] == 1
    assert mcp_payload["tool"] == "sheet.profile.data"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.profile.data"


def test_sheet_profile_data_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["sheet.profile.data"]["status"] == "beta"
    assert target["sheet.profile.data"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["sheet_profile_data"]["maps_to"] == "sheet.profile.data"


def _write_profile_xlsx(path: Path) -> None:
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
              <si><t>Region</t></si>
              <si><t>Revenue</t></si>
              <si><t>East</t></si>
              <si><t>West</t></si>
              <si><t>North</t></si>
              <si><t>source_refs_json</t></si>
            </sst>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:C4"/>
              <sheetData>
                <row r="1">
                  <c r="A1" t="s"><v>0</v></c>
                  <c r="B1" t="s"><v>1</v></c>
                  <c r="C1" t="inlineStr"><is><t>Score</t></is></c>
                </row>
                <row r="2">
                  <c r="A2" t="s"><v>2</v></c>
                  <c r="B2"><v>100</v></c>
                  <c r="C2"><f>B2*2</f><v>200</v></c>
                </row>
                <row r="3">
                  <c r="A3" t="s"><v>3</v></c>
                  <c r="C3"><v>5</v></c>
                </row>
                <row r="4">
                  <c r="A4" t="s"><v>4</v></c>
                  <c r="B4"><v>120</v></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet2.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:G3"/>
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>record_index</t></is></c>
                  <c r="G1" t="s"><v>5</v></c>
                </row>
                <row r="2"><c r="A2"><v>1</v></c><c r="G2" t="inlineStr"><is><t>[{}]</t></is></c></row>
                <row r="3"><c r="A3"><v>2</v></c><c r="G3" t="inlineStr"><is><t>[{}]</t></is></c></row>
              </sheetData>
            </worksheet>
            """,
        )
