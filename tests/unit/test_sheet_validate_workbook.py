import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner


def test_validate_sheet_workbook_passes_for_source_mapped_workbook(tmp_path: Path) -> None:
    from agentpdf.office.sheet import validate_sheet_workbook, write_sheet_workbook

    path = tmp_path / "model.xlsx"
    write_sheet_workbook(
        [
            {
                "source_path": "memo.docx",
                "source_format": "docx",
                "table_id": "table_1",
                "source_row_index": 1,
                "values": ["Metric", "Value"],
                "source_refs": [{"document_path": "memo.docx", "paragraph_index": 4}],
            }
        ],
        path,
    )

    result = validate_sheet_workbook(path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.validate.workbook"
    assert result.validation is not None
    assert result.validation.status == "passed"
    checks = {check.name: check for check in result.validation.checks}
    assert checks["format_is_xlsx"].status == "passed"
    assert checks["sheet_count_nonzero"].status == "passed"
    assert checks["nonempty_workbook"].status == "passed"
    assert checks["external_links_absent"].status == "passed"
    assert checks["source_refs_sheet_present"].status == "passed"
    assert result.usage["summary"]["sheet_count"] == 2
    assert result.usage["summary"]["source_ref_row_count"] == 1
    assert result.usage["summary"]["blank_sheet_count"] == 0
    assert "office.workflow.source_to_deck" in result.next_recommended_tools


def test_validate_sheet_workbook_warns_on_blank_sheets_and_external_links(tmp_path: Path) -> None:
    from agentpdf.office.sheet import validate_sheet_workbook

    path = tmp_path / "risky.xlsx"
    _write_risky_xlsx(path)

    result = validate_sheet_workbook(path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    checks = {check.name: check for check in result.validation.checks}
    assert checks["blank_sheets_absent"].status == "warning"
    assert checks["external_links_absent"].status == "warning"
    assert checks["source_refs_sheet_present"].status == "warning"
    assert result.usage["summary"]["blank_sheet_count"] == 1
    assert result.usage["summary"]["external_link_count"] == 1
    assert any("External workbook links" in warning for warning in result.warnings)


def test_validate_sheet_workbook_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import sheet_validate_workbook
    from agentpdf.office.sheet import write_sheet_workbook
    from agentpdf.workflows.runner import run_workflow
    from okoffice.cli.main import app

    path = tmp_path / "model.xlsx"
    write_sheet_workbook([{"values": ["Revenue", "42"], "source_refs": [{"cell_ref": "A1"}]}], path)

    runner = CliRunner()
    cli = runner.invoke(app, ["sheet", "validate", str(path), "--json"])
    response = TestClient(create_app()).post("/v1/tools/sheet.validate.workbook/run", json={"path": str(path)})
    mcp_payload = json.loads(sheet_validate_workbook(str(path)))
    workflow = run_workflow({"steps": [{"tool": "sheet.validate.workbook", "input": {"path": str(path)}}]})

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "sheet.validate.workbook"
    assert response.status_code == 200
    assert response.json()["validation"]["status"] == "passed"
    assert mcp_payload["tool"] == "sheet.validate.workbook"
    assert workflow.status == "succeeded"
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.validate.workbook"


def test_sheet_validate_workbook_is_listed_in_manifests() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target["sheet.validate.workbook"]["status"] == "beta"
    assert target["sheet.validate.workbook"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    entries = {tool["name"]: tool for tool in catalog["tools"]}
    assert entries["sheet_validate_workbook"]["maps_to"] == "sheet.validate.workbook"


def _write_risky_xlsx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "xl/workbook.xml",
            """
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets>
                <sheet name="Summary" sheetId="1" r:id="rId1"/>
                <sheet name="Empty" sheetId="2" r:id="rId2"/>
              </sheets>
            </workbook>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:B2"/>
              <sheetData>
                <row r="1"><c r="A1" t="inlineStr"><is><t>Metric</t></is></c></row>
              </sheetData>
            </worksheet>
            """,
        )
        archive.writestr(
            "xl/worksheets/sheet2.xml",
            """
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <dimension ref="A1:A1"/>
              <sheetData/>
            </worksheet>
            """,
        )
        archive.writestr("xl/externalLinks/externalLink1.xml", "<externalLink/>")
