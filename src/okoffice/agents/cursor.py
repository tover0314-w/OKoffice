from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from okoffice.artifacts.store import build_artifact
from okoffice.schemas.errors import OKofficeException
from okoffice.schemas.models import ToolResult
from okoffice.security.paths import resolve_output_path

DEFAULT_SAFE_ROOT = "."
RECOMMENDED_MCP_TOOLS = [
    "okoffice_tool_manifest",
    "office_inspect_file",
    "pdf_context_build_packet",
    "pdf_compose_from_context",
    "pdf_patch_plan",
    "pdf_patch_apply",
    "pdf_render_check",
    "office_workflow_source_to_deck",
]


def setup_cursor(
    output_path: str | Path | None = None,
    safe_root: str = DEFAULT_SAFE_ROOT,
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> ToolResult:
    tool = "agent.setup.cursor"
    config = build_cursor_mcp_config(
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    )
    usage: dict[str, Any] = {
        "agent": "cursor",
        "server_name": server_name,
        "safe_root": safe_root,
        "mcp_config": config,
        "recommended_config_files": [".cursor/mcp.json"],
        "recommended_mcp_tools": RECOMMENDED_MCP_TOOLS,
        "starter_prompt": (
            "Use the local okoffice MCP server for document operations. "
            "Keep all outputs explicit, validate every generated artifact."
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
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
        usage["config_path"] = destination.as_posix()
    return ToolResult(
        job_id=f"job_{uuid4().hex[:12]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage=usage,
        next_recommended_tools=["okoffice_tool_manifest", "office_inspect_file"],
    )


def build_cursor_mcp_config(
    safe_root: str = DEFAULT_SAFE_ROOT,
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> dict[str, Any]:
    command = command.strip()
    server_name = server_name.strip()
    safe_root = safe_root.strip()
    if not command:
        raise OKofficeException("unsafe_input_rejected", "Cursor MCP command cannot be empty.")
    if not server_name:
        raise OKofficeException("unsafe_input_rejected", "Cursor MCP server name cannot be empty.")
    prefix = [str(arg) for arg in (args_prefix or []) if str(arg)]
    return {
        "mcpServers": {
            server_name: {
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
