# OKoffice Core V0 Design

## Purpose

Build the first runnable open-source OKoffice implementation from the current development harness. The V0 should turn the repository root into a Python package with a real CLI, public Pydantic contracts, a stable tool registry, local artifact and validation models, and the first deterministic PDF tools.

## Scope

Core V0 implements:

- Root-level Python package under `src/okoffice`.
- `pyproject.toml` with local-first, license-safe default dependencies.
- Pydantic public models for files, artifacts, jobs, validation reports, tool results, errors, and tool manifests.
- Tool registry with the complete public namespace loaded from the existing manifest where possible.
- CLI entrypoints for help/version, tool discovery, inspect, merge, split, and render.
- Local MCP entrypoint so Claude Code, Claude Desktop, Cursor, Codex-style MCP clients, and other agents can call the same local tools.
- Deterministic PDF operations using non-GPL default dependencies.
- Artifact metadata with explicit paths, SHA-256, size, MIME type, and page count when available.
- Validation reports for generated PDFs, including page count and renderability-style structural checks available through `pypdf`.
- Tests and fixtures proving the root package works.

Core V0 does not implement hosted billing, proprietary cloud behavior, unauthorized PDF unlock, perfect layout-preserving edits, advanced OCR, AI parsing, or full REST coverage. MCP coverage is intentionally limited to the implemented local deterministic tools.

## Architecture

The repository root becomes the installable package. The package is split by stable responsibilities:

- `schemas/`: public Pydantic models and error helpers.
- `tools/`: registry, tool metadata, and routing helpers.
- `core/`: pure deterministic PDF operations.
- `artifacts/`: local artifact store and file metadata.
- `validation/`: generated-output validation.
- `cli/`: Typer commands that call the tool layer and print JSON when requested.
- `mcp/`: FastMCP server exposing implemented local tools as agent-callable functions.
- `security/`: safe path checks and traversal rejection.

CLI and MCP commands should not contain PDF manipulation logic. They normalize user input, call the relevant tool function, and render the uniform `ToolResult`.

## Open-Source Reference Direction

OKoffice should actively study strong open-source PDF projects, especially pdf-craft, but borrow patterns instead of copying implementation code. Relevant pdf-craft-inspired patterns for this project are:

- Local-first document processing by default.
- Clear separation between PDF handlers, OCR/model workers, and output transformers.
- Explicit model/cache paths for heavyweight AI workers.
- Offline/local-only modes for privacy-sensitive documents.
- Configurable page rendering DPI and output size controls.
- Per-page error handling that can either fail fast or continue with warnings.
- Optional cloud/LLM enhancement as a boundary above the local core, not hidden inside deterministic operations.

Core V0 applies these ideas through local CLI/MCP tooling, structured artifact output, and explicit future worker boundaries. OCR, advanced parse, and cloud-assisted transformations remain separate follow-up workers.

## Data Flow

For read-only tools such as `pdf.inspect.document`, the CLI validates the input path, calls the inspect worker, and returns a `ToolResult` with structured PDF details in `usage` or validation-adjacent data.

For generated-output tools such as merge, split, and render:

1. Validate input paths and reject unsafe names or traversal.
2. Run the deterministic PDF operation without mutating source files.
3. Write only to the requested output path or output directory.
4. Register produced files as artifacts.
5. Validate generated PDFs when the artifact is a PDF.
6. Return one uniform `ToolResult` with warnings and next recommended tools.

## Error Handling

Errors use stable codes from `schemas/error-codes.yaml` when possible. V0 must cover at least:

- `file_not_found`
- `unsupported_file_type`
- `encrypted_pdf_requires_password`
- `invalid_page_range`
- `pdf_parse_failed`
- `pdf_render_failed`
- `output_validation_failed`
- `dependency_missing`
- `tool_not_implemented`
- `unsafe_input_rejected`

CLI failures should still produce agent-readable JSON when `--json` is requested.

## Tool Surface

The complete public manifest remains visible from day one, even when many tools are `planned` or `cloud_only`. Core V0 marks only implemented local deterministic tools as implemented:

- `pdf.inspect.document`
- `pdf.organize.merge`
- `pdf.organize.split`
- `pdf.organize.extract_pages`
- `pdf.organize.remove_pages`
- `pdf.organize.rotate_pages`
- `pdf.convert.pdf_to_images` or CLI alias `render`
- `pdf.convert.pdf_to_text`
- `pdf.metadata.read`
- `pdf.metadata.update`
- `pdf.metadata.remove`
- `pdf.validation.validate_output`

The local MCP server exposes these implemented tools under agent-friendly names:

- `okoffice_tool_manifest`
- `pdf_inspect_document`
- `pdf_merge`
- `pdf_split`
- `pdf_extract_pages`
- `pdf_remove_pages`
- `pdf_rotate_pages`
- `pdf_render_pages`
- `pdf_extract_text`
- `pdf_metadata_read`
- `pdf_metadata_update`
- `pdf_metadata_remove`

Other tools stay discoverable with status labels and `implemented=false`.

## Testing

Tests should create or use local fixture PDFs and prove:

- The package imports from the root.
- Pydantic models serialize to JSON.
- Page ranges parse correctly.
- Tool registry lists and shows tools.
- Inspect returns page count and metadata.
- Merge and split produce new PDFs and do not mutate input files.
- Generated PDFs receive artifact metadata and validation reports.
- CLI help and JSON output commands work.

Acceptance commands for this V0:

```bash
python -m okoffice.cli --help
okoffice tools list --json
okoffice inspect tests/fixtures/simple.pdf --json
okoffice merge tests/fixtures/simple.pdf tests/fixtures/two_pages.pdf -o .okoffice-out/merged.pdf --json
okoffice split tests/fixtures/two_pages.pdf --pages 1 -o .okoffice-out/page-1.pdf --json
okoffice render tests/fixtures/simple.pdf --pages 1 --format png --out-dir .okoffice-out/renders --json
okoffice serve --mcp
pytest -q
```

## Constraints

Default dependencies must remain local-first and avoid GPL/AGPL. Rendering uses `pypdfium2`, which is license-compatible for the default core. Every generated PDF must be validated with the checks available in V0.

## Follow-Up Milestones

After Core V0, the next implementation plans should cover:

- More MCP tools as local workers are implemented.
- Local REST API exposing the same tool router.
- Markdown or HTML to PDF creation.
- Lightweight document IR, chunking, and local RAG demo.
- Documentation polish with CLI, MCP, REST, expected output, error examples, limitations, and dependency notes.
