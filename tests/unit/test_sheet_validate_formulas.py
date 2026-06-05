import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_validate_sheet_formulas_reports_formula_risks(tmp_path: Path) -> None:
    from okoffice.office.sheet import validate_sheet_formulas

    path = tmp_path / "formula-risks.xlsx"
    _write_formula_risk_xlsx(path)

    result = validate_sheet_formulas(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.validation.formulas"
    assert result.validation is not None
    assert result.validation.status == "warning"
    checks = {check.name: check for check in result.validation.checks}
    assert checks["formulas_scanned"].status == "passed"
    assert checks["formula_errors_absent"].status == "warning"
    assert checks["broken_refs_absent"].status == "warning"
    assert checks["external_formula_refs_absent"].status == "warning"
    assert checks["volatile_formulas_absent"].status == "warning"
    assert result.usage["summary"] == {
        "sheet_count": 2,
        "formula_count": 4,
        "formula_error_count": 1,
        "broken_ref_count": 1,
        "external_ref_count": 1,
        "volatile_formula_count": 1,
    }
    formulas = {(item["sheet_name"], item["cell_ref"]): item for item in result.usage["formulas"]}
    assert formulas[("Model", "C1")]["formula"] == "SUM(B1:B2)"
    assert formulas[("Model", "C1")]["precedents"] == ["B1:B2"]
    assert formulas[("Model", "D1")]["issues"][0]["kind"] == "formula_error"
    assert formulas[("Model", "E1")]["external_refs"] == ["[source.xlsx]Sheet1"]
    assert formulas[("Model", "F1")]["volatile_functions"] == ["NOW"]
    assert "sheet.validate.workbook" in result.next_recommended_tools
    assert "deck.compose.plan" in result.next_recommended_tools


def test_validate_sheet_formulas_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import sheet_validate_formulas
    from okoffice.workflows.runner import run_workflow
    from okoffice.cli_okoffice.main import app

    path = tmp_path / "formula-risks.xlsx"
    _write_formula_risk_xlsx(path)

    cli = CliRunner().invoke(app, ["sheet", "validate-formulas", str(path), "--json"])
    response = TestClient(create_app()).post("/v1/tools/sheet.validation.formulas/run", json={"path": str(path)})
    mcp_payload = json.loads(sheet_validate_formulas(str(path)))
    workflow = run_workflow({"steps": [{"tool": "sheet.validation.formulas", "input": {"path": str(path)}}]})

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "sheet.validation.formulas"
    assert response.status_code == 200
    assert response.json()["usage"]["summary"]["formula_count"] == 4
    assert mcp_payload["tool"] == "sheet.validation.formulas"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.validation.formulas"


def test_sheet_validation_formulas_is_listed_in_manifests() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["sheet.validation.formulas"]["status"] == "beta"
    assert target["sheet.validation.formulas"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["sheet_validate_formulas"]["maps_to"] == "sheet.validation.formulas"


def _write_formula_risk_xlsx(path: Path) -> None:
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
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:F2"/>
              <sheetData>
                <row r="1">
                  <c r="A1" t="inlineStr"><is><t>Metric</t></is></c>
                  <c r="B1"><v>10</v></c>
                  <c r="C1"><f>SUM(B1:B2)</f><v>30</v></c>
                  <c r="D1" t="e"><f>SUM(#REF!)</f><v>#REF!</v></c>
                  <c r="E1"><f>'[source.xlsx]Sheet1'!A1</f><v>10</v></c>
                  <c r="F1"><f>NOW()</f><v>45000</v></c>
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
                <row r="1"><c r="A1" t="inlineStr"><is><t>source_refs_json</t></is></c></row>
              </sheetData>
            </worksheet>
            """,
        )
