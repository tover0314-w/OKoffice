from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from okoffice.tools.registry import load_tool_manifest


@lru_cache(maxsize=1)
def load_okoffice_manifest() -> dict[str, Any]:
    target_manifest = _load_target_manifest()
    target_tools = list(target_manifest.get("target_tools", []))
    compatibility_tools = [_legacy_tool(tool.model_dump(mode="json")) for tool in load_tool_manifest().tools]
    return {
        **target_manifest,
        "target_tools": target_tools,
        "compatibility_manifest": {
            "product": "okoffice",
            "namespace": "pdf",
            "role": "legacy_compat",
            "surface": "slim_summary",
        },
        "compatibility_tools": compatibility_tools,
        "summary": {
            "target_tool_count": len(target_tools),
            "compatibility_tool_count": len(compatibility_tools),
            "implemented_target_tool_count": sum(
                1 for tool in target_tools if tool.get("implemented") is True
            ),
            "implemented_compatibility_tool_count": sum(1 for tool in compatibility_tools if tool.get("implemented") is True),
        },
    }


def _load_target_manifest() -> dict[str, Any]:
    manifest_path = _repo_root() / "schemas" / "office-tool-manifest.target.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["target_tools"] = _merge_tools(
        list(raw.get("target_tools") or []),
        list(raw.get("tools") or []),
    )
    raw["tool_count"] = len(raw["target_tools"])
    return raw


def _merge_tools(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for group in groups:
        for tool in group:
            name = str(tool.get("name") or "")
            if name and name not in by_name:
                by_name[name] = dict(tool)
    return list(by_name.values())


def _legacy_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(tool["name"]),
        "status": "legacy_compat",
        "description": str(tool.get("description") or ""),
        "category": tool.get("category"),
        "interfaces": list(tool.get("interfaces") or []),
        "implemented": bool(tool.get("implemented")),
        "compatibility_source": "agentpdf",
        "compatibility_status": str(tool.get("status") or ""),
        "compatibility_boundary": "pdf.*",
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
