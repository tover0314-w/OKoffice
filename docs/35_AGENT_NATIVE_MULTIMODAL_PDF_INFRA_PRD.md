# 35 - Agent-Native Multimodal PDF Infra PRD

## Status

This document updates the product direction for AgentPDF/okpdf beyond a basic PDF toolkit.

The open-source harness still starts with local deterministic PDF operations, CLI, MCP, REST, SDKs, schemas, artifacts, and validation. The larger product ambition is now explicit: AgentPDF should become agent-native multimodal document infrastructure where PDF is the durable, inspectable, verifiable delivery artifact.

## Product thesis

AgentPDF is the operating layer for agents that need to understand, compose, operate on, and verify PDF artifacts.

It should not be positioned as:

- A wrapper around existing Python or npm PDF libraries.
- A basic merge/split/convert utility.
- A simple PDF chat or RAG demo.
- A black-box prompt-to-PDF generator.

It should be positioned as:

- The PDF action and artifact layer for AI agents.
- A context-to-PDF compiler for turning many input contexts into specific PDF genres and styles.
- A verification and audit layer for generated or edited documents.
- A workflow substrate for batch document operations, source traceability, and enterprise review.

## Product formula

```text
context packet + target PDF profile -> understanding -> composition plan -> render/patch -> verify -> evidence-backed PDF artifact
```

The important product shift is that the first-class input is **context**, not PDF. Context may include PDFs, images, video, audio, documents, code, spreadsheets, databases, web links, prompts, and human review notes. The first-class output is a **target PDF profile**, not a generic PDF.

Target PDF profiles may include:

- Learning PDF.
- Resume PDF.
- Academic paper PDF.
- Research brief.
- PPT/deck-like PDF.
- Business report.
- Board deck.
- Legal review packet.
- Evidence packet.
- Training handout.
- Worksheet.
- Invoice or formal document.
- Code audit report.

Every output PDF should have provenance and evidence. An agent should be able to explain:

- What context was used.
- Which pages, timestamps, images, files, rows, or code ranges support each claim.
- Which operations changed the document.
- Which validations passed or failed.
- Which artifact lineage produced the final PDF.

## Platform pillars

### 1. Context

Accept and normalize many kinds of context before deciding what PDF to produce.

Capabilities:

- Context packets containing PDFs, images, screenshots, scans, videos, audio, web links, Markdown, HTML, Office-like documents, code, spreadsheets, JSON, database results, prompts, and review notes.
- Context classification, deduplication, safety checks, file limits, URL safety, and provenance capture.
- Context understanding that extracts usable signals such as transcripts, keyframes, OCR regions, tables, charts, file/line refs, rows, sections, and citations.
- PDF page inspection, text layer inspection, object inspection, forms, annotations, metadata, links, attachments, signatures, and health checks.
- Layout understanding with page numbers, bboxes, reading order, sections, tables, charts, figures, formulas, images, captions, headers, footers, footnotes, references, and confidence.
- Multimodal source understanding for images, screenshots, scans, video keyframes, audio transcripts, web captures, code repositories, Markdown, HTML, spreadsheets, JSON, and databases.
- Source-aware extraction where every extracted fact carries a source reference.

### 2. Target

Choose the target PDF type, style, structure, audience, and constraints before composing.

Capabilities:

- Target PDF profiles for learning materials, resumes, academic papers, deck-like PDFs, reports, evidence packets, legal packets, technical audits, worksheets, and formal documents.
- Audience and purpose constraints such as study, hiring, academic submission, board review, litigation, training, compliance, sales, or engineering review.
- Style packs, brand kits, layout modes, page size, typography, density, citation style, and validation requirements.
- Output variants such as report + deck, deck + speaker notes, resume + cover letter, paper + presentation, or evidence packet + redacted copy.

### 3. Compose

Compose new PDF artifacts from context packets and target PDF profiles.

Capabilities:

- Context-to-report: turn context packets into business reports, research briefs, legal packets, training handouts, technical reports, audit reports, and board memos.
- Context-to-deck: turn videos, PDFs, code, data, or research materials into slide-like PDF presentations.
- Insert rich blocks: figures, images, charts, code blocks, callouts, tables, equations, appendices, citation pages, and speaker notes.
- Use templates, style packs, brand kits, and layout constraints.
- Produce source maps from generated content back to source graph nodes.

### 4. Operate

Operate on existing PDFs through explicit, auditable actions.

Capabilities:

- Merge, split, reorder, rotate, extract, remove, insert, overlay, watermark, stamp, crop, resize, protect, sanitize, and validate.
- Agentic PDF edits such as insert figure, insert code block, add appendix, rewrite section, generate summary page, add evidence highlights, restyle report, convert report to deck, or regenerate a page from IR.
- Patch transactions that can be previewed, applied, verified, and rolled back.
- Clear refusal modes for unsafe, unsupported, unauthorized, or unverifiable edits.

