import json
import tomllib
from pathlib import Path

from okoffice.tools.registry import load_tool_manifest


def test_okoffice_target_manifest_separates_target_and_legacy_tools() -> None:
    from okoffice.tools.registry_okoffice import load_okoffice_manifest

    manifest = load_okoffice_manifest()

    assert manifest["product"] == "okoffice"
    assert manifest["manifest_version"] == "0.1"
    assert manifest["compatibility_manifest"]["product"] == "okoffice"
    assert manifest["compatibility_manifest"]["namespace"] == "pdf"
    assert manifest["compatibility_manifest"]["role"] == "legacy_compat"
    assert manifest["compatibility_manifest"]["surface"] == "slim_summary"
    target_names = {tool["name"] for tool in manifest["target_tools"]}
    compat_by_name = {tool["name"]: tool for tool in manifest["compatibility_tools"]}

    assert {"office.inspect.file", "word.inspect.document", "sheet.inspect.workbook", "deck.inspect.presentation"} <= target_names
    assert compat_by_name["pdf.inspect.document"]["status"] == "legacy_compat"
    assert compat_by_name["pdf.inspect.document"]["implemented"] is True
    assert compat_by_name["pdf.inspect.document"]["compatibility_source"] == "agentpdf"
    assert compat_by_name["pdf.inspect.document"]["compatibility_boundary"] == "pdf.*"
    assert len(manifest["compatibility_tools"]) == len(load_tool_manifest().tools)


def test_okoffice_machine_manifest_file_is_json_and_declares_first_wave() -> None:
    manifest_path = Path("schemas/office-tool-manifest.target.json")
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert raw["product"] == "okoffice"
    assert raw["namespace_strategy"]["legacy_pdf_namespace"] == "pdf.*"
    assert raw["namespace_strategy"]["target_cross_format_namespace"] == "office.*"
    assert any(tool["name"] == "office.inspect.file" for tool in raw["target_tools"])


def test_pyproject_exposes_okoffice_console_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["okoffice"] == "okoffice.cli_okoffice.main:app"
    assert pyproject["project"]["scripts"]["okpdf"] == "okoffice.cli.main:app"
