import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.mcp.server import create_mcp_server
from agentpdf.tools.registry import get_tool


runner = CliRunner()


def test_claude_code_setup_cli_writes_project_mcp_config(tmp_path: Path) -> None:
    output_path = tmp_path / ".mcp.json"

    result = runner.invoke(
        app,
        [
            "agent",
            "setup",
            "claude-code",
            "--output",
            str(output_path),
            "--safe-root",
            "${CLAUDE_PROJECT_DIR:-.}",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config = json.loads(output_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["agentpdf"]

    assert payload["tool"] == "agent.setup.claude_code"
    assert payload["usage"]["agent"] == "claude-code"
    assert payload["usage"]["scope"] == "project"
    assert payload["usage"]["config_path"] == output_path.as_posix()
    assert payload["usage"]["mcp_config"] == config
    assert server["type"] == "stdio"
    assert server["command"] == "okpdf"
    assert server["args"] == ["serve", "--mcp", "--safe-root", "${CLAUDE_PROJECT_DIR:-.}"]
    assert "pdf_context_build_packet" in payload["usage"]["recommended_mcp_tools"]
    assert "pdf_compose_from_context" in payload["usage"]["recommended_mcp_tools"]
    assert "pdf_ai_create_from_prompt" in payload["usage"]["recommended_mcp_tools"]
    assert payload["next_recommended_tools"] == ["agentpdf_tool_manifest", "pdf_target_profiles"]


def test_claude_code_setup_rest_and_mcp_are_exposed(tmp_path: Path) -> None:
    output_path = tmp_path / "claude-code.mcp.json"
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/agent.setup.claude_code/run",
        json={
            "output_path": str(output_path),
            "safe_root": "${CLAUDE_PROJECT_DIR:-.}",
            "command": "python",
            "args_prefix": ["-m", "agentpdf.cli"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    config = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["tool"] == "agent.setup.claude_code"
    assert config["mcpServers"]["agentpdf"]["command"] == "python"
    assert config["mcpServers"]["agentpdf"]["args"] == [
        "-m",
        "agentpdf.cli",
        "serve",
        "--mcp",
        "--safe-root",
        "${CLAUDE_PROJECT_DIR:-.}",
    ]

    tool_names = {tool.name for tool in asyncio.run(create_mcp_server().list_tools())}
    assert "agent_setup_claude_code" in tool_names
    assert get_tool("agent.setup.claude_code").implemented is True
