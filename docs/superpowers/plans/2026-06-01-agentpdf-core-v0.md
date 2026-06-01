# AgentPDF Core V0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository root into a runnable local-first AgentPDF Python package with typed public models, tool discovery, core PDF inspect/merge/split behavior, validation, artifacts, and a CLI.

**Architecture:** CLI and MCP call a small tool layer instead of manipulating PDFs directly. Public responses use Pydantic models and every generated PDF is registered as an artifact and validated. Rendering uses the license-compatible `pypdfium2` backend so local agents can produce real image artifacts.

**Tech Stack:** Python 3.11+, Typer, Rich, Pydantic v2, pypdf, pypdfium2, MCP Python SDK/FastMCP, pytest.

---

## File Structure

- Create `pyproject.toml`: package metadata, dependencies, CLI script, pytest config.
- Create `src/agentpdf/__init__.py`: package version.
- Create `src/agentpdf/__main__.py`: module entrypoint.
- Create `src/agentpdf/cli/__init__.py`: CLI package marker.
- Create `src/agentpdf/cli/__main__.py`: supports `python -m agentpdf.cli`.
- Create `src/agentpdf/cli/main.py`: Typer CLI commands.
- Create `src/agentpdf/schemas/models.py`: Pydantic contracts.
- Create `src/agentpdf/schemas/errors.py`: stable error code loading/fallbacks.
- Create `src/agentpdf/security/paths.py`: explicit safe path helpers.
- Create `src/agentpdf/core/page_ranges.py`: robust page range parser.
- Create `src/agentpdf/core/pdf.py`: deterministic PDF operations.
- Create `src/agentpdf/artifacts/store.py`: local artifact metadata.
- Create `src/agentpdf/validation/pdf.py`: generated PDF validation.
- Create `src/agentpdf/tools/registry.py`: tool manifest and discovery.
- Create `src/agentpdf/tools/runner.py`: stable tool result wrappers.
- Create `src/agentpdf/mcp/server.py`: FastMCP local agent-callable server.
- Create `tests/conftest.py`: fixture PDF generation.
- Create `tests/unit/test_models.py`: model serialization tests.
- Create `tests/unit/test_page_ranges.py`: page range parser tests.
- Create `tests/unit/test_registry.py`: registry tests.
- Create `tests/integration/test_cli.py`: CLI behavior tests.
- Create `tests/integration/test_pdf_tools.py`: inspect/merge/split validation tests.

## Task 1: Bootstrap Root Package

**Files:**
- Create: `pyproject.toml`
- Create: `src/agentpdf/__init__.py`
- Create: `src/agentpdf/__main__.py`
- Create: `src/agentpdf/cli/__init__.py`
- Create: `src/agentpdf/cli/__main__.py`
- Create: `src/agentpdf/cli/main.py`
- Create: `tests/unit/test_import.py`

- [ ] **Step 1: Write import and CLI smoke tests**

```python
def test_import_agentpdf() -> None:
    import agentpdf

    assert agentpdf.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the import test and confirm it fails before implementation**

Run: `pytest tests/unit/test_import.py -q`

Expected: FAIL because the root package does not exist yet.

- [ ] **Step 3: Add root package metadata and module entrypoints**

`pyproject.toml` should define `agentpdf = "agentpdf.cli.main:app"` and dependencies `pydantic`, `typer`, `rich`, and `pypdf`.

- [ ] **Step 4: Implement a minimal Typer CLI**

`src/agentpdf/cli/main.py` should expose `app`, `version`, and a callback so `python -m agentpdf.cli --help` works.

- [ ] **Step 5: Run smoke checks**

Run:

```bash
python -m agentpdf.cli --help
pytest tests/unit/test_import.py -q
```

Expected: both pass.

## Task 2: Public Pydantic Models

**Files:**
- Create: `src/agentpdf/schemas/models.py`
- Create: `src/agentpdf/schemas/errors.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write model serialization tests**

Test `FileRef`, `Artifact`, `ValidationReport`, `ToolResult`, and `ToolManifest` with `model_dump()` and `model_dump_json()`.

- [ ] **Step 2: Implement typed models**

Models must include the uniform output contract:

```python
class ToolResult(BaseModel):
    job_id: str
    status: Literal["succeeded", "failed"]
    tool: str
    artifacts: list[Artifact] = Field(default_factory=list)
    validation: ValidationReport | None = None
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    next_recommended_tools: list[str] = Field(default_factory=list)
    error: AgentPDFError | None = None
```

- [ ] **Step 3: Run model tests**

Run: `pytest tests/unit/test_models.py -q`

Expected: PASS.

## Task 3: Safe Paths and Page Ranges

**Files:**
- Create: `src/agentpdf/security/paths.py`
- Create: `src/agentpdf/core/page_ranges.py`
- Create: `tests/unit/test_page_ranges.py`

- [ ] **Step 1: Write page range tests**

Cover `1-3,7`, `all`, `odd`, `even`, reversed ranges, zero pages, and out-of-bounds pages.

- [ ] **Step 2: Implement safe path helpers**

`resolve_input_path()` must reject missing files and suspicious path segments. `resolve_output_path()` must create parent directories and reject unsafe output names.

- [ ] **Step 3: Implement `parse_page_range()`**

Return zero-based page indexes for internal use. Raise `AgentPDFException("invalid_page_range", ...)` for invalid input.

- [ ] **Step 4: Run page range tests**

Run: `pytest tests/unit/test_page_ranges.py -q`

Expected: PASS.

## Task 4: Artifact Store and Validation

