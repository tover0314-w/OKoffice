import json
from pathlib import Path

from typer.testing import CliRunner

from tests.unit.test_word_inspect import _write_docx_fixture


def test_word_document_validation_returns_structural_baseline(tmp_path: Path) -> None:
    from agentpdf.office.word_validation import validate_word_document

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    result = validate_word_document(path)

    assert result.status == "succeeded"
    assert result.tool == "word.validation.document"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"] == {
        "paragraph_count": 4,
        "heading_count": 2,
        "table_count": 1,
        "comment_count": 1,
        "tracked_change_count": 1,
        "field_count": 1,
        "style_count": 3,
        "section_count": 1,
        "metadata_title_present": True,
        "macro_enabled": False,
        "has_external_relationships": True,
    }
    assert result.usage["render_evidence"]["status"] == "skipped"
    assert result.usage["render_evidence"]["required_worker"] == "docx_render_preview_worker"
    assert result.usage["accessibility_hints"]["status"] == "warning"
    assert "Document contains unresolved comments: 1." in result.warnings
    assert "Document contains tracked changes: 1." in result.warnings

    checks = {check.name: check for check in result.validation.checks}
    assert checks["package_validation"].status == "warning"
    assert checks["document_reopened_by_inspect"].status == "passed"
    assert checks["comments_policy"].status == "warning"
    assert checks["tracked_changes_policy"].status == "warning"
    assert checks["metadata_title_present"].status == "passed"
    assert checks["render_preview_evidence"].status == "skipped"
    assert "word.inspect.document" in result.next_recommended_tools


def test_okoffice_word_validate_document_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    result = CliRunner().invoke(app, ["word", "validate-document", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "word.validation.document"
    assert payload["usage"]["summary"]["comment_count"] == 1


def test_word_document_validation_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    response = TestClient(create_app()).post(
        "/v1/tools/word.validation.document/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "word.validation.document"
    assert payload["usage"]["summary"]["tracked_change_count"] == 1


def test_word_document_validation_runs_through_mcp_function(tmp_path: Path) -> None:
    from agentpdf.mcp.server import word_validate_document

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    payload = json.loads(word_validate_document(str(path)))

    assert payload["tool"] == "word.validation.document"
    assert payload["status"] == "succeeded"
    assert payload["validation"]["status"] == "warning"


def test_word_document_validation_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    path = tmp_path / "memo.docx"
    _write_docx_fixture(path)

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "word.validation.document",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "word.validation.document"
    assert step["validation"]["status"] == "warning"
