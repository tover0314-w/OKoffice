import zipfile
from pathlib import Path

from typer.testing import CliRunner


def test_validate_office_package_passes_valid_docx(tmp_path: Path) -> None:
    from agentpdf.office.validation import validate_office_package

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    result = validate_office_package(path)

    assert result.status == "succeeded"
    assert result.tool == "office.validation.package"
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.warnings == []
    assert result.usage["summary"] == {
        "package_type": "ooxml_docx",
        "member_count": 2,
        "unsafe_member_count": 0,
        "warning_count": 0,
    }
    assert {check.name: check.status for check in result.validation.checks}["content_types_present"] == "passed"


def test_validate_office_package_rejects_unsafe_zip_member(tmp_path: Path) -> None:
    from agentpdf.office.validation import validate_office_package

    path = tmp_path / "unsafe.docx"
    _write_ooxml(path, "word/document.xml")
    with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("../evil.xml", "<evil/>")

    result = validate_office_package(path)

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == "unsafe_input_rejected"
    assert result.validation is not None
    assert result.validation.status == "failed"
    assert result.usage["summary"]["unsafe_member_count"] == 1
    assert result.usage["unsafe_members"] == ["../evil.xml"]


def test_validate_office_package_warns_for_macros_and_external_relationships(tmp_path: Path) -> None:
    from agentpdf.office.validation import validate_office_package

    path = tmp_path / "macro.docm"
    _write_ooxml(path, "word/document.xml")
    with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/vbaProject.bin", b"macro marker")
        archive.writestr(
            "word/_rels/document.xml.rels",
            (
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="hyperlink" Target="https://example.test" '
                'TargetMode="External"/>'
                "</Relationships>"
            ),
        )

    result = validate_office_package(path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["summary"]["package_type"] == "ooxml_docx"
    assert result.usage["summary"]["warning_count"] == 2
    assert any("Macro-enabled" in warning for warning in result.warnings)
    assert any("External Office relationship targets" in warning for warning in result.warnings)
    checks = {check.name: check.status for check in result.validation.checks}
    assert checks["macros_not_executed"] == "warning"
    assert checks["external_relationships"] == "warning"


def test_office_validation_package_runner_returns_tool_result(tmp_path: Path) -> None:
    from agentpdf.tools.runner import run_office_validation_package

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    result = run_office_validation_package(path)

    assert result.status == "succeeded"
    assert result.tool == "office.validation.package"
    assert result.validation is not None
    assert result.validation.status == "passed"


def test_okoffice_validation_package_cli_returns_tool_result_json(tmp_path: Path) -> None:
    from okoffice.cli.main import app

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    result = CliRunner().invoke(app, ["validation", "package", str(path), "--json"])

    assert result.exit_code == 0
    payload = result.stdout
    assert '"tool":"office.validation.package"' in payload
    assert '"status":"succeeded"' in payload


def test_office_validation_package_runs_through_rest_api(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from agentpdf.api.app import create_app

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    response = TestClient(create_app()).post(
        "/v1/tools/office.validation.package/run",
        json={"path": str(path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool"] == "office.validation.package"
    assert payload["validation"]["status"] == "passed"


def test_office_validation_package_runs_through_mcp_function(tmp_path: Path) -> None:
    import json

    from agentpdf.mcp.server import office_validation_package

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    payload = json.loads(office_validation_package(str(path)))

    assert payload["tool"] == "office.validation.package"
    assert payload["validation"]["status"] == "passed"


def test_office_validation_package_runs_through_workflow_runner(tmp_path: Path) -> None:
    from agentpdf.workflows.runner import run_workflow

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    result = run_workflow(
        {
            "steps": [
                {
                    "tool": "office.validation.package",
                    "input": {"path": str(path)},
                }
            ]
        }
    )

    assert result.status == "succeeded"
    step = result.usage["workflow_run"]["step_results"][0]
    assert step["tool"] == "office.validation.package"
    assert step["validation"]["status"] == "passed"


def _write_ooxml(path: Path, primary_member: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>",
        )
        archive.writestr(primary_member, "<root/>")
