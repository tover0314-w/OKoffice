from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_output_path

DEFAULT_SAFE_ROOT = "${CLAUDE_PROJECT_DIR:-.}"
RECOMMENDED_MCP_TOOLS = [
    "okoffice_tool_manifest",
    "pdf_ai_create_templates",
    "pdf_ai_create_from_prompt",
    "pdf_context_build_packet",
    "pdf_target_profiles",
    "pdf_target_validate_profile",
    "pdf_compose_from_context",
    "pdf_evidence_coverage_report",
    "pdf_evidence_context_packet_report",
    "pdf_patch_plan",
    "pdf_patch_apply",
    "pdf_patch_verify",
    "pdf_render_check",
]


def setup_claude_code(
    output_path: str | Path | None = None,
    safe_root: str = DEFAULT_SAFE_ROOT,
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
    scope: Literal["project", "local", "user"] = "project",
) -> ToolResult:
    """Build a Claude Code MCP config for the local OKoffice server."""
    tool = "agent.setup.claude_code"
    if scope not in {"project", "local", "user"}:
        raise OKofficeException(
            "unsafe_input_rejected",
            "Claude Code MCP scope must be project, local, or user.",
        )
    config = build_claude_code_mcp_config(
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    )
    usage: dict[str, Any] = {
        "agent": "claude-code",
        "scope": scope,
        "server_name": server_name,
        "safe_root": safe_root,
        "mcp_config": config,
        "recommended_mcp_tools": RECOMMENDED_MCP_TOOLS,
        "install_commands": _install_commands(
            command=command,
            args=config["mcpServers"][server_name]["args"],
            server_name=server_name,
            scope=scope,
        ),
        "starter_prompt": (
            "Use the okoffice MCP server. First call okoffice_tool_manifest, then build a "
            "context packet, inspect target profiles, compose the PDF, and run render/evidence "
            "validation before reporting success."
        ),
        "local_boundaries": {
            "cloud_required": False,
            "writes_only_explicit_outputs": True,
            "recommended_safe_root": safe_root,
        },
    }
    artifacts = []
    if output_path is not None:
        destination = resolve_output_path(output_path)
        destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
        usage["config_path"] = destination.as_posix()
    return ToolResult(
        job_id=f"job_{uuid4().hex[:12]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage=usage,
        next_recommended_tools=["okoffice_tool_manifest", "pdf_target_profiles"],
    )


def build_claude_code_mcp_config(
    safe_root: str = DEFAULT_SAFE_ROOT,
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> dict[str, Any]:
    command = command.strip()
    server_name = server_name.strip()
    safe_root = safe_root.strip()
    if not command:
        raise OKofficeException("unsafe_input_rejected", "Claude Code MCP command cannot be empty.")
    if not server_name:
        raise OKofficeException("unsafe_input_rejected", "Claude Code MCP server name cannot be empty.")
    if not safe_root:
        raise OKofficeException("unsafe_input_rejected", "Claude Code safe root cannot be empty.")
    prefix = [str(arg) for arg in (args_prefix or []) if str(arg)]
    return {
        "mcpServers": {
            server_name: {
                "type": "stdio",
                "command": command,
                "args": [
                    *prefix,
                    "serve",
                    "--mcp",
                    "--safe-root",
                    safe_root,
                ],
            }
        }
    }


def _install_commands(command: str, args: list[str], server_name: str, scope: str) -> list[str]:
    quoted_args = " ".join(_quote_cli_arg(arg) for arg in args)
    return [
        f"claude mcp add --scope {scope} {server_name} -- {command} {quoted_args}",
        "claude mcp list",
        "/mcp",
    ]


def _quote_cli_arg(value: str) -> str:
    if not value or any(char.isspace() for char in value):
        return json.dumps(value)
    return value
