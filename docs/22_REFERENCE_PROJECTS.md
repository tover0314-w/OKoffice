# 22 - Reference Projects To Study

These projects and skills inspire different parts of okoffice.

Do not blindly copy code. Study product surface, UX, docs, architecture, verification loops, agent ergonomics, and licensing.

## Agent-native Office Tooling

- OfficeCLI: single-binary agent surface for `.docx`, `.xlsx`, and `.pptx`; JSON output; MCP server; schema-driven help; DOM operations; raw XML fallback; HTML/screenshot/watch preview loop; specialized skills for Word, Excel, PowerPoint, dashboards, financial models, pitch decks, academic papers, and animated decks. Source: [iOfficeAI/OfficeCLI](https://github.com/iOfficeAI/OfficeCLI).
- Codex Documents skill: DOCX creation/editing discipline, render-to-PNG QA, style presets, table geometry, comments, redlines, metadata/privacy, accessibility, and Google Docs import workflow.
- Codex Spreadsheets skill: workbook/dashboard creation, formulas, charts, tables, data validation, rendering, formula-error scans, and analyst-grade layout conventions.
- Codex Presentations skill: claim spine, deck profiles, proof objects, HTML/contact-sheet QA, template-following mode, rendered slide checks, source notes, and final PPTX export discipline.

## Core PDF Engines And Utilities

- pypdf: pure-Python structure operations and license-safe local core.
- qpdf: validation, repair, linearization, encryption semantics, and diagnostics.
- pdfcpu: broad command/API coverage for validation, optimization, stamps, watermarks, permissions, and attachments.
- Apache PDFBox: mature preflight, extraction, and Java ecosystem patterns.

## Page Object, Geometry, And Browser Rendering

- pdfplumber: page objects, bboxes, tables, visual debugging.
- PyMuPDF: high-performance geometry, rendering, annotations, text spans. Keep behind explicit optional boundaries because of license/commercial constraints.
- PDF.js: browser rendering and viewer model.
- pdf-lib: TypeScript developer ergonomics for creation/edit primitives.

## Office And OOXML Concepts To Study

- Open XML SDK patterns: schema validation, package parts, relationships, typed elements, and element order.
- LibreOffice headless conversion: useful for optional preview/export, but must be treated as a worker with renderer-specific caveats.
- python-docx / python-pptx / openpyxl: useful ecosystem references, but not a complete agent-native workflow surface by themselves.

## Open-source + Cloud Monetization

- Firecrawl: open-source web data infrastructure, API-first, MCP-friendly, free quota and paid cloud credits.
- Marker: document conversion with managed platform and open-source components.
- Unstructured: OSS preprocessing plus hosted/platform features.

## Parsing And Document Understanding

- LlamaParse / LiteParse pattern: cloud agentic parse vs local-first lite parse.
- Docling: document understanding and structured export.
- Marker: PDF/document to Markdown/JSON/chunks.
- PyMuPDF4LLM: lightweight document-to-Markdown style extraction.

## Full Utility Coverage

- iLovePDF and PDF24: PDF tool category coverage benchmark.
- Stirling PDF: open-source PDF utility platform and workflow reference.
- Microsoft Office / Google Workspace mental model: documents, spreadsheets, presentations, comments, revisions, collaboration, export, and templates.

## OCR And Scanned Documents

- OCRmyPDF: OCR pipeline, sidecar text, skipped-page warnings, optimization, and validation discipline.

## Translation And Scientific PDFs

- PDFMathTranslate.
- BabelDOC.

## Interaction And Annotation Inspiration

- Kami-like PDF annotation and education workflows.
- Office document review workflows: comments, tracked changes, sheet comments, slide comments, and review packets.

## How To Use This List

The okoffice direction is higher level than any one reference. Low-level Office DOM tools are workers. The product moat is the agent-native workflow layer:

```text
context -> source graph -> extraction -> workbook/model -> report/deck/PDF -> validation -> bundle
```
