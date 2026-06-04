from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.office.inspect import inspect_office_file
from agentpdf.office.ooxml import DECK_NS, count_members, read_xml, sorted_members, zip_names
from agentpdf.schemas.models import AgentPDFError, ToolResult, ValidationCheck, ValidationReport


TOOL_NAME = "deck.inspect.presentation"


def inspect_deck_presentation(path: str | Path) -> ToolResult:
    preflight = inspect_office_file(path)
    if preflight.status == "failed":
        return _failed(preflight.error or AgentPDFError(code="unsupported_file_type", message="Deck inspect failed."))
    if preflight.usage["format"]["detected_format"] != "pptx":
        return _failed(
            AgentPDFError(
                code="unsupported_file_type",
                message="deck.inspect.presentation requires a PPTX-compatible OOXML package.",
                details={"detected_format": preflight.usage["format"]["detected_format"]},
            )
        )

    source_path = Path(preflight.usage["file"]["path"])
    names = zip_names(source_path)
    slide_members = sorted_members(names, prefix="ppt/slides/slide")
    text_run_count = _slide_text_run_count(source_path, slide_members)

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=TOOL_NAME,
        validation=ValidationReport(
            status="passed",
            checks=[
                ValidationCheck(name="format_is_pptx", status="passed", details=preflight.usage["format"]),
                ValidationCheck(name="presentation_xml_present", status="passed"),
            ],
        ),
        usage={
            "presentation": {
                "path": source_path.as_posix(),
                "format": "pptx",
                "package_type": preflight.usage["format"]["package_type"],
                "slide_count": len(slide_members),
                "text_run_count": text_run_count,
            },
            "notes": {"notes_slide_count": count_members(names, prefix="ppt/notesSlides/")},
            "layouts": {"layout_count": count_members(names, prefix="ppt/slideLayouts/")},
            "theme": {"theme_count": count_members(names, prefix="ppt/theme/")},
            "media": {"media_count": _media_count(names)},
            "charts": {"chart_count": count_members(names, prefix="ppt/charts/")},
            "safety": preflight.usage["safety"],
        },
        next_recommended_tools=["deck.edit.patch", "deck.export.pdf", "office.context.build_packet"],
    )


def _slide_text_run_count(path: Path, slide_members: list[str]) -> int:
    count = 0
    for member in slide_members:
        slide_root = read_xml(path, member)
        if slide_root is not None:
            count += len(slide_root.findall(".//a:t", DECK_NS))
    return count


def _media_count(names: set[str]) -> int:
    return sum(1 for name in names if name.startswith("ppt/media/"))


def _failed(error: AgentPDFError) -> ToolResult:
    return ToolResult(
        job_id=_job_id(),
        status="failed",
        tool=TOOL_NAME,
        warnings=[error.message],
        error=error,
    )


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
