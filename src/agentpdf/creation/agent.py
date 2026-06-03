from __future__ import annotations

import mimetypes
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentpdf.artifacts.bundle import export_artifact_bundle, verify_artifact_bundle
from agentpdf.artifacts.store import build_artifact
from agentpdf.compose.context import DEFAULT_TARGET_PROFILES
from agentpdf.context.classify import classify_context
from agentpdf.core.pdf import BUILTIN_STYLE_PACKS, SUPPORTED_IMAGE_SUFFIXES, create_markdown_pdf
from agentpdf.evidence.coverage import create_coverage_report
from agentpdf.evidence.context_packet_report import create_context_packet_report
from agentpdf.schemas.errors import AgentPDFException
from agentpdf.schemas.models import ToolResult, ValidationCheck, ValidationReport
from agentpdf.security.paths import resolve_input_path
from agentpdf.validation.pdf import blank_page_check_pdf, render_check_pdf, validate_pdf


CREATE_TEMPLATES: dict[str, dict[str, Any]] = {
    "one_pager": {
        "name": "One Page Brief",
        "description": "A compact one-page explainer for agent and developer handoffs.",
        "default_sections": ["Overview", "Key Points", "Next Steps"],
        "style_pack": "paper_ink",
        "keywords": {"one pager", "brief", "summary", "handout"},
    },
    "business_report": {
        "name": "Business Report",
        "description": "A structured report with executive summary and recommendations.",
        "default_sections": ["Executive Summary", "Findings", "Recommendations"],
        "style_pack": "business_report_modern",
        "keywords": {"report", "business", "executive", "metrics"},
    },
    "research_brief": {
        "name": "Research Brief",
        "description": "A cited-style research brief with scope, findings, and implications.",
        "default_sections": ["Research Question", "Findings", "Implications"],
        "style_pack": "paper_ink",
        "keywords": {"research", "brief", "analysis", "study"},
    },
    "proposal": {
        "name": "Proposal",
        "description": "A local proposal template with problem, approach, and deliverables.",
        "default_sections": ["Problem", "Approach", "Deliverables", "Timeline"],
        "style_pack": "business_report_modern",
        "keywords": {"proposal", "client", "scope", "deliverable"},
    },
    "worksheet": {
        "name": "Worksheet",
        "description": "An education or training worksheet with prompts and checklist items.",
        "default_sections": ["Learning Goal", "Practice", "Checklist"],
        "style_pack": "paper_ink",
        "keywords": {"worksheet", "training", "lesson", "exercise", "education"},
    },
    "resume": {
        "name": "Resume",
        "description": "A compact resume template for structured profile data.",
        "default_sections": ["Summary", "Experience", "Skills"],
        "style_pack": "resume_modern",
        "keywords": {"resume", "cv", "profile", "candidate"},
    },
    "invoice": {
        "name": "Invoice",
        "description": "A clean invoice document for local structured billing data.",
        "default_sections": ["Bill To", "Items", "Payment Notes"],
        "style_pack": "invoice_clean",
        "keywords": {"invoice", "bill", "payment", "quote"},
    },
}

SUPPORTED_AGENT_BLOCK_TYPES = [
    "section",
    "code",
    "table",
    "image",
    "slide",
    "audio_reference",
    "video_reference",
    "media_reference",
    "citation",
]


CREATE_TEMPLATE_CONTRACTS: dict[str, dict[str, Any]] = {
    "one_pager": {
        "template_kind": "prompt_document",
        "fields": {
            "required": [],
            "optional": ["audience", "sections", "checklist", "title"],
        },
        "layout_slots": ["header", "overview", "key_points", "next_steps"],
        "sample_data": {
            "title": "Local Agent One Pager",
            "audience": "agent builders",
            "sections": [
                {"heading": "Overview", "body": "A compact handoff for a local PDF workflow."},
                {"heading": "Key Points", "body": "The output is local, validated, and agent-readable."},
            ],
            "checklist": ["Inspect the PDF", "Run render validation", "Share the artifact path"],
        },
    },
    "business_report": {
        "template_kind": "structured_document",
        "fields": {
            "required": [],
            "optional": ["audience", "sections", "checklist", "title"],
        },
        "layout_slots": ["header", "executive_summary", "findings", "recommendations"],
        "sample_data": {
            "title": "Local PDF Infrastructure Report",
            "audience": "engineering leaders",
            "sections": [
                {"heading": "Executive Summary", "body": "Local PDF agents reduce workflow friction."},
                {"heading": "Recommendations", "body": "Ship CLI, MCP, REST, and SDK surfaces together."},
            ],
        },
    },
    "research_brief": {
        "template_kind": "structured_document",
        "fields": {
            "required": [],
            "optional": ["audience", "sections", "checklist", "title"],
        },
        "layout_slots": ["header", "research_question", "findings", "implications"],
        "sample_data": {
            "title": "Research Brief: Local PDF Agents",
            "audience": "agent infrastructure developers",
            "sections": [
                {"heading": "Research Question", "body": "How should agents create PDFs locally?"},
                {"heading": "Findings", "body": "Templates need fields, sample data, validation, and previews."},
            ],
        },
    },
    "proposal": {
        "template_kind": "structured_document",
        "fields": {
            "required": ["problem", "approach"],
            "optional": ["client", "deliverables", "timeline", "title"],
        },
        "layout_slots": ["header", "client", "problem", "approach", "deliverables", "timeline"],
        "sample_data": {
            "title": "Local PDF Agent Proposal",
            "client": "Agent teams",
            "problem": "Teams need reliable PDF creation tools that run before cloud services exist.",
            "approach": "Use local templates, style packs, structured JSON, and validation evidence.",
            "deliverables": ["Template catalog", "Preview PDF", "CLI/MCP/REST access"],
            "timeline": "Two local-first implementation passes.",
        },
    },
    "worksheet": {
        "template_kind": "structured_document",
        "fields": {
            "required": ["learning_goal"],
            "optional": ["questions", "checklist", "title"],
        },
        "layout_slots": ["header", "learning_goal", "practice", "checklist"],
        "sample_data": {
            "title": "PDF Validation Worksheet",
            "learning_goal": "Practice validating generated PDFs before an agent shares them.",
            "questions": [
                "What evidence proves the PDF rendered?",
                "Which tool checks for blank pages?",
            ],
            "checklist": ["Generate the PDF", "Run render-check", "Inspect extracted text"],
        },
    },
    "resume": {
        "template_kind": "structured_document",
        "fields": {
            "required": ["name"],
            "optional": ["headline", "contact", "summary", "skills", "experience", "title"],
        },
        "layout_slots": ["header", "contact", "summary", "skills", "experience"],
        "sample_data": {
            "name": "Alex Agent",
            "headline": "Agent Infrastructure Engineer",
            "contact": {"email": "alex@example.com", "location": "Remote"},
            "summary": "Builds local-first document agents.",
            "skills": ["PDF tooling", "MCP", "TypeScript", "Python"],
            "experience": [
                {
                    "role": "Lead Engineer",
                    "company": "OkPDF",
                    "period": "2024-2026",
                    "bullets": ["Built template-driven PDF creation."],
                }
            ],
        },
    },
    "invoice": {
        "template_kind": "structured_document",
        "fields": {
            "required": ["items"],
            "optional": ["invoice_number", "client", "bill_to", "due_date", "payment_notes", "total", "title"],
        },
        "layout_slots": ["header", "billing", "line_items", "totals", "notes"],
        "sample_data": {
            "title": "Invoice INV-1001",
            "invoice_number": "INV-1001",
            "client": "AgentPDF Labs",
            "due_date": "2026-06-30",
            "items": [
                {"description": "Template implementation", "quantity": 2, "unit_price": 500},
                {"description": "Validation workflow", "quantity": 1, "unit_price": 350},
            ],
            "payment_notes": "Pay by bank transfer.",
        },
    },
}


BUILTIN_TEMPLATE_PACKS: dict[str, dict[str, Any]] = {
    "local_agent_starter": {
        "pack_id": "local_agent_starter",
        "name": "Local Agent Starter",
        "version": "0.1.0",
        "description": "Local-first templates for agent-generated reports, packets, and worksheets.",
        "license": "Apache-2.0",
        "cloud_required": False,
        "templates": [
            {
                "template_id": "board_audit",
                "name": "Board Audit Packet",
                "description": "A leadership-ready audit packet for code, metrics, evidence, and recommendations.",
                "base_template": "business_report",
                "target_profile": "technical_audit",
                "default_style_pack": "business_report_modern",
                "fields": {
                    "required": ["title", "sections"],
                    "optional": ["audience", "checklist", "risks"],
                },
                "layout_slots": ["cover", "executive_summary", "findings", "evidence", "recommendations"],
                "supported_block_types": [
                    "section",
                    "code",
                    "table",
                    "image",
                    "slide",
                    "audio_reference",
                    "video_reference",
                    "media_reference",
                    "citation",
                ],
                "color_schemes": {
                    "executive_blue": {
                        "primary": "#1f3a5f",
                        "accent": "#f59e0b",
                        "text": "#111827",
                    },
                    "ink_review": {
                        "primary": "#111827",
                        "accent": "#0f766e",
                        "text": "#111827",
                    },
                },
                "sample_data": {
                    "title": "AgentPDF Board Audit",
                    "audience": "engineering leadership",
                    "sections": [
                        {
                            "heading": "Executive Summary",
                            "body": "AgentPDF turns heterogeneous context into validated PDF artifacts.",
                        },
                        {
                            "heading": "Evidence",
                            "body": "Every block can be traced through source refs, validation, and patch manifests.",
                        },
                    ],
                    "checklist": ["Run render-check", "Inspect evidence coverage", "Archive source map"],
                },
            },
            {
                "template_id": "research_brief_packet",
                "name": "Research Brief Packet",
                "description": "A cited research brief with findings, implications, and source notes.",
                "base_template": "research_brief",
                "target_profile": "research_brief",
                "default_style_pack": "paper_ink",
                "fields": {
                    "required": ["title", "sections"],
                    "optional": ["audience", "checklist", "citations"],
                },
                "layout_slots": ["cover", "research_question", "findings", "implications", "sources"],
                "supported_block_types": [
                    "section",
                    "table",
                    "image",
                    "code",
                    "audio_reference",
                    "video_reference",
                    "citation",
                ],
                "color_schemes": {
                    "paper_blue": {
                        "primary": "#1d4ed8",
                        "accent": "#0f766e",
                        "text": "#111827",
                    },
                    "citation_teal": {
                        "primary": "#0f766e",
                        "accent": "#9333ea",
                        "text": "#111827",
                    },
                },
                "sample_data": {
                    "title": "Local Agent Research Brief",
                    "audience": "agent infrastructure teams",
                    "sections": [
                        {
                            "heading": "Research Question",
                            "body": "How should local agents turn heterogeneous context into cited PDFs?",
                        },
                        {
                            "heading": "Findings",
                            "body": "Target profiles, template packs, and evidence coverage make outputs auditable.",
                        },
                    ],
                    "checklist": ["Review citations", "Run render-check", "Attach source map"],
                },
            },
            {
                "template_id": "evidence_packet",
                "name": "Evidence Packet",
                "description": "A source-backed packet for exhibits, claims, and validation evidence.",
                "base_template": "business_report",
                "target_profile": "evidence_packet_pdf",
                "default_style_pack": "business_report_modern",
                "fields": {
                    "required": ["title", "sections"],
                    "optional": ["audience", "checklist", "source_notes"],
                },
                "layout_slots": ["cover", "evidence_summary", "source_items", "source_map"],
                "supported_block_types": [
                    "section",
                    "code",
                    "table",
                    "image",
                    "slide",
                    "audio_reference",
                    "video_reference",
                    "media_reference",
                    "citation",
                ],
                "color_schemes": {
                    "evidence_slate": {
                        "primary": "#334155",
                        "accent": "#dc2626",
                        "text": "#111827",
                    }
                },
                "sample_data": {
                    "title": "Local Evidence Packet",
                    "audience": "reviewers",
                    "sections": [
                        {
                            "heading": "Evidence Summary",
                            "body": "Every included block keeps source refs and validation evidence.",
                        },
                        {
                            "heading": "Source Map",
                            "body": "Use the composition artifact to audit each claim and inserted asset.",
                        },
                    ],
                    "checklist": ["Confirm source refs", "Run coverage report", "Export audit bundle"],
                },
            },
            {
                "template_id": "agent_resume",
                "name": "Agent Resume",
                "description": "An ATS-friendly resume template with source-backed profile evidence.",
                "base_template": "resume",
                "target_profile": "resume_pdf",
                "default_style_pack": "resume_modern",
                "fields": {
                    "required": ["name"],
                    "optional": ["headline", "contact", "summary", "skills", "experience"],
                },
                "layout_slots": ["header", "contact", "summary", "skills", "experience"],
                "supported_block_types": ["section", "table", "citation"],
                "color_schemes": {
                    "resume_ink": {
                        "primary": "#111827",
                        "accent": "#2563eb",
                        "text": "#111827",
                    },
                    "resume_indigo": {
                        "primary": "#3730a3",
                        "accent": "#0f766e",
                        "text": "#111827",
                    },
                },
                "sample_data": {
                    "name": "Alex Agent",
                    "headline": "Agent Infrastructure Engineer",
                    "contact": {"email": "alex@example.com", "location": "Remote"},
                    "summary": "Builds local-first document agents with auditable PDF workflows.",
                    "skills": ["PDF tooling", "MCP", "TypeScript", "Python"],
                    "experience": [
                        {
                            "role": "Lead Engineer",
                            "company": "OkPDF",
                            "period": "2024-2026",
                            "bullets": ["Built template-driven PDF creation with validation evidence."],
                        }
                    ],
                },
            },
            {
                "template_id": "client_invoice",
                "name": "Client Invoice",
                "description": "A clean local invoice template with line items, totals, and payment notes.",
                "base_template": "invoice",
                "target_profile": "invoice_pdf",
                "default_style_pack": "invoice_clean",
                "fields": {
                    "required": ["items"],
                    "optional": ["invoice_number", "client", "bill_to", "due_date", "payment_notes", "total"],
                },
                "layout_slots": ["header", "billing", "line_items", "totals", "notes"],
                "supported_block_types": ["section", "table", "citation"],
                "color_schemes": {
                    "invoice_gold": {
                        "primary": "#92400e",
                        "accent": "#2563eb",
                        "text": "#111827",
                    }
                },
                "sample_data": {
                    "title": "Invoice INV-1001",
                    "invoice_number": "INV-1001",
                    "client": "AgentPDF Labs",
                    "due_date": "2026-06-30",
                    "items": [
                        {"description": "Template implementation", "quantity": 2, "unit_price": 500},
                        {"description": "Validation workflow", "quantity": 1, "unit_price": 350},
                    ],
                    "payment_notes": "Pay by bank transfer.",
                },
            },
            {
                "template_id": "project_proposal",
                "name": "Project Proposal",
                "description": "A scoped proposal with problem, approach, deliverables, and timeline.",
                "base_template": "proposal",
                "target_profile": "proposal_pdf",
                "default_style_pack": "business_report_modern",
                "fields": {
                    "required": ["problem", "approach"],
                    "optional": ["client", "deliverables", "timeline", "title"],
                },
                "layout_slots": ["header", "client", "problem", "approach", "deliverables", "timeline"],
                "supported_block_types": ["section", "table", "image", "citation"],
                "color_schemes": {
                    "proposal_violet": {
                        "primary": "#6d28d9",
                        "accent": "#0f766e",
                        "text": "#111827",
                    }
                },
                "sample_data": {
                    "title": "Local PDF Agent Proposal",
                    "client": "Agent teams",
                    "problem": "Teams need reliable PDF creation tools that run before cloud services exist.",
                    "approach": "Use local templates, style packs, structured JSON, and validation evidence.",
                    "deliverables": ["Template catalog", "Preview PDF", "CLI/MCP/REST access"],
                    "timeline": "Two local-first implementation passes.",
                },
            },
            {
                "template_id": "lesson_worksheet",
                "name": "Lesson Worksheet",
                "description": "A classroom or training worksheet with prompts and validation checklist.",
                "base_template": "worksheet",
                "target_profile": "training_handout",
                "default_style_pack": "paper_ink",
                "fields": {
                    "required": ["title", "learning_goal"],
                    "optional": ["questions", "checklist"],
                },
                "layout_slots": ["title", "learning_goal", "practice", "checklist"],
                "supported_block_types": [
                    "section",
                    "table",
                    "audio_reference",
                    "video_reference",
                    "media_reference",
                    "citation",
                ],
                "color_schemes": {
                    "classroom_green": {
                        "primary": "#166534",
                        "accent": "#2563eb",
                        "text": "#111827",
                    }
                },
                "sample_data": {
                    "title": "PDF Validation Worksheet",
                    "learning_goal": "Practice validating generated PDFs before sharing them with an agent.",
                    "questions": [
                        "Which command proves the PDF can render?",
                        "Which artifact records source evidence?",
                    ],
                    "checklist": ["Create the PDF", "Run render-check", "Review extracted text"],
                },
            },
            {
                "template_id": "media_review_deck",
                "name": "Media Review Deck",
                "description": "A slide-like review PDF for transcripts, keyframes, and source decisions.",
                "base_template": "one_pager",
                "target_profile": "slide_deck",
                "default_style_pack": "business_report_modern",
                "fields": {
                    "required": ["title", "sections"],
                    "optional": ["audience", "checklist"],
                },
                "layout_slots": ["title", "context", "media_evidence", "decisions"],
                "supported_block_types": ["section", "image", "slide", "citation"],
                "color_schemes": {
                    "studio_coral": {
                        "primary": "#7c2d12",
                        "accent": "#0f766e",
                        "text": "#111827",
                    }
                },
                "sample_data": {
                    "title": "Media Review Deck",
                    "audience": "agent operators",
                    "sections": [
                        {
                            "heading": "Context",
                            "body": "Summarize transcript, chapter, and keyframe evidence.",
                        },
                        {
                            "heading": "Decisions",
                            "body": "Capture next actions and validation requirements.",
                        },
                    ],
                },
            },
        ],
    }
}


