# 00 — Start Here for Codex

Read these files first, in order:

1. `README.md`
2. `AGENTS.md`
3. `docs/01_PRODUCT_VISION.md`
4. `docs/35_AGENT_NATIVE_MULTIMODAL_PDF_INFRA_PRD.md`
5. `docs/02_OPEN_SOURCE_SCOPE.md`
6. `docs/03_ARCHITECTURE.md`
7. `docs/05_COMPLETE_TOOL_CATALOG.md`
8. `schemas/tool-manifest.schema.json`
9. `codex/backlog/V0_IMPLEMENTATION_ORDER.md`
10. `codex/review/CODE_REVIEW_CHECKLIST.md`

## Primary objective

Implement the first open-source version of AgentPDF Infra with a beautiful developer experience, a full tool manifest, and a clear path toward agent-native multimodal PDF infrastructure.

The first code release does **not** need to fully implement every planned PDF tool. It does need to:

- Provide a complete, stable namespace.
- Implement the first core stable tools.
- Make CLI/MCP/API integration real.
- Produce structured outputs and validation reports.
- Treat PDFs as evidence-backed target artifacts created from context packets, target profiles, source maps, manifests, and next actions.
- Maintain open-source quality standards.

## Implementation milestones

### Milestone A — Repo bootstrap

- Python package.
- CLI entrypoint.
- Logging and config.
- Schemas copied into package.
- Basic tests.
- Documentation build path.

### Milestone B — Core deterministic PDF tools

- `pdf.inspect`
- `pdf.render.pages`
- `pdf.organize.merge`
- `pdf.organize.split`
- `pdf.organize.extract_pages`
- `pdf.organize.remove_pages`
- `pdf.organize.rotate_pages`
- `pdf.metadata.read`
- `pdf.metadata.update`
- `pdf.convert.pdf_to_images`
- `pdf.convert.image_to_pdf`
- `pdf.convert.markdown_to_pdf`
- `pdf.convert.text_to_pdf`
- `pdf.edit.watermark`
- `pdf.edit.page_numbers`
- `pdf.validation.validate_output`

### Milestone C — Agent interfaces

- MCP server exposing stable tools.
- REST API exposing stable tools.
- Tool registry and tool discovery endpoint.
- Example configs for Claude Desktop, Cursor, OpenAI Agents, and local API calls.

### Milestone D — Lightweight AI/document layer

- Lite parse.
- Text chunks.
- Local keyword/vector-like demo retrieval.
- RAG answer wrapper with citations.
- No paid models required by default.

### Milestone E - Agent-native product surface

The first release does not need full multimodal or cloud execution, but the harness should expose the product shape:

- Context packet, target PDF profile, source graph, and artifact lineage concepts.
- Composition IR direction for learning PDFs, resumes, papers, reports, packets, and slide-like PDFs.
- Patch transaction direction for agent edits.
- Evidence and citation tools as a broader layer than RAG.
- Workflow recipes for multimodal-to-PDF, PDF patching, verification packets, and presentations.

## Acceptance bar for the first public release

The public repository should look polished enough that a developer can star it, run it locally, and understand the path from local PDF tools to a complete agent-native document infrastructure product.
