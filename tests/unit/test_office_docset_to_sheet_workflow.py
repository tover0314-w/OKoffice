import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_docset_to_sheet_workflow_builds_validated_evidence_workbook(tmp_path: Path) -> None:
    from agentpdf.office.sheet import inspect_sheet_workbook
    from agentpdf.office.workflows import docset_to_sheet

    source = tmp_path / "memo.docx"
    output = tmp_path / "vendor-evidence.xlsx"
    _write_labeled_docx(source)

    result = docset_to_sheet(files=[source], schema=_schema(), output_path=output)

    assert result.status == "succeeded"
    assert result.tool == "office.workflow.docset_to_sheet"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output.exists()
    assert (tmp_path / "vendor-evidence.context.json").exists()
    assert (tmp_path / "vendor-evidence.evidence.json").exists()

    summary = result.usage["summary"]
    assert summary == {
        "file_count": 1,
        "field_count": 4,
        "row_count": 1,
        "filled_value_count": 4,
        "artifact_count": 3,
        "workbook_validation_status": "passed",
    }
    assert [step["tool"] for step in result.usage["steps"]] == [
        "office.context.build_packet",
        "office.extract.schema",
        "sheet.write.workbook",
        "sheet.validation.formulas",
    ]
    assert result.usage["workflow"]["sidecars"]["context_packet_path"].endswith("vendor-evidence.context.json")
    assert result.usage["workflow"]["sidecars"]["evidence_path"].endswith("vendor-evidence.evidence.json")
    assert "office.workflow.sheet_to_deck" in result.next_recommended_tools

    inspected = inspect_sheet_workbook(output)
    assert inspected.status == "succeeded"
    assert inspected.usage["summary"]["table_count"] == 4
    sheet_xml = _read_zip_text(output, "xl/worksheets/sheet1.xml")
    assert "Acme Corp" in sheet_xml
    assert "2026-09-30" in sheet_xml
    assert "120000" in sheet_xml


def test_okoffice_docset_to_sheet_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    source = tmp_path / "memo.docx"
    schema_path = tmp_path / "schema.json"
    output = tmp_path / "vendor-evidence.xlsx"
    _write_labeled_docx(source)
    schema_path.write_text(json.dumps(_schema()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "workflow",
            "docset-to-sheet",
            "--file",
            str(source),
            "--schema",
            str(schema_path),
            "-o",
            str(output),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.workflow.docset_to_sheet"
    assert payload["usage"]["summary"]["filled_value_count"] == 4
    assert output.exists()


def test_docset_to_sheet_workflow_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    source = tmp_path / "memo.docx"
    output = tmp_path / "vendor-evidence.xlsx"
    _write_labeled_docx(source)

    response = TestClient(create_app()).post(
        "/v1/tools/office.workflow.docset_to_sheet/run",
        json={"files": [str(source)], "schema": _schema(), "output_path": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.workflow.docset_to_sheet"
    assert payload["usage"]["summary"]["workbook_validation_status"] == "passed"


def test_docset_to_sheet_workflow_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import office_workflow_docset_to_sheet

    source = tmp_path / "memo.docx"
    output = tmp_path / "vendor-evidence.xlsx"
    _write_labeled_docx(source)

    payload = json.loads(office_workflow_docset_to_sheet([str(source)], _schema(), str(output)))

    assert payload["tool"] == "office.workflow.docset_to_sheet"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["row_count"] == 1


def test_docset_to_sheet_workflow_runs_through_generic_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    source = tmp_path / "memo.docx"
    output = tmp_path / "vendor-evidence.xlsx"
    _write_labeled_docx(source)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.workflow.docset_to_sheet",
                    "input": {"files": [str(source)], "schema": _schema(), "output_path": str(output)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.workflow.docset_to_sheet"
    assert step["validation"]["status"] == "passed"


def _schema() -> dict[str, object]:
    return {
        "name": "vendor_renewal",
        "fields": [
            {"name": "vendor", "type": "string", "aliases": ["Vendor"]},
            {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"]},
            {"name": "annual_amount", "type": "number", "aliases": ["Annual amount"]},
            {"name": "risk", "type": "string", "aliases": ["Risk"]},
        ],
    }


def _write_labeled_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Vendor: Acme Corp</w:t></w:r></w:p>
    <w:p><w:r><w:t>Renewal date: 2026-09-30</w:t></w:r></w:p>
    <w:p><w:r><w:t>Annual amount: $120,000</w:t></w:r></w:p>
    <w:p><w:r><w:t>Risk: High</w:t></w:r></w:p>
  </w:body>
</w:document>
""",
        )


def _read_zip_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
