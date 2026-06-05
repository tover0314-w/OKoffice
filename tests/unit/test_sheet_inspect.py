import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_sheet_inspect_workbook_reports_xlsx_structure(tmp_path: Path) -> None:
    from agentpdf.office.sheet import inspect_sheet_workbook

    path = tmp_path / "model.xlsx"
    _write_xlsx_fixture(path)

    result = inspect_sheet_workbook(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.inspect.workbook"
    assert result.validation is not None
    assert result.validation.status == "warning"

    summary = result.usage["summary"]
    assert summary["sheet_count"] == 2
    assert summary["visible_sheet_count"] == 1
    assert summary["hidden_sheet_count"] == 1
    assert summary["table_count"] == 1
    assert summary["formula_count"] == 2
    assert summary["chart_count"] == 1
    assert summary["named_range_count"] == 1
    assert summary["comment_count"] == 1
    assert summary["external_link_count"] == 1

    assert result.usage["package"]["has_external_relationships"] is True
    assert result.usage["package"]["macro_enabled"] is False
    assert result.usage["formula_evaluation"]["status"] == "structural_only"
    assert result.usage["formula_evaluation"]["evaluated"] is False
    assert "External workbook relationship targets were detected." in result.warnings

    summary_sheet = result.usage["sheets"][0]
    assert summary_sheet["name"] == "Summary"
    assert summary_sheet["used_range"] == "A1:C3"
    assert summary_sheet["hidden"] is False
    assert summary_sheet["locator"] == {"kind": "sheet", "sheet": "Summary"}

    hidden_sheet = result.usage["sheets"][1]
    assert hidden_sheet["name"] == "HiddenData"
    assert hidden_sheet["hidden"] is True

    formula = result.usage["formulas"][0]
    assert formula["sheet"] == "Summary"
    assert formula["cell"] == "C2"
    assert formula["formula"] == "SUM(A2:B2)"
    assert formula["cached_value"] == "12"
    assert formula["locator"] == {"kind": "sheet", "sheet": "Summary", "cell": "C2", "formula": "SUM(A2:B2)"}

    table = result.usage["tables"][0]
    assert table["sheet"] == "Summary"
    assert table["name"] == "RevenueTable"
    assert table["range"] == "A1:C3"
    assert table["locator"] == {"kind": "sheet", "sheet": "Summary", "range": "A1:C3", "table": "RevenueTable"}

    chart = result.usage["charts"][0]
    assert chart["sheet"] == "Summary"
    assert chart["chart_id"] == "chart1"
    assert chart["locator"] == {"kind": "sheet", "sheet": "Summary", "chart": "chart1"}

    comment = result.usage["comments"][0]
    assert comment["sheet"] == "Summary"
    assert comment["cell"] == "B2"
    assert comment["author"] == "Analyst"
    assert comment["text"] == "Check source."

    named_range = result.usage["named_ranges"][0]
    assert named_range["name"] == "RevenueRange"
    assert named_range["refers_to"] == "Summary!$A$1:$C$3"


def test_sheet_inspect_workbook_rejects_non_xlsx_zip(tmp_path: Path) -> None:
    from agentpdf.office.sheet import inspect_sheet_workbook

    path = tmp_path / "bad.xlsx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")

    result = inspect_sheet_workbook(path)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsupported_file_type"


