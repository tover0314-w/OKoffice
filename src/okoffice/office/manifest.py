from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from okoffice.office.models import OfficeToolManifest


@lru_cache(maxsize=1)
def load_office_tool_manifest() -> OfficeToolManifest:
    manifest_path = _repo_root() / "schemas" / "office-tool-manifest.target.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    return OfficeToolManifest.model_validate(_normalized_manifest(raw))


def _normalized_manifest(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(raw)
    merged_tools = _merge_tools(
        list(raw.get("target_tools") or []),
        list(raw.get("tools") or []),
    )
    normalized["tools"] = merged_tools
    normalized["tool_count"] = len(merged_tools)
    return normalized


def _merge_tools(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for group in groups:
        for tool in group:
            name = str(tool.get("name") or "")
            if name and name not in by_name:
                by_name[name] = dict(tool)
    return list(by_name.values())


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
