import json
import asyncio

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


def test_okoffice_claude_code_setup_writes_okoffice_mcp_config(tmp_path) -> None:
    from okoffice.cli.main import app

    output_path = tmp_path / ".mcp.json"

    result = CliRunner().invoke(
        app,
        [
            "agent",
            "setup",
            "claude-code",
            "--output",
            str(output_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config = json.loads(output_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["okoffice"]

    assert payload["tool"] == "office.agent.setup.claude_code"
    assert payload["usage"]["agent"] == "claude-code"
    assert payload["usage"]["product"] == "okoffice"
    assert payload["usage"]["mcp_config"] == config
    assert server["type"] == "stdio"
    assert server["command"] == "okoffice"
    assert server["args"] == ["serve", "--mcp", "--safe-root", "${CLAUDE_PROJECT_DIR:-.}"]
    assert "okoffice_tool_manifest" in payload["usage"]["recommended_mcp_tools"]
    assert "deck_render_html" in payload["usage"]["recommended_mcp_tools"]
    assert payload["next_recommended_tools"] == [
        "okoffice_tool_manifest",
        "office_context_build_packet",
        "office_workflow_extract_to_sheet",
    ]


def test_okoffice_serve_help_and_mcp_manifest_alias_are_available() -> None:
    from agentpdf.mcp.server import create_mcp_server, okoffice_tool_manifest
    from okoffice.cli.main import app

    help_result = CliRunner().invoke(app, ["serve", "--help"])
    tool_names = {tool.name for tool in asyncio.run(create_mcp_server().list_tools())}
    manifest = json.loads(okoffice_tool_manifest())

    assert help_result.exit_code == 0
    assert "Run the local OKoffice MCP server or REST API" in help_result.stdout
    assert "okoffice_tool_manifest" in tool_names
    assert manifest["product"] == "okoffice"
    assert any(tool["name"] == "deck.render.html" for tool in manifest["target_tools"])
