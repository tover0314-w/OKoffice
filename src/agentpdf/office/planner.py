from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport


FORMAT_BY_SUFFIX = {
    ".doc": "doc",
    ".docx": "docx",
    ".pdf": "pdf",
    ".ppt": "ppt",
    ".pptx": "pptx",
    ".xls": "xls",
    ".xlsx": "xlsx",
    ".csv": "csv",
    ".tsv": "tsv",
    ".md": "markdown",
    ".html": "html",
    ".htm": "html",
    ".txt": "text",
}

DOMAIN_BY_FORMAT = {
    "doc": "word",
    "docx": "word",
    "pdf": "pdf",
    "ppt": "deck",
    "pptx": "deck",
    "xls": "sheet",
    "xlsx": "sheet",
    "csv": "sheet",
    "tsv": "sheet",
    "markdown": "office",
    "html": "office",
    "text": "office",
}


def plan_office_workflow(
    *,
    goal: str,
    input_paths: list[Path],
    output_paths: list[Path],
) -> ToolResult:
    inputs = [_file_plan(path) for path in input_paths]
    outputs = [_file_plan(path) for path in output_paths]
    input_formats = _unique_known(item["format"] for item in inputs)
    output_formats = _unique_known(item["format"] for item in outputs)
    pipeline = _recommended_pipeline(input_formats=input_formats, output_formats=output_formats)
    warnings = _warnings(inputs=inputs, outputs=outputs)

    validation_status = "warning" if warnings else "passed"
    validation = ValidationReport(
        status=validation_status,
        checks=[
            ValidationCheck(
                name="goal_declared",
                status="passed" if goal.strip() else "warning",
                message="Workflow goal is present." if goal.strip() else "Workflow goal is empty.",
            ),
            ValidationCheck(
                name="inputs_declared",
                status="passed" if input_paths else "warning",
                details={"input_count": len(input_paths)},
            ),
            ValidationCheck(
                name="outputs_declared",
                status="passed" if output_paths else "warning",
                details={"output_count": len(output_paths)},
            ),
        ],
        warnings=warnings,
    )

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool="office.workflow.plan",
        validation=validation,
        warnings=warnings,
        usage={
            "plan": {
                "goal": goal,
                "inputs": inputs,
                "outputs": outputs,
                "input_formats": input_formats,
                "output_formats": output_formats,
                "recommended_pipeline": pipeline,
                "execution_mode": "local_planning_only",
                "compatibility_package": "agentpdf",
            }
        },
        next_recommended_tools=[step["tool"] for step in pipeline],
    )


def _file_plan(path: Path) -> dict[str, str]:
    file_format = FORMAT_BY_SUFFIX.get(path.suffix.lower(), "unknown")
    return {
        "path": path.as_posix(),
        "format": file_format,
        "domain": DOMAIN_BY_FORMAT.get(file_format, "unknown"),
    }


def _recommended_pipeline(
    *,
    input_formats: list[str],
    output_formats: list[str],
) -> list[dict[str, str]]:
    steps = [
        {
            "tool": "office.context.ingest",
            "status": "planned",
            "reason": "Normalize local sources into context items with provenance.",
        },
        {
            "tool": "office.context.packet",
            "status": "planned",
            "reason": "Create a portable evidence packet for later transforms.",
        },
    ]

    if _needs_sheet(output_formats):
        steps.append(
            {
                "tool": "office.workflow.extract_to_sheet",
                "status": "planned",
                "reason": "Build auditable tables before workbook creation.",
            }
        )
    if _needs_deck(output_formats):
        steps.append(
            {
                "tool": "office.workflow.source_to_deck",
                "status": "planned",
                "reason": "Turn evidence, tables, and outline into a presentation.",
            }
        )
    if _needs_doc(output_formats):
        steps.append(
            {
                "tool": "office.workflow.source_to_doc",
                "status": "planned",
                "reason": "Draft an editable Word output from the evidence packet.",
            }
        )
    if "pdf" in output_formats:
        steps.append(
            {
                "tool": "office.validate.output",
                "status": "planned",
                "reason": "Validate generated PDF renderability and artifacts.",
            }
        )
    if not any(step["tool"] == "office.validate.output" for step in steps):
        steps.append(
            {
                "tool": "office.validate.output",
                "status": "planned",
                "reason": "Validate generated Office artifacts before returning them.",
            }
        )

    if input_formats and not output_formats:
        steps.append(
            {
                "tool": "office.workflow.multi_format_brief",
                "status": "planned",
                "reason": "Clarify desired output files before execution.",
            }
        )

    return steps


def _needs_sheet(output_formats: list[str]) -> bool:
    return any(file_format in {"xlsx", "xls", "csv", "tsv"} for file_format in output_formats)


def _needs_deck(output_formats: list[str]) -> bool:
    return any(file_format in {"pptx", "ppt"} for file_format in output_formats)


def _needs_doc(output_formats: list[str]) -> bool:
    return any(file_format in {"docx", "doc"} for file_format in output_formats)


def _unique_known(values: object) -> list[str]:
    seen = []
    for value in values:
        if not isinstance(value, str) or value == "unknown" or value in seen:
            continue
        seen.append(value)
    return seen


def _warnings(*, inputs: list[dict[str, str]], outputs: list[dict[str, str]]) -> list[str]:
    warnings = []
    unknown_inputs = [item["path"] for item in inputs if item["format"] == "unknown"]
    unknown_outputs = [item["path"] for item in outputs if item["format"] == "unknown"]
    if unknown_inputs:
        warnings.append(f"Unknown input formats: {', '.join(unknown_inputs)}")
    if unknown_outputs:
        warnings.append(f"Unknown output formats: {', '.join(unknown_outputs)}")
    return warnings
