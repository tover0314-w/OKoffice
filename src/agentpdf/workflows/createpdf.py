from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.bundle import (
    build_artifact_graph,
    create_artifact_manifest,
    export_artifact_bundle,
    verify_artifact_bundle,
)
from agentpdf.artifacts.store import build_artifact
from agentpdf.authoring.html_deck import write_authoring_html_package, write_raw_html_package
from agentpdf.authoring.qa import visual_report
from agentpdf.compose.context import compose_from_context
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
    context_packet: dict[str, Any] | None = None,
    context_packet_path: str | Path | None = None,
    target_profile: dict[str, Any] | str = "research_brief",
    style_pack: str | None = None,
    title: str | None = None,
    artifact_dir: str | Path | None = None,
    bundle_output_path: str | Path | None = None,
    expected_page_count: int | None = None,
    pages: str = "all",
    renderer_backend: str = "auto",
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

    if context_packet is not None or context_packet_path is not None:
        return _create_from_context(
            workflow_id=workflow_id,
            context_packet=context_packet,
            context_packet_path=context_packet_path,
            target_profile=target_profile,
            style_pack=style_pack,
            title=title,
            html_path_out=html_path_out,
            pdf_path=pdf_path,
            audit_dir=audit_dir,
            qa_report_path=qa_report_path,
            artifact_manifest_path=artifact_manifest_path,
            artifact_graph_path=artifact_graph_path,
            bundle_output_path=bundle_output_path,
            expected_page_count=expected_page_count,
            pages=pages,
            renderer_backend=renderer_backend,
            steps=steps,
            warnings=warnings,
            artifacts=artifacts,
        )

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
    render_result = render_html_package(manifest_path, output_path=pdf_path, renderer_backend=renderer_backend)
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

    bundle_path, bundle_result, bundle_verification_result, failed = _maybe_export_bundle(
        bundle_output_path=bundle_output_path,
        workflow_id=workflow_id,
        title=title,
        source_format="page_document" if page_document else "raw_html",
        pdf_path=pdf_path,
        artifact_manifest_path=artifact_manifest_path,
        artifact_graph_path=artifact_graph_path,
        steps=steps,
        warnings=warnings,
        artifacts=artifacts,
    )
    if failed is not None:
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    audit_usage = _audit_usage(manifest_result, graph_result)
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
                **_render_backend_usage(render_result),
                **audit_usage,
                **_bundle_usage(bundle_path, bundle_result, bundle_verification_result),
                "steps": steps,
            }
        },
        next_recommended_tools=[
            "pdf.artifacts.export_bundle",
            "pdf.workflow.report",
            "pdf.patch.plan",
        ],
    )


