# Agent Infra, Context-to-PDF, AI PDF, and Cloud Strategy

This document captures the product direction for okpdf after the local OSS core. The project is agent infrastructure first: local, open-source, and free by default, with a future hosted cloud service that can monetize expensive AI, OCR, multimodal context processing, storage, batch, verification, and workflow features.

## Product Thesis

okpdf should become the PDF operating layer for agents. A coding or workflow agent should be able to inspect, transform, validate, understand, cite, compose, edit, present, and route PDFs without inventing one-off scripts for each repository or business process.

The local edition must stay useful without cloud billing. The hosted product can add Firecrawl-style convenience, scale, persistence, API keys, free quotas, and paid plans around resource-heavy work.

The bigger product loop is:

```text
context packet + target PDF profile -> understanding -> composition plan -> render/patch -> verify -> evidence-backed PDF artifact
```

RAG is useful, but it is not the product center. RAG is one evidence service inside a larger agent-native document infrastructure platform.

## Five Capability Layers

### 1. Basic PDF tools

- Inspect, merge, split, extract, remove, reorder, rotate, insert blank pages.
- Page-level inspection with geometry, text-layer, image-count, and render evidence.
- Convert image/text/Markdown/HTML/JSON to PDF.
- Render pages, extract text and embedded images, read/update/remove metadata.
- Validate parseability, page count, renderability, and blank pages.

### 2. Advanced PDF tools

- Compress, repair, optimize, crop/resize, n-up/booklet, attachments, forms, annotations, PDF/A, security, redaction verification, visual diff.
- Keep this deterministic layer license-safe and local-first.
- Current local baseline includes content-stream compression and parseable PDF repair/rewrite; deeper repair diagnostics remain a future optional worker.

### 3. Intelligence and evidence tools

- Parse to Document IR with page numbers, bboxes, spans, tables, images, formulas, charts, figures, and layout evidence.
- Chat with PDFs using cited retrieval when useful, but treat answers as evidence artifacts rather than the whole product.
- Current local baseline includes one-shot PDF chat with answer, citations, cited report PDF, and highlighted source PDF artifacts.
- Understand image-heavy pages, charts, math/LaTeX, tables, handwriting/scans, and mixed-language documents through optional local or cloud workers.
- Map generated claims, paragraphs, charts, figures, and code snippets back to source refs.
- Produce citation and source coverage reports.

### 4. Context-to-PDF composition and operation tools

- Create new PDFs from context packets, target PDF profiles, prompts, templates, style packs, colors, themes, brand constraints, and structured data.
- Turn videos, audio, images, web links/captures, documents, code, spreadsheets, and PDFs into learning PDFs, resumes, papers, reports, evidence packets, training handouts, and slide-like PDF presentations.
- Edit existing PDFs through explicit, evidence-backed operations.
- Use patch transactions for insertions, replacements, appendices, highlights, overlays, redactions, and page regeneration.
- Avoid claims of perfect layout-preserving arbitrary body text edits.

### 5. Agent workflow tools

- Agent-readable planning tools: inspect -> understand -> compose/operate -> validate -> report.
- Multi-agent roles for complex workflows: parser, evidence mapper, composer, layout planner, editor, verifier, reviewer, redactor, template designer, citation checker.
- Durable workflow manifests for batch operations and audit trails.
- Context packets, target PDF profiles, source graph, artifact graph, source maps, validation reports, and rollback manifests.
- MCP, REST, CLI, TypeScript SDK, and future wrappers for broader agent ecosystems.
- Current local baseline includes `pdf.workflow.plan`, which returns ordered tool steps, agent roles, validation expectations, and explicit cloud-boundary notes.
- Current local baseline also includes `pdf.workflow.run`, which executes supported local tools in order and returns per-step evidence for agents.
- Current local baseline includes `pdf.workflow.report`, which turns workflow runs into structured audit summaries and optional Markdown artifacts.

## Local-First Implementation Priority

Finish local development before cloud expansion:

1. Make Docker, CLI, REST, MCP, and Node SDK easy to run locally.
2. Complete deterministic PDF utility breadth.
3. Improve local Document IR, parse-lite, evidence search/query, and citation output.
4. Add context packet, target PDF profile, source graph, composition IR, source map, artifact graph, and patch manifest schemas.
5. Add local deterministic examples for context-to-report, code-context-to-audit, image packet, learning PDF, resume PDF, paper PDF, and slide-like PDF rendering.
6. Add optional worker contracts for newer parsers, OCR engines, video/audio processors, and vision tools.
7. Add cloud APIs only after the local contract is stable.

