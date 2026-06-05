# 02 - Open-source Scope

## Open-source Edition Goals

The open-source edition of okoffice should be genuinely useful without cloud services.

It should include:

- CLI.
- MCP server.
- Local REST API.
- Python SDK foundation.
- TypeScript/Node SDK.
- Docker/self-hosting path.
- Tool registry.
- Deterministic PDF operations from the current harness.
- Deterministic Office inspect/extract/create/validate paths as they are added.
- Context packet, source graph, Office IR, composition IR, patch manifest, artifact manifest, and validation models.
- Lite parse and local evidence/RAG demos.
- Cross-document workflow recipes.
- Example integrations.
- Complete documentation.

The open-source core should make developers believe the larger agent-native Office platform is real before hosted workers exist.

## Current Compatibility Scope

The existing implementation exposes `pdf.*` tools through compatibility names. These remain valid during migration, but they are not the okoffice product identity.

Compatibility rules:

- Keep `pdf.*` stable while introducing okoffice docs and future `office.*` aliases.
- Do not remove `okoffice` imports until compatibility entrypoints exist.
- Treat PDF as the first implemented okoffice domain.
- Document gaps honestly instead of pretending DOCX/XLSX/PPTX behavior is already complete.

## Open-source Deterministic Tools

These should be implemented first and remain free/local.

PDF:

- Inspect documents and pages.
- Read/update/remove metadata.
- Merge, split, extract, remove, reorder, rotate pages.
- Render pages to images.
- Convert image/Markdown/HTML/text/JSON to PDF where deterministic.
- Convert PDF to images/text/Markdown/JSON where supported.
- Watermark, page numbers, crop/resize, compression, repair.
- Authorized protect/unlock/decrypt.
- Redaction and verification where safe.
- Output validation.

Word:

- Inspect `.docx` structure, metadata, outline, sections, tables, comments, revisions, fields, headers, footers, and safety markers.
- Extract text and source locators.
- Create simple reports and memos from structured IR.
- Apply non-mutating patch transactions.
- Validate schema/structure, placeholder leakage, field presence, and preview evidence when available.

Excel:

- Inspect workbook sheets, dimensions, tables, formulas, named ranges, pivots, charts, comments, and safety markers.
- Extract data profiles and source locators.
- Create workbooks from structured data with formulas, tables, charts, and validation notes.
- Detect formula errors, placeholder leakage, `###` truncation, and suspicious cached values when possible.

PowerPoint:

- Inspect slide inventory, shapes, charts, tables, notes, media, comments, and safety markers.
- Extract slide text and source locators.
- Compose deck plans from storyboard/composition IR.
- Render self-contained HTML slide preview packages before PPTX export where the local route is available.
- Create simple editable decks from storyboard/composition IR as deterministic fallback.
- Validate HTML preview packages, slide order, bounds, text overflow, notes coverage, placeholder leakage, and preview evidence when available.

Bundles:

- Export portable artifact bundles with files, manifests, source maps, validations, and checksums.
- Verify bundle manifests before downstream agent use.

## Open-source Agent-native Baseline

These capabilities should exist locally as schemas, manifests, deterministic tools, examples, or lightweight implementations:

- Context packet model for PDFs, Word docs, Excel workbooks, PowerPoint decks, images, scans, video, audio, links, text, Markdown, HTML, code, CSV/JSON, and manually supplied prompts/review notes.
- Target artifact profile model for Word reports, Excel models, PowerPoint decks, PDF packets, board packs, evidence workbooks, research briefs, training handouts, and audit bundles.
- Source graph model for provenance and evidence refs derived from context packets.
- Artifact lineage model linking inputs, outputs, validations, manifests, previews, and reports.
- Office IR for parsed PDFs, Word documents, workbooks, decks, code/data sources, and generated artifacts.
- Composition IR for reports, workbooks, decks, packets, appendices, and bundles.
- Local style packs/templates for headings, tables, charts, figures, code blocks, callouts, citations, appendices, sheets, dashboards, and slides.
- Patch transaction manifests for planned edits across supported formats.
- Workflow recipes that show inspect -> extract/model/compose/operate -> verify -> report.
- Evidence reports that map claims, cells, slides, charts, and generated blocks back to source refs when available.

The local version may use simple heuristics and deterministic rendering. It should still expose the shape of the larger platform.

## Open-source AI-lite Tools

These should work locally without paid models:

- Lite parse using text layers and simple layout heuristics.
- Chunking.
- Keyword/embedding-optional retrieval.
- Evidence search returning citations.
- RAG demo returning source citations.
- Template-based document, workbook, deck, and PDF creation where deterministic.
- HTML-first deck preview packages with direct PPTX fallback where deterministic.
- Rule-based sensitive-data detection baseline.
- Local context packet examples for document/image/text/Markdown/code/data/link inputs.

RAG is a support capability, not the product center. The broader local goal is evidence-backed Office artifact assembly and verification.

## Optional Workers

Optional workers may power richer Office operations, but they must be explicit:

- OfficeCLI or another OOXML worker for `.docx`, `.xlsx`, and `.pptx` DOM operations.
- LibreOffice or document renderers for PDF export/preview.
- Browser renderers for HTML/source-package output and deck contact sheets.
- HTML-to-PPTX export workers.
- OCR engines.
- VLM/model workers.

Optional workers need:

- Feature flag or install extra.
- Dependency and license note.
- Capability detection.
- Structured unavailable-worker error.
- No silent cloud fallback.

## Future Hosted Or Advanced Features

These may be cloud-only or paid:

- Agentic Office parse.
- VLM OCR and advanced image understanding.
- Advanced table/chart/formula reconstruction.
- Video transcription and keyframe extraction.
- Audio transcription.
- Web capture at scale.
- AI translation.
- AI document/deck/workbook generation from prompts.
- AI editing/regeneration.
- Hosted context packet, source graph, artifact graph, and vector/evidence indexes.
- Managed rendering.
- Batch processing at scale.
- Persistent artifacts.
- Audit logs.
- Team management.
- SSO/SAML.
- Zero data retention.
- Enterprise VPC/on-prem.

## Boundary Rule

Open-source code may include interfaces, schemas, manifests, examples, and stubs for hosted features, but it must never require the hosted cloud service for deterministic local tools.

If a tool requires cloud, expose it as a separate `cloud_only` or optional-worker tool rather than hiding it behind the same deterministic command.

## Feature Status Labels

Every tool and doc page should label features as:

- `stable`
- `beta`
- `experimental`
- `planned`
- `cloud_only`

## Default License Stance

Use Apache-2.0 for the core project unless maintainers decide otherwise. Avoid copyleft dependencies in default install.

Optional workers must be named explicitly, documented with license notes, and gated by install extras or feature flags.
