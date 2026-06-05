import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_sheet_formula_validation_reports_structural_formula_risks(tmp_path: Path) -> None:
    from okoffice.office.validation import validate_sheet_formulas

    path = tmp_path / "risk-model.xlsx"
    _write_formula_risk_workbook(path)

    result = validate_sheet_formulas(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.validation.formulas"
    assert result.validation is not None
    assert result.validation.status == "warning"

    summary = result.usage["summary"]
    assert summary["formula_count"] == 3
    assert summary["external_formula_count"] == 1
    assert summary["cached_error_count"] == 1
    assert summary["self_reference_count"] == 1
    assert summary["formula_evaluated"] is False

    issues = result.usage["issues"]
    assert issues["external_references"][0]["cell"] == "C3"
    assert issues["cached_errors"][0]["cached_value"] == "#REF!"
    assert issues["self_references"][0]["formula"] == "D4+1"
    assert "Formula evaluation worker is not configured; validation is structural only." in result.warnings
    assert "office.workflow.sheet_to_deck" in result.next_recommended_tools


def test_sheet_formula_validation_passes_for_generated_evidence_workbook(tmp_path: Path) -> None:
    from okoffice.office.validation import validate_sheet_formulas
    from okoffice.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    _write_evidence(evidence_path)

    written = write_sheet_workbook(evidence_path=evidence_path, output_path=output_path)
    assert written.status == "succeeded"

    result = validate_sheet_formulas(output_path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["summary"]["formula_count"] == 0
    assert result.usage["summary"]["table_count"] == 4
    assert result.usage["summary"]["data_model_count"] == 2
    assert result.usage["summary"]["chart_plan_count"] == 1
    assert result.usage["formula_evaluation"]["status"] == "structural_only"


def test_okoffice_sheet_validate_formulas_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    path = tmp_path / "risk-model.xlsx"
    _write_formula_risk_workbook(path)

    result = CliRunner().invoke(app, ["sheet", "validate-formulas", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "sheet.validation.formulas"
    assert payload["validation"]["status"] == "warning"
    assert payload["usage"]["summary"]["external_formula_count"] == 1


def test_sheet_formula_validation_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    path = tmp_path / "risk-model.xlsx"
    _write_formula_risk_workbook(path)

    response = TestClient(create_app()).post(
        "/v1/tools/sheet.validation.formulas/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "sheet.validation.formulas"
    assert payload["usage"]["summary"]["cached_error_count"] == 1


def test_sheet_formula_validation_runs_through_mcp_function(tmp_path: Path) -> None:
    from okoffice.mcp.server import sheet_validate_formulas

    path = tmp_path / "risk-model.xlsx"
    _write_formula_risk_workbook(path)

    payload = json.loads(sheet_validate_formulas(str(path)))

    assert payload["tool"] == "sheet.validation.formulas"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["self_reference_count"] == 1


def test_sheet_formula_validation_runs_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    path = tmp_path / "risk-model.xlsx"
    _write_formula_risk_workbook(path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "sheet.validation.formulas",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "sheet.validation.formulas"
    assert step["validation"]["status"] == "warning"


def _write_formula_risk_workbook(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml())
        archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", _sheet_rels_xml())
        archive.writestr("xl/tables/table1.xml", _table_xml())


def _workbook_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Summary" sheetId="1" r:id="rId1"/></sheets>
  <definedNames><definedName name="RevenueRange">Summary!$A$1:$C$4</definedName></definedNames>
</workbook>
"""


def _workbook_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rIdExternal" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/externalLink" Target="https://example.com/external.xlsx" TargetMode="External"/>
</Relationships>
"""


def _sheet_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:D4"/>
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Revenue</t></is></c>
      <c r="B1" t="inlineStr"><is><t>Cost</t></is></c>
      <c r="C1" t="inlineStr"><is><t>Total</t></is></c>
      <c r="D1" t="inlineStr"><is><t>Self</t></is></c>
    </row>
    <row r="2">
      <c r="A2"><v>5</v></c>
      <c r="B2"><v>7</v></c>
      <c r="C2"><f>SUM(A2:B2)</f><v>12</v></c>
    </row>
    <row r="3">
      <c r="A3"><v>10</v></c>
      <c r="B3"><v>10</v></c>
      <c r="C3" t="e"><f>[1]External!A1</f><v>#REF!</v></c>
    </row>
    <row r="4">
      <c r="D4"><f>D4+1</f><v>1</v></c>
    </row>
  </sheetData>
  <tableParts count="1"><tablePart r:id="rIdTable1"/></tableParts>
</worksheet>
"""


def _sheet_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdTable1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/>
</Relationships>
"""


def _table_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="SummaryTable" displayName="SummaryTable" ref="A1:D4">
  <autoFilter ref="A1:D4"/>
  <tableColumns count="4">
    <tableColumn id="1" name="Revenue"/>
    <tableColumn id="2" name="Cost"/>
    <tableColumn id="3" name="Total"/>
    <tableColumn id="4" name="Self"/>
  </tableColumns>
</table>
"""


def _write_evidence(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "extraction_id": "extract_test",
                "schema_name": "vendor_renewal",
                "fields": [
                    {"name": "vendor", "type": "string"},
                    {"name": "amount", "type": "number"},
                ],
                "rows": [
                    {
                        "row_id": "row_001",
                        "values": {"vendor": "Acme Corp", "amount": "120000"},
                        "field_evidence": {
                            "vendor": {"source_ref": "ctx_001#p1", "confidence": 0.95},
                            "amount": {"source_ref": "ctx_001#p1", "confidence": 0.95},
                        },
                    }
                ],
                "source_refs": [{"source_ref": "ctx_001#p1"}],
            }
        ),
        encoding="utf-8",
    )
