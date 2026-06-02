# Reference Project Synthesis

This document turns the "learn from the best PDF projects" requirement into concrete AgentPDF design decisions. The goal is to borrow product surface, architecture, safety posture, and workflow ideas without copying code or pulling restrictive dependencies into the default OSS core.

## Projects Studied

| Project | What To Borrow | Dependency Stance |
|---|---|---|
| [pypdf](https://github.com/py-pdf/pypdf) | Pure-Python PDF structure operations: merge, split, rotate, metadata, encryption-aware errors. | Default core dependency is acceptable. |
| [qpdf](https://github.com/qpdf/qpdf) | Validation, repair, linearization, encryption/decryption semantics, CLI-quality diagnostics. | Study design; optional worker if needed. |
| [pdfcpu](https://github.com/pdfcpu/pdfcpu) | Broad CLI/API coverage: validate, optimize, stamp, watermark, permissions, attachments. | Study tool map and UX; do not vendor. |
| [Apache PDFBox](https://pdfbox.apache.org/) | Mature Java operations, preflight, text extraction, PDF/A thinking. | Optional integration only. |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | Page/object model, table extraction baseline, bbox-first debugging, visual overlays. | Candidate optional parser worker after license review. |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | High-performance rendering, text spans, annotations, page geometry. | Not default core because of AGPL/commercial boundary; optional explicit worker only. |
| [OCRmyPDF](https://ocrmypdf.readthedocs.io/) | Pipeline discipline for OCR, deskew/clean/optimize, sidecar text, skipped-page warnings. | Optional OCR worker; document native tools such as Ghostscript carefully. |
| [Docling](https://github.com/docling-project/docling) | AI-ready document conversion, structured IR, Markdown/JSON export, chunking. | Study IR/chunking architecture; optional worker later. |
| [Marker](https://github.com/VikParuchuri/marker) | PDF-to-Markdown/JSON/chunks, model-assisted paths, practical document QA examples. | Study UX and pipeline shape; license/dependency review before optional integration. |
| [pdf-craft](https://github.com/oomol-lab/pdf-craft) | Newer OCR-oriented PDF to Markdown workflows, with formulas/tables as first-class quality targets. | Study parser/OCR workflow shape; optional worker only after dependency review. |
| [LiteParse](https://github.com/run-llama/liteparse) | Local spatial parsing and AI-ready layout output. | Study IR/bbox ergonomics and local deployment expectations. |
| [Stirling-PDF](https://github.com/Stirling-Tools/Stirling-PDF) | Self-hosted product breadth, workflows, approachable docs, full utility coverage. | Study product surface and deployment ergonomics. |
| [pdf-lib](https://github.com/Hopding/pdf-lib) | TypeScript developer ergonomics and simple create/edit primitives. | Do not duplicate local core; inspire SDK ergonomics. |
| [PDF.js](https://github.com/mozilla/pdf.js) | Browser rendering/viewer integration and page viewport model. | Future frontend/viewer layer, not core processing. |
| [Firecrawl](https://github.com/mendableai/firecrawl) | OSS agent-infra plus hosted API packaging, docs, SDKs, and SaaS motion. | Business/product reference for cloud boundary, not a PDF dependency. |

## AgentPDF Synthesis

AgentPDF should become a local-first tool layer with the breadth of Stirling-PDF/pdfcpu, the structural safety of pypdf/qpdf, the bbox and page-object mindset of pdfplumber/PyMuPDF, and the IR/chunk/RAG workflow of Docling/Marker.

The key difference is the output contract: every capability must return agent-readable JSON with artifacts, validation, warnings, usage, citations, and next recommended tools.

## Capability Pillars

### 1. Structural PDF Core

Borrow from pypdf, qpdf, and pdfcpu:

- Never mutate inputs.
- Always emit a new artifact.
- Validate generated PDFs.
- Preserve page counts and explicit page ranges.
- Return stable error codes for encrypted, malformed, unsupported, unsafe, and unimplemented operations.

Implemented baseline:

- `pdf.inspect.pages`
- `pdf.organize.reorder_pages`
- `pdf.organize.insert_blank_pages`
- `pdf.validation.render_check`
- `pdf.validation.blank_page_check`
- `pdf.optimize.compress`
- `pdf.optimize.repair`
- `pdf.convert.extract_images`
- `pdf.workflow.plan`
- `pdf.workflow.run`
- `pdf.workflow.report`

Near-term tools:

- `pdf.security.remove_metadata`

### 2. Page Object and BBox Model

Borrow from pdfplumber and PyMuPDF:

- Treat every extracted item as page-scoped.
- Prefer page numbers and bboxes over plain text-only output.
- Include coordinate origin and bbox precision in IR metadata.
- Return partial warnings when spans, tables, or bboxes are heuristic.

Near-term tools:

- `pdf.ai.parse.lite`
- `pdf.convert.pdf_to_json`
- `pdf.ai.parse.tables`
- `pdf.metadata.page_info`

### 3. Document IR and Local RAG

Borrow from Docling and Marker:

- Convert PDF into a stable Document IR first.
- Chunk from IR, not from raw PDF pages directly.
- Store local JSON indexes with source path, page number, bbox, chunk id, and text.
- Offer extractive local answers by default; generative answers require BYOK/cloud/local model config.

Implemented baseline:

- `pdf.ai.parse.lite`
- `pdf.ai.rag.ingest`
- `pdf.ai.rag.chat`
- `pdf.ai.rag.query`
- `pdf.ai.rag.search`
- `pdf.ai.rag.cite_answer`
- `pdf.ai.rag.highlight_sources`
- `pdf.ai.rag.export_report`
- `pdf.ai.create.from_prompt`
- `pdf.ai.create.templates`
- `pdf.convert.pdf_to_json`
- `pdf.convert.pdf_to_markdown`
- `pdf.organize.reorder_pages`
- `pdf.organize.insert_blank_pages`

Next local improvements:

- Highlighted source reports.
- Local prompt-to-template PDF creation should stay deterministic in OSS: list templates, choose a template, apply a style pack and color overrides, render, validate, and return the generated Markdown and agent plan.
- Better paragraph/table/formula/image segmentation.
- Optional parser worker contracts inspired by pdf-craft and LiteParse.

### 4. OCR and Scanned Documents

Borrow from OCRmyPDF:

- OCR is a pipeline, not a single flag.
- Report skipped pages and reasons.
- Keep original image quality choices explicit.
- Emit sidecar text and validation artifacts.

Default OSS core should not bundle heavyweight OCR engines. OCR belongs behind optional workers and feature flags.

### 5. Self-Hosted Product Surface

Borrow from Stirling-PDF:

- Wide, discoverable tool catalog.
- Simple local setup.
- Docker/self-hosted path.
- Workflow recipes for common document tasks.

AgentPDF should keep the first screen agent/developer focused: CLI, MCP, REST, SDK, examples, and machine-readable schemas.

## License Boundary Rules

- Default dependencies must remain permissive or otherwise compatible with Apache-2.0 distribution.
- GPL/AGPL/commercial-boundary tools can inspire architecture but must not become default dependencies.
- Optional workers must be named explicitly, documented with license notes, and gated by install extras or feature flags.
- Do not copy implementation code from reference projects without a license review.

## Implementation Order From This Synthesis

1. Finish local Document IR, parse lite, local RAG ingest/query.
2. Add citation-only helpers and better search ranking.
3. Add deterministic utility breadth from pdfcpu/Stirling-PDF: crop, attachments, forms, and workflow recipes.
4. Add validation breadth from qpdf/OCRmyPDF: repair diagnostics, visual diff, redaction verification.
5. Add optional parser/OCR worker contracts inspired by Docling/Marker/pdf-craft/LiteParse/OCRmyPDF without bundling heavy dependencies.
6. Add agent-infra packaging inspired by Firecrawl: SDKs, cloud boundary, API keys later, examples, and hosted/free/paid plan docs.
