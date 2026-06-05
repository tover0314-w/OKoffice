from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.store import build_artifact
from agentpdf.core.pdf import create_markdown_pdf, create_slide_deck_pdf
from agentpdf.renderers.html_package import render_html_package, write_composition_html_package
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationReport
from agentpdf.validation.pdf import validate_pdf


DEFAULT_TARGET_PROFILES: dict[str, dict[str, Any]] = {
    "technical_audit": {
        "profile_id": "technical_audit",
        "name": "Technical Audit",
        "layout_mode": "document",
        "style_pack": "paper_ink",
        "sections": ["Executive Summary", "Evidence Table", "Code Review", "Source Map"],
        "layout_slots": {
            "summary": {"accepts": ["section"], "required": True},
            "evidence_table": {"accepts": ["table", "data", "citation"], "required": True},
            "code_review": {"accepts": ["code"]},
            "visual_evidence": {"accepts": ["image"]},
            "media_evidence": {"accepts": ["audio_reference", "video_reference", "media_reference"]},
            "source_appendix": {"accepts": ["pdf_reference", "section"]},
        },
        "accepted_block_types": [
            "section",
            "code",
            "table",
            "data",
            "image",
            "pdf_reference",
            "audio_reference",
            "video_reference",
            "media_reference",
            "citation",
        ],
        "accepted_context_types": ["text", "document", "code", "data", "image", "pdf", "audio", "video", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "evidence_packet_pdf": {
        "profile_id": "evidence_packet_pdf",
        "name": "Evidence Packet",
        "layout_mode": "document",
        "style_pack": "paper_ink",
        "sections": ["Evidence Summary", "Source Items", "Source Map"],
        "layout_slots": {
            "evidence_summary": {"accepts": ["section", "citation"], "required": True},
            "source_items": {
                "accepts": [
                    "section",
                    "code",
                    "table",
                    "image",
                    "pdf_reference",
                    "audio_reference",
                    "video_reference",
                    "media_reference",
                ],
                "repeats": True,
            },
            "source_map": {"accepts": ["section"], "required": True},
        },
        "accepted_block_types": [
            "section",
            "code",
            "table",
            "data",
            "image",
            "pdf_reference",
            "audio_reference",
            "video_reference",
            "media_reference",
            "citation",
        ],
        "accepted_context_types": ["text", "document", "code", "data", "image", "pdf", "audio", "video", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "research_brief": {
        "profile_id": "research_brief",
        "name": "Research Brief",
        "layout_mode": "document",
        "style_pack": "paper_ink",
        "sections": ["Research Question", "Findings", "Implications", "Source Map"],
        "layout_slots": {
            "research_question": {"accepts": ["section", "citation"], "required": True},
            "findings": {"accepts": ["section", "table", "image", "citation"], "repeats": True},
            "appendix": {"accepts": ["pdf_reference", "audio_reference", "video_reference", "code"]},
        },
        "accepted_block_types": [
            "section",
            "table",
            "image",
            "pdf_reference",
            "audio_reference",
            "video_reference",
            "code",
            "citation",
        ],
        "accepted_context_types": ["text", "document", "data", "image", "pdf", "audio", "video", "web_link", "code"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "training_handout": {
        "profile_id": "training_handout",
        "name": "Training Handout",
        "layout_mode": "document",
        "style_pack": "paper_ink",
        "sections": ["Learning Goal", "Practice", "Checklist", "Source Map"],
        "layout_slots": {
            "learning_goal": {"accepts": ["section"], "required": True},
            "practice": {"accepts": ["section", "table", "image", "code"], "repeats": True},
            "media_context": {"accepts": ["audio_reference", "video_reference", "media_reference"]},
            "checklist": {"accepts": ["section", "table"]},
        },
        "accepted_block_types": [
            "section",
            "table",
            "image",
            "code",
            "audio_reference",
            "video_reference",
            "media_reference",
            "citation",
        ],
        "accepted_context_types": ["text", "document", "data", "image", "code", "audio", "video", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "resume_pdf": {
        "profile_id": "resume_pdf",
        "name": "Resume PDF",
        "layout_mode": "document",
        "style_pack": "resume_modern",
        "sections": ["Header", "Summary", "Skills", "Experience", "Source Notes"],
        "layout_slots": {
            "header": {"accepts": ["section"], "required": True},
            "summary": {"accepts": ["section"], "required": True},
            "skills": {"accepts": ["section", "table"]},
            "experience": {"accepts": ["section", "citation"], "repeats": True},
            "source_notes": {"accepts": ["citation", "pdf_reference"]},
        },
        "accepted_block_types": ["section", "table", "citation", "pdf_reference"],
        "accepted_context_types": ["text", "document", "pdf", "web_link", "data"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "invoice_pdf": {
        "profile_id": "invoice_pdf",
        "name": "Invoice PDF",
        "layout_mode": "document",
        "style_pack": "invoice_clean",
        "sections": ["Billing", "Line Items", "Totals", "Notes"],
        "layout_slots": {
            "billing": {"accepts": ["section"], "required": True},
            "line_items": {"accepts": ["table", "data"], "required": True},
            "totals": {"accepts": ["section", "table"]},
            "notes": {"accepts": ["section", "citation"]},
        },
        "accepted_block_types": ["section", "table", "data", "citation"],
        "accepted_context_types": ["text", "document", "data", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "proposal_pdf": {
        "profile_id": "proposal_pdf",
        "name": "Proposal PDF",
        "layout_mode": "document",
        "style_pack": "business_report_modern",
        "sections": ["Client", "Problem", "Approach", "Deliverables", "Timeline"],
        "layout_slots": {
            "client": {"accepts": ["section"]},
            "problem": {"accepts": ["section", "citation"], "required": True},
            "approach": {"accepts": ["section", "image"], "required": True},
            "deliverables": {"accepts": ["section", "table"], "repeats": True},
            "timeline": {"accepts": ["section", "table"]},
        },
        "accepted_block_types": ["section", "table", "image", "citation"],
        "accepted_context_types": ["text", "document", "data", "image", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
    "slide_deck": {
        "profile_id": "slide_deck",
        "name": "AgentPDF Slide Deck",
        "style_pack": "paper_ink",
        "layout_mode": "slides",
        "sections": ["Title", "Context Summary", "Evidence Slides", "Source Map"],
        "layout_slots": {
            "title": {"accepts": ["section"], "required": True},
            "context_summary": {"accepts": ["section"], "required": True},
            "evidence_slide": {
                "accepts": [
                    "slide",
                    "code",
                    "table",
                    "image",
                    "pdf_reference",
                    "audio_reference",
                    "video_reference",
                    "media_reference",
                    "citation",
                ],
                "repeats": True,
            },
            "source_map": {"accepts": ["slide", "section"], "required": True},
        },
        "accepted_block_types": [
            "slide",
            "section",
            "code",
            "table",
            "image",
            "pdf_reference",
            "audio_reference",
            "video_reference",
            "media_reference",
            "citation",
        ],
        "accepted_context_types": ["text", "document", "code", "data", "image", "pdf", "audio", "video", "web_link"],
        "validation_required": ["render_check", "evidence_coverage_report"],
    },
}

KNOWN_LAYOUT_MODES = {"document", "slides"}
KNOWN_BLOCK_TYPES = {
    "section",
    "slide",
    "code",
    "table",
    "image",
    "data",
    "pdf_reference",
    "audio_reference",
    "video_reference",
    "media_reference",
    "citation",
}
KNOWN_CONTEXT_TYPES = {"text", "document", "code", "data", "image", "pdf", "audio", "video", "media", "web_link", "file"}


def compose_from_context(
    context_packet: dict[str, Any] | str | Path,
    target_profile: dict[str, Any] | str,
    output_path: str | Path,
    style_pack: str | None = None,
    title: str | None = None,
    renderer: str = "markdown",
    html_output_path: str | Path | None = None,
    renderer_backend: str = "auto",
) -> ToolResult:
    tool = "pdf.compose.from_context"
    packet = _load_context_packet(context_packet)
    profile = _resolve_target_profile(target_profile)
    renderer_mode = _normalize_renderer(renderer)
    if style_pack:
        profile["style_pack"] = style_pack
    if title:
        profile["title"] = title
    if profile.get("layout_mode") == "slides":
        slides, composition_ir, source_map, coverage = _compose_slides(packet, profile)
        markdown = _slides_to_outline(slides)
        render_plan = _render_plan(profile, markdown=markdown, slides=slides)
    else:
        markdown, composition_ir, source_map, coverage = _compose_markdown(packet, profile)
        slides = []
        render_plan = _render_plan(profile, markdown=markdown, slides=slides)

    html_package: dict[str, Any] | None = None
    if renderer_mode == "html":
        resolved_html_output = html_output_path or Path(output_path).with_suffix(".html")
        render_plan = {
            **render_plan,
            "renderer": "html_package",
            "html_output_path": str(Path(resolved_html_output).expanduser().resolve()),
            "fallback_renderer": "local_markdown_pdf",
        }
        html_package = write_composition_html_package(
            composition_ir=composition_ir,
            source_map=source_map,
            target_profile=profile,
            render_plan=render_plan,
            html_output_path=resolved_html_output,
            source_tool=tool,
        )
        rendered = render_html_package(
            html_package["html_package_manifest_path"],
            output_path=output_path,
            renderer_backend=renderer_backend,
        )
        if rendered.status == "failed":
            return ToolResult(
                job_id=f"job_{uuid4().hex[:16]}",
                status="failed",
                tool=tool,
                artifacts=[*html_package["artifacts"], *rendered.artifacts],
                validation=rendered.validation,
                warnings=[*rendered.warnings, *_composition_warnings(packet)],
                usage={
                    "context_packet_id": packet["context_packet_id"],
                    "target_profile": profile,
                    "renderer": "html_package",
                    "composition_ir": composition_ir,
                    "source_map": source_map,
                    "evidence_coverage": coverage,
                    "render_plan": render_plan,
                    "generated_markdown": markdown,
                    "html_output_path": html_package["html_output_path"],
                    "html_package_manifest_path": html_package["html_package_manifest_path"],
                    "html_package_manifest": html_package["html_package_manifest"],
                    "html_package_validation": html_package["html_package_validation"].model_dump(mode="json"),
                    "requested_renderer_backend": rendered.usage.get("requested_renderer_backend"),
                    "renderer_backend": rendered.usage.get("renderer_backend", {}),
                    "render_skipped": bool(rendered.usage.get("render_skipped", False)),
                    "render_skip_reason": rendered.usage.get("render_skip_reason"),
                    **({"slides": slides, "slide_count": len(slides)} if slides else {}),
                },
                next_recommended_tools=["pdf.render.html_package"],
                error=rendered.error,
            )
    elif profile.get("layout_mode") == "slides":
        rendered = create_slide_deck_pdf(
            slides,
            output_path=output_path,
            title=profile.get("title") or profile.get("name") or "AgentPDF Slide Deck",
            style_pack=str(profile.get("style_pack") or "paper_ink"),
        )
    else:
        rendered = create_markdown_pdf(
            markdown,
            output_path=output_path,
            title=profile.get("title") or profile.get("name") or "AgentPDF Composition",
            style_pack=str(profile.get("style_pack") or "plain_report"),
        )
    rendered_path = rendered.artifacts[0].path if rendered.artifacts else Path(output_path).resolve()
    validation = validate_pdf(rendered_path)
    if html_package is not None:
        validation = _merge_html_package_validation(validation, html_package["html_package_validation"])
    warnings = [*rendered.warnings, *validation.warnings, *_composition_warnings(packet)]
    pdf_artifact = build_artifact(rendered_path, source_tool=tool)
    ir_path = Path(output_path).with_suffix(".composition.json")
    ir_payload = {
        "composition_ir": composition_ir,
        "source_map": source_map,
        "evidence_coverage": coverage,
        "target_profile": profile,
        "context_packet_id": packet["context_packet_id"],
        "render_plan": render_plan,
    }
    if html_package is not None:
        ir_payload.update(
            {
                "html_output_path": html_package["html_output_path"],
                "html_package_manifest_path": html_package["html_package_manifest_path"],
                "html_package_manifest": html_package["html_package_manifest"],
                "html_package_validation": html_package["html_package_validation"].model_dump(mode="json"),
            }
        )
    if slides:
        ir_payload["slides"] = slides
    ir_path.write_text(json.dumps(ir_payload, indent=2), encoding="utf-8")
    ir_artifact = build_artifact(ir_path, source_tool=tool)
    artifacts = [pdf_artifact, ir_artifact]
    if html_package is not None:
        artifacts.extend(html_package["artifacts"])

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=artifacts,
        validation=validation,
        warnings=warnings,
        usage={
            "context_packet_id": packet["context_packet_id"],
            "target_profile": profile,
            "renderer": "html_package" if html_package is not None else render_plan["renderer"],
            "composition_ir": composition_ir,
            "source_map": source_map,
            "evidence_coverage": coverage,
            "render_plan": render_plan,
            "generated_markdown": markdown,
            **(
                {
                    "html_output_path": html_package["html_output_path"],
                    "html_package_manifest_path": html_package["html_package_manifest_path"],
                    "html_package_manifest": html_package["html_package_manifest"],
                    "html_package_validation": html_package["html_package_validation"].model_dump(mode="json"),
                    "requested_renderer_backend": rendered.usage.get("requested_renderer_backend"),
                    "renderer_backend": rendered.usage.get("renderer_backend", {}),
                    "render_skipped": bool(rendered.usage.get("render_skipped", False)),
                    "render_skip_reason": rendered.usage.get("render_skip_reason"),
                }
                if html_package is not None
                else {}
            ),
            **({"slides": slides, "slide_count": len(slides)} if slides else {}),
        },
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.evidence.coverage_report",
            "pdf.patch.plan",
        ],
    )


def _merge_html_package_validation(pdf_validation: ValidationReport, html_validation: ValidationReport) -> ValidationReport:
    checks = [*html_validation.checks, *pdf_validation.checks]
    status = "passed"
    if any(check.status == "failed" for check in checks):
        status = "failed"
    elif any(check.status == "warning" for check in checks):
        status = "warning"
    elif checks and all(check.status == "skipped" for check in checks):
        status = "skipped"
    return ValidationReport(
        status=status,
        checks=checks,
        page_count=pdf_validation.page_count,
        warnings=[*html_validation.warnings, *pdf_validation.warnings],
    )


def plan_composition(
    context_packet: dict[str, Any] | str | Path,
    target_profile: dict[str, Any] | str,
    output_path: str | Path | None = None,
    style_pack: str | None = None,
    title: str | None = None,
) -> ToolResult:
    tool = "pdf.compose.plan"
    packet = _load_context_packet(context_packet)
    profile = _resolve_target_profile(target_profile)
    if style_pack:
        profile["style_pack"] = style_pack
    if title:
        profile["title"] = title

    if profile.get("layout_mode") == "slides":
        slides, composition_ir, source_map, coverage = _compose_slides(packet, profile)
        markdown = _slides_to_outline(slides)
    else:
        markdown, composition_ir, source_map, coverage = _compose_markdown(packet, profile)
        slides = []

    render_plan = _render_plan(profile, markdown=markdown, slides=slides)
    plan = {
        "composition_plan_version": "0.1",
        "composition_plan_id": f"cmpplan_{uuid4().hex[:16]}",
        "context_packet_id": packet["context_packet_id"],
        "target_profile": profile,
        "composition_ir": composition_ir,
        "source_map": source_map,
        "evidence_coverage": coverage,
        "render_plan": render_plan,
        "validation_plan": {
            "required": profile.get("validation_required", ["render_check", "evidence_coverage_report"]),
            "output_must_be_new_artifact": True,
            "recommended_tools": ["pdf.compose.render_ir", "pdf.validation.render_check", "pdf.evidence.coverage_report"],
        },
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=_composition_warnings(packet),
        usage={
            "context_packet_id": packet["context_packet_id"],
            "composition_plan_id": plan["composition_plan_id"],
            "target_profile": profile,
            "composition_ir": composition_ir,
            "source_map": source_map,
            "evidence_coverage": coverage,
            "render_plan": render_plan,
            "validation_plan": plan["validation_plan"],
            "generated_markdown": markdown,
            **({"slides": slides, "slide_count": len(slides)} if slides else {}),
        },
        next_recommended_tools=[
            "pdf.compose.render_ir",
            "pdf.evidence.coverage_report",
            "pdf.validation.render_check",
        ],
    )


def render_composition_ir(
    composition: dict[str, Any] | str | Path,
    output_path: str | Path,
    style_pack: str | None = None,
    title: str | None = None,
) -> ToolResult:
    tool = "pdf.compose.render_ir"
    payload = _load_composition_payload(composition)
    composition_ir = _composition_ir_from_payload(payload)
    if not isinstance(composition_ir, dict):
        raise AgentPDFException("invalid_input", "composition_ir must be present to render composition IR.")
    render_plan = _render_plan_from_payload(payload)
    target_profile = payload.get("target_profile") if isinstance(payload.get("target_profile"), dict) else {}
    effective_style = style_pack or str(render_plan.get("style_pack") or target_profile.get("style_pack") or "paper_ink")
    effective_title = title or str(render_plan.get("title") or target_profile.get("title") or target_profile.get("name") or "AgentPDF Composition")
    layout_mode = str(render_plan.get("layout_mode") or target_profile.get("layout_mode") or "document")
    warnings: list[str] = []

    if layout_mode == "slides" and isinstance(render_plan.get("slides"), list):
        slides = [slide for slide in render_plan["slides"] if isinstance(slide, dict)]
        rendered = create_slide_deck_pdf(
            slides,
            output_path=output_path,
            title=effective_title,
            style_pack=effective_style,
        )
        generated_markdown = _slides_to_outline(slides)
    else:
        generated_markdown = str(render_plan.get("markdown") or "")
        if not generated_markdown.strip():
            generated_markdown = _fallback_markdown_from_ir(composition_ir, target_profile)
            warnings.append("Composition IR did not include a render_plan markdown payload; rendered a structural fallback.")
        rendered = create_markdown_pdf(
            generated_markdown,
            output_path=output_path,
            title=effective_title,
            style_pack=effective_style,
        )

    rendered_path = rendered.artifacts[0].path if rendered.artifacts else Path(output_path).resolve()
    validation = validate_pdf(rendered_path)
    pdf_artifact = build_artifact(rendered_path, source_tool=tool)
    source_map = payload.get("source_map") if isinstance(payload.get("source_map"), list) else []
    coverage = payload.get("evidence_coverage") if isinstance(payload.get("evidence_coverage"), dict) else {}

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[pdf_artifact],
        validation=validation,
        warnings=[*warnings, *validation.warnings],
        usage={
            "composition_id": composition_ir.get("composition_id"),
            "context_packet_id": composition_ir.get("context_packet_id") or payload.get("context_packet_id"),
            "target_profile": target_profile,
            "composition_ir": composition_ir,
            "source_map": source_map,
            "evidence_coverage": coverage,
            "render_plan": render_plan,
            "generated_markdown": generated_markdown,
        },
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.evidence.coverage_report",
            "pdf.patch.plan",
        ],
    )


def list_target_profiles(output_path: str | Path | None = None) -> ToolResult:
    tool = "pdf.target.profiles"
    profiles = {
        profile_id: _profile_catalog_entry(profile)
        for profile_id, profile in sorted(DEFAULT_TARGET_PROFILES.items())
    }
    catalog = {
        "profile_catalog_version": "0.1",
        "profile_count": len(profiles),
        "profiles": profiles,
        "default_profile": "research_brief",
        "next_recommended_tools": ["pdf.target.validate_profile", "pdf.compose.from_context"],
    }
    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage={"profile_catalog": catalog},
        next_recommended_tools=["pdf.target.validate_profile", "pdf.compose.from_context"],
    )


def validate_target_profile(
    target_profile: dict[str, Any] | str,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.target.validate_profile"
    profile = _resolve_target_profile(target_profile)
    report = _target_profile_validation_report(profile)
    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if report["is_valid"] else "failed",
        tool=tool,
        artifacts=artifacts,
        warnings=list(report["warnings"]),
        usage={"profile_validation": report},
        next_recommended_tools=["pdf.compose.from_context"] if report["is_valid"] else ["pdf.target.profiles"],
    )


def select_target_profile(
    goal: str = "",
    context_packet: dict[str, Any] | str | Path | None = None,
    preferred_profile: str | None = None,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.target.select_profile"
    packet = _load_context_packet(context_packet) if context_packet is not None else None
    context_types = [
        str(item.get("type", "")).lower()
        for item in (packet.get("items", []) if packet else [])
        if isinstance(item, dict)
    ]
    candidates = _target_profile_candidates(
        goal=goal,
        context_types=context_types,
        preferred_profile=preferred_profile,
    )
    selected_id = candidates[0]["profile_id"]
    selected_profile = _profile_catalog_entry(DEFAULT_TARGET_PROFILES[selected_id])
    selection = {
        "selection_version": "0.1",
        "selected_profile_id": selected_id,
        "selected_profile": selected_profile,
        "candidates": candidates,
        "input_summary": {
            "goal": goal,
            "context_packet_id": packet.get("context_packet_id") if packet else None,
            "context_types": context_types,
            "preferred_profile": preferred_profile,
        },
        "selection_method": "local_deterministic_keyword_and_context_type_scoring",
    }

    artifacts = []
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(selection, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage=selection,
        next_recommended_tools=["pdf.target.validate_profile", "pdf.compose.plan", "pdf.compose.from_context"],
    )


def _render_plan(profile: dict[str, Any], markdown: str, slides: list[dict[str, Any]]) -> dict[str, Any]:
    layout_mode = str(profile.get("layout_mode") or "document")
    plan = {
        "render_plan_version": "0.1",
        "layout_mode": layout_mode,
        "title": str(profile.get("title") or profile.get("name") or "AgentPDF Composition"),
        "style_pack": str(profile.get("style_pack") or "paper_ink"),
        "renderer": "local_markdown_pdf" if layout_mode != "slides" else "local_slide_deck_pdf",
    }
    if layout_mode == "slides":
        plan["slides"] = slides
        plan["markdown_outline"] = markdown
    else:
        plan["markdown"] = markdown
    return plan


def _normalize_renderer(renderer: str | None) -> str:
    value = str(renderer or "markdown").strip().lower()
    if value in {"markdown", "local_markdown_pdf", "reportlab"}:
        return "markdown"
    if value in {"html", "html_package", "html-first", "html_first"}:
        return "html"
    raise AgentPDFException(
        "invalid_input",
        "Unsupported compose renderer. Use 'markdown' or 'html'.",
        details={"renderer": renderer},
    )


def _load_composition_payload(composition: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(composition, dict):
        payload = composition
    else:
        payload = json.loads(Path(composition).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AgentPDFException("invalid_input", "Composition payload must be a JSON object.")
    return payload


def _composition_ir_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(payload.get("composition_ir"), dict):
        return payload["composition_ir"]
    if payload.get("composition_id") and isinstance(payload.get("blocks"), list):
        return payload
    return None


def _render_plan_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("render_plan"), dict):
        return payload["render_plan"]
    render_plan: dict[str, Any] = {
        "render_plan_version": "0.1",
        "layout_mode": "document",
        "title": "AgentPDF Composition",
        "style_pack": "paper_ink",
        "renderer": "local_markdown_pdf",
    }
    if isinstance(payload.get("slides"), list):
        render_plan.update(
            {
                "layout_mode": "slides",
                "slides": payload["slides"],
                "renderer": "local_slide_deck_pdf",
            }
        )
    if isinstance(payload.get("generated_markdown"), str):
        render_plan["markdown"] = payload["generated_markdown"]
    return render_plan


def _fallback_markdown_from_ir(composition_ir: dict[str, Any], target_profile: dict[str, Any]) -> str:
    title = str(target_profile.get("title") or target_profile.get("name") or "Composition IR")
    lines = [
        f"# {title}",
        "",
        "## Composition IR",
        "",
        f"Composition ID: `{composition_ir.get('composition_id', 'unknown')}`",
        f"Target profile: `{composition_ir.get('target_profile_id', 'custom')}`",
        "",
        "| Block | Type | Source refs | Target slot |",
        "|---|---|---|---|",
    ]
    blocks = composition_ir.get("blocks") if isinstance(composition_ir.get("blocks"), list) else []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        refs = ", ".join(f"`{ref}`" for ref in _string_list(block.get("source_refs")))
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{block.get('block_id', '')}`",
                    str(block.get("type", "")),
                    refs,
                    str(block.get("target_slot", "")),
                ]
            )
            + " |"
        )
    return "\n".join(lines).strip() + "\n"


def _load_context_packet(context_packet: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(context_packet, dict):
        packet = context_packet
    else:
        packet = json.loads(Path(context_packet).read_text(encoding="utf-8"))
    if "context_packet_id" not in packet or not isinstance(packet.get("items"), list):
        raise AgentPDFException("invalid_context_packet", "Context packet must include context_packet_id and items.")
    return packet


def _resolve_target_profile(target_profile: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(target_profile, dict):
        profile_id = str(target_profile.get("profile_id") or target_profile.get("id") or "custom")
        base = dict(DEFAULT_TARGET_PROFILES.get(profile_id, {}))
        base.update(target_profile)
        base["profile_id"] = profile_id
        return _normalize_target_profile(base)
    profile_id = target_profile.strip() or "research_brief"
    if profile_id not in DEFAULT_TARGET_PROFILES:
        available = ", ".join(sorted(DEFAULT_TARGET_PROFILES))
        raise AgentPDFException("invalid_target_profile", f"Unknown target profile: {profile_id}. Available: {available}.")
    return _normalize_target_profile(dict(DEFAULT_TARGET_PROFILES[profile_id]))


def _normalize_target_profile(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(profile)
    normalized["layout_mode"] = str(normalized.get("layout_mode") or "document")
    normalized["style_pack"] = str(normalized.get("style_pack") or "paper_ink")
    normalized["sections"] = _string_list(normalized.get("sections"))
    if not isinstance(normalized.get("layout_slots"), dict) or not normalized["layout_slots"]:
        normalized["layout_slots"] = _default_layout_slots(str(normalized["layout_mode"]))
    accepted_block_types = _string_list(normalized.get("accepted_block_types"))
    if not accepted_block_types:
        accepted_block_types = _accepted_block_types_from_slots(normalized["layout_slots"])
    normalized["accepted_block_types"] = accepted_block_types
    accepted_context_types = _string_list(normalized.get("accepted_context_types"))
    if not accepted_context_types:
        accepted_context_types = _context_types_for_blocks(accepted_block_types)
    normalized["accepted_context_types"] = accepted_context_types
    validation_required = _string_list(normalized.get("validation_required"))
    normalized["validation_required"] = validation_required or ["render_check", "evidence_coverage_report"]
    return normalized


def _profile_catalog_entry(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_target_profile(profile)
    return {
        "profile_id": normalized["profile_id"],
        "name": normalized.get("name", normalized["profile_id"]),
        "layout_mode": normalized["layout_mode"],
        "style_pack": normalized["style_pack"],
        "sections": normalized["sections"],
        "layout_slots": normalized["layout_slots"],
        "accepted_block_types": normalized["accepted_block_types"],
        "accepted_context_types": normalized["accepted_context_types"],
        "validation_required": normalized["validation_required"],
        "compose_tool": "pdf.compose.from_context",
        "schema": "schemas/target-pdf-profile.schema.json",
    }


def _target_profile_candidates(
    goal: str,
    context_types: list[str],
    preferred_profile: str | None,
) -> list[dict[str, Any]]:
    normalized_goal = goal.lower()
    scored: list[dict[str, Any]] = []
    keyword_scores = {
        "slide_deck": ["slide", "slides", "deck", "presentation", "present"],
        "resume_pdf": ["resume", "cv", "candidate", "career"],
        "invoice_pdf": ["invoice", "billing", "bill", "payment", "line item"],
        "proposal_pdf": ["proposal", "sales", "client", "deliverable"],
        "technical_audit": ["audit", "code", "security", "architecture", "risk", "technical"],
        "evidence_packet_pdf": ["evidence", "packet", "source", "citation", "appendix"],
        "research_brief": ["research", "brief", "paper", "findings", "study"],
        "training_handout": ["training", "lesson", "learning", "worksheet", "handout"],
    }
    type_boosts = {
        "code": {"technical_audit": 3},
        "data": {"technical_audit": 1, "invoice_pdf": 2, "research_brief": 1},
        "image": {"slide_deck": 2, "evidence_packet_pdf": 1},
        "audio": {"slide_deck": 2, "evidence_packet_pdf": 1, "training_handout": 1},
        "video": {"slide_deck": 2, "evidence_packet_pdf": 1, "training_handout": 1},
        "pdf": {"research_brief": 1, "evidence_packet_pdf": 2},
        "web_link": {"research_brief": 1, "evidence_packet_pdf": 1},
    }

    for profile_id, profile in sorted(DEFAULT_TARGET_PROFILES.items()):
        normalized = _normalize_target_profile(profile)
        score = 1
        reasons = ["available built-in target profile"]
        if preferred_profile and preferred_profile == profile_id:
            score += 10
            reasons.append("preferred_profile matched")
        for keyword in keyword_scores.get(profile_id, []):
            if keyword in normalized_goal:
                score += 4
                reasons.append(f"goal keyword matched: {keyword}")
        accepted_context_types = set(normalized["accepted_context_types"])
        matched_types = sorted({item_type for item_type in context_types if item_type in accepted_context_types})
        if matched_types:
            score += len(matched_types) * 2
            reasons.append("context types accepted: " + ", ".join(matched_types))
        for item_type in context_types:
            score += int(type_boosts.get(item_type, {}).get(profile_id, 0))
        if normalized["layout_mode"] == "slides" and any(word in normalized_goal for word in ["slide", "deck", "presentation"]):
            score += 3
            reasons.append("slide layout requested")
        scored.append(
            {
                "profile_id": profile_id,
                "score": score,
                "reasons": reasons,
                "layout_mode": normalized["layout_mode"],
                "style_pack": normalized["style_pack"],
                "accepted_context_types": normalized["accepted_context_types"],
            }
        )

    scored.sort(key=lambda item: (-int(item["score"]), str(item["profile_id"])))
    return scored


def _target_profile_validation_report(profile: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    profile_id = str(profile.get("profile_id") or "")
    if not profile_id:
        errors.append("profile_id is required.")
    layout_mode = str(profile.get("layout_mode") or "")
    if layout_mode not in KNOWN_LAYOUT_MODES:
        errors.append("layout_mode must be one of: document, slides.")
    layout_slots = profile.get("layout_slots")
    if not isinstance(layout_slots, dict) or not layout_slots:
        errors.append("layout_slots must include at least one slot.")
    else:
        for slot_name, slot in layout_slots.items():
            if not isinstance(slot, dict):
                errors.append(f"layout slot {slot_name} must be an object.")
                continue
            accepts = _string_list(slot.get("accepts"))
            if not accepts:
                warnings.append(f"layout slot {slot_name} does not declare accepted block types.")
            unknown = [block_type for block_type in accepts if block_type not in KNOWN_BLOCK_TYPES]
            if unknown:
                warnings.append(f"layout slot {slot_name} has unknown block types: {', '.join(unknown)}.")
    accepted_block_types = _string_list(profile.get("accepted_block_types"))
    unknown_blocks = [block_type for block_type in accepted_block_types if block_type not in KNOWN_BLOCK_TYPES]
    if unknown_blocks:
        warnings.append(f"accepted_block_types includes unknown values: {', '.join(unknown_blocks)}.")
    accepted_context_types = _string_list(profile.get("accepted_context_types"))
    unknown_context = [item_type for item_type in accepted_context_types if item_type not in KNOWN_CONTEXT_TYPES]
    if unknown_context:
        warnings.append(f"accepted_context_types includes unknown values: {', '.join(unknown_context)}.")
    if "render_check" not in _string_list(profile.get("validation_required")):
        warnings.append("validation_required should include render_check for generated PDFs.")
    return {
        "profile_validation_version": "0.1",
        "is_valid": not errors,
        "profile": profile,
        "errors": errors,
        "warnings": warnings,
        "compatibility": {
            "layout_mode": layout_mode,
            "accepted_block_types": accepted_block_types,
            "accepted_context_types": accepted_context_types,
            "required_slots": [
                str(name)
                for name, slot in (layout_slots or {}).items()
                if isinstance(slot, dict) and bool(slot.get("required"))
            ],
            "repeating_slots": [
                str(name)
                for name, slot in (layout_slots or {}).items()
                if isinstance(slot, dict) and bool(slot.get("repeats"))
            ],
            "validation_required": _string_list(profile.get("validation_required")),
        },
    }


def _default_layout_slots(layout_mode: str) -> dict[str, dict[str, Any]]:
    if layout_mode == "slides":
        return {
            "title": {"accepts": ["section"], "required": True},
            "evidence_slide": {"accepts": ["slide", "section", "table", "image", "code"], "repeats": True},
            "source_map": {"accepts": ["slide", "section"], "required": True},
        }
    return {
        "body": {"accepts": ["section", "table", "image", "code", "citation"], "repeats": True},
        "source_map": {"accepts": ["section"], "required": True},
    }


def _accepted_block_types_from_slots(layout_slots: dict[str, Any]) -> list[str]:
    block_types: list[str] = []
    for slot in layout_slots.values():
        if isinstance(slot, dict):
            for block_type in _string_list(slot.get("accepts")):
                if block_type not in block_types:
                    block_types.append(block_type)
    return block_types or ["section"]


def _context_types_for_blocks(block_types: list[str]) -> list[str]:
    mapping = {
        "section": ["text", "document"],
        "slide": ["text", "document", "image", "data", "code", "audio", "video"],
        "code": ["code"],
        "table": ["data"],
        "data": ["data"],
        "image": ["image"],
        "pdf_reference": ["pdf"],
        "audio_reference": ["audio"],
        "video_reference": ["video"],
        "media_reference": ["audio", "video", "media"],
        "citation": ["web_link", "text", "document"],
    }
    context_types: list[str] = []
    for block_type in block_types:
        for context_type in mapping.get(block_type, []):
            if context_type not in context_types:
                context_types.append(context_type)
    return context_types or ["text"]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _compose_slides(
    packet: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    items = list(packet.get("items", []))
    title = str(profile.get("title") or profile.get("name") or "AgentPDF Slide Deck")
    all_refs = [item["source_ref"] for item in items]
    slides: list[dict[str, Any]] = [
        {
            "slide_id": "slide_001",
            "title": title,
            "subtitle": str(packet.get("title") or "Context-backed PDF deck"),
            "body": [str(packet.get("intent") or "Generated from a local Context Packet.")],
            "source_refs": all_refs,
            "layout": "title",
        },
        {
            "slide_id": "slide_002",
            "title": "Context Summary",
            "body": [
                f"{item['source_ref']} {item['type']}: {item.get('label', 'source')} ({item.get('role', 'source')})"
                for item in items
            ],
            "source_refs": all_refs,
            "layout": "bullets",
        },
    ]
    for item in items:
        slides.append(_slide_for_item(item, len(slides) + 1))
    slides.append(
        {
            "slide_id": f"slide_{len(slides) + 1:03d}",
            "title": "Source Map",
            "body": [
                f"slide_{index + 1:03d} -> {', '.join(slide.get('source_refs', [])) or 'no source refs'}"
                for index, slide in enumerate(slides)
            ],
            "source_refs": all_refs,
            "layout": "source_map",
        }
    )
    source_map: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    for index, slide in enumerate(slides, start=1):
        source_refs = [str(ref) for ref in slide.get("source_refs", [])]
        block_id = str(slide["slide_id"])
        blocks.append(
            {
                "block_id": block_id,
                "type": "slide",
                "title": str(slide.get("title") or block_id),
                "source_refs": source_refs,
                "target_slot": "slide",
                "render_hints": {
                    "slide_number": index,
                    "layout": slide.get("layout", "content"),
                    "contains": _slide_contains(slide),
                },
            }
        )
        for ref in source_refs:
            item = next((candidate for candidate in items if candidate["source_ref"] == ref), None)
            source_map.append(
                {
                    "block_id": block_id,
                    "context_item_id": item.get("context_item_id") if item else ref,
                    "source_ref": ref,
                    "type": item.get("type") if item else "source",
                    "block_type": "slide",
                    "label": item.get("label") if item else None,
                }
            )

    covered_refs = sorted({mapping["source_ref"] for mapping in source_map})
    coverage = {
        "context_item_count": len(items),
        "covered_context_items": len(covered_refs),
        "source_ref_count": len(covered_refs),
        "coverage_ratio": 1.0 if not items else round(len(covered_refs) / len(items), 4),
        "uncovered_context_items": [
            item["context_item_id"] for item in items if item["source_ref"] not in covered_refs
        ],
    }
    composition_ir = {
        "composition_version": "0.1",
        "composition_id": f"cmp_{uuid4().hex[:16]}",
        "context_packet_id": packet["context_packet_id"],
        "target_profile_id": profile.get("profile_id", "custom"),
        "blocks": blocks,
    }
    return slides, composition_ir, source_map, coverage


def _slide_for_item(item: dict[str, Any], slide_number: int) -> dict[str, Any]:
    item_type = str(item.get("type") or "source")
    content = item.get("content") or {}
    metadata = item.get("metadata") or {}
    source_refs = [item["source_ref"]]
    slide: dict[str, Any] = {
        "slide_id": f"slide_{slide_number:03d}",
        "title": str(item.get("label") or item_type),
        "subtitle": f"{item_type} evidence | source {item['source_ref']}",
        "source_refs": source_refs,
        "layout": _slide_layout_for_item(item_type),
    }
    if item_type == "data" and isinstance(content.get("table"), dict):
        table = content["table"]
        slide["table"] = {
            "columns": [str(column) for column in table.get("columns", [])],
            "rows": [[str(cell) for cell in row] for row in table.get("rows", [])],
        }
        slide["body"] = ["Structured table evidence rendered from Context Packet data."]
    elif item_type == "image":
        slide["image_path"] = str(metadata.get("path") or item.get("uri") or "")
        slide["body"] = [f"Figure dimensions: {metadata.get('width')}x{metadata.get('height')}"]
    elif item_type == "code":
        slide["code"] = _clip(str(content.get("text", "")), 1500)
        slide["body"] = [
            f"Language: {_language_from_extension(str(metadata.get('extension', '')))}",
            f"Lines captured: {metadata.get('line_count', 'unknown')}",
        ]
    elif item_type == "pdf":
        slide["body"] = [
            f"PDF pages: {metadata.get('page_count', '?')}",
            f"Path: {metadata.get('path', item.get('uri', ''))}",
        ]
    elif item_type in {"audio", "video", "media"}:
        slide["body"] = _media_body_lines(item)
        transcript = _transcript_excerpt(content)
        if transcript:
            slide["body"].append(f"Transcript excerpt: {transcript}")
    elif item_type == "web_link":
        slide["body"] = [f"Web source: {item.get('uri')}"]
    else:
        slide["body"] = [_clip(str(content.get("text", metadata.get("preview", ""))), 520)]
    return slide


def _slide_layout_for_item(item_type: str) -> str:
    return {
        "data": "table",
        "image": "image",
        "code": "code",
        "pdf": "pdf_reference",
        "audio": "media",
        "video": "media",
        "media": "media",
        "web_link": "citation",
    }.get(item_type, "content")


def _slide_contains(slide: dict[str, Any]) -> list[str]:
    contains = ["text"]
    if slide.get("table"):
        contains.append("table")
    if slide.get("image_path"):
        contains.append("image")
    if slide.get("code"):
        contains.append("code")
    return contains


def _slides_to_outline(slides: list[dict[str, Any]]) -> str:
    lines = []
    for index, slide in enumerate(slides, start=1):
        lines.append(f"# Slide {index}: {slide.get('title', '')}")
        for ref in slide.get("source_refs", []):
            lines.append(f"- Source: `{ref}`")
        if slide.get("body"):
            for item in slide["body"]:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _compose_markdown(
    packet: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    title = str(profile.get("title") or profile.get("name") or packet.get("title") or "AgentPDF Composition")
    items = list(packet.get("items", []))
    blocks: list[dict[str, Any]] = []
    source_map: list[dict[str, Any]] = []
    lines = [
        f"# {title}",
        "",
        "## Target Profile",
        "",
        f"**Profile:** {profile.get('profile_id', 'custom')}",
    ]
    if profile.get("audience"):
        lines.append(f"**Audience:** {profile['audience']}")
    if packet.get("intent"):
        lines.extend(["", "## Context Intent", "", str(packet["intent"])])

    summary_block = _block("summary", "Context Summary", [item["source_ref"] for item in items])
    blocks.append(summary_block)
    lines.extend(["", "## Context Summary", ""])
    for item in items:
        lines.append(f"- `{item['source_ref']}` {item['type']}: {item.get('label', 'source')} ({item.get('role', 'source')})")
        source_map.append(
            {
                "block_id": summary_block["block_id"],
                "context_item_id": item["context_item_id"],
                "source_ref": item["source_ref"],
                "type": item["type"],
                "label": item.get("label"),
            }
        )

    lines.extend(["", "## Evidence Table", "", "| Source Ref | Type | Label | Evidence |", "|---|---|---|---|"])
    evidence_block = _block("evidence_table", "Evidence Table", [item["source_ref"] for item in items])
    blocks.append(evidence_block)
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['source_ref']}`",
                    item["type"],
                    _escape_table(str(item.get("label", ""))),
                    _escape_table(_evidence_summary(item)),
                ]
            )
            + " |"
        )

    for item in items:
        block = _block_for_item(item)
        blocks.append(block)
        lines.extend(_render_context_item(item))
        source_map.append(
            {
                "block_id": block["block_id"],
                "context_item_id": item["context_item_id"],
                "source_ref": item["source_ref"],
                "type": item["type"],
                "block_type": block["type"],
                "label": item.get("label"),
            }
        )

    lines.extend(["", "## Source Map", ""])
    for mapping in source_map:
        lines.append(f"- `{mapping['block_id']}` -> `{mapping['source_ref']}` ({mapping['type']})")

    covered_refs = sorted({mapping["source_ref"] for mapping in source_map})
    coverage = {
        "context_item_count": len(items),
        "covered_context_items": len(covered_refs),
        "source_ref_count": len(covered_refs),
        "coverage_ratio": 1.0 if not items else round(len(covered_refs) / len(items), 4),
        "uncovered_context_items": [
            item["context_item_id"] for item in items if item["source_ref"] not in covered_refs
        ],
    }
    lines.extend(
        [
            "",
            "## Evidence Coverage",
            "",
            f"Covered context items: {coverage['covered_context_items']} / {coverage['context_item_count']}",
            f"Coverage ratio: {coverage['coverage_ratio']}",
        ]
    )
    composition_ir = {
        "composition_version": "0.1",
        "composition_id": f"cmp_{uuid4().hex[:16]}",
        "context_packet_id": packet["context_packet_id"],
        "target_profile_id": profile.get("profile_id", "custom"),
        "blocks": blocks,
    }
    return "\n".join(lines).strip() + "\n", composition_ir, source_map, coverage


def _render_context_item(item: dict[str, Any]) -> list[str]:
    item_type = item["type"]
    source_ref = item["source_ref"]
    label = str(item.get("label") or item_type)
    lines = ["", f"## {label}", "", f"Source ref: `{source_ref}`", ""]
    content = item.get("content") or {}
    metadata = item.get("metadata") or {}
    if item_type == "text":
        lines.extend([str(content.get("text", "")), ""])
    elif item_type == "code":
        language = _language_from_extension(str(metadata.get("extension", "")))
        code_evidence = metadata.get("code_evidence") if isinstance(metadata.get("code_evidence"), dict) else {}
        if code_evidence:
            lines.extend(
                [
                    f"Code evidence: {code_evidence.get('language')}, {code_evidence.get('line_count')} lines, {code_evidence.get('symbol_count')} symbols",
                    f"Code hash: `{code_evidence.get('code_hash')}`",
                    "",
                ]
            )
            symbols = code_evidence.get("symbols")
            if isinstance(symbols, list) and symbols:
                lines.append("Symbols: " + ", ".join(str(symbol.get("name")) for symbol in symbols[:12] if isinstance(symbol, dict)))
                lines.append("")
        lines.extend([f"```{language}", _clip(str(content.get("text", "")), 2400).rstrip(), "```", ""])
    elif item_type == "data":
        lines.extend(_render_data_item(content, metadata))
    elif item_type == "document":
        text = str(content.get("text", ""))
        if text:
            lines.extend(["```text", _clip(text, 2400).rstrip(), "```", ""])
        else:
            lines.append(f"Document source path: `{metadata.get('path', item.get('uri', ''))}`")
            lines.append("")
    elif item_type == "image":
        path = str(metadata.get("path") or item.get("uri") or "")
        filename = str(metadata.get("filename") or label)
        visual = metadata.get("visual_evidence") if isinstance(metadata.get("visual_evidence"), dict) else {}
        lines.extend(
            [
                f"Figure source `{filename}` ({metadata.get('width')}x{metadata.get('height')}).",
                "",
                *(
                    [
                        f"Visual evidence: non-white ratio {visual.get('non_white_ratio')}, blank={str(visual.get('is_blank')).lower()}, hash `{visual.get('perceptual_hash')}`.",
                        "",
                    ]
                    if visual
                    else []
                ),
                f"![{filename}]({path})",
                "",
            ]
        )
    elif item_type == "pdf":
        lines.append(f"PDF source has {metadata.get('page_count', '?')} page(s) at `{metadata.get('path')}`.")
        pdf_evidence = metadata.get("pdf_evidence") if isinstance(metadata.get("pdf_evidence"), dict) else {}
        if pdf_evidence:
            lines.append(
                f"Text evidence: {pdf_evidence.get('text_char_count', 0)} characters across {pdf_evidence.get('extracted_page_count', 0)} extracted page(s)."
            )
            for page in pdf_evidence.get("pages", [])[:3]:
                if not isinstance(page, dict) or not page.get("text_preview"):
                    continue
                lines.extend(
                    [
                        "",
                        f"### Page {page.get('page_number')} Text Evidence",
                        "",
                        str(page.get("text_preview")),
                    ]
                )
        lines.append("")
    elif item_type in {"audio", "video", "media"}:
        lines.extend(_render_media_item(item))
    elif item_type == "web_link":
        citation = metadata.get("citation_evidence") if isinstance(metadata.get("citation_evidence"), dict) else {}
        title = str(citation.get("title") or item.get("label") or "Web source")
        url = str(citation.get("normalized_url") or item.get("uri") or "")
        lines.append(f"Web source: [{title}]({url})")
        if citation.get("domain"):
            lines.append(f"Domain: `{citation['domain']}`")
        if citation.get("snippet"):
            lines.extend(["", str(citation["snippet"])])
        lines.append(f"Fetch status: `{citation.get('fetch_status', 'not_fetched')}`")
        lines.append("")
    else:
        lines.append(f"Local source path: `{metadata.get('path', item.get('uri', ''))}`")
        lines.append("")
    return lines


def _render_data_item(content: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    table = content.get("table")
    if isinstance(table, dict):
        rows = _rows_from_table_payload(table)
        if rows:
            lines: list[str] = []
            table_evidence = table.get("table_evidence") if isinstance(table.get("table_evidence"), dict) else metadata.get("table_evidence")
            if isinstance(table_evidence, dict):
                lines.extend(
                    [
                        f"Table evidence: {table_evidence.get('row_count')} rows, {table_evidence.get('column_count')} columns",
                        f"Table hash: `{table_evidence.get('table_hash')}`",
                        "",
                    ]
                )
            lines.extend(_markdown_table(rows))
            return lines
    path = Path(str(metadata.get("path", "")))
    text = str(content.get("text", ""))
    if path.suffix.lower() == ".csv" and text:
        rows = list(csv.reader(text.splitlines()))[:6]
        if rows:
            return _markdown_table([[str(cell) for cell in row] for row in rows])
    if path.suffix.lower() == ".json" and text:
        try:
            raw = json.loads(text)
            return ["```json", json.dumps(raw, indent=2)[:2400], "```", ""]
        except json.JSONDecodeError:
            pass
    return ["```text", _clip(text, 2400).rstrip(), "```", ""]


def _render_media_item(item: dict[str, Any]) -> list[str]:
    content = item.get("content") or {}
    metadata = item.get("metadata") or {}
    lines = _media_body_lines(item)
    transcript = _transcript_excerpt(content, max_chars=1800)
    if transcript:
        lines.extend(["", "### Transcript Excerpt", "", "```text", transcript.rstrip(), "```", ""])
    chapters = content.get("chapters")
    if isinstance(chapters, list) and chapters:
        lines.extend(["", "### Chapters", ""])
        for chapter in chapters[:10]:
            lines.append(f"- {_format_marker(chapter)}")
        lines.append("")
    keyframes = content.get("keyframes")
    if isinstance(keyframes, list) and keyframes:
        lines.extend(["", "### Keyframes", ""])
        for keyframe in keyframes[:10]:
            lines.append(f"- {_format_marker(keyframe)}")
        lines.append("")
    if not transcript and not chapters and not keyframes:
        lines.extend(
            [
                "",
                "Media source is recorded as local file metadata. Provide `transcript`, `chapters`, or `keyframes` in the Context Packet for richer local composition.",
                "",
            ]
        )
    if metadata.get("sha256"):
        lines.extend([f"SHA-256: `{str(metadata['sha256'])[:16]}...`", ""])
    return lines


def _media_body_lines(item: dict[str, Any]) -> list[str]:
    metadata = item.get("metadata") or {}
    content = item.get("content") or {}
    media = content.get("media") if isinstance(content.get("media"), dict) else {}
    filename = str(metadata.get("filename") or media.get("filename") or item.get("label") or "media")
    lines = [
        f"Media file: `{filename}`",
        f"Kind: {metadata.get('media_kind', item.get('type', 'media'))}",
    ]
    if metadata.get("duration_seconds") is not None:
        lines.append(f"Duration: {metadata['duration_seconds']} second(s)")
    if metadata.get("transcript_char_count") is not None:
        lines.append(f"Transcript characters: {metadata['transcript_char_count']}")
    if metadata.get("transcript_source"):
        lines.append(f"Transcript source: `{metadata['transcript_source']}`")
    if metadata.get("chapter_count") is not None:
        lines.append(f"Chapters: {metadata['chapter_count']}")
    if metadata.get("keyframe_count") is not None:
        lines.append(f"Keyframes: {metadata['keyframe_count']}")
    return lines


def _transcript_excerpt(content: dict[str, Any], max_chars: int = 520) -> str:
    transcript = content.get("transcript")
    if not isinstance(transcript, dict):
        return ""
    return _clip(str(transcript.get("text") or ""), max_chars).strip()


def _format_marker(marker: Any) -> str:
    if not isinstance(marker, dict):
        return str(marker)
    timestamp = marker.get("timestamp_seconds")
    if timestamp is None:
        timestamp = marker.get("start_seconds")
    label = marker.get("title") or marker.get("label") or marker.get("text") or marker.get("marker_id") or "marker"
    if timestamp is None:
        return str(label)
    return f"{timestamp}s: {label}"


def _media_render_hints(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata") or {}
    return {
        "path": str(metadata.get("path") or item.get("uri") or ""),
        "mime_type": metadata.get("mime_type"),
        "media_kind": metadata.get("media_kind", item.get("type")),
        "duration_seconds": metadata.get("duration_seconds"),
        "transcript_char_count": metadata.get("transcript_char_count"),
        "transcript_source": metadata.get("transcript_source"),
        "transcript_source_path": metadata.get("transcript_source_path"),
        "transcript_sha256": metadata.get("transcript_sha256"),
        "chapter_count": metadata.get("chapter_count"),
        "keyframe_count": metadata.get("keyframe_count"),
    }


def _block(block_id: str, title: str, source_refs: list[str]) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "type": "section",
        "title": title,
        "source_refs": source_refs,
    }


def _block_for_item(item: dict[str, Any]) -> dict[str, Any]:
    item_type = str(item.get("type") or "section")
    metadata = item.get("metadata") or {}
    block_type = {
        "code": "code",
        "data": "table" if _has_table_preview(item) else "data",
        "image": "image",
        "pdf": "pdf_reference",
        "audio": "audio_reference",
        "video": "video_reference",
        "media": "media_reference",
        "web_link": "citation",
    }.get(item_type, "section")
    hints: dict[str, Any] = {}
    if block_type == "code":
        hints["language"] = _language_from_extension(str(metadata.get("extension", "")))
        hints["line_count"] = metadata.get("line_count")
        hints["code_evidence"] = metadata.get("code_evidence")
    elif block_type == "table":
        rows = _data_rows(item)
        hints["columns"] = rows[0] if rows else []
        hints["preview_rows"] = max(len(rows) - 1, 0)
        hints["table_evidence"] = metadata.get("table_evidence")
    elif block_type == "image":
        hints.update(
            {
                "path": str(metadata.get("path") or item.get("uri") or ""),
                "width": metadata.get("width"),
                "height": metadata.get("height"),
                "alt": str(metadata.get("filename") or item.get("label") or "image"),
                "visual_evidence": metadata.get("visual_evidence"),
            }
        )
    elif block_type == "pdf_reference":
        hints["page_count"] = metadata.get("page_count")
        hints["path"] = str(metadata.get("path") or item.get("uri") or "")
        hints["pdf_evidence"] = metadata.get("pdf_evidence")
    elif block_type in {"audio_reference", "video_reference", "media_reference"}:
        hints.update(_media_render_hints(item))
    elif block_type == "citation":
        hints["uri"] = item.get("uri")
        hints["citation_evidence"] = metadata.get("citation_evidence")
    return {
        "block_id": f"item_{item['context_item_id']}",
        "type": block_type,
        "title": str(item.get("label", item_type)),
        "source_refs": [item["source_ref"]],
        "target_slot": _target_slot_for_block(block_type),
        "render_hints": {key: value for key, value in hints.items() if value is not None},
    }


def _target_slot_for_block(block_type: str) -> str:
    return {
        "code": "code_review",
        "table": "evidence_table",
        "data": "data_appendix",
        "image": "visual_evidence",
        "pdf_reference": "source_appendix",
        "audio_reference": "media_evidence",
        "video_reference": "media_evidence",
        "media_reference": "media_evidence",
        "citation": "citations",
    }.get(block_type, "body")


def _has_table_preview(item: dict[str, Any]) -> bool:
    return bool(_data_rows(item))


def _data_rows(item: dict[str, Any]) -> list[list[str]]:
    metadata = item.get("metadata") or {}
    content = item.get("content") or {}
    table = content.get("table")
    if isinstance(table, dict):
        return _rows_from_table_payload(table)
    path = Path(str(metadata.get("path", "")))
    text = str(content.get("text", ""))
    if path.suffix.lower() != ".csv" or not text:
        return []
    return [[str(cell) for cell in row] for row in list(csv.reader(text.splitlines()))[:6]]


def _rows_from_table_payload(table: dict[str, Any]) -> list[list[str]]:
    columns = [str(column) for column in table.get("columns", [])]
    rows = [[str(cell) for cell in row] for row in table.get("rows", [])]
    if not columns:
        return []
    return [columns, *rows[:10]]


def _markdown_table(rows: list[list[str]]) -> list[str]:
    header = rows[0]
    lines = [
        "| " + " | ".join(_escape_table(cell) for cell in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows[1:]:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(_escape_table(cell) for cell in padded[: len(header)]) + " |")
    lines.append("")
    return lines


def _evidence_summary(item: dict[str, Any]) -> str:
    metadata = item.get("metadata", {})
    bits = []
    if metadata.get("page_count") is not None:
        bits.append(f"{metadata['page_count']} page(s)")
    if metadata.get("line_count") is not None:
        bits.append(f"{metadata['line_count']} line(s)")
    if metadata.get("width") is not None and metadata.get("height") is not None:
        bits.append(f"{metadata['width']}x{metadata['height']}")
    if metadata.get("duration_seconds") is not None:
        bits.append(f"{metadata['duration_seconds']} second(s)")
    if metadata.get("transcript_char_count") is not None:
        bits.append(f"{metadata['transcript_char_count']} transcript chars")
    if metadata.get("chapter_count") is not None:
        bits.append(f"{metadata['chapter_count']} chapter(s)")
    if metadata.get("keyframe_count") is not None:
        bits.append(f"{metadata['keyframe_count']} keyframe(s)")
    if metadata.get("sha256"):
        bits.append(f"sha256 {str(metadata['sha256'])[:12]}")
    return ", ".join(bits) or "recorded source ref"


def _composition_warnings(packet: dict[str, Any]) -> list[str]:
    items = packet.get("items", [])
    if any(item.get("type") in {"audio", "video", "media"} for item in items):
        return ["Media context uses provided transcript"]
    return []


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _language_from_extension(extension: str) -> str:
    return {
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".py": "python",
        ".rs": "rust",
        ".go": "go",
        ".sql": "sql",
    }.get(extension, extension.lstrip("."))


def _clip(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "\n...[truncated]"