### 5. Verify

Verify that documents are correct, safe, traceable, and usable.

Capabilities:

- Renderability, page count, blank page detection, file integrity, text layer checks, visual diff, semantic diff, redaction verification, metadata removal checks, accessibility checks, and citation checks.
- Source coverage reports: which claims, charts, tables, sections, and generated paragraphs have source evidence.
- Layout checks: overflow, clipped text, broken code blocks, missing images, unreadable tables, orphan headings, and bad page breaks.
- Transaction reports that summarize what changed, what evidence supports it, and what warnings remain.

### 6. Orchestrate

Run repeatable workflows over individual documents or large batches.

Capabilities:

- Workflow planner, runner, report generator, batch manifests, retries, parallel steps, webhooks, scheduled runs, artifact graph, and audit logs.
- Agent roles such as parser, composer, editor, verifier, reviewer, redactor, citation checker, template designer, and compliance reviewer.
- Local-first execution with optional cloud workers for expensive multimodal, AI, OCR, storage, and high-concurrency workloads.

## Context packet

A context packet is the agent-facing input object. It groups heterogeneous materials and the user's intent before any target PDF is produced.

Context packet example:

```json
{
  "context_id": "ctx_...",
  "goal": "Create a learning PDF and deck-like handout from this product training video and notes.",
  "items": [
    {
      "context_item_id": "ctx_video_001",
      "type": "video",
      "uri": "local://training.mp4",
      "role": "primary_material"
    },
    {
      "context_item_id": "ctx_notes_001",
      "type": "markdown",
      "uri": "local://trainer-notes.md",
      "role": "instructor_notes"
    }
  ]
}
```

Supported context item categories should include:

- PDF.
- Image and screenshot.
- Scan.
- Video.
- Audio.
- Web link or captured page.
- Markdown.
- HTML.
- Office-like document.
- Text.
- Code repository or file.
- Spreadsheet, CSV, or database result.
- JSON or structured data.
- Human-provided prompt or review note.

## Source graph

The source graph is an internal evidence and provenance structure derived from the context packet. It records every input and derived node that contributes to a generated or edited artifact.

Source node example:

```json
{
  "source_id": "src_video_001",
  "type": "video",
  "uri": "local://meeting.mp4",
  "sha256": "...",
  "derived_nodes": [
    {
      "source_id": "src_video_001_transcript_0007",
      "type": "transcript_segment",
      "time_range": ["00:03:12", "00:03:48"],
      "text": "The renewal-risk explanation starts here."
    },
    {
      "source_id": "src_video_001_frame_0012",
      "type": "video_frame",
      "timestamp": "00:03:31",
      "image_artifact_id": "art_frame_0012"
    }
  ]
}
```

Every generated block in a PDF should be able to point back to one or more source refs when evidence exists.

## Target PDF profile

The target PDF profile defines the intended output before composition begins.

```json
{
  "target_profile_id": "target_learning_deck",
  "pdf_type": "learning_pdf",
  "layout_mode": "deck",
  "audience": "new customer-success hires",
  "style_pack": "training_slide_handout",
  "required_blocks": ["cover", "learning_objectives", "slides", "speaker_notes", "quiz", "source_appendix"],
  "citation_policy": "timestamp_and_page_refs",
  "validation_required": ["render_check", "layout_overflow_check", "evidence_coverage_report"]
}
```

Examples:

- `learning_pdf`: lessons, examples, exercises, quizzes, instructor notes.
- `resume_pdf`: profile, skills, work history, portfolio, ATS-friendly formatting.
- `academic_paper_pdf`: abstract, sections, citations, figures, references.
- `deck_pdf`: slide pages, speaker notes, appendix, visual rhythm.
- `business_report_pdf`: executive summary, metrics, findings, recommendations.
- `evidence_packet_pdf`: source exhibits, callouts, OCR/captions, chain of custody.
- `code_audit_pdf`: findings, code blocks, file/line refs, dependency appendix.

## Document and composition IR

Document IR captures what exists in a parsed document or context-derived material. Composition IR captures what should be rendered into a specific target PDF profile.

Composition IR should support:

- `document`
- `section`
- `slide`
- `title`
- `heading`
- `paragraph`
- `list`
- `table`
- `chart`
- `figure`
- `image`
- `caption`
- `formula`
- `code_block`
- `callout`
- `quote`
- `metric_card`
- `timeline`
- `speaker_note`
- `appendix`
- `citation_list`
- `source_ref`
- `review_comment`
- `approval_marker`

Example block:

