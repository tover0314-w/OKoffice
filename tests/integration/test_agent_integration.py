import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from agentpdf.api.app import create_app
from agentpdf.cli.main import app
from agentpdf.mcp.server import create_mcp_server
from agentpdf.tools.registry import get_tool
from okoffice.cli.main import app as okoffice_app


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
    assert "pdf_evidence_context_packet_report" in payload["usage"]["recommended_mcp_tools"]
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


def test_codex_setup_cli_writes_local_mcp_config(tmp_path: Path) -> None:
    output_path = tmp_path / "codex.mcp.json"

    result = runner.invoke(
        app,
        [
            "agent",
            "setup",
            "codex",
            "--output",
            str(output_path),
            "--safe-root",
            ".",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config = json.loads(output_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["agentpdf"]

    assert payload["tool"] == "agent.setup.codex"
    assert payload["usage"]["agent"] == "codex"
    assert payload["usage"]["config_path"] == output_path.as_posix()
    assert payload["usage"]["mcp_config"] == config
    assert server["command"] == "okpdf"
    assert server["args"] == ["serve", "--mcp", "--safe-root", "."]
    assert "AGENTS.md" in payload["usage"]["recommended_workspace_files"]
    assert "pdf_context_build_packet" in payload["usage"]["recommended_mcp_tools"]
    assert "pdf_ai_create_agent" in payload["usage"]["recommended_mcp_tools"]
    assert "pdf_evidence_context_packet_report" in payload["usage"]["recommended_mcp_tools"]
    assert "pdf_patch_plan" in payload["usage"]["recommended_mcp_tools"]
    assert payload["next_recommended_tools"] == ["agentpdf_tool_manifest", "pdf_target_profiles"]


def test_okoffice_codex_setup_cli_defaults_to_okoffice_mcp_server(tmp_path: Path) -> None:
    output_path = tmp_path / "codex.mcp.json"

    result = runner.invoke(
        okoffice_app,
        [
            "agent",
            "setup",
            "codex",
            "--output",
            str(output_path),
            "--safe-root",
            ".",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config = json.loads(output_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["okoffice"]

    assert payload["tool"] == "agent.setup.codex"
    assert payload["usage"]["server_name"] == "okoffice"
    assert payload["usage"]["mcp_config"] == config
    assert server["command"] == "okoffice"
    assert server["args"] == ["serve", "--mcp", "--safe-root", "."]


def test_codex_setup_rest_and_mcp_are_exposed(tmp_path: Path) -> None:
    output_path = tmp_path / "codex.mcp.json"
    client = TestClient(create_app())

    response = client.post(
        "/v1/tools/agent.setup.codex/run",
        json={
            "output_path": str(output_path),
            "safe_root": ".",
            "command": "python",
            "args_prefix": ["-m", "agentpdf.cli"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    config = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["tool"] == "agent.setup.codex"
    assert config["mcpServers"]["agentpdf"]["command"] == "python"
    assert config["mcpServers"]["agentpdf"]["args"] == [
        "-m",
        "agentpdf.cli",
        "serve",
        "--mcp",
        "--safe-root",
        ".",
    ]

    tool_names = {tool.name for tool in asyncio.run(create_mcp_server().list_tools())}
    assert "agent_setup_codex" in tool_names
    assert get_tool("agent.setup.codex").implemented is True


def test_kilo_code_setup_cli_writes_mcp_config(tmp_path: Path) -> None:
    output_path = tmp_path / "kilo-code.mcp.json"

    result = runner.invoke(
        app,
        [
            "agent",
            "setup",
            "kilo-code",
            "--output",
            str(output_path),
            "--safe-root",
            ".",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config = json.loads(output_path.read_text(encoding="utf-8"))
    server = config["mcpServers"]["agentpdf"]

    assert payload["tool"] == "agent.setup.kilo_code"
    assert payload["usage"]["agent"] == "kilo-code"
    assert payload["usage"]["mcp_config"] == config
    assert server["command"] == "okpdf"
    assert server["args"] == ["serve", "--mcp", "--safe-root", "."]
    assert "pdf_context_build_packet" in payload["usage"]["recommended_mcp_tools"]
    assert "kilo-code.mcp.json" in payload["usage"]["recommended_config_files"]


def test_openclaw_setup_cli_rest_and_mcp_are_exposed(tmp_path: Path) -> None:
    output_path = tmp_path / "openclaw.mcp.json"
    client = TestClient(create_app())

    cli = runner.invoke(
        app,
        [
            "agent",
            "setup",
            "openclaw",
            "--output",
            str(output_path),
            "--safe-root",
            ".",
            "--json",
        ],
    )
    response = client.post(
        "/v1/tools/agent.setup.openclaw/run",
        json={
            "output_path": str(tmp_path / "openclaw.api.json"),
            "safe_root": ".",
            "command": "python",
            "args_prefix": ["-m", "agentpdf.cli"],
        },
    )

    assert cli.exit_code == 0
    assert json.loads(cli.stdout)["tool"] == "agent.setup.openclaw"
    assert response.status_code == 200
    payload = response.json()
    config = json.loads((tmp_path / "openclaw.api.json").read_text(encoding="utf-8"))
    assert payload["tool"] == "agent.setup.openclaw"
    assert config["mcpServers"]["agentpdf"]["command"] == "python"
    assert config["mcpServers"]["agentpdf"]["args"] == [
        "-m",
        "agentpdf.cli",
        "serve",
        "--mcp",
        "--safe-root",
        ".",
    ]

    tool_names = {tool.name for tool in asyncio.run(create_mcp_server().list_tools())}
    assert "agent_setup_kilo_code" in tool_names
    assert "agent_setup_openclaw" in tool_names
    assert get_tool("agent.setup.kilo_code").implemented is True
    assert get_tool("agent.setup.openclaw").implemented is True