def _create_from_context(
    *,
    workflow_id: str,
    context_packet: dict[str, Any] | None,
    context_packet_path: str | Path | None,
    target_profile: dict[str, Any] | str,
    style_pack: str | None,
    title: str | None,
    html_path_out: Path,
    pdf_path: Path,
    audit_dir: Path,
    qa_report_path: Path,
    artifact_manifest_path: Path,
    artifact_graph_path: Path,
    bundle_output_path: str | Path | None,
    expected_page_count: int | None,
    pages: str,
    steps: list[dict[str, Any]],
    warnings: list[str],
    artifacts: list[Artifact],
    renderer_backend: str,
) -> ToolResult:
    audit_context_packet_path = _context_packet_audit_path(
        context_packet=context_packet,
        context_packet_path=context_packet_path,
        audit_dir=audit_dir,
        pdf_path=pdf_path,
    )
    if audit_context_packet_path is not None:
        artifacts.append(build_artifact(audit_context_packet_path, source_tool=TOOL_NAME))
    packet_input: str | Path = audit_context_packet_path or ""
    compose_result = compose_from_context(
        packet_input,
        target_profile=target_profile,
        output_path=pdf_path,
        style_pack=style_pack,
        title=title,
        renderer="html",
        html_output_path=html_path_out,
        renderer_backend=renderer_backend,
    )
    if failed := _record_step(compose_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    manifest_path = Path(str(compose_result.usage["html_package_manifest_path"])).expanduser().resolve()
    composition_path = pdf_path.with_suffix(".composition.json")
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

    artifact_paths: list[str | Path] = [
        *(artifact.path for artifact in compose_result.artifacts),
        qa_report_path,
    ]
    if audit_context_packet_path is not None:
        artifact_paths.append(audit_context_packet_path)
    manifest_result = create_artifact_manifest(
        artifact_paths=_unique_paths(artifact_paths),
        output_path=artifact_manifest_path,
        title=title or "AgentPDF CreatePDF Artifact Manifest",
        metadata={
            "workflow_id": workflow_id,
            "source_tool": TOOL_NAME,
            "source_format": "context_packet",
            "pdf_output_path": str(pdf_path),
            "html_package_manifest_path": str(manifest_path),
            "context_packet_path": str(audit_context_packet_path) if audit_context_packet_path is not None else None,
            "target_profile": compose_result.usage.get("target_profile"),
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

    bundle_path, bundle_result, bundle_verification_result, failed = _maybe_export_bundle(
        bundle_output_path=bundle_output_path,
        workflow_id=workflow_id,
        title=title,
        source_format="context_packet",
        pdf_path=pdf_path,
        artifact_manifest_path=artifact_manifest_path,
        artifact_graph_path=artifact_graph_path,
        steps=steps,
        warnings=warnings,
        artifacts=artifacts,
        context_packet_id=compose_result.usage.get("context_packet_id"),
    )
    if failed is not None:
        return _failed(workflow_id, steps=steps, warnings=warnings, artifacts=artifacts, failed=failed)

    audit_usage = _audit_usage(manifest_result, graph_result)
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
                "mode": "context_packet",
                "source_format": "context_packet",
                "context_packet_id": compose_result.usage.get("context_packet_id"),
                "context_packet_path": str(audit_context_packet_path) if audit_context_packet_path is not None else None,
                "target_profile": compose_result.usage.get("target_profile"),
                "renderer": compose_result.usage.get("renderer"),
                **_render_backend_usage(compose_result),
                "html_output_path": str(html_path_out),
                "html_package_manifest_path": str(manifest_path),
                "composition_path": str(composition_path),
                "pdf_output_path": str(pdf_path),
                "qa_report_path": str(qa_report_path),
                "artifact_manifest_path": str(artifact_manifest_path),
                "artifact_graph_path": str(artifact_graph_path),
                **audit_usage,
                **_bundle_usage(bundle_path, bundle_result, bundle_verification_result),
                "steps": steps,
            }
        },
        next_recommended_tools=[
            "pdf.artifacts.export_bundle",
            "pdf.workflow.report",
            "pdf.patch.plan",
        ],
    )