**Files:**
- Create: `src/agentpdf/artifacts/store.py`
- Create: `src/agentpdf/validation/pdf.py`
- Modify: `tests/unit/test_models.py`
- Create: `tests/integration/test_pdf_tools.py`

- [ ] **Step 1: Write artifact/validation tests**

Create fixture PDFs and assert artifact metadata includes path, SHA-256, size, MIME type, and page count.

- [ ] **Step 2: Implement artifact registration**

`build_artifact(path, source_tool)` computes deterministic metadata and uses `pypdf.PdfReader` to count PDF pages.

- [ ] **Step 3: Implement output validation**

`validate_pdf(path, expected_pages=None)` checks file exists, is parseable, has nonzero pages, and matches expected page count when provided.

- [ ] **Step 4: Run validation tests**

Run: `pytest tests/integration/test_pdf_tools.py -q`

Expected: tests that target implemented behavior pass.

## Task 5: Tool Registry

**Files:**
- Create: `src/agentpdf/tools/registry.py`
- Create: `tests/unit/test_registry.py`

- [ ] **Step 1: Write registry tests**

Assert `pdf.inspect.document`, `pdf.organize.merge`, `pdf.organize.split`, `pdf.convert.pdf_to_images`, and `pdf.validation.validate_output` exist and implemented tools are marked `implemented=True`.

- [ ] **Step 2: Implement registry**

Load `schemas/tool-manifest.full.json` when available. If it is absent or incompatible, fall back to a built-in V0 manifest.

- [ ] **Step 3: Run registry tests**

Run: `pytest tests/unit/test_registry.py -q`

Expected: PASS.

## Task 6: Core PDF Operations

**Files:**
- Create: `src/agentpdf/core/pdf.py`
- Create: `src/agentpdf/tools/runner.py`
- Modify: `tests/integration/test_pdf_tools.py`

- [ ] **Step 1: Write inspect/merge/split tests**

Assert inspect returns page count; merge produces combined pages; split/extract produces selected pages; generated outputs include artifacts and validation.

- [ ] **Step 2: Implement inspect**

Use `pypdf.PdfReader` to return page count, encryption status, metadata, page sizes, and rotations.

- [ ] **Step 3: Implement merge and split**

Use `pypdf.PdfWriter`; never mutate inputs; always write a new output artifact.

- [ ] **Step 4: Implement render**

Use `pypdfium2` to render selected pages to PNG/JPEG/WebP image artifacts. Do not create fake images.

- [ ] **Step 5: Run PDF integration tests**

Run: `pytest tests/integration/test_pdf_tools.py -q`

Expected: PASS.

## Task 7: CLI Tool Surface

**Files:**
- Modify: `src/agentpdf/cli/main.py`
- Create: `tests/integration/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Use `typer.testing.CliRunner` for `tools list --json`, `tools show`, `inspect`, `merge`, `split`, and render dependency behavior.

- [ ] **Step 2: Implement CLI commands**

Commands should call `tools.runner` functions and print JSON with `model_dump_json()` for agent-first outputs.

- [ ] **Step 3: Run CLI tests**

Run: `pytest tests/integration/test_cli.py -q`

Expected: PASS.

## Task 8: Local MCP Agent Surface

**Files:**
- Create: `src/agentpdf/mcp/server.py`
- Modify: `src/agentpdf/cli/main.py`
- Create: `tests/integration/test_mcp_server.py`

- [ ] **Step 1: Write MCP tests**

Assert the FastMCP server exposes `agentpdf_tool_manifest`, `pdf_inspect_document`, `pdf_merge`, `pdf_split`, and `pdf_render_pages`.

- [ ] **Step 2: Implement MCP wrappers**

Each MCP tool calls the same runner functions as the CLI and returns `ToolResult.model_dump_json()`.

- [ ] **Step 3: Add CLI serve command**

`agentpdf serve --mcp` starts the stdio MCP server; `--transport streamable-http` can be used for HTTP-compatible clients.

- [ ] **Step 4: Run MCP tests**

Run: `pytest tests/integration/test_mcp_server.py -q`

Expected: PASS.

## Task 9: Final Verification

**Files:**
- Modify docs only if command syntax differs from existing examples.

- [ ] **Step 1: Run the full test suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 2: Run required CLI commands**

Run:

```bash
python -m agentpdf.cli --help
agentpdf tools list --json
agentpdf inspect tests/fixtures/simple.pdf --json
agentpdf merge tests/fixtures/simple.pdf tests/fixtures/two_pages.pdf -o .agentpdf-out/merged.pdf --json
agentpdf split tests/fixtures/two_pages.pdf --pages 1 -o .agentpdf-out/page-1.pdf --json
agentpdf render tests/fixtures/simple.pdf --pages 1 --format png --out-dir .agentpdf-out/renders --json
python -m agentpdf.cli serve --help
```

Expected: help/list/inspect/merge/split/render succeed. MCP serve help is available; long-running `agentpdf serve --mcp` is not run as a blocking final verification command.

- [ ] **Step 3: Record git limitation**

Run: `if (Test-Path .git) { git status --short } else { 'NO_GIT_REPOSITORY' }`

Expected in this workspace: `NO_GIT_REPOSITORY`; skip commit steps.

## Self-Review Notes

- The plan covers all Core V0 design requirements.
- No cloud, billing, proprietary, GPL, or AGPL dependency is required.
- Render is honest about missing optional dependencies.
- REST/RAG and advanced cloud workers are intentionally excluded from this first implementation plan and remain follow-up milestones.
