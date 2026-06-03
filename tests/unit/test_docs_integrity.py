import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_chinese_readme_is_readable_utf8_and_mentions_current_tool_count() -> None:
    readme_text = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    english_readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    tool_manifest = json.loads(
        (REPO_ROOT / "schemas" / "tool-manifest.full.json").read_text(encoding="utf-8")
    )
    tool_count = str(tool_manifest["tool_count"])

    assert "\u672c\u5730\u4f18\u5148" in readme_text
    assert tool_count in readme_text
    assert tool_count in english_readme_text
    assert "\u4e2d\u6587\u8bf4\u660e" in readme_text
    assert "\u6d93" not in readme_text
    assert "\u9286" not in readme_text


def test_harness_manifest_tool_count_matches_full_manifest() -> None:
    harness = json.loads((REPO_ROOT / "HARNESS_MANIFEST.json").read_text(encoding="utf-8"))
    tool_manifest = json.loads(
        (REPO_ROOT / "schemas" / "tool-manifest.full.json").read_text(encoding="utf-8")
    )

    assert harness["total_tool_manifest_count"] == tool_manifest["tool_count"]


def test_complete_tool_catalog_covers_full_manifest() -> None:
    catalog_text = (REPO_ROOT / "docs" / "05_COMPLETE_TOOL_CATALOG.md").read_text(encoding="utf-8")
    catalog_tools = set()
    for line in catalog_text.splitlines():
        if line.startswith("| `"):
            catalog_tools.add(line.split("`", 2)[1])
    tool_manifest = json.loads(
        (REPO_ROOT / "schemas" / "tool-manifest.full.json").read_text(encoding="utf-8")
    )
    manifest_tools = {tool["name"] for tool in tool_manifest["tools"]}

    assert sorted(manifest_tools - catalog_tools) == []
    assert sorted(catalog_tools - manifest_tools) == []


def test_example_tool_manifest_statuses_match_full_manifest() -> None:
    full_manifest = json.loads(
        (REPO_ROOT / "schemas" / "tool-manifest.full.json").read_text(encoding="utf-8")
    )
    example_manifest = json.loads(
        (REPO_ROOT / "schemas" / "tool-manifest.example.json").read_text(encoding="utf-8")
    )
    full_by_name = {tool["name"]: tool for tool in full_manifest["tools"]}

    for example_tool in example_manifest["tools"]:
        full_tool = full_by_name[example_tool["name"]]
        assert example_tool["status"] == full_tool["status"]
        assert example_tool["implemented"] == full_tool["implemented"]
