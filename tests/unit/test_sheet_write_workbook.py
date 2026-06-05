import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_sheet_write_workbook_creates_valid_evidence_xlsx(tmp_path: Path) -> None:
    from agentpdf.office.sheet import inspect_sheet_workbook
    from agentpdf.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    _write_evidence(evidence_path)

    result = write_sheet_workbook(evidence_path=evidence_path, output_path=output_path)

    assert result.status == "succeeded"
    assert result.tool == "sheet.write.workbook"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output_path.exists()
    assert zipfile.is_zipfile(output_path)
    assert result.artifacts[0].path == output_path.resolve()

    summary = result.usage["summary"]
    assert summary == {
        "row_count": 1,
        "field_count": 4,
        "sheet_count": 4,
        "source_map_count": 4,
        "data_model_count": 4,
        "chart_plan_count": 2,
    }
    assert result.usage["sheets"][0]["name"] == "Evidence"
    assert result.usage["sheets"][0]["range"] == "A1:D2"
    assert result.usage["sheets"][1]["name"] == "SourceMap"
    assert result.usage["sheets"][1]["range"] == "A1:G5"
    assert result.usage["sheets"][2]["name"] == "DataModel"
    assert result.usage["sheets"][3]["name"] == "Charts"
    assert result.usage["workbook_manifest"]["mutates_inputs"] is False
    assert "sheet.inspect.workbook" in result.next_recommended_tools

    with zipfile.ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        assert "xl/worksheets/sheet3.xml" in names
        assert "xl/worksheets/sheet4.xml" in names
        assert "xl/tables/table1.xml" in names
        assert "xl/tables/table2.xml" in names
        assert "xl/tables/table3.xml" in names
        assert "xl/tables/table4.xml" in names
        sheet1 = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        sheet2 = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
        sheet3 = archive.read("xl/worksheets/sheet3.xml").decode("utf-8")
        sheet4 = archive.read("xl/worksheets/sheet4.xml").decode("utf-8")
        assert "Acme Corp" in sheet1
        assert "2026-09-30" in sheet1
        assert "ctx_001#p1" in sheet2
        assert "annual_amount" in sheet3
        assert "risk_distribution" in sheet4

    inspected = inspect_sheet_workbook(output_path)
    assert inspected.status == "succeeded"
    assert inspected.validation is not None
    assert inspected.validation.status == "passed"
    assert inspected.usage["summary"]["sheet_count"] == 4
    assert inspected.usage["summary"]["table_count"] == 4
    assert inspected.usage["sheets"][0]["used_range"] == "A1:D2"


def test_okoffice_sheet_write_workbook_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    _write_evidence(evidence_path)

    result = CliRunner().invoke(
        app,
        ["sheet", "write-workbook", str(evidence_path), "-o", str(output_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "sheet.write.workbook"
    assert payload["usage"]["summary"]["source_map_count"] == 4
    assert output_path.exists()


def test_sheet_write_workbook_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    _write_evidence(evidence_path)

    response = TestClient(create_app()).post(
        "/v1/tools/sheet.write.workbook/run",
        json={"evidence_path": str(evidence_path), "output_path": str(output_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "sheet.write.workbook"
    assert payload["usage"]["sheets"][0]["name"] == "Evidence"


def test_sheet_write_workbook_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import sheet_write_workbook

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    _write_evidence(evidence_path)

    payload = json.loads(sheet_write_workbook(str(evidence_path), str(output_path)))

    assert payload["tool"] == "sheet.write.workbook"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["field_count"] == 4


def test_sheet_write_workbook_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "evidence.xlsx"
    _write_evidence(evidence_path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "sheet.write.workbook",
                    "input": {"evidence_path": str(evidence_path), "output_path": str(output_path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "sheet.write.workbook"
    assert step["status"] == "succeeded"
    assert "sheet.inspect.workbook" in step["next_recommended_tools"]


def _write_evidence(path: Path) -> None:
    extraction = {
        "extraction_id": "extract_test",
        "schema_name": "vendor_renewal",
        "fields": [
            {"name": "vendor", "type": "string", "aliases": ["Vendor"], "required": True},
            {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"], "required": True},
            {"name": "annual_amount", "type": "number", "aliases": ["Annual amount"], "required": True},
            {"name": "risk", "type": "string", "aliases": ["Risk"], "required": False},
        ],
        "rows": [
            {
                "row_id": "row_001",
                "values": {
                    "vendor": "Acme Corp",
                    "renewal_date": "2026-09-30",
                    "annual_amount": "120000",
                    "risk": "High",
                },
                "field_evidence": {
                    "vendor": {
                        "source_ref": "ctx_001#p1",
                        "source_id": "src_002",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Vendor: Acme Corp",
                        "confidence": 0.95,
                    },
                    "renewal_date": {
                        "source_ref": "ctx_001#p1",
                        "source_id": "src_002",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Renewal date: 2026-09-30",
                        "confidence": 0.95,
                    },
                    "annual_amount": {
                        "source_ref": "ctx_001#p1",
                        "source_id": "src_002",
                        "source_type": "word_paragraph",
                        "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
                        "excerpt": "Annual amount: $120,000",
                        "confidence": 0.95,
                    },
                    "risk": {
                        "source_ref": "ctx_002#s1",
                        "source_id": "src_004",
                        "source_type": "slide",
                        "locator": {"kind": "deck", "slide": 1, "slide_id": "256"},
                        "excerpt": "Risk: High",
                        "confidence": 0.95,
                    },
                },
            }
        ],
        "source_refs": [
            {
                "source_ref": "ctx_001#p1",
                "source_id": "src_002",
                "source_type": "word_paragraph",
                "locator": {"kind": "word", "paragraph_id": "p_0001", "paragraph_index": 0},
            },
            {
                "source_ref": "ctx_002#s1",
                "source_id": "src_004",
                "source_type": "slide",
                "locator": {"kind": "deck", "slide": 1, "slide_id": "256"},
            },
        ],
        "method": "local_label_value_match_v0",
    }
    path.write_text(json.dumps(extraction), encoding="utf-8")