def create_pdf_from_prompt(
    prompt: str,
    output_path: str | Path,
    template: str | None = None,
    style_pack: str | None = None,
    data: dict[str, Any] | None = None,
    title: str | None = None,
    colors: dict[str, str] | None = None,
) -> ToolResult:
    tool = "pdf.ai.create.from_prompt"
    if not prompt.strip():
        raise AgentPDFException("invalid_input", "prompt is required for PDF creation.")

    selected_template = _select_template(prompt, template)
    template_spec = CREATE_TEMPLATES[selected_template]
    resolved_style_pack = style_pack or str(template_spec["style_pack"])
    normalized_colors = _normalize_colors(colors)
    style_input: str | dict[str, Any] = (
        _style_pack_with_colors(resolved_style_pack, normalized_colors)
        if normalized_colors
        else resolved_style_pack
    )
    content = dict(data or {})
    resolved_title = title or _title_from_data_or_prompt(content, prompt, template_spec["name"])
    markdown, template_renderer = render_template_markdown(
        prompt=prompt,
        template_id=selected_template,
        data=content,
        title=resolved_title,
    )

    rendered = create_markdown_pdf(
        markdown,
        output_path=output_path,
        title=resolved_title,
        style_pack=style_input,
    )
    rendered_path = rendered.artifacts[0].path if rendered.artifacts else Path(output_path).resolve()
    validation = validate_pdf(rendered_path)
    artifact = build_artifact(rendered_path, source_tool=tool)

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if validation.status == "passed" else "failed",
        tool=tool,
        artifacts=[artifact],
        validation=validation,
        warnings=validation.warnings,
        usage={
            "prompt": prompt,
            "title": resolved_title,
            "template_id": selected_template,
            "template_name": template_spec["name"],
            "template_description": template_spec["description"],
            "style_pack": resolved_style_pack,
            "colors": normalized_colors or rendered.usage.get("colors", {}),
            "rendered_style_pack": rendered.usage.get("style_pack"),
            "template_renderer": template_renderer,
            "data_keys": sorted(content),
            "generated_markdown": markdown,
            "agent_plan": {
                "steps": [
                    "select_template",
                    "normalize_content",
                    "apply_theme",
                    "render_markdown",
                    "create_pdf",
                    "validate_pdf",
                ],
                "selection_reason": _selection_reason(prompt, selected_template, template),
                "cloud_required": False,
            },
        },
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.validation.blank_page_check",
            "pdf.ai.rag.chat",
        ],
    )


def list_create_templates() -> ToolResult:
    templates = {
        template_id: {
            "template_id": template_id,
            "name": spec["name"],
            "description": spec["description"],
            "default_sections": list(spec["default_sections"]),
            "default_style_pack": spec["style_pack"],
            "keywords": sorted(spec["keywords"]),
            "template_kind": CREATE_TEMPLATE_CONTRACTS[template_id]["template_kind"],
            "fields": deepcopy(CREATE_TEMPLATE_CONTRACTS[template_id]["fields"]),
            "layout_slots": list(CREATE_TEMPLATE_CONTRACTS[template_id]["layout_slots"]),
            "sample_data": deepcopy(CREATE_TEMPLATE_CONTRACTS[template_id]["sample_data"]),
            "preview_tool": "pdf.ai.create.template_preview",
        }
        for template_id, spec in sorted(CREATE_TEMPLATES.items())
    }
    style_packs = {
        style_id: {
            "style_id": style_id,
            "name": spec.get("name"),
            "description": spec.get("description"),
            "page": spec.get("page", {}),
            "colors": spec.get("colors", {}),
            "components": spec.get("components", []),
        }
        for style_id, spec in sorted(BUILTIN_STYLE_PACKS.items())
    }
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool="pdf.ai.create.templates",
        usage={
            "template_count": len(templates),
            "style_pack_count": len(style_packs),
            "templates": templates,
            "style_packs": style_packs,
            "color_keys": ["primary", "accent", "text"],
            "cloud_required": False,
        },
        next_recommended_tools=["pdf.ai.create.template_preview", "pdf.ai.create.from_prompt"],
    )


def create_template_preview(
    template: str,
    output_path: str | Path,
    style_pack: str | None = None,
    data: dict[str, Any] | None = None,
    colors: dict[str, str] | None = None,
) -> ToolResult:
    tool = "pdf.ai.create.template_preview"
    selected_template = _select_template("", template)
    template_spec = CREATE_TEMPLATES[selected_template]
    contract = CREATE_TEMPLATE_CONTRACTS[selected_template]
    preview_data = deepcopy(data) if data is not None else deepcopy(contract["sample_data"])
    data_source = "custom_data" if data is not None else "template_sample_data"
    preview_prompt = f"Preview the {template_spec['name']} template with local sample data."

    created = create_pdf_from_prompt(
        preview_prompt,
        output_path=output_path,
        template=selected_template,
        style_pack=style_pack,
        data=preview_data,
        colors=colors,
    )
    artifact_path = created.artifacts[0].path if created.artifacts else Path(output_path).resolve()
    artifact = build_artifact(artifact_path, source_tool=tool)

    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status=created.status,
        tool=tool,
        artifacts=[artifact],
        validation=created.validation,
        warnings=list(created.warnings),
        usage={
            "template_id": selected_template,
            "template_name": template_spec["name"],
            "template_kind": contract["template_kind"],
            "fields": deepcopy(contract["fields"]),
            "layout_slots": list(contract["layout_slots"]),
            "data_source": data_source,
            "data_keys": sorted(preview_data),
            "preview_prompt": preview_prompt,
            "style_pack": style_pack or template_spec["style_pack"],
            "colors": created.usage.get("colors", {}),
            "create_result": created.model_dump(mode="json"),
        },
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.validation.blank_page_check",
            "pdf.ai.create.from_prompt",
        ],
        error=created.error,
    )


def list_template_packs(output_path: str | Path | None = None) -> ToolResult:
    tool = "pdf.ai.create.template_packs"
    packs = {
        pack_id: _template_pack_catalog_entry(pack)
        for pack_id, pack in sorted(BUILTIN_TEMPLATE_PACKS.items())
    }
    usage = {
        "template_pack_catalog": {
            "pack_count": len(packs),
            "packs": packs,
        },
        "cloud_required": False,
    }
    artifacts = []
    if output_path is not None:
        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(usage, indent=2) + "\n", encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        usage=usage,
        next_recommended_tools=[
            "pdf.ai.create.validate_template_pack",
            "pdf.ai.create.from_template_pack",
        ],
    )


def validate_template_pack(
    template_pack: dict[str, Any] | str | Path,
    output_path: str | Path | None = None,
) -> ToolResult:
    tool = "pdf.ai.create.validate_template_pack"
    pack = _load_template_pack(template_pack)
    report = _template_pack_validation_report(pack)
    artifacts = []
    if output_path is not None:
        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded" if report["is_valid"] else "failed",
        tool=tool,
        artifacts=artifacts,
        usage={"template_pack_validation": report},
        warnings=list(report["warnings"]),
        next_recommended_tools=["pdf.ai.create.from_template_pack"]
        if report["is_valid"]
        else ["pdf.ai.create.template_packs"],
    )


def plan_template_pack_creation(
    template_pack: dict[str, Any] | str | Path,
    target_profile: dict[str, Any] | str | None = None,
    context_packet: dict[str, Any] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    planned_output_path: str | Path | None = None,
    output_path: str | Path | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
) -> ToolResult:
    tool = "pdf.ai.create.plan_template_pack"
    pack = _load_template_pack(template_pack)
    validation_report = _template_pack_validation_report(pack)
    if not validation_report["is_valid"]:
        raise AgentPDFException(
            "invalid_template_pack",
            "Template pack failed validation.",
            details={"template_pack_validation": validation_report},
        )
    target_profile_id = _target_profile_id(target_profile)
    packet = _load_context_packet_for_template(context_packet=context_packet, context_packet_path=context_packet_path)
    context_blocks = _context_packet_agent_blocks(packet, target_profile=target_profile) if packet is not None else []
    context_block_type_counts = _block_type_counts(context_blocks)
    candidates = _rank_template_pack_candidates(
        pack=pack,
        target_profile_id=target_profile_id,
        context_block_type_counts=context_block_type_counts,
        preferred_template_id=preferred_template_id,
    )
    if not candidates:
        raise AgentPDFException("invalid_template_pack", "Template pack contains no template candidates.")
    selected = candidates[0]
    selected_template = _find_template_in_pack(pack, selected["template_id"])
    selected_color_scheme = _select_template_color_scheme(selected_template, preferred_color_scheme)
    selected_style_pack = str(
        selected_template.get("default_style_pack")
        or CREATE_TEMPLATES[str(selected_template.get("base_template"))]["style_pack"]
    )
    planned_pdf = str(planned_output_path) if planned_output_path is not None else (
        f".agentpdf-out/{selected['template_id']}.pdf"
    )
    create_payload = {
        **_template_pack_payload_ref(template_pack, pack),
        "template_id": selected["template_id"],
        "color_scheme": selected_color_scheme,
        "output_path": planned_pdf,
    }
    if context_packet_path is not None:
        create_payload["context_packet_path"] = str(context_packet_path)
    elif context_packet is not None:
        create_payload["context_packet"] = context_packet
    if selected_color_scheme is None:
        create_payload.pop("color_scheme")
    base_template = str(selected_template.get("base_template") or "")
    preview_payload = {
        "template": base_template,
        "output_path": str(Path(planned_pdf).with_suffix(".preview.pdf")),
        "style_pack": selected_style_pack,
    }
    warnings = [
        f"Selected template has unsupported context block types: {', '.join(selected['unsupported_context_block_types'])}"
    ] if selected["unsupported_context_block_types"] else []
    plan = {
        "template_pack_plan_version": "0.1",
        "template_pack_plan_id": f"tplplan_{uuid4().hex[:16]}",
        "pack_id": str(pack.get("pack_id") or "custom_template_pack"),
        "pack_name": str(pack.get("name") or ""),
        "target_profile": target_profile_id,
        "target_profile_known": target_profile_id in DEFAULT_TARGET_PROFILES if target_profile_id else False,
        "context_packet_id": str(packet.get("context_packet_id")) if packet is not None else None,
        "context_packet_item_count": len(packet.get("items", [])) if packet is not None else 0,
        "context_block_count": len(context_blocks),
        "context_block_type_counts": context_block_type_counts,
        "selected_template_id": selected["template_id"],
        "selected_color_scheme": selected_color_scheme,
        "selected_style_pack": selected_style_pack,
        "selection_reason": selected["selection_reason"],
        "selected_template": {
            "template_id": str(selected_template.get("template_id") or ""),
            "name": str(selected_template.get("name") or ""),
            "base_template": base_template,
            "target_profile": selected_template.get("target_profile"),
            "supported_block_types": _template_pack_supported_block_types(
                selected_template.get("supported_block_types")
            ),
            "layout_slots": _template_pack_string_list(selected_template.get("layout_slots")),
        },
        "candidates": candidates,
        "create_payload": create_payload,
        "preview_payload": preview_payload,
        "validation_required": [
            "pdf.validation.render_check",
            "pdf.validation.blank_page_check",
            "pdf.evidence.coverage_report",
        ],
    }
    artifacts = []
    if output_path is not None:
        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        artifacts.append(build_artifact(destination, source_tool=tool))
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status="succeeded",
        tool=tool,
        artifacts=artifacts,
        warnings=warnings,
        usage={"template_pack_plan": plan, "template_pack_validation": validation_report},
        next_recommended_tools=[
            "pdf.ai.create.from_template_pack",
            "pdf.ai.create.template_preview",
            "pdf.evidence.coverage_report",
        ],
    )


