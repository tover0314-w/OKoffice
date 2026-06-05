import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_word_create_report_writes_valid_docx_from_evidence_workbook(tmp_path: Path) -> None:
    from okoffice.office.word import inspect_word_document
    from okoffice.office.word_report import create_word_report

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "memo.docx"

    result = create_word_report(
        workbook_path=workbook,
        output_path=output,
        title="Vendor Renewal Memo",
        profile="executive_memo",
    )

    assert result.status == "succeeded"
    assert result.tool == "word.create.report"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert output.exists()
    assert zipfile.is_zipfile(output)
    assert result.artifacts[0].path == output.resolve()
    assert result.usage["summary"] == {
        "paragraph_count": 6,
        "row_count": 1,
        "field_count": 4,
        "source_ref_count": 4,
    }
    assert result.usage["report_manifest"]["mutates_inputs"] is False
    assert "word.inspect.document" in result.next_recommended_tools

    document_xml = _read_zip_text(output, "word/document.xml")
    assert "Vendor Renewal Memo" in document_xml
    assert "Vendor: Acme Corp" in document_xml
    assert "Renewal date: 2026-09-30" in document_xml
    assert "Sources: ctx_001#p1, ctx_002#s1" in document_xml

    inspected = inspect_word_document(output)
    assert inspected.status == "succeeded"
    assert inspected.usage["summary"]["paragraph_count"] == 6
    assert inspected.usage["paragraphs"][0]["text"] == "Vendor Renewal Memo"


def test_okoffice_word_create_report_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "memo.docx"

    result = CliRunner().invoke(
        app,
        ["word", "create-report", "--from-workbook", str(workbook), "-o", str(output), "--title", "Vendor Renewal Memo", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "word.create.report"
    assert payload["usage"]["summary"]["source_ref_count"] == 4
    assert output.exists()


def test_word_create_report_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "memo.docx"

    response = TestClient(create_app()).post(
        "/v1/tools/word.create.report/run",
        json={"workbook_path": str(workbook), "output_path": str(output), "title": "Vendor Renewal Memo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "word.create.report"
    assert payload["usage"]["summary"]["row_count"] == 1


def test_word_create_report_runs_through_mcp_function(tmp_path: Path) -> None:
    from okoffice.mcp.server import word_create_report

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "memo.docx"

    payload = json.loads(word_create_report(str(workbook), str(output), title="Vendor Renewal Memo"))

    assert payload["tool"] == "word.create.report"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["summary"]["field_count"] == 4


def test_word_create_report_runs_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    workbook = _write_evidence_workbook(tmp_path)
    output = tmp_path / "memo.docx"

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "word.create.report",
                    "input": {"workbook_path": str(workbook), "output_path": str(output), "title": "Vendor Renewal Memo"},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "word.create.report"
    assert step["validation"]["status"] == "passed"


def _write_evidence_workbook(tmp_path: Path) -> Path:
    from okoffice.office.workbook import write_sheet_workbook

    evidence_path = tmp_path / "evidence.json"
    workbook_path = tmp_path / "evidence.xlsx"
    evidence_path.write_text(json.dumps(_evidence()), encoding="utf-8")
    result = write_sheet_workbook(evidence_path=evidence_path, output_path=workbook_path)
    assert result.status == "succeeded"
    return workbook_path


def _evidence() -> dict[str, object]:
    return {
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
                    "vendor": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "renewal_date": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "annual_amount": {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
                    "risk": {"source_ref": "ctx_002#s1", "source_type": "slide"},
                },
            }
        ],
        "source_refs": [
            {"source_ref": "ctx_001#p1", "source_type": "word_paragraph"},
            {"source_ref": "ctx_002#s1", "source_type": "slide"},
        ],
    }


def _read_zip_text(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read(member).decode("utf-8")
