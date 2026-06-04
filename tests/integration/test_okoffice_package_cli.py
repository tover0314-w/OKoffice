import json

from typer.testing import CliRunner


def test_okoffice_tools_list_json_exposes_target_and_compatibility_tools() -> None:
    from okoffice.cli.main import app

    result = CliRunner().invoke(app, ["tools", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    target_names = {tool["name"] for tool in payload["target_tools"]}
    compat_names = {tool["name"] for tool in payload["compatibility_tools"]}

    assert payload["product"] == "okoffice"
    assert "office.inspect.file" in target_names
    assert "word.inspect.document" in target_names
    assert "pdf.inspect.document" in compat_names
    assert all(tool["status"] == "legacy_compat" for tool in payload["compatibility_tools"])


def test_okoffice_version_command_uses_product_name() -> None:
    from okoffice.cli.main import app

    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.startswith("okoffice ")
