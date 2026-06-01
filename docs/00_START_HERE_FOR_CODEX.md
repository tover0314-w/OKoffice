# 00 — Start Here for Codex

Read these files first, in order:

1. `README.md`
2. `AGENTS.md`
3. `docs/01_PRODUCT_VISION.md`
4. `docs/02_OPEN_SOURCE_SCOPE.md`
5. `docs/03_ARCHITECTURE.md`
6. `docs/05_COMPLETE_TOOL_CATALOG.md`
7. `schemas/tool-manifest.schema.json`
8. `codex/backlog/V0_IMPLEMENTATION_ORDER.md`
9. `codex/review/CODE_REVIEW_CHECKLIST.md`

## Primary objective

Implement the first open-source version of AgentPDF Infra with a beautiful developer experience and a full tool manifest.

The first code release does **not** need to fully implement every planned PDF tool. It does need to:

- Provide a complete, stable namespace.
- Implement the first core stable tools.
- Make CLI/MCP/API integration real.
- Produce structured outputs and validation reports.
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
- `pdf.convert.images_to_pdf`
- `pdf.create.markdown_to_pdf` or `pdf.create.html_to_pdf`
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

## Acceptance bar for the first public release

The public repository should look polished enough that a developer can star it, run it locally, and understand the path to a complete PDF infrastructure product.