def _maybe_export_bundle(
    *,
    bundle_output_path: str | Path | None,
    workflow_id: str,
    title: str | None,
    source_format: str,
    pdf_path: Path,
    artifact_manifest_path: Path,
    artifact_graph_path: Path,
    steps: list[dict[str, Any]],
    warnings: list[str],
    artifacts: list[Artifact],
    context_packet_id: Any | None = None,
) -> tuple[Path | None, ToolResult | None, ToolResult | None, ToolResult | None]:
    if bundle_output_path is None:
        return None, None, None, None

    bundle_path = Path(bundle_output_path).expanduser().resolve()
    bundle_result = export_artifact_bundle(
        artifact_paths=_unique_paths([artifact.path for artifact in _unique_artifacts(artifacts)]),
        output_path=bundle_path,
        title=f"{title or 'AgentPDF CreatePDF'} Audit Bundle",
        metadata={
            "workflow": TOOL_NAME,
            "workflow_id": workflow_id,
            "source_format": source_format,
            "context_packet_id": context_packet_id,
            "pdf_output_path": str(pdf_path),
            "artifact_manifest_path": str(artifact_manifest_path),
            "artifact_graph_path": str(artifact_graph_path),
        },
    )
    if failed := _record_step(bundle_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return bundle_path, bundle_result, None, failed

    verification_result = verify_artifact_bundle(bundle_path)
    if failed := _record_step(verification_result, steps=steps, warnings=warnings, artifacts=artifacts):
        return bundle_path, bundle_result, verification_result, failed

    return bundle_path, bundle_result, verification_result, None


def _bundle_usage(
    bundle_path: Path | None,
    bundle_result: ToolResult | None,
    bundle_verification_result: ToolResult | None,
) -> dict[str, Any]:
    if bundle_path is None:
        return {}
    return {
        "bundle_path": str(bundle_path),
        **({"bundle_export": bundle_result.model_dump(mode="json")} if bundle_result is not None else {}),
        **(
            {"bundle_verification": bundle_verification_result.model_dump(mode="json")}
            if bundle_verification_result is not None
            else {}
        ),
    }


def _render_backend_usage(render_result: ToolResult) -> dict[str, Any]:
    renderer_backend = render_result.usage.get("renderer_backend")
    return {
        "requested_renderer_backend": render_result.usage.get("requested_renderer_backend"),
        "renderer_backend": renderer_backend if isinstance(renderer_backend, dict) else {},
        "render_skipped": bool(render_result.usage.get("render_skipped", False)),
        "render_skip_reason": render_result.usage.get("render_skip_reason"),
    }


def _audit_usage(manifest_result: ToolResult, graph_result: ToolResult) -> dict[str, Any]:
    manifest = _usage_payload(manifest_result, "artifact_manifest")
    graph = _usage_payload(graph_result, "artifact_graph")
    manifest_summary = {
        "artifact_count": manifest.get("artifact_count", 0),
        "source_ref_count": manifest.get("source_ref_count", 0),
        "html_package_count": manifest.get("html_package_count", 0),
        "html_render_profile_count": manifest.get("html_render_profile_count", 0),
        "renderer_backend_count": manifest.get("renderer_backend_count", 0),
        "html_layer_count": manifest.get("html_layer_count", 0),
        "context_packet_count": manifest.get("context_packet_count", 0),
        "source_graph_node_count": manifest.get("source_graph_node_count", 0),
        "source_graph_edge_count": manifest.get("source_graph_edge_count", 0),
    }
    graph_summary = {
        "artifact_count": graph.get("artifact_count", 0),
        "source_ref_count": graph.get("source_ref_count", 0),
        "html_render_profile_count": graph.get("html_render_profile_count", 0),
        "renderer_backend_count": graph.get("renderer_backend_count", 0),
        "html_layer_count": graph.get("html_layer_count", 0),
        "source_graph_node_count": graph.get("source_graph_node_count", 0),
        "source_graph_edge_count": graph.get("source_graph_edge_count", 0),
        "node_count": graph.get("node_count", 0),
        "edge_count": graph.get("edge_count", 0),
    }
    return {
        "artifact_manifest_summary": manifest_summary,
        "artifact_graph_summary": graph_summary,
        "html_render_profile_count": manifest_summary["html_render_profile_count"],
        "html_render_profile_refs": manifest.get("html_render_profile_refs", []),
        "renderer_backend_count": manifest_summary["renderer_backend_count"],
        "renderer_backend_refs": manifest.get("renderer_backend_refs", []),
        "html_layer_count": manifest_summary["html_layer_count"],
        "html_layer_refs": manifest.get("html_layer_refs", []),
        "source_graph_node_count": manifest_summary["source_graph_node_count"],
        "source_graph_edge_count": manifest_summary["source_graph_edge_count"],
    }


def _usage_payload(result: ToolResult, key: str) -> dict[str, Any]:
    value = result.usage.get(key)
    return value if isinstance(value, dict) else {}


def _context_packet_audit_path(
    *,
    context_packet: dict[str, Any] | None,
    context_packet_path: str | Path | None,
    audit_dir: Path,
    pdf_path: Path,
) -> Path | None:
    if context_packet is not None:
        destination = audit_dir / f"{pdf_path.stem}.context.packet.json"
        destination.write_text(json.dumps(context_packet, indent=2), encoding="utf-8")
        return destination.resolve()
    if context_packet_path is not None:
        return Path(context_packet_path).expanduser().resolve()
    return None


def _record_step(
    result: ToolResult,
    *,
    steps: list[dict[str, Any]],
    warnings: list[str],
    artifacts: list[Artifact],
) -> ToolResult | None:
    step = {
        "tool": result.tool,
        "job_id": result.job_id,
        "status": result.status,
        "validation_status": result.validation.status if result.validation else None,
        "artifact_paths": [artifact.path.as_posix() for artifact in result.artifacts],
        "warning_count": len(result.warnings),
    }
    renderer_backend = result.usage.get("renderer_backend")
    if isinstance(renderer_backend, dict):
        step["renderer_backend_id"] = renderer_backend.get("backend_id")
        step["render_skipped"] = bool(result.usage.get("render_skipped", False))
    steps.append(step)
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
                **_render_backend_usage(failed),
                "steps": steps,
            }
        },
    )


def _unique_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    unique: dict[str, Artifact] = {}
    for artifact in artifacts:
        unique[artifact.path.as_posix()] = artifact
    return list(unique.values())


def _unique_paths(paths: list[str | Path]) -> list[Path]:
    unique: dict[str, Path] = {}
    for path in paths:
        resolved = Path(path).expanduser().resolve()
        unique[resolved.as_posix()] = resolved
    return list(unique.values())