```json
{
  "id": "blk_summary_003",
  "type": "paragraph",
  "text": "Renewal risk is the largest short-term revenue concern.",
  "source_refs": [
    {
      "source_id": "src_video_001_transcript_0007",
      "locator": {"time_range": ["00:03:12", "00:03:48"]},
      "confidence": 0.86
    },
    {
      "source_id": "src_pdf_002",
      "locator": {"page": 5, "bbox": [72, 144, 520, 210]},
      "confidence": 0.91
    }
  ],
  "layout": {
    "role": "body",
    "keep_with_next": false,
    "max_lines": 5
  }
}
```

## PDF patch transactions

Agents should not perform opaque edits when a structured patch can be used.

Patch examples:

- Insert image after a section.
- Add a code block to an appendix.
- Replace an executive summary.
- Convert a report section into slide pages.
- Add citations and evidence highlights.
- Remove metadata and verify removal.
- Redact sensitive spans and verify true redaction.

Patch transaction shape:

```json
{
  "patch_id": "patch_...",
  "input_artifact_id": "art_source_pdf",
  "operations": [
    {
      "op": "insert_block",
      "target": {"after_block_id": "blk_market_analysis"},
      "block": {
        "type": "figure",
        "title": "Renewal Risk Trend",
        "source_refs": [{"source_id": "src_sheet_004", "locator": {"range": "B2:E9"}}]
      }
    }
  ],
  "validation_required": [
    "pdf.validation.render_check",
    "pdf.validation.visual_diff",
    "pdf.evidence.coverage_report"
  ],
  "rollback": {
    "strategy": "preserve_input_artifact"
  }
}
```

## Agent roles

The platform should describe complex workflows as roles even when the first implementation runs them in one process.

- Context Agent: builds context packets from files, links, prompts, and structured data.
- Parser Agent: converts context items into IR and source graph nodes.
- Evidence Agent: maps claims and blocks to source refs.
- Target Agent: chooses or validates the target PDF profile.
- Composer Agent: turns context packets and target profiles into composition IR.
- Layout Agent: chooses templates, page breaks, slide rhythm, and block placement.
- Editor Agent: creates PDF patch transactions.
- Validator Agent: runs render, diff, citation, safety, accessibility, and layout checks.
- Reviewer Agent: produces human-readable review packets and warnings.
- Redaction Agent: finds, removes, and verifies sensitive content.
- Template Agent: applies style packs, brand kits, and domain templates.
- Workflow Agent: plans, schedules, retries, and reports on multi-step jobs.

## Tool namespace direction

AgentPDF should keep the existing `pdf.*` namespace and add first-class agent-native families.

Recommended families:

- `pdf.context.*`: ingest and normalize PDFs, images, video, audio, web pages, links, code, documents, and data into context packets.
- `pdf.target.*`: choose and validate target PDF profiles such as learning, resume, paper, deck, report, packet, and audit.
- `pdf.evidence.*`: map claims to sources, cite blocks, produce coverage reports, highlight source material.
- `pdf.compose.*`: plan, create, compile, and render composition IR into PDF artifacts.
- `pdf.patch.*`: preview, apply, verify, and roll back structured PDF edits.
- `pdf.present.*`: create slide-like PDF decks, speaker notes, handouts, and appendix packs.
- `pdf.workflow.*`: plan and execute document workflows with roles and validation.
- `pdf.artifacts.*`: inspect artifact lineage, source graph, manifests, checksums, and retention.

RAG tools remain useful, but they are a subset of `pdf.evidence.*`. RAG should not be the top-level product story.

## Open-source versus cloud boundary

The local open-source core should remain useful and trustworthy:

- Deterministic PDF operations.
- Local CLI, MCP, REST, Python, TypeScript, and Docker.
- Local artifact manifests.
- Local validation.
- Local lite parse.
- Local context packet schema.
- Local target PDF profile schema.
- Local source graph schema.
- Local composition IR schema.
- Local Markdown/HTML/JSON/image-to-PDF rendering.
- Local template/style packs.
- Local patch manifests and preview reports where deterministic.

Cloud and optional workers can monetize expensive or operationally complex work:

- Video transcription and keyframe extraction at scale.
- Audio transcription.
- Advanced OCR and handwriting recognition.
- VLM/LLM layout understanding.
- Chart, formula, table, and figure understanding.
- Agentic parse for complex documents.
- Long-running batch workflows.
- Hosted artifact graph and retention.
- Persistent hosted RAG/evidence indexes.
- Brand kits, template gallery, and enterprise templates.
- High-concurrency rendering and composition.
- Enterprise audit logs, SSO/SAML, VPC/on-prem, zero data retention, and compliance controls.

Cloud features must remain additive. Local deterministic tools must not require hosted billing.

## Landing scenario candidates

These scenarios are strong candidates for discussion and prioritization.

### 1. Video/context to learning deck PDF

Input: meeting recording, lecture, webinar, demo, sales call, notes, links, screenshots, or existing PDFs.

