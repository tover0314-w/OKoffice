from __future__ import annotations

from pathlib import Path
from typing import Any

from agentpdf.office.deck import export_deck_pptx, render_deck_html, validate_deck_html_preview
from agentpdf.schemas.models import ToolResult


def render_html(plan_or_path: dict[str, Any] | str | Path, output_path: str | Path) -> ToolResult:
    return render_deck_html(plan_or_path, output_path)


def validate_html_preview(path: str | Path) -> ToolResult:
    return validate_deck_html_preview(path)


def export_pptx(html_path: str | Path, output_path: str | Path) -> ToolResult:
    return export_deck_pptx(html_path, output_path)