def create_pdf_with_agent(
    template_pack: dict[str, Any] | str | Path,
    target_profile: dict[str, Any] | str | None,
    context_packet: dict[str, Any] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    output_path: str | Path = ".agentpdf-out/create-agent.pdf",
    plan_output_path: str | Path | None = None,
    coverage_output_path: str | Path | None = None,
    context_classification_output_path: str | Path | None = None,
    context_report_output_path: str | Path | None = None,
    context_report_json_output_path: str | Path | None = None,
    bundle_output_path: str | Path | None = None,
    preferred_template_id: str | None = None,
    preferred_color_scheme: str | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
) -> ToolResult:
    tool = "pdf.ai.create.agent"
    resolved_output_path = Path(output_path).expanduser().resolve()
    resolved_plan_path = (
        Path(plan_output_path).expanduser().resolve()
        if plan_output_path is not None
        else resolved_output_path.with_suffix(".plan.json")
    )
    resolved_coverage_path = (
        Path(coverage_output_path).expanduser().resolve()
        if coverage_output_path is not None
        else resolved_output_path.with_suffix(".coverage.json")
    )
    context_packet_source = _context_packet_source_for_report(context_packet, context_packet_path)
    resolved_context_classification_path = (
        (
            Path(context_classification_output_path).expanduser().resolve()
            if context_classification_output_path is not None
            else resolved_output_path.with_suffix(".context-classification.json")
        )
        if context_packet_source is not None
        else None
    )
    resolved_context_report_path = (
        Path(context_report_output_path).expanduser().resolve()
        if context_report_output_path is not None
        else resolved_output_path.with_suffix(".context-report.pdf")
    )
    resolved_context_report_json_path = (
        Path(context_report_json_output_path).expanduser().resolve()
        if context_report_json_output_path is not None
        else resolved_output_path.with_suffix(".context-report.json")
    )
    resolved_bundle_path = (
        Path(bundle_output_path).expanduser().resolve() if bundle_output_path is not None else None
    )
    plan_result = plan_template_pack_creation(
        template_pack=template_pack,
        target_profile=target_profile,
        context_packet=context_packet,
        context_packet_path=context_packet_path,
        planned_output_path=resolved_output_path,
        output_path=resolved_plan_path,
        preferred_template_id=preferred_template_id,
        preferred_color_scheme=preferred_color_scheme,
    )
    plan = plan_result.usage["template_pack_plan"]
    context_classification_result = (
        classify_context(
            context_packet_source,
            target_profile=target_profile or plan.get("target_profile"),
            output_path=resolved_context_classification_path,
        )
        if context_packet_source is not None
        else None
    )
    context_report_result = (
        create_context_packet_report(
            context_packet_source,
            output_path=resolved_context_report_path,
            report_output_path=resolved_context_report_json_path,
            title=f"{title or plan.get('selected_template_id') or 'Create Agent'} Context Packet Report",
        )
        if context_packet_source is not None
        else None
    )
    create_result = create_pdf_from_template_pack(
        template_pack=template_pack,
        template_id=str(plan["selected_template_id"]),
        output_path=resolved_output_path,
        color_scheme=plan.get("selected_color_scheme"),
        context_packet=context_packet,
        context_packet_path=context_packet_path,
        title=title,
        prompt=prompt,
        style_pack=style_pack,
    )
    composition_path = Path(str(create_result.usage["composition_path"])).resolve()
    layer_path = Path(str(create_result.usage["template_layer_manifest_path"])).resolve()
    render_report, render_usage = render_check_pdf(resolved_output_path, pages="all")
    blank_report, blank_usage = blank_page_check_pdf(resolved_output_path, pages="all")
    coverage_result = create_coverage_report(composition_path, output_path=resolved_coverage_path)
    bundle_result = None
    bundle_verification_result = None
    if resolved_bundle_path is not None:
        bundle_inputs = _create_agent_bundle_inputs(
            output_path=resolved_output_path,
            plan_path=resolved_plan_path,
            composition_path=composition_path,
            layer_path=layer_path,
            coverage_path=resolved_coverage_path,
            context_classification_result=context_classification_result,
            context_report_result=context_report_result,
        )
        bundle_result = export_artifact_bundle(
            artifact_paths=bundle_inputs,
            output_path=resolved_bundle_path,
            title=f"{title or plan.get('selected_template_id') or 'Create Agent'} Audit Bundle",
            metadata={
                "workflow": "pdf.ai.create.agent",
                "context_packet_id": plan.get("context_packet_id"),
                "selected_template_id": plan.get("selected_template_id"),
                "selected_color_scheme": plan.get("selected_color_scheme"),
            },
        )
        bundle_verification_result = verify_artifact_bundle(resolved_bundle_path)
    validation = _create_agent_validation_report(
        create_result=create_result,
        render_report=render_report,
        blank_report=blank_report,
        coverage_result=coverage_result,
        context_classification_result=context_classification_result,
        context_report_result=context_report_result,
        bundle_verification_result=bundle_verification_result,
    )
    run_status = "succeeded" if validation.status in {"passed", "warning"} else "failed"
    create_agent_run = {
        "create_agent_run_version": "0.1",
        "create_agent_run_id": f"createagent_{uuid4().hex[:16]}",
        "status": run_status,
        "target_profile": plan.get("target_profile"),
        "context_packet_id": plan.get("context_packet_id"),
        "selected_template_id": plan["selected_template_id"],
        "selected_color_scheme": plan.get("selected_color_scheme"),
        "selected_style_pack": plan.get("selected_style_pack"),
        "step_order": [
            "pdf.ai.create.plan_template_pack",
            *(
                ["pdf.context.classify"]
                if context_classification_result is not None
                else []
            ),
            *(
                ["pdf.evidence.context_packet_report"]
                if context_report_result is not None
                else []
            ),
            "pdf.ai.create.from_template_pack",
            "pdf.validation.render_check",
            "pdf.validation.blank_page_check",
            "pdf.evidence.coverage_report",
            *(["pdf.artifacts.export_bundle", "pdf.artifacts.verify_bundle"] if bundle_result is not None else []),
        ],
        "output_pdf_path": str(resolved_output_path),
        "composition_path": str(composition_path),
        "template_layer_manifest_path": str(layer_path),
        "plan_path": str(resolved_plan_path),
        "coverage_path": str(resolved_coverage_path),
        **(
            {"context_classification_path": str(resolved_context_classification_path)}
            if context_classification_result is not None and resolved_context_classification_path is not None
            else {}
        ),
        **(
            {
                "context_report_path": str(resolved_context_report_path),
                "context_report_json_path": str(resolved_context_report_json_path),
            }
            if context_report_result is not None
            else {}
        ),
        **({"bundle_path": str(resolved_bundle_path)} if resolved_bundle_path is not None else {}),
        "plan": plan,
        "create_result": create_result.model_dump(mode="json"),
        "render_check": {
            "validation": render_report.model_dump(mode="json"),
            "usage": render_usage,
        },
        "blank_page_check": {
            "validation": blank_report.model_dump(mode="json"),
            "usage": blank_usage,
        },
        "coverage_report": coverage_result.model_dump(mode="json"),
        **(
            {"context_classification": context_classification_result.model_dump(mode="json")}
            if context_classification_result is not None
            else {}
        ),
        **(
            {"context_packet_report": context_report_result.model_dump(mode="json")}
            if context_report_result is not None
            else {}
        ),
        **({"bundle_export": bundle_result.model_dump(mode="json")} if bundle_result is not None else {}),
        **(
            {"bundle_verification": bundle_verification_result.model_dump(mode="json")}
            if bundle_verification_result is not None
            else {}
        ),
        "slot_routing_plan": create_result.usage["slot_routing_plan"],
        "template_layer_manifest": create_result.usage["template_layer_manifest"],
        "evidence_coverage": create_result.usage["evidence_coverage"],
        "validation_summary": {
            "create_pdf": create_result.validation.status if create_result.validation else "skipped",
            "render_check": render_report.status,
            "blank_page_check": blank_report.status,
            "coverage_ratio": coverage_result.usage["coverage"].get("coverage_ratio"),
            **(
                {"context_classification": context_classification_result.status}
                if context_classification_result is not None
                else {}
            ),
            **(
                {"context_packet_report": context_report_result.validation.status}
                if context_report_result is not None and context_report_result.validation is not None
                else {}
            ),
            **(
                {"bundle_verification": bundle_verification_result.validation.status}
                if bundle_verification_result is not None and bundle_verification_result.validation is not None
                else {}
            ),
        },
    }
    warnings = [
        *list(plan_result.warnings),
        *list(create_result.warnings),
        *list(render_report.warnings),
        *list(blank_report.warnings),
        *list(coverage_result.warnings),
        *(
            list(context_classification_result.warnings)
            if context_classification_result is not None
            else []
        ),
        *(
            list(context_report_result.warnings)
            if context_report_result is not None
            else []
        ),
        *(list(bundle_result.warnings) if bundle_result is not None else []),
        *(list(bundle_verification_result.warnings) if bundle_verification_result is not None else []),
    ]
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status=run_status,
        tool=tool,
        artifacts=[
            *list(plan_result.artifacts),
            *(
                list(context_classification_result.artifacts)
                if context_classification_result is not None
                else []
            ),
            *(
                list(context_report_result.artifacts)
                if context_report_result is not None
                else []
            ),
            *list(create_result.artifacts),
            *list(coverage_result.artifacts),
            *(list(bundle_result.artifacts) if bundle_result is not None else []),
        ],
        validation=validation,
        warnings=warnings,
        usage={
            "create_agent_run": create_agent_run,
            "template_pack_plan": plan,
            "composition_path": str(composition_path),
            "template_layer_manifest_path": str(layer_path),
            "coverage_path": str(resolved_coverage_path),
            **(
                {"context_classification_path": str(resolved_context_classification_path)}
                if context_classification_result is not None and resolved_context_classification_path is not None
                else {}
            ),
            **(
                {
                    "context_report_path": str(resolved_context_report_path),
                    "context_report_json_path": str(resolved_context_report_json_path),
                }
                if context_report_result is not None
                else {}
            ),
            **({"bundle_path": str(resolved_bundle_path)} if resolved_bundle_path is not None else {}),
        },
        next_recommended_tools=[
            "pdf.patch.plan",
            "pdf.artifacts.export_bundle",
            "pdf.inspect.document",
        ],
    )


