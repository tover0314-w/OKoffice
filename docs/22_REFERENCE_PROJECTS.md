# Reference Projects to Study

These projects inspire different parts of AgentPDF Infra.

See `docs/33_REFERENCE_PROJECT_SYNTHESIS.md` for the concrete design decisions derived from these references.

## Core PDF engines and utilities

- pypdf: pure-Python structure operations and license-safe local core.
- qpdf: validation, repair, linearization, encryption semantics, and diagnostics.
- pdfcpu: broad command/API coverage for validation, optimization, stamps, watermarks, permissions, and attachments.
- Apache PDFBox: mature preflight, extraction, and Java ecosystem patterns.

## Page object, geometry, and browser rendering

- pdfplumber: page objects, bboxes, tables, visual debugging.
- PyMuPDF: high-performance geometry, rendering, annotations, text spans. Keep behind explicit optional boundaries because of license/commercial constraints.
- PDF.js: browser rendering and viewer model.
- pdf-lib: TypeScript developer ergonomics for creation/edit primitives.

## Open-source + cloud monetization

- Firecrawl: open-source web data infrastructure, API-first, MCP-friendly, free quota and paid cloud credits.
- Marker: document conversion with managed platform and open-source components.
- Unstructured: OSS preprocessing plus hosted/platform features.

## Parsing and document understanding

- LlamaParse / LiteParse pattern: cloud agentic parse vs local-first lite parse.
- Docling: document understanding and structured export.
- Marker: PDF/document to Markdown/JSON/chunks.
- PyMuPDF4LLM: lightweight document-to-Markdown style extraction.

## Full PDF utility coverage

- iLovePDF and PDF24: tool category coverage benchmark.
- Stirling PDF: open-source PDF utility platform and workflow reference.

## OCR and scanned documents

- OCRmyPDF: OCR pipeline, sidecar text, skipped-page warnings, optimization, and validation discipline.

## Translation and scientific PDFs

- PDFMathTranslate.
- BabelDOC.

## Interaction and annotation inspiration

- Kami-like PDF annotation and education workflows.

## How to use this list

Do not blindly copy code. Study product surface, UX, docs, architecture, and licensing. Maintain AgentPDF's agent-first positioning.