def test_okoffice_sheet_inspect_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    path = tmp_path / "model.xlsx"
    _write_xlsx_fixture(path)

    result = CliRunner().invoke(app, ["sheet", "inspect", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "sheet.inspect.workbook"
    assert payload["usage"]["summary"]["formula_count"] == 2
    assert payload["usage"]["formulas"][0]["locator"]["kind"] == "sheet"


def test_sheet_inspect_workbook_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    path = tmp_path / "model.xlsx"
    _write_xlsx_fixture(path)

    response = TestClient(create_app()).post(
        "/v1/tools/sheet.inspect.workbook/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "sheet.inspect.workbook"
    assert payload["usage"]["summary"]["table_count"] == 1


def test_sheet_inspect_workbook_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import sheet_inspect_workbook

    path = tmp_path / "model.xlsx"
    _write_xlsx_fixture(path)

    payload = json.loads(sheet_inspect_workbook(str(path)))

    assert payload["tool"] == "sheet.inspect.workbook"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["named_range_count"] == 1


def test_sheet_inspect_workbook_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    path = tmp_path / "model.xlsx"
    _write_xlsx_fixture(path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "sheet.inspect.workbook",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "sheet.inspect.workbook"
    assert step["status"] == "succeeded"
    assert "sheet.validation.formulas" in step["next_recommended_tools"]


def _write_xlsx_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", _workbook_xml())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _sheet1_xml())
        archive.writestr("xl/worksheets/sheet2.xml", _sheet2_xml())
        archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", _sheet1_rels_xml())
        archive.writestr("xl/tables/table1.xml", _table_xml())
        archive.writestr("xl/comments1.xml", _comments_xml())
        archive.writestr("xl/drawings/drawing1.xml", _drawing_xml())
        archive.writestr("xl/drawings/_rels/drawing1.xml.rels", _drawing_rels_xml())
        archive.writestr("xl/charts/chart1.xml", "<c:chartSpace xmlns:c='http://schemas.openxmlformats.org/drawingml/2006/chart'/>")
        archive.writestr("docProps/core.xml", _core_xml())


def _workbook_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Summary" sheetId="1" r:id="rId1"/>
    <sheet name="HiddenData" sheetId="2" state="hidden" r:id="rId2"/>
  </sheets>
  <definedNames>
    <definedName name="RevenueRange">Summary!$A$1:$C$3</definedName>
  </definedNames>
  <calcPr calcMode="auto"/>
</workbook>
"""


def _workbook_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rIdExternal" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/externalLink" Target="https://example.com/model.xlsx" TargetMode="External"/>
</Relationships>
"""


def _sheet1_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="A1:C3"/>
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Revenue</t></is></c>
      <c r="B1" t="inlineStr"><is><t>Cost</t></is></c>
      <c r="C1" t="inlineStr"><is><t>Total</t></is></c>
    </row>
    <row r="2">
      <c r="A2"><v>5</v></c>
      <c r="B2"><v>7</v></c>
      <c r="C2"><f>SUM(A2:B2)</f><v>12</v></c>
    </row>
    <row r="3">
      <c r="A3"><v>10</v></c>
      <c r="B3"><v>10</v></c>
      <c r="C3"><f>[1]External!A1</f><v>20</v></c>
    </row>
  </sheetData>
  <tableParts count="1"><tablePart r:id="rIdTable1"/></tableParts>
  <drawing r:id="rIdDrawing1"/>
  <legacyDrawing r:id="rIdComments"/>
</worksheet>
"""


def _sheet2_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:A1"/>
  <sheetData><row r="1"><c r="A1"><v>1</v></c></row></sheetData>
</worksheet>
"""


def _sheet1_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdTable1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/>
  <Relationship Id="rIdDrawing1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/>
  <Relationship Id="rIdComments" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments1.xml"/>
</Relationships>
"""


def _table_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="RevenueTable" displayName="RevenueTable" ref="A1:C3">
  <tableColumns count="3">
    <tableColumn id="1" name="Revenue"/>
    <tableColumn id="2" name="Cost"/>
    <tableColumn id="3" name="Total"/>
  </tableColumns>
</table>
"""


def _comments_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<comments xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <authors><author>Analyst</author></authors>
  <commentList>
    <comment ref="B2" authorId="0"><text><r><t>Check source.</t></r></text></comment>
  </commentList>
</comments>
"""


def _drawing_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <xdr:twoCellAnchor><xdr:graphicFrame><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData><c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" r:id="rIdChart1"/></a:graphicData></a:graphic></xdr:graphicFrame></xdr:twoCellAnchor>
</xdr:wsDr>
"""


def _drawing_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdChart1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/>
</Relationships>
"""


def _core_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Revenue Model</dc:title>
  <dc:creator>okoffice tests</dc:creator>
</cp:coreProperties>
"""