## First Agent Ecosystem Targets

1. Claude Code / Claude Desktop through MCP stdio and streamable HTTP.
2. Codex and Cursor through AGENTS.md, CLI, REST, and MCP examples.
3. KiloCode, OpenCode/OpenClaw-style skill ecosystems, OpenAI Agents, LangChain, LlamaIndex, n8n, Zapier, and Make.
4. Hosted API and frontend integrations after local agent workflows are credible.

## Cloud Service Boundary

The OSS core should never require hosted billing. Cloud should provide:

- Free quota for trying agentic parse, OCR, hosted evidence indexes, context-to-PDF composition, and template generation.
- Paid tiers for high page volume, model tokens, advanced OCR, video/audio/image processing, batch concurrency, long retention, team/org features, webhooks, and enterprise controls.
- BYOK mode when users want to pay model providers directly.
- Platform-margin mode for managed model routing and hosted convenience.

Paid features should be additive services, not hidden dependencies of local deterministic tools.

## Reference Projects To Study

These projects should guide architecture and product taste, not be copied blindly:

- Firecrawl: OSS plus hosted API positioning for agents.
- pdf-craft: modern OCR/PDF-to-Markdown thinking, including formulas and tables.
- LiteParse: local-first spatial document parsing and AI-ready layout output.
- Docling and Marker: Document IR, Markdown/JSON/chunk export, and parsing pipelines.
- OCRmyPDF: pipeline discipline, skipped-page warnings, sidecar text, and validation.
- pdfplumber/PyMuPDF/PDF.js: page object, bbox, rendering, and viewer mental models.
- KiloCode, Claude Code, OpenAI Agents, and OpenCode/OpenClaw-style tools: agent ecosystem integration patterns.
- Karpathy-style research/wiki projects: source-grounded synthesis, citations, iterative exploration, and user-facing knowledge artifacts.
- Notebook/video-to-doc and meeting-summary products: inspiration for context-to-presentation workflows, not architecture to copy blindly.

## AI PDF Roadmap

Implemented local baseline:

- Local Document IR from text-layer PDFs.
- JSON and Markdown export with page/bbox evidence.
- Local RAG ingest/query/search with citations.
- Highlighted source PDFs from local RAG citations.

Near-term local:

- Improve IR segmentation into headings, paragraphs, lists, tables, images, and formulas placeholders.
- Add source-highlighting reports and local Q&A export PDFs.
- Add context packet, target PDF profile, source graph, and composition IR schemas.
- Add local style blocks for code, figures, citations, appendices, and slide pages.
- Add deterministic context-to-PDF examples.

Optional worker layer:

- OCR worker contract.
- Table/formula parser contract.
- Vision parser contract for scanned/image-heavy PDFs.
- Video transcription and keyframe worker contract.
- Audio transcription worker contract.
- Local model/BYOK/cloud routing config.

Cloud later:

- Agentic parse API.
- PDF chat with persistent hosted evidence indexes.
- Video/image/audio/document/code/link context-to-PDF pipelines.
- Template gallery and SEO-friendly template pages.
- PDF creation from context packets, target profiles, templates, colors, brand kits, and data.
- PDF edit workflows with previews, validation, and rollback manifests.
- Hosted context packet, source graph, and artifact graph.

## Multi-Agent Architecture Sketch

```mermaid
flowchart LR
  A["User / Agent"] --> B["PDF Workflow Planner"]
  B --> C["Parser Agent"]
  B --> D["Evidence Agent"]
  B --> E["Composer Agent"]
  B --> F["Editor Agent"]
  B --> G["Validator Agent"]
  B --> H["Reviewer Agent"]
  C --> I["Document IR"]
  D --> J["Source Graph + Citations"]
  E --> K["Composition IR"]
  F --> L["Patch Manifest + New PDF"]
  G --> M["Validation Reports"]
  H --> N["Review Packet + Warnings"]
  I --> B
  J --> E
  K --> F
  L --> G
  M --> A
  N --> A
```

Every agent action must produce structured evidence: artifacts, source refs, page numbers, bboxes, timestamps, file/line refs, validation checks, warnings, and next recommended tools.
