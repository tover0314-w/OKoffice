from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolManifest, ToolSpec

IMPLEMENTED_TOOLS = {
    "pdf.inspect.document",
    "pdf.organize.merge",
    "pdf.organize.split",
    "pdf.organize.extract_pages",
    "pdf.organize.remove_pages",
    "pdf.organize.rotate_pages",
    "pdf.convert.image_to_pdf",
    "pdf.convert.markdown_to_pdf",
    "pdf.convert.text_to_pdf",
    "pdf.convert.pdf_to_images",
    "pdf.convert.pdf_to_text",
    "pdf.edit.watermark",
    "pdf.edit.page_numbers",
    "pdf.metadata.read",
    "pdf.metadata.update",
    "pdf.metadata.remove",
    "pdf.validation.validate_output",
}


@lru_cache(maxsize=1)
def load_tool_manifest() -> ToolManifest:
    manifest_path = _repo_root() / "schemas" / "tool-manifest.full.json"
    if manifest_path.exists():
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        tools = [_tool_spec_from_raw(item) for item in raw.get("tools", [])]
        return ToolManifest(
            manifest_version=str(raw.get("manifest_version", "0.1")),
            tools=tools,
        )
    return _fallback_manifest()


def list_tools() -> list[ToolSpec]:
    return load_tool_manifest().tools


def get_tool(name: str) -> ToolSpec:
    for tool in list_tools():
        if tool.name == name:
            return tool
    raise AgentPDFException("tool_not_implemented", f"Unknown tool: {name}")


def _tool_spec_from_raw(raw: dict[str, Any]) -> ToolSpec:
    name = str(raw["name"])
    return ToolSpec(
        name=name,
        status=raw["status"],
        description=raw["description"],
        category=raw.get("category"),
        interfaces=list(raw.get("interfaces", [])),
        input_schema=raw.get("input_schema"),
        output_schema=raw.get("output_schema"),
        implemented=name in IMPLEMENTED_TOOLS,
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _fallback_manifest() -> ToolManifest:
    return ToolManifest(
        tools=[
            ToolSpec(
                name="pdf.inspect.document",
                status="stable",
                description="Inspect a PDF document.",
                category="inspect",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.organize.merge",
                status="stable",
                description="Merge multiple PDFs.",
                category="organize",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.organize.split",
                status="stable",
                description="Split or extract selected PDF pages.",
                category="organize",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.organize.extract_pages",
                status="stable",
                description="Extract specific pages into a new PDF.",
                category="organize",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.organize.remove_pages",
                status="stable",
                description="Remove selected pages.",
                category="organize",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.organize.rotate_pages",
                status="stable",
                description="Rotate selected pages.",
                category="organize",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.convert.image_to_pdf",
                status="stable",
                description="Create a PDF from local image files.",
                category="convert_to_pdf",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.convert.markdown_to_pdf",
                status="stable",
                description="Create a PDF from Markdown content.",
                category="convert_to_pdf",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.convert.text_to_pdf",
                status="stable",
                description="Create a PDF from plain text content.",
                category="convert_to_pdf",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.convert.pdf_to_images",
                status="stable",
                description="Render PDF pages to images.",
                category="convert",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.convert.pdf_to_text",
                status="stable",
                description="Extract text from PDF pages.",
                category="convert_from_pdf",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.edit.watermark",
                status="stable",
                description="Add a text watermark overlay.",
                category="edit",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.edit.page_numbers",
                status="stable",
                description="Add page number overlays.",
                category="edit",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.metadata.read",
                status="stable",
                description="Read document metadata.",
                category="metadata",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.metadata.update",
                status="stable",
                description="Update document metadata.",
                category="metadata",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.metadata.remove",
                status="stable",
                description="Remove document metadata.",
                category="metadata",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
            ToolSpec(
                name="pdf.validation.validate_output",
                status="stable",
                description="Validate generated PDF output.",
                category="validation",
                interfaces=["cli", "mcp", "rest", "sdk"],
                implemented=True,
            ),
        ]
    )
