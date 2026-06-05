import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from fastapi.testclient import TestClient
from typer.testing import CliRunner


SHEET_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def test_sheet_write_workbook_creates_source_mapped_xlsx(tmp_path: Path) -> None:
    from okoffice.office.sheet import write_sheet_workbook

    output_path = tmp_path / "modeled.xlsx"

    result = write_sheet_workbook({"records": _records()}, output_path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.write.workbook"
    assert output_path.exists()
    assert result.artifacts[0].path == output_path.resolve()
    assert result.usage["summary"] == {"record_count": 2, "column_count": 2, "source_ref_count": 2}
    assert result.usage["workbook"]["sheets"] == ["Workbook", "SourceRefs"]
    assert _sheet_names(output_path) == ["Workbook", "SourceRefs"]
    values = _inline_values(output_path, "xl/worksheets/sheet1.xml")
    assert "source_path" in values
    assert "Name" in values
    assert "42" in values
    assert "office.context.build_packet" in result.next_recommended_tools


def test_sheet_create_evidence_workbook_is_canonical_source_mapped_xlsx(tmp_path: Path) -> None:
    from okoffice.office.sheet import create_evidence_workbook

    output_path = tmp_path / "evidence.xlsx"

    result = create_evidence_workbook({"records": _records()}, output_path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.create.evidence_workbook"
    assert output_path.exists()
    assert result.artifacts[0].source_tool == "sheet.create.evidence_workbook"
    assert result.usage["summary"] == {"record_count": 2, "column_count": 2, "source_ref_count": 2}
    assert _sheet_names(output_path) == ["Workbook", "SourceRefs"]
    assert "deck.compose.plan" in result.next_recommended_tools


def test_sheet_write_workbook_cli_accepts_json_records(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    data_path = tmp_path / "records.json"
    output_path = tmp_path / "modeled.xlsx"
    data_path.write_text(json.dumps({"records": _records()}), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["sheet", "write-workbook", str(data_path), "--output", str(output_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "sheet.write.workbook"
    assert payload["usage"]["summary"]["record_count"] == 2
    assert output_path.exists()


def test_sheet_create_evidence_workbook_cli_accepts_json_records(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    data_path = tmp_path / "records.json"
    output_path = tmp_path / "evidence.xlsx"
    data_path.write_text(json.dumps({"records": _records()}), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["sheet", "create-evidence-workbook", str(data_path), "--output", str(output_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "sheet.create.evidence_workbook"
    assert payload["usage"]["summary"]["record_count"] == 2
    assert output_path.exists()


def test_sheet_write_workbook_runs_through_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import sheet_write_workbook
    from okoffice.workflows.runner import run_workflow

    api_output = tmp_path / "api.xlsx"
    mcp_output = tmp_path / "mcp.xlsx"
    workflow_output = tmp_path / "workflow.xlsx"

    response = TestClient(create_app()).post(
        "/v1/tools/sheet.write.workbook/run",
        json={"records": _records(), "output_path": str(api_output)},
    )
    mcp_payload = json.loads(sheet_write_workbook({"records": _records()}, str(mcp_output)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "sheet.write.workbook",
                    "input": {"records": _records(), "output_path": str(workflow_output)},
                }
            ]
        }
    )

    assert response.status_code == 200
    assert response.json()["tool"] == "sheet.write.workbook"
    assert api_output.exists()
    assert mcp_payload["tool"] == "sheet.write.workbook"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.write.workbook"


def test_sheet_create_evidence_workbook_runs_through_agent_interfaces(tmp_path: Path) -> None:
    from okoffice.api.app import create_app
    from okoffice.mcp.server import sheet_create_evidence_workbook
    from okoffice.workflows.runner import run_workflow

    api_output = tmp_path / "api-evidence.xlsx"
    mcp_output = tmp_path / "mcp-evidence.xlsx"
    workflow_output = tmp_path / "workflow-evidence.xlsx"

    response = TestClient(create_app()).post(
        "/v1/tools/sheet.create.evidence_workbook/run",
        json={"records": _records(), "output_path": str(api_output)},
    )
    mcp_payload = json.loads(sheet_create_evidence_workbook({"records": _records()}, str(mcp_output)))
    workflow = run_workflow(
        {
            "steps": [
                {
                    "tool": "sheet.create.evidence_workbook",
                    "input": {"records": _records(), "output_path": str(workflow_output)},
                }
            ]
        }
    )

    assert response.status_code == 200
    assert response.json()["tool"] == "sheet.create.evidence_workbook"
    assert api_output.exists()
    assert mcp_payload["tool"] == "sheet.create.evidence_workbook"
    assert mcp_output.exists()
    assert workflow.status == "succeeded"
    assert workflow_output.exists()
    assert workflow.usage["workflow_run"]["step_results"][0]["tool"] == "sheet.create.evidence_workbook"


def test_sheet_write_workbook_manifest_and_mcp_catalog_mark_tool_beta() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target_tools = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target_tools["sheet.write.workbook"]["status"] == "beta"
    assert target_tools["sheet.write.workbook"]["implemented"] is True
    assert target_tools["sheet.create.evidence_workbook"]["status"] == "beta"
    assert target_tools["sheet.create.evidence_workbook"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    catalog_tools = {tool["name"]: tool for tool in catalog["tools"]}
    assert catalog_tools["sheet_write_workbook"]["maps_to"] == "sheet.write.workbook"
    assert catalog_tools["sheet_create_evidence_workbook"]["maps_to"] == "sheet.create.evidence_workbook"


def _records() -> list[dict[str, object]]:
    return [
        {
            "source_path": "memo.docx",
            "source_format": "docx",
            "table_id": "word_table_1",
            "source_row_index": 1,
            "values": ["Name", "Value"],
            "source_refs": [{"document_path": "memo.docx", "table_index": 1, "row_index": 1}],
        },
        {
            "source_path": "model.xlsx",
            "source_format": "xlsx",
            "table_id": "sheet_1_table_1",
            "source_sheet": "Summary",
            "source_row_index": 2,
            "values": ["Alpha", "42"],
            "source_refs": [{"workbook_path": "model.xlsx", "sheet_name": "Summary", "cell_ref": "B2"}],
        },
    ]


def _sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    return [str(sheet.get("name")) for sheet in workbook.findall(".//main:sheet", SHEET_NS)]


def _inline_values(path: Path, member: str) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        worksheet = ElementTree.fromstring(archive.read(member))
    return [node.text or "" for node in worksheet.findall(".//main:t", SHEET_NS)]
