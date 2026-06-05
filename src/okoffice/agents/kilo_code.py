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
    "agentpdf_tool_manifest",
    "pdf_context_build_packet",
    "pdf_target_profiles",
    "pdf_target_select_profile",
    "pdf_compose_from_context",
    "pdf_evidence_map_sources",
    "pdf_evidence_cite_claims",
    "pdf_evidence_coverage_report",
    "pdf_validation_render_check",
]


def setup_kilo_code(
    output_path: str | Path | None = None,
    safe_root: str = DEFAULT_SAFE_ROOT,
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> ToolResult:
    tool = "agent.setup.kilo_code"
    config = build_kilo_code_mcp_config(
        safe_root=safe_root,
        command=command,
        args_prefix=args_prefix,
        server_name=server_name,
    )
    usage: dict[str, Any] = {
        "agent": "kilo-code",
        "server_name": server_name,
        "safe_root": safe_root,
        "mcp_config": config,
        "recommended_config_files": ["kilo-code.mcp.json", ".kilocode/mcp.json"],
        "recommended_mcp_tools": RECOMMENDED_MCP_TOOLS,
        "starter_prompt": (
            "Use the local okoffice MCP server. Read the tool manifest, build a Context Packet, "
            "select a target profile, compose or edit the PDF, then run source-map, citation, "
            "coverage, and render validation before reporting success."
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
        next_recommended_tools=["agentpdf_tool_manifest", "pdf_target_profiles"],
    )


def build_kilo_code_mcp_config(
    safe_root: str = DEFAULT_SAFE_ROOT,
    command: str = "okoffice",
    args_prefix: list[str] | None = None,
    server_name: str = "okoffice",
) -> dict[str, Any]:
    command = command.strip()
    server_name = server_name.strip()
    safe_root = safe_root.strip()
    if not command:
        raise OKofficeException("unsafe_input_rejected", "Kilo Code MCP command cannot be empty.")
    if not server_name:
        raise OKofficeException("unsafe_input_rejected", "Kilo Code MCP server name cannot be empty.")
    if not safe_root:
        raise OKofficeException("unsafe_input_rejected", "Kilo Code safe root cannot be empty.")
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
