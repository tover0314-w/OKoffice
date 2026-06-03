from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.bundle import build_artifact_graph, create_artifact_manifest
from agentpdf.artifacts.store import build_artifact
from agentpdf.authoring.html_deck import write_authoring_html_package, write_raw_html_package
from agentpdf.authoring.qa import visual_report
from agentpdf.renderers.html_package import render_html_package
from agentpdf.schemas.models import AgentPDFError, Artifact, ToolResult


TOOL_NAME = "pdf.workflow.createpdf"


def createpdf_html_first(
    *,
    pdf_output_path: str | Path,
    html_output_path: str | Path | None = None,
    html: str | None = None,
    html_path: str | Path | None = None,
    page_document: dict[str, Any] | None = None,
    title: str | None = None,
    artifact_dir: str | Path | None = None,
    expected_page_count: int | None = None,
    pages: str = "all",
) -> ToolResult:
    workflow_id = f"createpdf_{uuid4().hex[:12]}"
    pdf_path = Path(pdf_output_path).expanduser().resolve()
    html_path_out = Path(html_output_path).expanduser().resolve() if html_output_path else pdf_path.with_suffix(".html")
    audit_dir = Path(artifact_dir).expanduser().resolve() if artifact_dir else pdf_path.parent
    audit_dir.mkdir(parents=True, exist_ok=True)
    qa_report_path = audit_dir / f"{pdf_path.stem}.qa.json"
    artifact_manifest_path = audit_dir / f"{pdf_path.stem}.artifact-manifest.json"
    artifact_graph_path = audit_dir / f"{pdf_path.stem}.artifact-graph.json"

    steps: list[dict[str, Any]] = []
    warnings: list[str] = []
    artifacts: list[Artifact] = []

    create_result = (
        write_authoring_html_package(
            page_document=page_document,
            html_output_path=html_path_out,
            title=title,
        )
        if page_document
        else write_raw_html_package(
            html_source=html,
            html_input_path=html_path,
            html_output_path=html_path_out,
            title=title,
        )
    )
    if failed := _record_step(create_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    manifest_path = Path(str(create_result.usage["html_package_manifest_path"])).expanduser().resolve()
    render_result = render_html_package(manifest_path, output_path=pdf_path)
    if failed := _record_step(render_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    qa_result = visual_report(
        input_path=pdf_path,
        expected_page_count=expected_page_count,
        html_package_manifest_path=manifest_path,
        pages=pages,
    )
    if failed := _record_step(qa_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)
    qa_report_path.write_text(qa_result.model_dump_json(indent=2), encoding="utf-8")
    artifacts.append(build_artifact(qa_report_path, source_tool=TOOL_NAME))

    manifest_result = create_artifact_manifest(
        artifact_paths=[html_path_out, manifest_path, pdf_path, qa_report_path],
        output_path=artifact_manifest_path,
        title=title or "AgentPDF CreatePDF Artifact Manifest",
        metadata={
            "workflow_id": workflow_id,
            "source_tool": TOOL_NAME,
            "pdf_output_path": str(pdf_path),
            "html_package_manifest_path": str(manifest_path),
        },
    )
    if failed := _record_step(manifest_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    graph_result = build_artifact_graph(
        artifact_manifest_path=artifact_manifest_path,
        output_path=artifact_graph_path,
        title=title or "AgentPDF CreatePDF Artifact Graph",
    )
    if failed := _record_step(graph_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=TOOL_NAME,
        artifacts=_unique_artifacts(artifacts),
        validation=qa_result.validation,
        warnings=warnings,
        usage={
            "createpdf": {
                "workflow_id": workflow_id,
                "mode": "html_first",
                "source_format": "page_document" if page_document else "raw_html",
                "html_output_path": str(html_path_out),
                "html_package_manifest_path": str(manifest_path),
                "pdf_output_path": str(pdf_path),
                "qa_report_path": str(qa_report_path),
                "artifact_manifest_path": str(artifact_manifest_path),
                "artifact_graph_path": str(artifact_graph_path),
                "steps": steps,
            }
        },
        next_recommended_tools=[
            "pdf.artifacts.export_bundle",
            "pdf.workflow.report",
            "pdf.patch.plan",
        ],
    )


def _record_step(
    result: ToolResult,
    *,
    steps: list[dict[str, Any]],
    warnings: list[str],
    artifacts: list[Artifact],
) -> ToolResult | None:
    steps.append(
        {
            "tool": result.tool,
            "job_id": result.job_id,
            "status": result.status,
            "validation_status": result.validation.status if result.validation else None,
            "artifact_paths": [artifact.path.as_posix() for artifact in result.artifacts],
            "warning_count": len(result.warnings),
        }
    )
    warnings.extend(result.warnings)
    artifacts.extend(result.artifacts)
    return result if result.status == "failed" else None


def _failed(
    workflow_id: str,
    *,
    steps: list[dict[str, Any]],
    warnings: list[str],
    artifacts: list[Artifact],
    failed: ToolResult,
) -> ToolResult:
    error = failed.error or AgentPDFError(
        code="output_validation_failed",
        message=f"CreatePDF workflow step failed: {failed.tool}",
    )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="failed",
        tool=TOOL_NAME,
        artifacts=_unique_artifacts(artifacts),
        validation=failed.validation,
        warnings=warnings,
        error=error,
        usage={
            "createpdf": {
                "workflow_id": workflow_id,
                "mode": "html_first",
                "failed_tool": failed.tool,
                "steps": steps,
            }
        },
    )


def _unique_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    unique: dict[str, Artifact] = {}
    for artifact in artifacts:
        unique[artifact.path.as_posix()] = artifact
    return list(unique.values())
