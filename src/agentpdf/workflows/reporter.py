from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.schemas.models import AgentPDFError, ToolResult
from agentpdf.security.paths import resolve_output_path


def create_workflow_report(
    workflow_run: Mapping[str, Any],
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.workflow.report"
    normalized = _normalize_workflow_run(workflow_run)
    if normalized is None:
        error = AgentPDFError(
            code="unsafe_input_rejected",
            message="workflow_run must be a workflow run payload or ToolResult containing usage.workflow_run.",
        )
        return ToolResult(
            job_id=_job_id(),
            status="failed",
            tool=tool,
            warnings=[error.message],
            error=error,
        )

    report = _build_report(normalized, workflow_run)
    markdown = _render_markdown(report)
    report["markdown"] = markdown
    artifacts = []
    if output_path is not None:
        output = resolve_output_path(output_path)
        output.write_text(markdown, encoding="utf-8")
        artifacts.append(build_artifact(output, source_tool=tool))

    return ToolResult(
        job_id=_job_id(),
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage={"workflow_report": report},
        next_recommended_tools=["pdf.workflow.plan", "pdf.workflow.run"],
    )


def _normalize_workflow_run(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    usage = payload.get("usage")
    if isinstance(usage, Mapping):
        nested = usage.get("workflow_run")
        if isinstance(nested, Mapping):
            return nested
    nested = payload.get("workflow_run")
    if isinstance(nested, Mapping):
        return nested
    if "step_results" in payload:
        return payload
    return None


def _build_report(workflow_run: Mapping[str, Any], source_payload: Mapping[str, Any]) -> dict[str, Any]:
    steps = workflow_run.get("step_results", [])
    step_results = [step for step in steps if isinstance(step, Mapping)] if isinstance(steps, list) else []
    tools = [str(step.get("tool", "")) for step in step_results if step.get("tool")]
    failed_steps = [step for step in step_results if step.get("status") == "failed"]
    warnings = _collect_warnings(workflow_run, step_results)
    artifacts = source_payload.get("artifacts", [])
    artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
    succeeded_steps = len([step for step in step_results if step.get("status") == "succeeded"])

    return {
        "run_id": str(workflow_run.get("run_id", "")),
        "run_status": str(workflow_run.get("status", "unknown")),
        "planned_steps": int(workflow_run.get("planned_steps", len(step_results)) or 0),
        "executed_steps": int(workflow_run.get("executed_steps", succeeded_steps) or 0),
        "failed_steps": int(workflow_run.get("failed_steps", len(failed_steps)) or 0),
        "succeeded_steps": succeeded_steps,
        "failed_step_ids": [str(step.get("step_id", "")) for step in failed_steps],
        "tools": tools,
        "artifact_count": artifact_count,
        "warning_count": len(warnings),
        "warnings": warnings,
        "bindings": workflow_run.get("bindings", {}) if isinstance(workflow_run.get("bindings"), Mapping) else {},
        "step_summaries": [_step_summary(step) for step in step_results],
    }


def _collect_warnings(workflow_run: Mapping[str, Any], steps: list[Mapping[str, Any]]) -> list[str]:
    warnings: list[str] = []
    top_warnings = workflow_run.get("warnings", [])
    if isinstance(top_warnings, list):
        warnings.extend(str(warning) for warning in top_warnings)
    for step in steps:
        step_warnings = step.get("warnings", [])
        if isinstance(step_warnings, list):
            warnings.extend(str(warning) for warning in step_warnings)
    return list(dict.fromkeys(warning for warning in warnings if warning))


def _step_summary(step: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "step_id": str(step.get("step_id", "")),
        "tool": str(step.get("tool", "")),
        "status": str(step.get("status", "unknown")),
        "job_id": step.get("job_id"),
        "artifact_ids": list(step.get("artifact_ids", []))
        if isinstance(step.get("artifact_ids", []), list)
        else [],
        "warning_count": len(step.get("warnings", [])) if isinstance(step.get("warnings"), list) else 0,
        "next_recommended_tools": list(step.get("next_recommended_tools", []))
        if isinstance(step.get("next_recommended_tools", []), list)
        else [],
    }


def _render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# AgentPDF Workflow Report",
        "",
        f"- Run ID: `{report['run_id']}`",
        f"- Status: `{report['run_status']}`",
        f"- Planned steps: {report['planned_steps']}",
        f"- Executed steps: {report['executed_steps']}",
        f"- Failed steps: {report['failed_steps']}",
        f"- Artifact count: {report['artifact_count']}",
        f"- Warning count: {report['warning_count']}",
        "",
        "## Steps",
        "",
        "| Step | Tool | Status | Artifacts |",
        "|---|---|---:|---:|",
    ]
    for step in report["step_summaries"]:
        lines.append(
            f"| `{step['step_id']}` | `{step['tool']}` | `{step['status']}` | {len(step['artifact_ids'])} |"
        )
    warnings = report.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    failed_step_ids = report.get("failed_step_ids", [])
    if failed_step_ids:
        lines.extend(["", "## Failed Steps", ""])
        for step_id in failed_step_ids:
            lines.append(f"- `{step_id}`")
    return "\n".join(lines) + "\n"


def _job_id() -> str:
    return f"job_{uuid4().hex[:16]}"
