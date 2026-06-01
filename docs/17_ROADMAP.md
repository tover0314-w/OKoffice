# 17 — Roadmap

## Phase 0 — Harness and design

Status: this ZIP.

Deliverables:

- Product specification.
- Tool catalog.
- Schemas.
- Codex instructions.
- Open-source standards.

## Phase 1 — Open-source core foundation

Goal: useful local PDF toolkit for agents.

Tools:

- Inspect.
- Page-level inspection.
- Merge.
- Split.
- Extract/remove/reorder/rotate pages.
- Insert blank pages.
- Render.
- Text extraction.
- Embedded image extraction.
- Metadata.
- Images to PDF.
- PDF to images.
- Markdown to PDF.
- Compression.
- Repair/rewrite for parseable PDFs.
- Validation.

Interfaces:

- CLI.
- MCP server.
- REST server.
- Python SDK basics.
- TypeScript/Node REST client and Node CLI.
- Local workflow planner, runner, and report generator.

Current validation baseline:

- `pdf.validation.validate_output` checks parseability and page counts.
- `pdf.validation.render_check` verifies selected pages render in memory.
- `pdf.validation.blank_page_check` reports blank pages with text and render evidence.
- `pdf.workflow.plan` creates local-first agent workflow plans with roles, steps, and cloud-boundary notes.
- `pdf.workflow.run` executes supported local workflow manifests and returns per-step evidence.
- `pdf.workflow.report` summarizes workflow runs and can write Markdown audit reports.

## Phase 2 — Full deterministic PDF utility coverage

Add:

- Watermarks.
- Page numbers.
- Header/footer.
- Crop/resize.
- Basic forms.
- Basic security.
- Metadata removal.
- Attachments.
- Compare/diff.

## Phase 3 — Lite document intelligence

Add:

- Document IR.
- Lite parse.
- Tables baseline.
- Markdown/JSON export.
- Local RAG demo.
- Citation support.
- Style packs.

Current baseline:

- `pdf.ai.parse.lite` creates a local Document IR from the PDF text layer.
- `pdf.ai.rag.ingest` writes a local JSON index with page and bbox citations.
- `pdf.ai.rag.chat` runs local PDF Q&A, cited report export, and highlighted source output in one tool call.
- `pdf.ai.rag.query` returns extractive local answers with cited chunks.
- `pdf.ai.rag.search` returns ranked cited chunks without composing an answer.
- `pdf.ai.rag.cite_answer` maps an answer back to page/bbox evidence.
- `pdf.ai.rag.highlight_sources` writes a highlighted source PDF from local citations.
- `pdf.ai.rag.export_report` writes a cited Q&A/source PDF report and validates it.
- `pdf.convert.pdf_to_json` exports Document IR JSON artifacts.

Next improvements:

- Better paragraph/table segmentation.
- IR-to-Markdown/JSON export commands.
- Optional OCR/parser worker contracts inspired by OCRmyPDF, Docling, and Marker.

## Phase 4 — AI and cloud boundary

Add optional capabilities:

- BYOK model providers.
- Agentic parse.
- Advanced OCR.
- AI summarize/extract/review.
- AI create/edit/translate.
- Hosted index API shape.

## Phase 5 — Hosted service

Not part of the first OSS implementation, but design-compatible:

- Free quotas.
- Credits.
- Team keys.
- Persistent artifacts.
- Batch jobs.
- Webhooks.
- Usage analytics.
- Enterprise controls.

## Phase 6 — Ecosystem

- LangChain integration.
- LlamaIndex integration.
- Vercel AI SDK examples.
- TypeScript package publishing.
- n8n/Zapier/Make examples.
- Cursor/Claude/OpenAI Agents examples.
- Template/style marketplace.