Output:

- Learning PDF or slide-like PDF deck.
- Transcript appendix.
- Keyframe pages.
- Speaker notes.
- Timestamp citations.
- Source map.
- Validation report.

Why it matters: visually impressive, easy to demo, and hard to replicate with simple PDF libraries.

### 2. Image evidence packet

Input: photos, screenshots, scans, or field evidence.

Output:

- OCR/captioned report.
- Image pages with callouts.
- Extracted facts with bbox evidence.
- Review checklist.
- Exportable PDF packet.

Why it matters: useful for legal, insurance, construction, healthcare, research, and operations.

### 3. Code context to technical audit PDF

Input: code repo, config files, logs, CI output, API schemas.

Output:

- Architecture summary.
- Risk findings.
- Code snippets with file/line references.
- Dependency/license/security appendix.
- Reviewer-ready PDF.

Why it matters: this fits coding agents naturally and differentiates AgentPDF from parser-only products.

### 4. Existing PDF to reviewed and verified deliverable

Input: contract, report, pitch deck, policy, invoice set, or research paper.

Output:

- Edited or reorganized PDF.
- Evidence highlights.
- Redaction verification.
- Visual diff.
- Change report.
- Review packet.

Why it matters: this is the core PDF Agent Operator use case.

### 5. Multi-context business report

Input: PDFs, spreadsheets, charts, screenshots, notes, and web pages.

Output:

- Polished business report.
- Board deck PDF variant.
- Appendix with source tables and screenshots.
- Claim/source coverage report.

Why it matters: high willingness to pay for teams and SaaS workflows.

### 6. Research paper to cited deck and literature brief

Input: one or more papers.

Output:

- Literature summary PDF.
- Slide-like presentation PDF.
- Claim citations with page/bbox.
- Figure/table extraction.
- Related-work matrix.

Why it matters: researchers, analysts, students, and agents need this repeatedly.

### 7. Training material generator

Input: video, SOP, policy PDF, screenshots, product docs, or code examples.

Output:

- Training handout.
- Slide PDF.
- Exercises/worksheet.
- Instructor notes.
- Quiz appendix.

Why it matters: converts messy internal knowledge into distributable artifacts.

### 8. Compliance and redaction packet

Input: sensitive document set.

Output:

- Redacted PDFs.
- Redaction verification.
- Metadata removal report.
- Audit log.
- Reviewer signoff packet.

Why it matters: strong enterprise value and clear safety requirements.

## Commercial implication

The strongest monetization is not basic PDF operations. It is the hosted version of expensive, high-trust workflows:

- Multimodal context processing.
- Agentic parse, target PDF profiling, and source graph creation.
- High-quality composition and rendering.
- Evidence coverage and citation verification.
- Batch workflow orchestration.
- Persistent artifact graph.
- Enterprise review, audit, retention, and deployment controls.

This supports a credible OSS-to-cloud path:

1. Developers adopt the local toolchain because it is useful.
2. Agents integrate through CLI, MCP, REST, and SDKs.
3. Teams hit limits around multimodal processing, batch, retention, and enterprise controls.
4. Hosted AgentPDF sells convenience, scale, quality, and compliance without weakening the local core.

## Roadmap guidance

The product should not try to implement every advanced capability immediately. It should make the architecture ready from day one.

Near-term local priorities:

1. Keep deterministic PDF tools and validation polished.
2. Add context packet, target PDF profile, source graph, and composition IR schemas.
3. Make style packs support richer target PDF profiles such as learning PDFs, resumes, papers, deck PDFs, reports, packets, and audit PDFs.
4. Add workflow recipes for context-to-PDF, PDF patch, evidence packet, and presentation PDF.
5. Add local deterministic examples that prove the model without cloud dependency.

Mid-term priorities:

1. Structured patch transactions.
2. Artifact lineage and source map reports.
3. Better local layout, table, image, and citation handling.
4. Batch workflow engine with retries and richer bindings.
5. Optional worker contracts for OCR, video, audio, vision, and advanced parse.

Cloud priorities:

1. Hosted agentic parse with strong evidence output.
2. Video/image/audio-to-PDF pipelines.
3. Hosted context packet, source graph, and artifact graph.
4. High-concurrency batch workflows.
5. Enterprise audit, retention, security, and deployment controls.

## Quality bar

AgentPDF should feel different from a PDF library because every serious operation returns evidence.

Every agent-native tool should return:

- `job_id`
- `status`
- `tool`
- `artifacts`
- `context`
- `target_profile`
- `source_graph_delta`
- `patch_manifest` when applicable
- `validation`
- `warnings`
- `usage`
- `next_recommended_tools`

Generated PDFs should be validated. Generated claims should be source-mapped where possible. Unsafe or unverifiable operations should be explicit about their limits.
