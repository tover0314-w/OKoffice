# Reference Project Synthesis

This document turns the "learn from the best Office/PDF projects" requirement into concrete okoffice design decisions. The goal is to borrow product surface, architecture, safety posture, and workflow ideas without copying code or pulling restrictive dependencies into the default OSS core.

## Projects and Skills Studied

| Reference | What To Borrow | Dependency Stance |
|---|---|---|
| [OfficeCLI](https://github.com/iOfficeAI/OfficeCLI) | Single-binary Office operations, DOCX/XLSX/PPTX read/create/modify, JSON output, schema-driven help, MCP server, resident mode, and L1/L2/L3 abstraction. | Study deeply; do not vendor blindly. |
| [Microsoft Office Agent](https://techcommunity.microsoft.com/blog/microsoft365copilotblog/office-agent-%E2%80%93-%E2%80%9Ctaste-driven%E2%80%9D-multi-agent-system-for-microsoft-365-copilot/4457397) | Taste-driven multi-agent deck creation, HTML5 slide intermediate artifacts, iterative visual review, and editable PowerPoint export. | Product/architecture signal only; do not depend on Microsoft-hosted agents. |
| Codex Documents skill | DOCX render-and-inspect workflow, design presets, comments/redlines, metadata/privacy checks, and accessibility expectations. | Internal workflow reference. |
| Codex Spreadsheets skill | Workbook creation discipline, formula correctness, dashboard quality, visual inspection, and zero formula-error bar. | Internal workflow reference. |
| Codex Presentations skill | Claim spine, deck profiles, proof objects, contact-sheet QA, rendered previews, and template-following discipline. | Internal workflow reference. |
| [pypdf](https://github.com/py-pdf/pypdf) | Pure-Python PDF structure operations: merge, split, rotate, metadata, encryption-aware errors. | Default core dependency is acceptable after review. |
| [qpdf](https://github.com/qpdf/qpdf) | Validation, repair, linearization, encryption/decryption semantics, CLI-quality diagnostics. | Study design; optional worker if needed. |
| [pdfcpu](https://github.com/pdfcpu/pdfcpu) | Broad CLI/API coverage: validate, optimize, stamp, watermark, permissions, attachments. | Study tool map and UX; do not vendor. |
| [Apache PDFBox](https://pdfbox.apache.org/) | Mature Java operations, preflight, text extraction, PDF/A thinking. | Optional integration only. |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Page/object model, table extraction baseline, bbox-first debugging, visual overlays. | Candidate optional parser worker after license review. |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | High-performance rendering, text spans, annotations, page geometry. | Not default core because of AGPL/commercial boundary; optional explicit worker only. |
| [OCRmyPDF](https://ocrmypdf.readthedocs.io/) | Pipeline discipline for OCR, deskew/clean/optimize, sidecar text, skipped-page warnings. | Optional OCR worker; document native tools carefully. |
| [Docling](https://github.com/docling-project/docling) | AI-ready document conversion, structured IR, Markdown/JSON export, chunking. | Study IR/chunking architecture; optional worker later. |
| [Marker](https://github.com/VikParuchuri/marker) | PDF-to-Markdown/JSON/chunks, model-assisted paths, practical document QA examples. | Study UX and pipeline shape; license/dependency review before optional integration. |
| [Stirling-PDF](https://github.com/Stirling-Tools/Stirling-PDF) | Self-hosted product breadth, workflows, approachable docs, full utility coverage. | Study product surface and deployment ergonomics. |
| [Firecrawl](https://github.com/mendableai/firecrawl) | OSS agent-infra plus hosted API packaging, docs, SDKs, and SaaS motion. | Business/product reference for cloud boundary, not a document dependency. |

## okoffice Synthesis

okoffice should become a local-first tool layer with:

- OfficeCLI-style schema-driven Office operations.
- PDF utility breadth and safety from mature PDF tools.
- Source Graph and Office IR for cross-format reasoning.
- Codex skill-inspired quality gates for Word, Excel, and PowerPoint.
- Agent-first outputs: JSON, artifacts, validation, warnings, usage, citations, and next recommended tools.

The key difference from classic document libraries is the output contract. okoffice is not just a Python API for editing files. It is infrastructure that lets agents safely plan, produce, inspect, validate, cite, and patch Office artifacts.

## Capability Pillars

### 1. Office Package Core

Borrow from OfficeCLI:

- Treat DOCX/XLSX/PPTX as package formats with relationships, content types, and stable internal locators.
- Expose L1 read APIs for summaries and structured facts.
- Expose L2 DOM-style edit APIs for common document changes.
- Keep L3 raw XML/package escape hatches explicit and advanced.
- Provide schema-driven tool help and contract tests.
- Support resident/server mode for agent workflows.

Target baseline:

- `office.inspect.file`
- `word.inspect.document`
- `sheet.inspect.workbook`
- `deck.inspect.presentation`
- `office.validation.package`

### 2. Word Quality

Borrow from the Documents skill:

- Do not blindly ship DOCX artifacts.
- Render or inspect previews when possible.
- Preserve named styles.
- Handle comments/redlines deliberately.
- Check metadata and privacy.
- Treat accessibility as part of document quality.

Target tools:

- `word.create.document`
- `word.extract.tables`
- `word.patch.apply`
- `word.validation.document`

### 3. Excel Quality

Borrow from the Spreadsheets skill:

- Workbooks need formulas, checks, and meaningful layouts.
- Dashboards should be readable and visually inspected.
- Formula errors are completion blockers.
- Tables/charts need explicit source ranges.

Target tools:

- `sheet.write.workbook`
- `sheet.extract.tables`
- `sheet.validation.formulas`
- `sheet.review.model`

### 4. PowerPoint Quality

Borrow from the Presentations skill and Microsoft Office Agent's taste-driven deck pattern:

- Decks need a claim spine.
- Slides should be proof objects, not decorative summaries.
- HTML slide packages should be the inspectable visual source layer before editable PPTX export when the worker path is available.
- Contact-sheet QA is a first-class validation step.
- Speaker notes and source refs matter for agent-built decks.
- Direct outline-to-PPTX writing is a useful local fallback, not the long-term quality ceiling.

Target tools:

- `deck.create.presentation`
- `deck.compose.plan`
- `deck.validation.presentation`
- `deck.render.html`
- `deck.export.pptx`
- `deck.validation.html_preview`
- `deck.validation.contact_sheet`
- `deck.review.story`

### 5. PDF Domain

Borrow from pypdf, qpdf, pdfcpu, pdfplumber, OCRmyPDF, Docling, Marker, and Stirling-PDF:

- Never mutate inputs.
- Always emit a new artifact.
- Validate generated PDFs.
- Preserve page counts and explicit page ranges.
- Prefer page numbers and bboxes over plain text-only output.
- Keep OCR and heavy parse workers optional.

Current baseline:

- `pdf.inspect.document`
- `pdf.inspect.pages`
- `pdf.organize.merge`
- `pdf.organize.split`
- `pdf.validation.render_check`
- `pdf.validation.blank_page_check`
- `pdf.ai.parse.lite`
- `pdf.ai.rag.*`
- `pdf.ai.create.*`

### 6. Cross-Format Workflows

The flagship workflows should be:

- Multiple Word/PDF sources to cited Excel workbook.
- Excel workbook to executive PowerPoint deck.
- Word memo plus workbook plus deck to PDF handout.
- Bundle export/verify with manifest, source map, validation, and warnings.

These workflows are where okoffice becomes more than "OfficeCLI plus PDF tools".

## License Boundary Rules

- Default dependencies must remain permissive or compatible with Apache-2.0 distribution.
- GPL/AGPL/commercial-boundary tools can inspire architecture but must not become default dependencies.
- Optional workers must be named explicitly, documented with license notes, and gated by install extras or feature flags.
- Do not copy implementation code from reference projects without a license review.

## Implementation Order From This Synthesis

1. Preserve current `pdf.*` behavior and tests.
2. Add okoffice naming, docs, and manifest scaffolding.
3. Add Office package inspection for DOCX/XLSX/PPTX.
4. Add Source Graph and Office IR across PDF/Word/Excel/PowerPoint.
5. Add validation tools for Word, Excel, and PowerPoint.
6. Add `office.workflow.docset_to_sheet`.
7. Add `office.workflow.sheet_to_deck`.
8. Add `office.bundle.export` and `office.bundle.verify`.
9. Add optional workers for OCR, render previews, conversion, formula evaluation, and agentic parse.
10. Add hosted packaging only after the local OSS surface is credible.