def create_pdf_from_template_pack(
    template_pack: dict[str, Any] | str | Path,
    template_id: str,
    output_path: str | Path,
    color_scheme: str | None = None,
    data: dict[str, Any] | None = None,
    context_packet: dict[str, Any] | str | Path | None = None,
    context_packet_path: str | Path | None = None,
    title: str | None = None,
    prompt: str | None = None,
    style_pack: str | None = None,
) -> ToolResult:
    tool = "pdf.ai.create.from_template_pack"
    pack = _load_template_pack(template_pack)
    validation_report = _template_pack_validation_report(pack)
    if not validation_report["is_valid"]:
        raise AgentPDFException(
            "invalid_template_pack",
            "Template pack failed validation.",
            details={"template_pack_validation": validation_report},
        )
    template = _find_template_in_pack(pack, template_id)
    base_template = str(template.get("base_template") or "").strip()
    if base_template not in CREATE_TEMPLATES:
        raise AgentPDFException(
            "invalid_template",
            f"Template pack entry {template_id} references unknown base template: {base_template}.",
        )
    target_profile_id = str(template.get("target_profile") or base_template)
    packet = _load_context_packet_for_template(context_packet=context_packet, context_packet_path=context_packet_path)
    context_blocks = (
        _context_packet_agent_blocks(packet, target_profile=target_profile_id)
        if packet is not None
        else []
    )
    merged_data = deepcopy(template.get("sample_data") if isinstance(template.get("sample_data"), dict) else {})
    if data:
        merged_data.update(data)
    if context_blocks:
        explicit_blocks = merged_data.get("blocks") if isinstance(merged_data.get("blocks"), list) else []
        merged_data["blocks"] = [*explicit_blocks, *context_blocks]
    resolved_title = title or _stringify(merged_data.get("title")) or str(template.get("name") or template_id)
    merged_data["title"] = resolved_title
    resolved_style_pack = style_pack or str(template.get("default_style_pack") or CREATE_TEMPLATES[base_template]["style_pack"])
    resolved_color_scheme, colors = _template_pack_colors(template, color_scheme)
    create_prompt = prompt or (
        f"Create {template.get('name', template_id)} from template pack "
        f"{pack.get('pack_id', 'custom_template_pack')}."
    )
    created = create_pdf_from_prompt(
        create_prompt,
        output_path=output_path,
        template=base_template,
        style_pack=resolved_style_pack,
        data=merged_data,
        title=resolved_title,
        colors=colors,
    )
    artifact_path = created.artifacts[0].path if created.artifacts else Path(output_path).resolve()
    artifact = build_artifact(artifact_path, source_tool=tool)
    composition_path = Path(output_path).with_suffix(".composition.json").resolve()
    composition_payload = _template_pack_composition_payload(
        pack=pack,
        template=template,
        template_id=template_id,
        base_template=base_template,
        merged_data=merged_data,
        created=created,
        output_path=artifact_path,
        used_custom_data=bool(data),
        color_scheme=resolved_color_scheme,
        context_packet=packet,
    )
    composition_path.write_text(json.dumps(composition_payload, indent=2), encoding="utf-8")
    composition_artifact = build_artifact(composition_path, source_tool=tool)
    layer_path = Path(output_path).with_suffix(".layers.json").resolve()
    layer_path.write_text(
        json.dumps(composition_payload["template_layer_manifest"], indent=2),
        encoding="utf-8",
    )
    layer_artifact = build_artifact(layer_path, source_tool=tool)
    usage = dict(created.usage)
    routing_warnings = [
        _stringify(warning)
        for warning in composition_payload.get("warnings", [])
        if _stringify(warning)
    ]
    usage.update(
        {
            "pack_id": str(pack.get("pack_id")),
            "pack_name": str(pack.get("name")),
            "template_id": template_id,
            "template_name": str(template.get("name")),
            "base_template": base_template,
            "target_profile": template.get("target_profile"),
            "color_scheme": resolved_color_scheme,
            "template_pack_validation": validation_report,
            "composition_path": composition_path.as_posix(),
            "composition_ir": composition_payload["composition_ir"],
            "source_map": composition_payload["source_map"],
            "evidence_coverage": composition_payload["evidence_coverage"],
            "slot_routing_plan": composition_payload["slot_routing_plan"],
            "template_layer_manifest_path": layer_path.as_posix(),
            "template_layer_manifest": composition_payload["template_layer_manifest"],
            "context_packet_id": composition_payload["context_packet_id"],
            "context_packet_item_count": len(packet.get("items", [])) if packet is not None else 0,
            "context_block_count": len(context_blocks),
            "context_packet_source_refs": [
                str(item.get("source_ref"))
                for item in packet.get("items", [])
            ]
            if packet is not None
            else [],
            "create_result": created.model_dump(mode="json"),
        }
    )
    return ToolResult(
        job_id=f"job_{uuid4().hex[:16]}",
        status=created.status,
        tool=tool,
        artifacts=[artifact, composition_artifact, layer_artifact],
        validation=created.validation,
        warnings=[*list(created.warnings), *routing_warnings],
        usage=usage,
        next_recommended_tools=[
            "pdf.validation.render_check",
            "pdf.evidence.coverage_report",
            "pdf.validation.blank_page_check",
            "pdf.target.profiles",
        ],
        error=created.error,
    )


def _template_pack_catalog_entry(pack: dict[str, Any]) -> dict[str, Any]:
    templates = [
        template
        for template in pack.get("templates", [])
        if isinstance(template, dict)
    ]
    return {
        "pack_id": str(pack.get("pack_id", "")),
        "name": str(pack.get("name", "")),
        "version": str(pack.get("version", "")),
        "description": str(pack.get("description", "")),
        "license": str(pack.get("license", "")),
        "cloud_required": bool(pack.get("cloud_required", False)),
        "template_count": len(templates),
        "template_ids": [str(template.get("template_id")) for template in templates],
        "color_scheme_ids": _template_pack_color_scheme_ids(pack),
        "templates": [
            {
                "template_id": str(template.get("template_id", "")),
                "name": str(template.get("name", "")),
                "description": str(template.get("description", "")),
                "base_template": str(template.get("base_template", "")),
                "target_profile": template.get("target_profile"),
                "default_style_pack": template.get("default_style_pack"),
                "fields": deepcopy(template.get("fields", {})),
                "layout_slots": list(template.get("layout_slots", []))
                if isinstance(template.get("layout_slots"), list)
                else [],
                "supported_block_types": _template_pack_supported_block_types(template.get("supported_block_types")),
                "color_schemes": sorted(
                    template.get("color_schemes", {}).keys()
                    if isinstance(template.get("color_schemes"), dict)
                    else []
                ),
            }
            for template in templates
        ],
        "tools": {
            "validate": "pdf.ai.create.validate_template_pack",
            "create": "pdf.ai.create.from_template_pack",
            "preview": "pdf.ai.create.template_preview",
        },
    }


def _create_agent_validation_report(
    create_result: ToolResult,
    render_report: ValidationReport,
    blank_report: ValidationReport,
    coverage_result: ToolResult,
    context_classification_result: ToolResult | None = None,
    context_report_result: ToolResult | None = None,
    bundle_verification_result: ToolResult | None = None,
) -> ValidationReport:
    checks: list[ValidationCheck] = []
    if create_result.validation is not None:
        checks.extend(create_result.validation.checks)
    checks.extend(render_report.checks)
    checks.extend(blank_report.checks)
    if context_classification_result is not None:
        checks.append(
            ValidationCheck(
                name="context_classification_completed",
                status="passed" if context_classification_result.status == "succeeded" else "failed",
                details={
                    "tool": context_classification_result.tool,
                    "classification_count": context_classification_result.usage.get("classification_count"),
                },
                message=None
                if context_classification_result.status == "succeeded"
                else "Context classification did not succeed.",
            )
        )
    if context_report_result is not None and context_report_result.validation is not None:
        checks.append(
            ValidationCheck(
                name="context_packet_report_validation",
                status=context_report_result.validation.status,
                details={"tool": context_report_result.tool},
                message=None
                if context_report_result.validation.status == "passed"
                else "Context Packet report validation did not pass.",
            )
        )
    coverage_ratio = coverage_result.usage["coverage"].get("coverage_ratio")
    checks.append(
        ValidationCheck(
            name="evidence_coverage_ratio",
            status="passed" if coverage_ratio == 1.0 else "warning",
            details={"coverage_ratio": coverage_ratio},
            message=None if coverage_ratio == 1.0 else "Not every source ref is covered by generated blocks.",
        )
    )
    if bundle_verification_result is not None and bundle_verification_result.validation is not None:
        checks.append(
            ValidationCheck(
                name="audit_bundle_verification",
                status=bundle_verification_result.validation.status,
                details={"tool": bundle_verification_result.tool},
                message=None
                if bundle_verification_result.validation.status == "passed"
                else "Audit bundle verification did not pass.",
            )
        )
    warnings = [
        *(create_result.validation.warnings if create_result.validation is not None else []),
        *render_report.warnings,
        *blank_report.warnings,
        *(
            context_report_result.validation.warnings
            if context_report_result is not None and context_report_result.validation is not None
            else []
        ),
        *(
            bundle_verification_result.validation.warnings
            if bundle_verification_result is not None and bundle_verification_result.validation is not None
            else []
        ),
    ]
    if any(check.status == "failed" for check in checks):
        status = "failed"
    elif warnings or any(check.status == "warning" for check in checks):
        status = "warning"
    else:
        status = "passed"
    return ValidationReport(
        status=status,
        checks=checks,
        page_count=create_result.validation.page_count if create_result.validation is not None else None,
        warnings=warnings,
    )


def _context_packet_source_for_report(
    context_packet: dict[str, Any] | str | Path | None,
    context_packet_path: str | Path | None,
) -> dict[str, Any] | str | Path | None:
    if context_packet is not None:
        return context_packet
    if context_packet_path is not None:
        return context_packet_path
    return None


def _create_agent_bundle_inputs(
    output_path: Path,
    plan_path: Path,
    composition_path: Path,
    layer_path: Path,
    coverage_path: Path,
    context_classification_result: ToolResult | None,
    context_report_result: ToolResult | None,
) -> list[Path]:
    paths = [
        output_path,
        plan_path,
        composition_path,
        layer_path,
        coverage_path,
    ]
    if context_classification_result is not None:
        paths.extend(artifact.path for artifact in context_classification_result.artifacts)
    if context_report_result is not None:
        paths.extend(artifact.path for artifact in context_report_result.artifacts)
    return paths


def _target_profile_id(target_profile: dict[str, Any] | str | None) -> str | None:
    if target_profile is None:
        return None
    if isinstance(target_profile, dict):
        profile_id = target_profile.get("profile_id") or target_profile.get("id")
        return str(profile_id).strip() if profile_id else "custom"
    normalized = str(target_profile).strip()
    return normalized or None


