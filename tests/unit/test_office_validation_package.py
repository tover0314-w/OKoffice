import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
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


def test_validate_office_package_warns_when_relationship_scan_is_limited(tmp_path: Path) -> None:
    from agentpdf.office.validation import MAX_XML_SCAN_BYTES, validate_office_package

    path = tmp_path / "large-rels.docx"
    _write_ooxml(path, "word/document.xml")
    with zipfile.ZipFile(path, "a", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/_rels/document.xml.rels", " " * (MAX_XML_SCAN_BYTES + 1))

    result = validate_office_package(path)

    assert result.status == "succeeded"
    assert result.validation is not None
    assert result.validation.status == "warning"
    assert result.usage["scan_limited_members"] == [
        {"name": "word/_rels/document.xml.rels", "size_bytes": MAX_XML_SCAN_BYTES + 1}
    ]
    assert any("too large for local safety scan" in warning for warning in result.warnings)
    checks = {check.name: check.status for check in result.validation.checks}
    assert checks["safety_sensitive_xml_scan"] == "warning"


def test_validate_office_package_runs_through_agent_interfaces(tmp_path: Path) -> None:
    from agentpdf.api.app import create_app
    from agentpdf.mcp.server import office_validation_package
    from agentpdf.tools.runner import run_office_validation_package
    from okoffice.cli.main import app

    path = tmp_path / "memo.docx"
    _write_ooxml(path, "word/document.xml")

    runner_result = run_office_validation_package(path)
    response = TestClient(create_app()).post("/v1/tools/office.validation.package/run", json={"path": str(path)})
    mcp_payload = json.loads(office_validation_package(str(path)))
    cli_result = CliRunner().invoke(app, ["validate", "package", str(path), "--json"])

    assert runner_result.status == "succeeded"
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert mcp_payload["status"] == "succeeded"
    assert cli_result.exit_code == 0
    assert json.loads(cli_result.stdout)["tool"] == "office.validation.package"


def test_validate_office_package_manifest_and_mcp_catalog_mark_tool_beta() -> None:
    from okoffice.tools.registry import load_okoffice_manifest

    manifest = load_okoffice_manifest()
    target_tools = {tool["name"]: tool for tool in manifest["target_tools"]}
    assert target_tools["office.validation.package"]["status"] == "beta"
    assert target_tools["office.validation.package"]["implemented"] is True

    catalog = json.loads(Path("schemas/mcp-tools.catalog.json").read_text(encoding="utf-8"))
    catalog_tools = {tool["name"]: tool for tool in catalog["tools"]}
    assert catalog_tools["office_validation_package"]["maps_to"] == "office.validation.package"


def _write_ooxml(path: Path, primary_member: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>",
        )
        archive.writestr(primary_member, "<root/>")
