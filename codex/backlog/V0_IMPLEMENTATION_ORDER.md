# V0 Implementation Order for Codex

Do not implement randomly. Follow this sequence.

## Step 1 — Repo bootstrap

Create:

- `pyproject.toml`
- `src/agentpdf/__init__.py`
- `src/agentpdf/cli/main.py`
- `src/agentpdf/tools/registry.py`
- `src/agentpdf/schemas/common.py`
- `tests/unit/test_import.py`

Acceptance:

```bash
python -m agentpdf.cli --help
pytest -q
```

## Step 2 — Schema models

Implement Pydantic models:

- `FileRef`
- `Artifact`
- `Job`
- `ToolResult`
- `ValidationReport`
- `ToolManifest`

Acceptance:

- Models serialize to JSON.
- Schemas export.
- Tests cover required fields.

## Step 3 — Artifact store

Implement local artifact store:

- Safe output directory.
- Artifact ID generation.
- SHA-256.
- File size.
- MIME type.
- PDF page count where possible.

## Step 4 — Page range parser

Implement robust page range parsing.

Acceptance:

- `1-3,7` works.
- `all`, `odd`, `even` work.
- Invalid ranges return `invalid_page_range`.

## Step 5 — Tool registry

Implement registry with status labels and discovery.

Acceptance:

```bash
agentpdf tools list --json
agentpdf tools show pdf.inspect.document --json
```

## Step 6 — Core PDF inspect

Implement `pdf.inspect.document`.

## Step 7 — Organize operations

Implement:

- merge.
- split.
- extract pages.
- remove pages.
- rotate pages.

## Step 8 — Validation

Implement `pdf.validation.validate_output`.

Attach validation to every generated PDF operation.

## Step 9 — Render and text

Implement:

- render pages.
- extract text.
- metadata read/update.

## Step 10 — CLI polish

All stable tools available through CLI with `--json`.

## Step 11 — MCP server

Expose stable tools through MCP.

## Step 12 — REST server

Expose local API.

## Step 13 — Markdown/create baseline

Implement Markdown-to-PDF or HTML-to-PDF with style packs.

## Step 14 — Lite parse and local RAG demo

Implement minimal Document IR, chunking, and retrieval.

## Step 15 — Docs and examples polish

Update README, examples, screenshots/GIF instructions, and integration configs.