def _block_type_counts(blocks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in blocks:
        block_type = str(block.get("type") or "").strip()
        if not block_type:
            continue
        counts[block_type] = counts.get(block_type, 0) + 1
    return counts


def _rank_template_pack_candidates(
    pack: dict[str, Any],
    target_profile_id: str | None,
    context_block_type_counts: dict[str, int],
    preferred_template_id: str | None,
) -> list[dict[str, Any]]:
    context_block_types = set(context_block_type_counts)
    candidates: list[dict[str, Any]] = []
    for template in pack.get("templates", []):
        if not isinstance(template, dict):
            continue
        template_id = str(template.get("template_id") or "").strip()
        if not template_id:
            continue
        supported_block_types = _template_pack_supported_block_types(template.get("supported_block_types"))
        supported_set = set(supported_block_types)
        matched_block_types = sorted(context_block_types & supported_set)
        unsupported_block_types = sorted(context_block_types - supported_set)
        template_target_profile = str(template.get("target_profile") or "").strip()
        target_profile_match = bool(target_profile_id and template_target_profile == target_profile_id)
        score = 0
        signals: list[str] = []
        if target_profile_match:
            score += 60
            signals.append("target_profile_match")
        elif target_profile_id:
            signals.append("target_profile_mismatch")
        if preferred_template_id and template_id == preferred_template_id:
            score += 25
            signals.append("preferred_template")
        if matched_block_types:
            score += len(matched_block_types) * 8
            signals.append("context_block_types_supported")
        if unsupported_block_types:
            score -= len(unsupported_block_types) * 6
            signals.append("unsupported_context_block_types")
        color_schemes = template.get("color_schemes")
        if isinstance(color_schemes, dict) and color_schemes:
            score += 5
            signals.append("color_schemes_available")
        default_style_pack = str(template.get("default_style_pack") or "").strip()
        if default_style_pack in BUILTIN_STYLE_PACKS:
            score += 3
            signals.append("style_pack_available")
        fields = template.get("fields")
        if isinstance(fields, dict) and (
            _template_pack_string_list(fields.get("required"))
            or _template_pack_string_list(fields.get("optional"))
        ):
            score += 3
            signals.append("field_contract_available")
        reason = _template_pack_candidate_reason(
            target_profile_match=target_profile_match,
            matched_block_types=matched_block_types,
            unsupported_block_types=unsupported_block_types,
            signals=signals,
        )
        candidates.append(
            {
                "template_id": template_id,
                "name": str(template.get("name") or ""),
                "base_template": str(template.get("base_template") or ""),
                "target_profile": template.get("target_profile"),
                "target_profile_match": target_profile_match,
                "score": score,
                "matched_block_types": matched_block_types,
                "unsupported_context_block_types": unsupported_block_types,
                "supported_block_types": supported_block_types,
                "color_scheme_ids": sorted(color_schemes) if isinstance(color_schemes, dict) else [],
                "signals": signals,
                "selection_reason": reason,
            }
        )
    return sorted(candidates, key=lambda candidate: (-int(candidate["score"]), str(candidate["template_id"])))


def _template_pack_candidate_reason(
    target_profile_match: bool,
    matched_block_types: list[str],
    unsupported_block_types: list[str],
    signals: list[str],
) -> str:
    parts: list[str] = []
    if target_profile_match:
        parts.append("Target PDF Profile matches the template.")
    if matched_block_types:
        parts.append("Supports context block types: " + ", ".join(matched_block_types) + ".")
    if unsupported_block_types:
        parts.append("Unsupported context block types: " + ", ".join(unsupported_block_types) + ".")
    if "color_schemes_available" in signals:
        parts.append("Provides local color schemes.")
    if not parts:
        parts.append("General local template candidate.")
    return " ".join(parts)


def _select_template_color_scheme(template: dict[str, Any], preferred_color_scheme: str | None) -> str | None:
    color_schemes = template.get("color_schemes")
    if not isinstance(color_schemes, dict) or not color_schemes:
        return None
    if preferred_color_scheme:
        if preferred_color_scheme not in color_schemes:
            available = ", ".join(sorted(color_schemes))
            raise AgentPDFException(
                "invalid_color_key",
                f"Unknown template pack color scheme: {preferred_color_scheme}. Available schemes: {available}.",
            )
        return preferred_color_scheme
    return next(iter(sorted(color_schemes)))


def _template_pack_payload_ref(
    template_pack: dict[str, Any] | str | Path,
    loaded_pack: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(template_pack, dict):
        return {"template_pack": deepcopy(loaded_pack)}
    raw = str(template_pack)
    if raw in BUILTIN_TEMPLATE_PACKS:
        return {"template_pack": raw}
    if Path(raw).exists() or raw.lower().endswith(".json"):
        return {"template_pack_path": raw}
    return {"template_pack": raw}


def _template_pack_composition_payload(
    pack: dict[str, Any],
    template: dict[str, Any],
    template_id: str,
    base_template: str,
    merged_data: dict[str, Any],
    created: ToolResult,
    output_path: str | Path,
    used_custom_data: bool,
    color_scheme: str | None,
    context_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack_id = str(pack.get("pack_id") or "custom_template_pack")
    target_profile_id = str(template.get("target_profile") or base_template)
    context_packet_id = (
        str(context_packet.get("context_packet_id"))
        if context_packet is not None and context_packet.get("context_packet_id")
        else f"ctxpkt_tpl_{uuid4().hex[:12]}"
    )
    composition_id = f"cmp_{uuid4().hex[:16]}"
    source_refs = [f"tpl://{pack_id}/{template_id}/sample_data"]
    if used_custom_data:
        source_refs.append(f"tpl://{pack_id}/{template_id}/input_data")
    context_source_refs = [
        str(item.get("source_ref"))
        for item in (context_packet.get("items", []) if context_packet is not None else [])
        if isinstance(item, dict) and item.get("source_ref")
    ]

    blocks = _template_pack_blocks(template=template, merged_data=merged_data, source_refs=source_refs)
    slot_routing_plan = _template_pack_slot_routing_plan(
        template=template,
        template_id=template_id,
        target_profile_id=target_profile_id,
        blocks=blocks,
    )
    source_map = []
    for block in blocks:
        for source_ref in block["source_refs"]:
            source_map.append(
                {
                    "block_id": block["block_id"],
                    "source_ref": source_ref,
                    "source_kind": _source_kind_for_ref(source_ref),
                    "pack_id": pack_id,
                    "template_id": template_id,
                    "target_profile_id": target_profile_id,
                    "target_slot": block.get("target_slot"),
                }
            )

    page_count = created.artifacts[0].page_count if created.artifacts else None
    layer_manifest = _template_pack_layer_manifest(
        pack_id=pack_id,
        template=template,
        template_id=template_id,
        target_profile_id=target_profile_id,
        base_template=base_template,
        color_scheme=color_scheme,
        output_path=output_path,
        composition_id=composition_id,
        context_packet_id=context_packet_id,
        slot_routing_plan=slot_routing_plan,
        blocks=blocks,
        source_map=source_map,
        page_count=page_count,
    )
    covered_refs = sorted({mapping["source_ref"] for mapping in source_map})
    known_source_refs = sorted(
        set(source_refs).union(context_source_refs).union(
            ref
            for block in blocks
            for ref in block.get("source_refs", [])
        )
    )
    uncovered_source_refs = sorted(set(known_source_refs).difference(covered_refs))
    coverage = {
        "coverage_version": "0.1",
        "context_item_count": len(known_source_refs),
        "covered_context_items": len(covered_refs),
        "coverage_ratio": len(covered_refs) / len(known_source_refs) if known_source_refs else 0.0,
        "covered_source_refs": covered_refs,
        "uncovered_source_refs": uncovered_source_refs,
        "block_count": len(blocks),
        "covered_block_count": len([block for block in blocks if block["source_refs"]]),
    }
    return {
        "composition_ir": {
            "composition_version": "0.1",
            "composition_id": composition_id,
            "context_packet_id": context_packet_id,
            "target_profile_id": target_profile_id,
            "blocks": blocks,
            "metadata": {
                "source_tool": "pdf.ai.create.from_template_pack",
                "pack_id": pack_id,
                "template_id": template_id,
                "base_template": base_template,
                "color_scheme": color_scheme,
                "output_path": str(Path(output_path).resolve()).replace("\\", "/"),
                "slot_routing_plan_id": slot_routing_plan["slot_routing_plan_id"],
                "template_layer_manifest_id": layer_manifest["template_layer_manifest_id"],
            },
        },
        "source_map": source_map,
        "evidence_coverage": coverage,
        "slot_routing_plan": slot_routing_plan,
        "template_layer_manifest": layer_manifest,
        "warnings": list(slot_routing_plan["warnings"]),
        "target_profile": {
            "profile_id": target_profile_id,
            "source": "template_pack",
            "template_id": template_id,
            "base_template": base_template,
        },
        "context_packet_id": context_packet_id,
        "template_pack": {
            "pack_id": pack_id,
            "name": str(pack.get("name") or ""),
            "version": str(pack.get("version") or ""),
            "template_id": template_id,
            "template_name": str(template.get("name") or ""),
            "base_template": base_template,
            "color_scheme": color_scheme,
        },
        "created_pdf": created.model_dump(mode="json"),
    }


def _template_pack_layer_manifest(
    pack_id: str,
    template: dict[str, Any],
    template_id: str,
    target_profile_id: str,
    base_template: str,
    color_scheme: str | None,
    output_path: str | Path,
    composition_id: str,
    context_packet_id: str,
    slot_routing_plan: dict[str, Any],
    blocks: list[dict[str, Any]],
    source_map: list[dict[str, Any]],
    page_count: int | None,
) -> dict[str, Any]:
    manifest_id = f"layers_{uuid4().hex[:16]}"
    layer_path = Path(output_path).with_suffix(".layers.json").resolve()
    source_map_by_block: dict[str, list[dict[str, Any]]] = {}
    for entry in source_map:
        source_map_by_block.setdefault(_stringify(entry.get("block_id")), []).append(entry)
    routes = {
        _stringify(route.get("block_id")): route
        for route in slot_routing_plan.get("routes", [])
        if isinstance(route, dict)
    }
    layers = [
        _template_pack_layer_entry(
            block=block,
            index=index,
            page_count=page_count,
            route=routes.get(_stringify(block.get("block_id")), {}),
            source_entries=source_map_by_block.get(_stringify(block.get("block_id")), []),
            style_pack=_stringify(template.get("default_style_pack") or CREATE_TEMPLATES[base_template]["style_pack"]),
            color_scheme=color_scheme,
        )
        for index, block in enumerate(blocks, start=1)
    ]
    layer_types = []
    for layer in layers:
        block_type = _stringify(layer.get("block_type"))
        if block_type and block_type not in layer_types:
            layer_types.append(block_type)
    return {
        "template_layer_manifest_version": "0.1",
        "template_layer_manifest_id": manifest_id,
        "pack_id": pack_id,
        "template_id": template_id,
        "template_name": _stringify(template.get("name")),
        "base_template": base_template,
        "target_profile_id": target_profile_id,
        "context_packet_id": context_packet_id,
        "composition_id": composition_id,
        "slot_routing_plan_id": slot_routing_plan["slot_routing_plan_id"],
        "output_pdf_path": str(Path(output_path).resolve()),
        "template_layer_manifest_path": str(layer_path),
        "page_count": page_count,
        "layer_count": len(layers),
        "editable_layer_count": len([layer for layer in layers if layer["edit_policy"]["editable"]]),
        "layer_types": layer_types,
        "coordinate_policy": {
            "coordinate_system": "normalized_page",
            "bbox_kind": "estimated",
            "notes": "Anchors are deterministic template-slot estimates until the renderer returns exact text/image bboxes.",
        },
        "layers": layers,
        "warnings": [],
        "next_recommended_tools": [
            "pdf.patch.plan",
            "pdf.evidence.coverage_report",
            "pdf.artifacts.export_bundle",
        ],
    }


def _template_pack_layer_entry(
    block: dict[str, Any],
    index: int,
    page_count: int | None,
    route: dict[str, Any],
    source_entries: list[dict[str, Any]],
    style_pack: str,
    color_scheme: str | None,
) -> dict[str, Any]:
    block_id = _stringify(block.get("block_id")) or f"block_{index:03d}"
    block_type = _stringify(block.get("type")) or "section"
    source_refs = _template_pack_string_list(block.get("source_refs"))
    source_kinds = []
    for entry in source_entries:
        source_kind = _stringify(entry.get("source_kind"))
        if source_kind and source_kind not in source_kinds:
            source_kinds.append(source_kind)
    if not source_kinds:
        source_kinds = [_source_kind_for_ref(source_ref) for source_ref in source_refs]
    return {
        "layer_id": f"layer_{block_id}",
        "block_id": block_id,
        "block_type": block_type,
        "title": _stringify(block.get("title")),
        "target_slot": _stringify(block.get("target_slot")),
        "slot_known": bool(route.get("slot_known", False)),
        "routing_status": _stringify(route.get("routing_status")) or "accepted",
        "source_refs": source_refs,
        "source_kinds": sorted(set(source_kinds)),
        **(
            {"source_context_item_id": _stringify(block.get("source_context_item_id"))}
            if _stringify(block.get("source_context_item_id"))
            else {}
        ),
        "anchor": _estimated_layer_anchor(block_id=block_id, block_type=block_type, index=index, page_count=page_count),
        "edit_policy": {
            "editable": True,
            "mode": "template_block",
            "allowed_operations": [
                "replace_block",
                "append_to_slot",
                "annotate",
                "hide_layer",
                "regenerate_block",
            ],
            "requires_source_ref": True,
            "preserves_input_pdf": True,
            "claims_layout_preservation": False,
        },
        "style": {
            "style_pack": style_pack,
            "color_scheme": color_scheme,
        },
    }


def _estimated_layer_anchor(
    block_id: str,
    block_type: str,
    index: int,
    page_count: int | None,
) -> dict[str, Any]:
    safe_page_count = max(int(page_count or 1), 1)
    page_number = min(max(index, 1), safe_page_count)
    row = (index - 1) % 6
    height = 0.16 if block_type in {"code", "table", "image"} else 0.11
    y = min(0.88 - height, 0.08 + row * 0.14)
    return {
        "anchor_id": f"anchor_{block_id}",
        "anchor_kind": "estimated_slot_anchor",
        "page_number": page_number,
        "confidence": "estimated",
        "bbox": {
            "x": 0.08,
            "y": round(y, 3),
            "width": 0.84,
            "height": height,
            "coordinate_system": "normalized_page",
        },
        "notes": "Estimated from template block order; use render/OCR workers for exact physical bboxes.",
    }


def _load_context_packet_for_template(
    context_packet: dict[str, Any] | str | Path | None,
    context_packet_path: str | Path | None,
) -> dict[str, Any] | None:
    if context_packet is not None and context_packet_path is not None:
        raise AgentPDFException("invalid_input", "Use context_packet or context_packet_path, not both.")
    raw_packet: dict[str, Any] | None
    if context_packet is None and context_packet_path is None:
        return None
    if isinstance(context_packet, dict):
        raw_packet = deepcopy(context_packet)
    else:
        packet_path = context_packet_path if context_packet_path is not None else context_packet
        raw_packet = json.loads(Path(str(packet_path)).read_text(encoding="utf-8"))
    if not isinstance(raw_packet, dict):
        raise AgentPDFException("invalid_context_packet", "Context packet must be a JSON object.")
    if not raw_packet.get("context_packet_id") or not isinstance(raw_packet.get("items"), list):
        raise AgentPDFException("invalid_context_packet", "Context packet must include context_packet_id and items.")
    return raw_packet


def _context_packet_agent_blocks(
    packet: dict[str, Any],
    target_profile: dict[str, Any] | str | None = None,
) -> list[dict[str, Any]]:
    resolved_target_profile = _target_profile_for_context_mapping(target_profile)
    blocks: list[dict[str, Any]] = []
    for index, item in enumerate(packet.get("items", []), start=1):
        if not isinstance(item, dict):
            continue
        block = _context_item_agent_block(item, index=index, target_profile=resolved_target_profile)
        if block is not None:
            blocks.append(block)
    return blocks


def _context_item_agent_block(
    item: dict[str, Any],
    index: int,
    target_profile: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    item_type = _stringify(item.get("type")).strip().lower()
    context_item_id = _stringify(item.get("context_item_id")) or f"ctx_{index:03d}"
    source_ref = _stringify(item.get("source_ref")) or context_item_id
    title = _stringify(item.get("label")) or f"Context item {index}"
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    block: dict[str, Any] = {
        "block_id": _context_block_id(context_item_id, index),
        "title": title,
        "source_refs": [source_ref],
        "source_context_item_id": context_item_id,
    }
    if item_type == "code":
        code = _stringify(content.get("text") or metadata.get("preview"))
        if not code:
            return None
        block.update(
            {
                "type": "code",
                "target_slot": "evidence",
                "language": _language_from_extension(_stringify(metadata.get("extension"))),
                "code": code,
                "caption": _context_caption(item),
            }
        )
        return block
    if item_type == "data" and isinstance(content.get("table"), dict):
        table = content["table"]
        block.update(
            {
                "type": "table",
                "target_slot": "findings",
                "columns": [_stringify(column) for column in table.get("columns", [])],
                "rows": [
                    [_stringify(cell) for cell in row]
                    for row in table.get("rows", [])
                    if isinstance(row, list)
                ],
            }
        )
        return block
    if item_type == "image":
        image = content.get("image") if isinstance(content.get("image"), dict) else {}
        image_path = _stringify(metadata.get("path") or image.get("path") or item.get("uri"))
        if not image_path:
            return None
        block.update(
            {
                "type": "image",
                "target_slot": "evidence",
                "path": image_path,
                "caption": _context_caption(item),
                "alt": title,
            }
        )
        return block
    if item_type == "web_link":
        uri = _stringify(item.get("uri"))
        block.update(
            {
                "type": "citation",
                "target_slot": "recommendations",
                "quote": _stringify(metadata.get("preview") or title),
                "source": uri,
            }
        )
        return block
    if item_type in {"audio", "video", "media"}:
        block_type = _context_media_block_type(item_type, target_profile)
        body = _context_media_body(item)
        block.update(
            {
                "type": block_type,
                "target_slot": _context_media_target_slot(block_type, target_profile),
                "body": body or [f"Media source recorded: {_stringify(metadata.get('filename') or title)}"],
                **_context_media_block_fields(item=item, item_type=item_type),
            }
        )
        return block

    text = _stringify(content.get("text") or metadata.get("preview") or item.get("uri"))
    if item_type == "pdf" and not text:
        text = f"PDF source at {_stringify(metadata.get('path') or item.get('uri'))} with {metadata.get('page_count', '?')} page(s)."
    if not text:
        return None
    block.update(
        {
            "type": "section",
            "target_slot": "executive_summary" if item_type == "text" else "evidence",
            "body": text,
        }
    )
    return block


def _context_block_id(context_item_id: str, index: int) -> str:
    raw = context_item_id.strip() or f"ctx_{index:03d}"
    candidate = raw if raw.startswith("blk_") else f"blk_{raw}"
    candidate = candidate.replace(" ", "_").replace("-", "_")
    candidate = "".join(char for char in candidate if char.isalnum() or char == "_")
    return candidate or f"blk_ctx_{index:03d}"


def _context_caption(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    bits = [_stringify(item.get("label"))]
    if metadata.get("filename"):
        bits.append(_stringify(metadata.get("filename")))
    if metadata.get("sha256"):
        bits.append(f"sha256 {str(metadata['sha256'])[:12]}")
    return " | ".join(bit for bit in bits if bit)


def _context_media_body(item: dict[str, Any]) -> list[str]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    body = [
        f"Media file: {_stringify(metadata.get('filename') or item.get('label'))}",
        f"Kind: {_stringify(metadata.get('media_kind') or item.get('type'))}",
    ]
    transcript = content.get("transcript") if isinstance(content.get("transcript"), dict) else {}
    transcript_text = _stringify(transcript.get("text")) if transcript else ""
    if transcript_text:
        body.append(transcript_text[:1200])
    return [line for line in body if line]


def _target_profile_for_context_mapping(target_profile: dict[str, Any] | str | None) -> dict[str, Any] | None:
    profile_id = _target_profile_id(target_profile)
    if isinstance(target_profile, dict):
        if profile_id in DEFAULT_TARGET_PROFILES:
            merged = deepcopy(DEFAULT_TARGET_PROFILES[profile_id])
            merged.update(target_profile)
            return merged
        return deepcopy(target_profile)
    if profile_id:
        return deepcopy(DEFAULT_TARGET_PROFILES.get(profile_id))
    return None


def _context_media_block_type(item_type: str, target_profile: dict[str, Any] | None) -> str:
    specific_reference_type = {
        "audio": "audio_reference",
        "video": "video_reference",
    }.get(item_type, "media_reference")
    if target_profile is not None:
        layout_mode = str(target_profile.get("layout_mode") or "").strip().lower()
        accepts_specific_reference = _target_profile_accepts_block_type(
            target_profile,
            specific_reference_type,
        )
        accepts_generic_reference = _target_profile_accepts_block_type(target_profile, "media_reference")
        accepts_slide = _target_profile_accepts_block_type(target_profile, "slide")
        if layout_mode == "slides" and accepts_slide:
            return "slide"
        if accepts_specific_reference:
            return specific_reference_type
        if accepts_generic_reference:
            return "media_reference"
        if accepts_slide:
            return "slide"
    return "slide"


def _context_media_target_slot(block_type: str, target_profile: dict[str, Any] | None) -> str:
    slot = _first_target_profile_slot(target_profile, block_type)
    if slot:
        return slot
    if block_type in {"audio_reference", "video_reference", "media_reference"}:
        return "media_evidence"
    if block_type == "slide":
        return "evidence"
    return _agent_block_default_slot(block_type)


def _target_profile_accepts_block_type(target_profile: dict[str, Any] | None, block_type: str) -> bool:
    if target_profile is None:
        return False
    accepted_block_types = _template_pack_string_list(target_profile.get("accepted_block_types"))
    return block_type in accepted_block_types or bool(_first_target_profile_slot(target_profile, block_type))


def _first_target_profile_slot(target_profile: dict[str, Any] | None, block_type: str) -> str:
    for slot_name, accepted_types in _target_profile_slot_acceptance(target_profile).items():
        if block_type in accepted_types:
            return slot_name
    return ""


def _context_media_block_fields(item: dict[str, Any], item_type: str) -> dict[str, Any]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    media = content.get("media") if isinstance(content.get("media"), dict) else {}
    path = _stringify(metadata.get("path") or media.get("path") or item.get("uri"))
    filename = _stringify(metadata.get("filename") or media.get("filename"))
    if not filename and path:
        filename = Path(path).name
    chapters = content.get("chapters") if isinstance(content.get("chapters"), list) else []
    keyframes = content.get("keyframes") if isinstance(content.get("keyframes"), list) else []
    chapter_count = metadata.get("chapter_count") if metadata.get("chapter_count") is not None else len(chapters)
    keyframe_count = metadata.get("keyframe_count") if metadata.get("keyframe_count") is not None else len(keyframes)
    fields: dict[str, Any] = {
        "media_kind": _stringify(metadata.get("media_kind") or media.get("kind") or item_type),
        "path": path,
        "filename": filename,
        "duration_seconds": metadata.get("duration_seconds"),
        "transcript_excerpt": _context_transcript_excerpt(content),
        "chapter_count": chapter_count,
        "keyframe_count": keyframe_count,
    }
    return {key: value for key, value in fields.items() if value not in {"", None}}


def _context_transcript_excerpt(content: dict[str, Any], max_chars: int = 1800) -> str:
    transcript = content.get("transcript")
    if not isinstance(transcript, dict):
        return ""
    text = _stringify(transcript.get("text"))
    return text[:max_chars].strip()


def _template_pack_slot_routing_plan(
    template: dict[str, Any],
    template_id: str,
    target_profile_id: str,
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    template_slots = _template_pack_string_list(template.get("layout_slots"))
    supported_block_types = _template_pack_supported_block_types(template.get("supported_block_types"))
    target_profile = DEFAULT_TARGET_PROFILES.get(target_profile_id)
    target_profile_known = target_profile is not None
    target_profile_slots = _target_profile_slot_acceptance(target_profile)
    target_profile_block_types = _template_pack_string_list(
        target_profile.get("accepted_block_types") if target_profile is not None else None
    )
    routes: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, block in enumerate(blocks, start=1):
        block_type = _stringify(block.get("type")) or "section"
        target_slot = _stringify(block.get("target_slot"))
        source_refs = _template_pack_string_list(block.get("source_refs"))
        block_type_supported = block_type in supported_block_types
        target_profile_candidate_slots = [
            slot_name
            for slot_name, accepted_types in target_profile_slots.items()
            if block_type in accepted_types
        ]
        target_profile_accepts_block_type = (
            block_type in target_profile_block_types
            or bool(target_profile_candidate_slots)
            if target_profile_known
            else False
        )
        slot_known = target_slot in template_slots if target_slot else False
        routing_status = "accepted" if block_type_supported else "warning"
        if not block_type_supported:
            warnings.append(
                f"Block {block.get('block_id')} uses type {block_type}, which is not declared in template {template_id} supported_block_types."
            )
        routes.append(
            {
                "route_id": f"route_{index:03d}",
                "block_id": _stringify(block.get("block_id")) or f"block_{index:03d}",
                "block_type": block_type,
                "title": _stringify(block.get("title")),
                "source_refs": source_refs,
                **(
                    {"source_context_item_id": _stringify(block.get("source_context_item_id"))}
                    if _stringify(block.get("source_context_item_id"))
                    else {}
                ),
                "target_slot": target_slot,
                "slot_known": slot_known,
                "block_type_supported": block_type_supported,
                "target_profile_known": target_profile_known,
                "target_profile_accepts_block_type": target_profile_accepts_block_type,
                "target_profile_candidate_slots": target_profile_candidate_slots,
                "routing_status": routing_status,
                "routing_reason": _slot_routing_reason(block_type, target_slot, block),
            }
        )
    return {
        "slot_routing_plan_version": "0.1",
        "slot_routing_plan_id": f"route_{uuid4().hex[:16]}",
        "template_id": template_id,
        "target_profile_id": target_profile_id,
        "target_profile_known": target_profile_known,
        "target_profile_slots": target_profile_slots,
        "template_slots": template_slots,
        "supported_block_types": supported_block_types,
        "route_count": len(routes),
        "accepted_route_count": len([route for route in routes if route["routing_status"] == "accepted"]),
        "warning_route_count": len([route for route in routes if route["routing_status"] != "accepted"]),
        "routes": routes,
        "warnings": warnings,
        "next_recommended_tools": [
            "pdf.evidence.coverage_report",
            "pdf.validation.render_check",
            "pdf.patch.plan",
        ],
    }


def _slot_routing_reason(block_type: str, target_slot: str, block: dict[str, Any]) -> str:
    if block.get("source_context_item_id"):
        return f"Context {block_type} item routed to {target_slot or 'unspecified'} slot from Context Packet evidence."
    if block.get("render_hints", {}).get("agent_supplied_block"):
        return f"Agent supplied {block_type} block requested {target_slot or 'unspecified'} slot."
    return f"Template sample {block_type} block assigned to {target_slot or 'unspecified'} slot."


def _target_profile_slot_acceptance(target_profile: dict[str, Any] | None) -> dict[str, list[str]]:
    if target_profile is None:
        return {}
    layout_slots = target_profile.get("layout_slots")
    if not isinstance(layout_slots, dict):
        return {}
    return {
        str(slot_name): _template_pack_string_list(slot.get("accepts"))
        for slot_name, slot in layout_slots.items()
        if isinstance(slot, dict)
    }


def _template_pack_blocks(
    template: dict[str, Any],
    merged_data: dict[str, Any],
    source_refs: list[str],
) -> list[dict[str, Any]]:
    slots = _template_pack_string_list(template.get("layout_slots"))
    blocks: list[dict[str, Any]] = []
    sections = _normalize_sections(merged_data.get("sections"))
    for index, section in enumerate(sections, start=1):
        title = _stringify(section.get("heading") or f"Section {index}")
        blocks.append(
            {
                "block_id": f"blk_tpl_{index:03d}",
                "type": "section",
                "title": title,
                "source_refs": list(source_refs),
                "target_slot": _slot_for_index(slots, index - 1, fallback=title),
                "render_hints": {"template_pack_block": True},
                "data": {
                    "heading": title,
                    "body": _stringify(section.get("body")),
                    "bullets": section.get("bullets") if isinstance(section.get("bullets"), list) else [],
                },
            }
        )

    checklist = merged_data.get("checklist")
    if isinstance(checklist, list) and checklist:
        blocks.append(
            {
                "block_id": f"blk_tpl_{len(blocks) + 1:03d}",
                "type": "section",
                "title": "Checklist",
                "source_refs": list(source_refs),
                "target_slot": "checklist",
                "render_hints": {"template_pack_block": True, "list": "checkbox"},
                "data": {"items": [_stringify(item) for item in checklist]},
            }
        )

    seen_block_ids = {block["block_id"] for block in blocks}
    blocks.extend(
        _agent_blocks_from_raw(
            merged_data.get("blocks"),
            default_source_refs=source_refs,
            seen_block_ids=seen_block_ids,
        )
    )

    if not blocks:
        blocks.append(
            {
                "block_id": "blk_tpl_001",
                "type": "section",
                "title": _stringify(merged_data.get("title")) or str(template.get("name") or "Template Data"),
                "source_refs": list(source_refs),
                "target_slot": _slot_for_index(slots, 0, fallback="template_data"),
                "render_hints": {"template_pack_block": True},
                "data": {"fields": deepcopy(merged_data)},
            }
        )
    return blocks


def _agent_blocks_from_raw(
    raw_blocks: Any,
    default_source_refs: list[str],
    seen_block_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if raw_blocks is None:
        return []
    if not isinstance(raw_blocks, list):
        raise AgentPDFException("invalid_input", "data.blocks must be an array when provided.")

    seen = set(seen_block_ids or set())
    blocks: list[dict[str, Any]] = []
    for index, raw_block in enumerate(raw_blocks, start=1):
        if not isinstance(raw_block, dict):
            raise AgentPDFException("invalid_input", f"data.blocks[{index - 1}] must be an object.")
        block_type = _normalize_agent_block_type(raw_block.get("type") or raw_block.get("kind"))
        block_id = _agent_block_id(raw_block.get("block_id"), index=index, seen_block_ids=seen)
        seen.add(block_id)
        title = _stringify(raw_block.get("title") or raw_block.get("heading")) or f"Agent Block {index}"
        source_refs = _template_pack_string_list(raw_block.get("source_refs")) or list(default_source_refs)
        target_slot = (
            _stringify(raw_block.get("target_slot") or raw_block.get("slot"))
            or _agent_block_default_slot(block_type)
        )
        source_context_item_id = _stringify(raw_block.get("source_context_item_id"))
        blocks.append(
            {
                "block_id": block_id,
                "type": block_type,
                "title": title,
                "source_refs": source_refs,
                **({"source_context_item_id": source_context_item_id} if source_context_item_id else {}),
                "target_slot": target_slot,
                "render_hints": {
                    "template_pack_block": True,
                    "agent_supplied_block": True,
                },
                "data": _agent_block_data(block_type, raw_block),
            }
        )
    return blocks


def _normalize_agent_block_type(raw_type: Any) -> str:
    block_type = _stringify(raw_type).strip().lower().replace("-", "_") or "section"
    aliases = {
        "markdown": "section",
        "text": "section",
        "callout": "section",
        "figure": "image",
        "metric_table": "table",
        "deck_slide": "slide",
        "audio": "audio_reference",
        "video": "video_reference",
        "media": "media_reference",
    }
    normalized = aliases.get(block_type, block_type)
    allowed = set(SUPPORTED_AGENT_BLOCK_TYPES)
    if normalized not in allowed:
        raise AgentPDFException(
            "invalid_input",
            f"Unsupported agent block type: {raw_type}. Supported types: {', '.join(sorted(allowed))}.",
        )
    return normalized


def _agent_block_id(raw_block_id: Any, index: int, seen_block_ids: set[str]) -> str:
    raw = _stringify(raw_block_id).strip()
    candidate = raw or f"blk_agent_{index:03d}"
    candidate = candidate.replace(" ", "_").replace("-", "_")
    candidate = "".join(char for char in candidate if char.isalnum() or char == "_")
    if not candidate:
        candidate = f"blk_agent_{index:03d}"
    if candidate not in seen_block_ids:
        return candidate
    suffix = 2
    while f"{candidate}_{suffix}" in seen_block_ids:
        suffix += 1
    return f"{candidate}_{suffix}"


def _agent_block_default_slot(block_type: str) -> str:
    if block_type in {"audio_reference", "video_reference", "media_reference"}:
        return "media_evidence"
    if block_type in {"code", "table", "image", "citation"}:
        return "evidence"
    if block_type == "slide":
        return "slide"
    return "content"


def _agent_block_data(block_type: str, raw_block: dict[str, Any]) -> dict[str, Any]:
    if block_type == "code":
        code = _stringify(raw_block.get("code"))
        if not code:
            raise AgentPDFException("invalid_input", "code blocks require a non-empty code field.")
        return {
            "language": _stringify(raw_block.get("language")) or "text",
            "code": code,
            "caption": _stringify(raw_block.get("caption")),
        }
    if block_type == "table":
        columns = [_stringify(column) for column in raw_block.get("columns", [])] if isinstance(raw_block.get("columns"), list) else []
        rows = _normalize_table_rows(raw_block.get("rows"), columns)
        if not columns and rows:
            columns = [f"column_{index}" for index in range(1, len(rows[0]) + 1)]
        if not columns:
            raise AgentPDFException("invalid_input", "table blocks require columns or rows.")
        return {"columns": columns, "rows": rows}
    if block_type == "image":
        path = _stringify(raw_block.get("path") or raw_block.get("image_path"))
        if not path:
            raise AgentPDFException("invalid_input", "image blocks require path or image_path.")
        image_evidence = _image_block_evidence(path)
        return {
            "path": image_evidence["path"],
            "caption": _stringify(raw_block.get("caption")),
            "alt": _stringify(raw_block.get("alt") or raw_block.get("caption")),
            "image_evidence": {
                "exists": image_evidence["exists"],
                "width": image_evidence["width"],
                "height": image_evidence["height"],
                "mime_type": image_evidence["mime_type"],
            },
        }
    if block_type == "slide":
        return {
            "body": _normalize_body_lines(raw_block.get("body") or raw_block.get("bullets")),
            "speaker_notes": _normalize_body_lines(raw_block.get("speaker_notes")),
        }
    if block_type in {"audio_reference", "video_reference", "media_reference"}:
        return _agent_media_reference_data(block_type, raw_block)
    if block_type == "citation":
        return {
            "quote": _stringify(raw_block.get("quote") or raw_block.get("body")),
            "source": _stringify(raw_block.get("source")),
            "page": _stringify(raw_block.get("page")),
        }
    return {
        "body": _stringify(raw_block.get("body") or raw_block.get("markdown")),
        "bullets": [_stringify(item) for item in raw_block.get("bullets", [])]
        if isinstance(raw_block.get("bullets"), list)
        else [],
    }


def _normalize_table_rows(raw_rows: Any, columns: list[str]) -> list[list[str]]:
    if not isinstance(raw_rows, list):
        return []
    rows: list[list[str]] = []
    for raw_row in raw_rows:
        if isinstance(raw_row, dict):
            ordered_keys = columns or [str(key) for key in raw_row]
            rows.append([_stringify(raw_row.get(key)) for key in ordered_keys])
        elif isinstance(raw_row, list):
            rows.append([_stringify(cell) for cell in raw_row])
        else:
            rows.append([_stringify(raw_row)])
    return rows


def _normalize_body_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_stringify(item) for item in value if _stringify(item)]
    text = _stringify(value)
    return [text] if text else []


def _agent_media_reference_data(block_type: str, raw_block: dict[str, Any]) -> dict[str, Any]:
    data = raw_block.get("data") if isinstance(raw_block.get("data"), dict) else raw_block
    path = _stringify(data.get("path") or data.get("media_path") or data.get("uri"))
    filename = _stringify(data.get("filename"))
    if not filename and path:
        filename = Path(path).name
    transcript_excerpt = _stringify(data.get("transcript_excerpt") or data.get("transcript"))
    payload: dict[str, Any] = {
        "media_kind": _stringify(data.get("media_kind")) or block_type.replace("_reference", ""),
        "path": path,
        "filename": filename,
        "duration_seconds": _coerce_number(data.get("duration_seconds")),
        "transcript_excerpt": transcript_excerpt,
        "chapter_count": _coerce_int(data.get("chapter_count")),
        "keyframe_count": _coerce_int(data.get("keyframe_count")),
        "body": _normalize_body_lines(data.get("body") or data.get("bullets")),
    }
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != []
    }


def _coerce_number(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _image_block_evidence(path: str) -> dict[str, Any]:
    resolved = resolve_input_path(path)
    if resolved.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise AgentPDFException(
            "unsupported_file_type",
            f"Unsupported image block format: {resolved.suffix}",
            details={"supported_suffixes": sorted(SUPPORTED_IMAGE_SUFFIXES)},
        )
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - Pillow is installed with reportlab in normal use
        raise AgentPDFException("dependency_missing", "Image block evidence requires Pillow.") from exc

    with Image.open(resolved) as image:
        width, height = image.size
    return {
        "path": str(resolved),
        "exists": True,
        "width": int(width),
        "height": int(height),
        "mime_type": mimetypes.guess_type(resolved.name)[0] or "application/octet-stream",
    }


def _source_kind_for_ref(source_ref: str) -> str:
    normalized = source_ref.strip().lower()
    if normalized.startswith("tpl://"):
        return "template_pack"
    if normalized.startswith(("ctx://", "ctx_")):
        return "agent_context"
    if normalized.startswith(("http://", "https://")):
        return "web_link"
    if normalized.startswith(("file://", "path://")):
        return "local_file"
    return "agent_context"


def _language_from_extension(extension: str) -> str:
    return {
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".py": "python",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".sql": "sql",
        ".sh": "bash",
    }.get(extension.lower(), extension.lstrip(".") or "text")


def _agent_block_markdown_lines(block: dict[str, Any]) -> list[str]:
    block_type = str(block["type"])
    data = block["data"]
    lines = [f"### {_stringify(block.get('title'))}", ""]
    source_refs = block.get("source_refs")
    if isinstance(source_refs, list) and source_refs:
        lines.extend([f"**Source refs:** {', '.join(_stringify(ref) for ref in source_refs)}", ""])

    if block_type == "code":
        language = _stringify(data.get("language")) or "text"
        lines.extend([f"```{language}", _stringify(data.get("code")).rstrip(), "```"])
        caption = _stringify(data.get("caption"))
        if caption:
            lines.extend(["", caption])
        return lines
    if block_type == "table":
        columns = [_stringify(column) for column in data.get("columns", [])]
        rows = data.get("rows") if isinstance(data.get("rows"), list) else []
        lines.append("| " + " | ".join(_markdown_table_cell(column) for column in columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            cells = row if isinstance(row, list) else [row]
            normalized = [_markdown_table_cell(_stringify(cell)) for cell in cells]
            normalized.extend([""] * (len(columns) - len(normalized)))
            lines.append("| " + " | ".join(normalized[: len(columns)]) + " |")
        return lines
    if block_type == "image":
        path = _stringify(data.get("path"))
        alt = _stringify(data.get("alt") or block.get("title"))
        caption = _stringify(data.get("caption"))
        lines.append(f"![{alt}](<{path}>)")
        if caption:
            lines.extend(["", caption])
        return lines
    if block_type == "slide":
        body = data.get("body") if isinstance(data.get("body"), list) else []
        for item in body:
            lines.append(f"- {_stringify(item)}")
        speaker_notes = data.get("speaker_notes") if isinstance(data.get("speaker_notes"), list) else []
        if speaker_notes:
            lines.extend(["", "**Speaker notes:**"])
            for note in speaker_notes:
                lines.append(f"- {_stringify(note)}")
        return lines
    if block_type in {"audio_reference", "video_reference", "media_reference"}:
        media_kind = _stringify(data.get("media_kind")) or block_type.replace("_reference", "")
        filename = _stringify(data.get("filename") or data.get("path") or block.get("title"))
        lines.append(f"Media file: {filename}")
        lines.append(f"Kind: {media_kind}")
        if data.get("duration_seconds") is not None:
            lines.append(f"Duration: {data['duration_seconds']} second(s)")
        if data.get("chapter_count") is not None:
            lines.append(f"Chapters: {data['chapter_count']}")
        if data.get("keyframe_count") is not None:
            lines.append(f"Keyframes: {data['keyframe_count']}")
        transcript_excerpt = _stringify(data.get("transcript_excerpt"))
        if transcript_excerpt:
            lines.extend(["", transcript_excerpt])
        body = data.get("body") if isinstance(data.get("body"), list) else []
        if body:
            lines.append("")
            for item in body:
                lines.append(f"- {_stringify(item)}")
        return lines
    if block_type == "citation":
        quote = _stringify(data.get("quote"))
        if quote:
            lines.append(f"> {quote}")
        source_parts = [
            _stringify(data.get("source")),
            f"page {_stringify(data.get('page'))}" if _stringify(data.get("page")) else "",
        ]
        source = ", ".join(part for part in source_parts if part)
        if source:
            lines.extend(["", f"Source: {source}"])
        return lines

    body = _stringify(data.get("body"))
    if body:
        lines.append(body)
    bullets = data.get("bullets") if isinstance(data.get("bullets"), list) else []
    for bullet in bullets:
        lines.append(f"- {_stringify(bullet)}")
    return lines


def _markdown_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _slot_for_index(slots: list[str], index: int, fallback: str) -> str:
    if 0 <= index < len(slots):
        return slots[index]
    return fallback.strip().lower().replace(" ", "_") or "section"


def _load_template_pack(template_pack: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(template_pack, dict):
        return deepcopy(template_pack)
    raw = str(template_pack).strip()
    if raw in BUILTIN_TEMPLATE_PACKS:
        return deepcopy(BUILTIN_TEMPLATE_PACKS[raw])
    candidate = Path(raw)
    if candidate.exists():
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            available = ", ".join(sorted(BUILTIN_TEMPLATE_PACKS))
            raise AgentPDFException(
                "invalid_template_pack",
                f"Template pack must be a JSON object, JSON file path, or built-in pack id. Available built-ins: {available}.",
            ) from exc
    if not isinstance(payload, dict):
        raise AgentPDFException("invalid_template_pack", "Template pack JSON must be an object.")
    return payload


def _template_pack_validation_report(pack: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    templates_raw = pack.get("templates")
    templates = templates_raw if isinstance(templates_raw, list) else []
    if not str(pack.get("pack_id", "")).strip():
        errors.append("pack_id is required")
    if not str(pack.get("name", "")).strip():
        errors.append("name is required")
    if not templates:
        errors.append("templates must contain at least one template")

    seen_template_ids: set[str] = set()
    template_reports: list[dict[str, Any]] = []
    for index, raw_template in enumerate(templates):
        if not isinstance(raw_template, dict):
            errors.append(f"templates[{index}] must be an object")
            continue
        template_id = str(raw_template.get("template_id", "")).strip()
        template_errors: list[str] = []
        template_warnings: list[str] = []
        if not template_id:
            template_errors.append("template_id is required")
        elif template_id in seen_template_ids:
            template_errors.append(f"duplicate template_id: {template_id}")
        seen_template_ids.add(template_id)

        base_template = str(raw_template.get("base_template", "")).strip()
        if base_template not in CREATE_TEMPLATES:
            template_errors.append(f"base_template must be one of: {', '.join(sorted(CREATE_TEMPLATES))}")

        style_pack = str(raw_template.get("default_style_pack", "")).strip()
        if style_pack and style_pack not in BUILTIN_STYLE_PACKS:
            template_warnings.append(f"default_style_pack is not a built-in style pack: {style_pack}")

        fields = raw_template.get("fields")
        if not isinstance(fields, dict):
            template_errors.append("fields must be an object with required/optional arrays")
            required_fields: list[str] = []
            optional_fields: list[str] = []
        else:
            required_fields = _template_pack_string_list(fields.get("required"))
            optional_fields = _template_pack_string_list(fields.get("optional"))

        sample_data = raw_template.get("sample_data") if isinstance(raw_template.get("sample_data"), dict) else {}
        missing_sample_fields = [
            field for field in required_fields if field not in sample_data and field != "title"
        ]
        if missing_sample_fields:
            template_warnings.append(
                "sample_data is missing required fields: " + ", ".join(missing_sample_fields)
            )

        try:
            supported_block_types = _template_pack_supported_block_types(raw_template.get("supported_block_types"))
        except AgentPDFException as exc:
            supported_block_types = []
            template_errors.append(f"unsupported block type: {exc.message}")

        color_schemes = raw_template.get("color_schemes")
        color_scheme_ids = sorted(color_schemes) if isinstance(color_schemes, dict) else []
        if not color_scheme_ids:
            template_warnings.append("template has no color_schemes; default style colors will be used")
        for scheme_id, colors in (color_schemes.items() if isinstance(color_schemes, dict) else []):
            if not isinstance(colors, dict):
                template_errors.append(f"color_schemes.{scheme_id} must be an object")
                continue
            try:
                _normalize_colors({str(key): str(value) for key, value in colors.items()})
            except AgentPDFException as exc:
                template_errors.append(f"color_schemes.{scheme_id}: {exc.message}")

        agent_ready = not template_errors and bool(base_template) and bool(required_fields or optional_fields)
        template_reports.append(
            {
                "template_id": template_id,
                "name": str(raw_template.get("name", "")),
                "base_template": base_template,
                "target_profile": raw_template.get("target_profile"),
                "default_style_pack": style_pack,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "layout_slots": _template_pack_string_list(raw_template.get("layout_slots")),
                "supported_block_types": supported_block_types,
                "color_scheme_ids": color_scheme_ids,
                "agent_ready": agent_ready,
                "errors": template_errors,
                "warnings": template_warnings,
            }
        )
        errors.extend(f"{template_id or f'templates[{index}]'}: {error}" for error in template_errors)
        warnings.extend(f"{template_id or f'templates[{index}]'}: {warning}" for warning in template_warnings)

    return {
        "is_valid": not errors,
        "pack_id": str(pack.get("pack_id", "")),
        "name": str(pack.get("name", "")),
        "version": str(pack.get("version", "")),
        "license": str(pack.get("license", "")),
        "template_count": len(template_reports),
        "style_pack_count": len(
            {
                template.get("default_style_pack")
                for template in templates
                if isinstance(template, dict) and template.get("default_style_pack")
            }
        ),
        "color_scheme_count": len(_template_pack_color_scheme_ids(pack)),
        "templates": template_reports,
        "errors": errors,
        "warnings": warnings,
        "agent_contract": {
            "catalog_tool": "pdf.ai.create.template_packs",
            "validate_tool": "pdf.ai.create.validate_template_pack",
            "create_tool": "pdf.ai.create.from_template_pack",
            "preview_tool": "pdf.ai.create.template_preview",
            "returns_tool_result": True,
            "cloud_required": bool(pack.get("cloud_required", False)),
        },
    }


def _find_template_in_pack(pack: dict[str, Any], template_id: str) -> dict[str, Any]:
    normalized = template_id.strip()
    for template in pack.get("templates", []):
        if isinstance(template, dict) and str(template.get("template_id")) == normalized:
            return template
    available = [
        str(template.get("template_id"))
        for template in pack.get("templates", [])
        if isinstance(template, dict)
    ]
    raise AgentPDFException(
        "invalid_template",
        f"Template pack does not contain template {template_id}. Available templates: {', '.join(sorted(available))}.",
    )


def _template_pack_colors(
    template: dict[str, Any],
    color_scheme: str | None,
) -> tuple[str | None, dict[str, str] | None]:
    schemes = template.get("color_schemes") if isinstance(template.get("color_schemes"), dict) else {}
    if not schemes:
        return None, None
    selected = color_scheme or next(iter(sorted(schemes)))
    if selected not in schemes:
        available = ", ".join(sorted(schemes))
        raise AgentPDFException(
            "invalid_color_key",
            f"Unknown template pack color scheme: {selected}. Available schemes: {available}.",
        )
    raw_colors = schemes[selected]
    if not isinstance(raw_colors, dict):
        raise AgentPDFException("invalid_color_value", f"Color scheme must be an object: {selected}")
    return selected, _normalize_colors({str(key): str(value) for key, value in raw_colors.items()})


def _template_pack_color_scheme_ids(pack: dict[str, Any]) -> list[str]:
    scheme_ids: set[str] = set()
    for template in pack.get("templates", []):
        if not isinstance(template, dict):
            continue
        schemes = template.get("color_schemes")
        if isinstance(schemes, dict):
            scheme_ids.update(str(key) for key in schemes)
    return sorted(scheme_ids)


def _template_pack_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _template_pack_supported_block_types(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return list(SUPPORTED_AGENT_BLOCK_TYPES)
    normalized: list[str] = []
    for item in value:
        block_type = _normalize_agent_block_type(item)
        if block_type not in normalized:
            normalized.append(block_type)
    return normalized


def render_template_markdown(
    prompt: str,
    template_id: str,
    data: dict[str, Any] | None = None,
    title: str | None = None,
) -> tuple[str, str]:
    if template_id not in CREATE_TEMPLATES:
        raise AgentPDFException("invalid_template", f"Unknown create template: {template_id}")
    content = dict(data or {})
    template_spec = CREATE_TEMPLATES[template_id]
    resolved_title = title or _title_from_data_or_prompt(content, prompt, template_spec["name"])
    if template_id == "invoice" and _has_structured_invoice_data(content):
        return _render_invoice_markdown(prompt, content, resolved_title), "invoice"
    if template_id == "resume" and _has_structured_resume_data(content):
        return _render_resume_markdown(prompt, content, resolved_title), "resume"
    if template_id == "worksheet" and _has_structured_worksheet_data(content):
        return _render_worksheet_markdown(prompt, content, resolved_title), "worksheet"
    if template_id == "proposal" and _has_structured_proposal_data(content):
        return _render_proposal_markdown(prompt, content, resolved_title), "proposal"

    lines = [f"# {resolved_title}", ""]

    audience = content.get("audience") or content.get("client")
    if audience:
        lines.extend([f"**Audience:** {_stringify(audience)}", ""])

    lines.extend(["## Creation Brief", "", prompt.strip(), ""])

    sections = _normalize_sections(content.get("sections"))
    if not sections:
        sections = [
            {"heading": heading, "body": _default_section_body(heading, prompt)}
            for heading in template_spec["default_sections"]
        ]

    for section in sections:
        heading = _stringify(section.get("heading", "Section"))
        body = _stringify(section.get("body", ""))
        lines.extend([f"## {heading}", "", body or _default_section_body(heading, prompt), ""])
        bullets = section.get("bullets")
        if isinstance(bullets, list):
            for bullet in bullets:
                lines.append(f"- {_stringify(bullet)}")
            lines.append("")

    agent_blocks = _agent_blocks_from_raw(content.get("blocks"), default_source_refs=[])
    if agent_blocks:
        lines.extend(["## Agent Blocks", ""])
        for block in agent_blocks:
            lines.extend(_agent_block_markdown_lines(block))
            lines.append("")

    checklist = content.get("checklist")
    if isinstance(checklist, list):
        lines.extend(["## Checklist", ""])
        for item in checklist:
            lines.append(f"- [ ] {_stringify(item)}")
        lines.append("")

    lines.extend(
        [
            "## Agent Evidence",
            "",
            "- Created locally without cloud services.",
            "- Template, style pack, artifact metadata, and validation are returned as structured JSON.",
        ]
    )
    return "\n".join(lines).strip() + "\n", "generic"


def _render_invoice_markdown(prompt: str, content: dict[str, Any], title: str) -> str:
    invoice_number = _stringify(content.get("invoice_number"))
    client = _stringify(content.get("client") or content.get("bill_to"))
    due_date = _stringify(content.get("due_date"))
    items = content.get("items") if isinstance(content.get("items"), list) else []
    lines = [f"# {title}", "", "## Invoice Details", ""]
    if invoice_number:
        lines.append(f"**Invoice:** {invoice_number}")
    if client:
        lines.append(f"**Bill To:** {client}")
    if due_date:
        lines.append(f"**Due Date:** {due_date}")
    lines.extend(["", "## Items", "", "| Description | Qty | Unit Price | Line Total |", "|---|---:|---:|---:|"])

    total = 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        description = _stringify(item.get("description") or item.get("name") or "Item")
        quantity = _number(item.get("quantity"), default=1.0)
        unit_price = _number(item.get("unit_price") or item.get("price"), default=0.0)
        line_total = quantity * unit_price
        total += line_total
        lines.append(
            f"| {description} | {_format_number(quantity)} | {_format_number(unit_price)} | {_format_number(line_total)} |"
        )

    explicit_total = content.get("total")
    if explicit_total is not None:
        total = _number(explicit_total, default=total)
    lines.extend(["", f"**Total:** {_format_number(total)}", ""])
    notes = _stringify(content.get("payment_notes") or content.get("notes"))
    if notes:
        lines.extend(["## Payment Notes", "", notes, ""])
    lines.extend(_agent_evidence_lines(prompt))
    return "\n".join(lines).strip() + "\n"


def _render_resume_markdown(prompt: str, content: dict[str, Any], title: str) -> str:
    name = _stringify(content.get("name") or title)
    headline = _stringify(content.get("headline") or content.get("title"))
    summary = _stringify(content.get("summary"))
    contact = content.get("contact") if isinstance(content.get("contact"), dict) else {}
    skills = content.get("skills") if isinstance(content.get("skills"), list) else []
    experience = content.get("experience") if isinstance(content.get("experience"), list) else []

    lines = [f"# {name}", ""]
    if headline:
        lines.extend([headline, ""])
    contact_bits = [
        _stringify(value)
        for value in contact.values()
        if _stringify(value)
    ]
    if contact_bits:
        lines.extend(["**Contact:** " + " | ".join(contact_bits), ""])
    if summary:
        lines.extend(["## Summary", "", summary, ""])
    if skills:
        lines.extend(["## Skills", ""])
        for skill in skills:
            lines.append(f"- {_stringify(skill)}")
        lines.append("")
    if experience:
        lines.extend(["## Experience", ""])
        for role in experience:
            if not isinstance(role, dict):
                continue
            heading = " - ".join(
                part
                for part in [
                    _stringify(role.get("role") or role.get("title")),
                    _stringify(role.get("company")),
                ]
                if part
            )
            period = _stringify(role.get("period"))
            lines.append(f"### {heading or 'Role'}")
            if period:
                lines.append(period)
            bullets = role.get("bullets") if isinstance(role.get("bullets"), list) else []
            for bullet in bullets:
                lines.append(f"- {_stringify(bullet)}")
            lines.append("")
    lines.extend(_agent_evidence_lines(prompt))
    return "\n".join(lines).strip() + "\n"


def _render_worksheet_markdown(prompt: str, content: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", "", "## Learning Goal", ""]
    lines.append(_stringify(content.get("learning_goal")) or prompt.strip())
    questions = content.get("questions") if isinstance(content.get("questions"), list) else []
    if questions:
        lines.extend(["", "## Practice", ""])
        for index, question in enumerate(questions, start=1):
            lines.append(f"{index}. {_stringify(question)}")
        lines.append("")
    checklist = content.get("checklist") if isinstance(content.get("checklist"), list) else []
    if checklist:
        lines.extend(["## Checklist", ""])
        for item in checklist:
            lines.append(f"- [ ] {_stringify(item)}")
        lines.append("")
    lines.extend(_agent_evidence_lines(prompt))
    return "\n".join(lines).strip() + "\n"


def _render_proposal_markdown(prompt: str, content: dict[str, Any], title: str) -> str:
    fields = [
        ("Problem", content.get("problem")),
        ("Approach", content.get("approach")),
        ("Deliverables", content.get("deliverables")),
        ("Timeline", content.get("timeline")),
    ]
    lines = [f"# {title}", ""]
    client = _stringify(content.get("client"))
    if client:
        lines.extend([f"**Client:** {client}", ""])
    lines.extend(["## Creation Brief", "", prompt.strip(), ""])
    for heading, value in fields:
        if value is None:
            continue
        lines.extend([f"## {heading}", ""])
        if isinstance(value, list):
            for item in value:
                lines.append(f"- {_stringify(item)}")
        else:
            lines.append(_stringify(value))
        lines.append("")
    lines.extend(_agent_evidence_lines(prompt))
    return "\n".join(lines).strip() + "\n"


def _agent_evidence_lines(prompt: str) -> list[str]:
    return [
        "## Agent Evidence",
        "",
        "- Created locally without cloud services.",
        "- Template, style pack, artifact metadata, and validation are returned as structured JSON.",
    ]


def _select_template(prompt: str, template: str | None) -> str:
    if template:
        normalized = template.strip().lower().replace("-", "_")
        if normalized not in CREATE_TEMPLATES:
            available = ", ".join(sorted(CREATE_TEMPLATES))
            raise AgentPDFException(
                "invalid_template",
                f"Unknown create template: {template}. Available templates: {available}.",
            )
        return normalized

    normalized_prompt = prompt.lower()
    best_template = "one_pager"
    best_score = 0
    for template_id, spec in CREATE_TEMPLATES.items():
        score = sum(1 for keyword in spec["keywords"] if keyword in normalized_prompt)
        if score > best_score:
            best_template = template_id
            best_score = score
    return best_template


def _selection_reason(prompt: str, template_id: str, explicit_template: str | None) -> str:
    if explicit_template:
        return f"Template explicitly requested as {template_id}."
    matches = [
        keyword
        for keyword in CREATE_TEMPLATES[template_id]["keywords"]
        if keyword in prompt.lower()
    ]
    if matches:
        return f"Selected from prompt keywords: {', '.join(sorted(matches))}."
    return "Defaulted to one_pager because no stronger local template keyword matched."


def _style_pack_with_colors(style_pack: str, colors: dict[str, str]) -> dict[str, Any]:
    if style_pack in BUILTIN_STYLE_PACKS:
        pack = dict(BUILTIN_STYLE_PACKS[style_pack])
    else:
        candidate = Path(style_pack)
        if not candidate.exists():
            available = ", ".join(sorted(BUILTIN_STYLE_PACKS))
            raise AgentPDFException(
                "invalid_style_pack",
                f"Unknown style pack for color override: {style_pack}. Available built-ins: {available}.",
            )
        import json

        raw = json.loads(candidate.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise AgentPDFException("invalid_style_pack", "Style pack JSON must be an object.")
        pack = raw
    merged_colors = dict(pack.get("colors", {}))
    merged_colors.update(colors)
    pack["colors"] = merged_colors
    pack["style_id"] = f"{pack.get('style_id', style_pack)}_custom"
    pack["name"] = f"{pack.get('name', style_pack)} Custom"
    return pack


def _normalize_colors(colors: dict[str, str] | None) -> dict[str, str]:
    if not colors:
        return {}
    normalized = {}
    allowed = {"primary", "accent", "text"}
    for key, raw_value in colors.items():
        if key not in allowed:
            raise AgentPDFException(
                "invalid_color_key",
                f"Unsupported color key: {key}. Use primary, accent, or text.",
            )
        value = raw_value.strip()
        if not value.startswith("#"):
            value = f"#{value}"
        hex_value = value[1:]
        if len(hex_value) != 6 or any(char not in "0123456789abcdefABCDEF" for char in hex_value):
            raise AgentPDFException("invalid_color_value", f"Invalid hex color: {raw_value}")
        normalized[key] = f"#{hex_value.lower()}"
    return normalized


def _title_from_data_or_prompt(content: dict[str, Any], prompt: str, fallback: str) -> str:
    raw_title = content.get("title")
    if raw_title:
        return _stringify(raw_title)
    cleaned = prompt.strip().replace("\n", " ")
    for prefix in ["create a ", "create an ", "make a ", "generate a ", "draft a "]:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    sentence = cleaned.split(".")[0].strip(" :;-")
    if not sentence:
        return fallback
    return sentence[:96]


def _normalize_sections(raw_sections: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_sections, list):
        return []
    normalized = []
    for index, item in enumerate(raw_sections, start=1):
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({"heading": f"Section {index}", "body": item})
    return normalized


def _has_structured_invoice_data(content: dict[str, Any]) -> bool:
    return isinstance(content.get("items"), list) or any(
        key in content for key in ["invoice_number", "client", "bill_to", "due_date", "payment_notes"]
    )


def _has_structured_resume_data(content: dict[str, Any]) -> bool:
    return any(key in content for key in ["name", "headline", "contact", "summary", "skills", "experience"])


def _has_structured_worksheet_data(content: dict[str, Any]) -> bool:
    return any(key in content for key in ["learning_goal", "questions", "checklist"])


def _has_structured_proposal_data(content: dict[str, Any]) -> bool:
    return any(key in content for key in ["problem", "approach", "deliverables", "timeline", "client"])


def _default_section_body(heading: str, prompt: str) -> str:
    return f"This section is generated from the local creation brief: {prompt.strip()}"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
