import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner


def test_office_inspect_file_detects_pdf_fixture() -> None:
    from okoffice.office.inspect import inspect_office_file

    result = inspect_office_file(Path("tests/fixtures/simple.pdf"))

    assert result.status == "succeeded"
    assert result.tool == "office.inspect.file"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["format"]["detected_format"] == "pdf"
    assert result.usage["format"]["domain"] == "pdf"
    assert result.usage["file"]["sha256"]
    assert result.next_recommended_tools[:2] == ["pdf.inspect.document", "pdf.inspect.health"]


@pytest.mark.parametrize(
    ("filename", "member_name", "expected_format", "expected_domain", "expected_tool"),
    [
        ("memo.docx", "word/document.xml", "docx", "word", "word.inspect.document"),
        ("model.xlsx", "xl/workbook.xml", "xlsx", "sheet", "sheet.inspect.workbook"),
        ("deck.pptx", "ppt/presentation.xml", "pptx", "deck", "deck.inspect.presentation"),
    ],
)
def test_office_inspect_file_detects_ooxml_packages(
    tmp_path: Path,
    filename: str,
    member_name: str,
    expected_format: str,
    expected_domain: str,
    expected_tool: str,
) -> None:
    from okoffice.office.inspect import inspect_office_file

    path = tmp_path / filename
    _write_ooxml(path, member_name)

    result = inspect_office_file(path)

    assert result.status == "succeeded"
    assert result.usage["format"]["detected_format"] == expected_format
    assert result.usage["format"]["domain"] == expected_domain
    assert result.usage["format"]["package_type"] == f"ooxml_{expected_format}"
    assert result.usage["safety"]["macro_enabled"] is False
    assert expected_tool in result.next_recommended_tools


@pytest.mark.parametrize(
    ("filename", "contents", "expected_format", "expected_domain", "expected_mime"),
    [
        ("data.csv", "name,value\nalpha,1\n", "csv", "sheet", "text/csv"),
        ("notes.md", "# Notes\n\nA local markdown brief.\n", "markdown", "office", "text/markdown"),
        ("page.html", "<!doctype html><html><body>Hi</body></html>", "html", "office", "text/html"),
        ("brief.txt", "Plain text source", "text", "office", "text/plain"),
    ],
)
def test_office_inspect_file_detects_text_like_sources(
    tmp_path: Path,
    filename: str,
    contents: str,
    expected_format: str,
    expected_domain: str,
    expected_mime: str,
) -> None:
    from okoffice.office.inspect import inspect_office_file

    path = tmp_path / filename
    path.write_text(contents, encoding="utf-8")

    result = inspect_office_file(path)

    assert result.status == "succeeded"
    assert result.usage["format"]["detected_format"] == expected_format
    assert result.usage["format"]["domain"] == expected_domain
    assert result.usage["format"]["mime_type"] == expected_mime
    assert "office.context.build_packet" in result.next_recommended_tools


def test_office_inspect_file_rejects_path_traversal() -> None:
    from okoffice.office.inspect import inspect_office_file

    result = inspect_office_file(Path("..") / "secret.docx")

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    assert result.tool == "office.inspect.file"


def test_okoffice_inspect_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli_okoffice.main import app

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    result = CliRunner().invoke(app, ["inspect", str(path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["tool"] == "office.inspect.file"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["format"]["detected_format"] == "docx"
    assert "word.inspect.document" in payload["next_recommended_tools"]


def test_office_inspect_file_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from okoffice.api.app import create_app

    path = tmp_path / "model.xlsx"
    _write_ooxml(path, "xl/workbook.xml")

    response = TestClient(create_app()).post(
        "/v1/tools/office.inspect.file/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.inspect.file"
    assert payload["usage"]["format"]["detected_format"] == "xlsx"
    assert "sheet.inspect.workbook" in payload["next_recommended_tools"]


def test_office_inspect_file_runs_through_mcp_function(tmp_path: Path) -> None:
    from okoffice.mcp.server import office_inspect_file

    path = tmp_path / "deck.pptx"
    _write_ooxml(path, "ppt/presentation.xml")

    payload = json.loads(office_inspect_file(str(path)))

    assert payload["tool"] == "office.inspect.file"
    assert payload["status"] == "succeeded"
    assert payload["usage"]["format"]["detected_format"] == "pptx"


def test_office_inspect_file_runs_through_workflow_runner(tmp_path: Path) -> None:
    from okoffice.workflows.runner import run_workflow

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.inspect.file",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.inspect.file"
    assert step["status"] == "succeeded"
    assert "word.inspect.document" in step["next_recommended_tools"]


def _write_ooxml(path: Path, primary_member: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>",
        )
        archive.writestr(primary_member, "<root/>")
