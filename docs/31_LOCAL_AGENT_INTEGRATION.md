# 31 - Local Agent Integration

okoffice's first implementation priority is local agent-callable Office tooling. Cloud workers can be added later, but CLI, MCP, REST, schemas, and SDKs must remain useful without paid services, hosted URLs, or proprietary keys.

Compatibility note: the runnable implementation currently exposes PDF tools through `okpdf`, `agentpdf`, and `pdf.*`. Those names belong in compatibility docs. New agent integration docs should use okoffice target names first.

## Fast Setup

```bash
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
```

Target local servers:

```bash
okoffice serve --mcp --safe-root .
okoffice serve --api --safe-root .
```

Current compatibility servers:

```bash
okpdf serve --mcp --safe-root .
okpdf serve --api
```

## Agent Surfaces

Agents should be able to use:

- MCP stdio.
- MCP streamable HTTP.
- REST API.
- CLI with `--json`.
- TypeScript SDK.
- Python SDK.
- JSON schemas.
- artifact manifests.
- source maps.
- bundles.

## Target Setup Commands

```bash
okoffice agent setup codex -o codex.mcp.json --safe-root . --json
okoffice agent setup claude-code -o .mcp.json --safe-root . --json
okoffice agent setup cursor -o cursor.mcp.json --safe-root . --json
okoffice agent setup kilo-code -o kilo-code.mcp.json --safe-root . --json
okoffice agent setup openclaw -o openclaw.mcp.json --safe-root . --json
okoffice agent setup openai-agents -o openai-agents.tools.json --safe-root . --json
```

Generated MCP config shape:

```json
{
  "mcpServers": {
    "okoffice": {
      "type": "stdio",
      "command": "okoffice",
      "args": ["serve", "--mcp", "--safe-root", "."]
    }
  }
}
```

## Target Local Tools

MCP wrapper groups:

- `office_inspect_file`
- `word_inspect_document`
- `sheet_inspect_workbook`
- `deck_inspect_presentation`
- `office_context_build_packet`
- `office_extract_schema`
- `office_validation_package`
- `office_workflow_extract_to_sheet`
- `sheet_create_evidence_workbook`
- `sheet_write_workbook`
- `sheet_validate_formulas`
- `deck_compose_plan`
- `deck_create_from_outline`
- `deck_validate_presentation`
- `word_create_report`
- `deck_create_presentation`
- `office_workflow_docset_to_sheet`
- `office_workflow_sheet_to_deck`
- `office_workflow_board_pack`
- `office_patch_plan`
- `office_patch_preview`
- `office_patch_apply`
- `office_patch_verify`
- `office_bundle_export`
- `office_bundle_verify`

Each wrapper returns the same ToolResult JSON used by CLI and REST.

## REST Pattern

Useful endpoints:

- `GET /healthz`
- `GET /v1/tools`
- `GET /v1/tools/{tool_name}`
- `POST /v1/tools/{tool_name}/run`
- `GET /v1/jobs/{job_id}`
- `GET /v1/artifacts/{artifact_id}`
- `GET /v1/artifacts/{artifact_id}/download`

Example:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.workflow.board_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "files": ["memo.docx", "diligence.pdf", "metrics.xlsx"],
    "out_dir": ".okoffice-out/board-pack",
    "profile": "board_review"
  }'
```

## Optional Workers

Agents must not assume optional workers are installed.

Worker adapters may include:

- OfficeCLI for `.docx`, `.xlsx`, and `.pptx` DOM operations and previews.
- LibreOffice for optional export/preview.
- browser renderers for HTML/source-package output.
- OCR engines.
- formula engines.
- model/VLM workers.

Worker unavailability should return structured evidence:

```json
{
  "status": "skipped",
  "reason": "worker_unavailable",
  "worker": "office_preview",
  "retry_hint": "Install an optional Office worker or run without preview validation."
}
```

## Agent Behavior Guidelines

Agents should:

- inspect before editing;
- build context packets before multi-source composition;
- preserve input artifacts;
- request patch preview for risky edits;
- use source refs in generated claims, rows, charts, slides, and report sections;
- run validation before handing artifacts to users;
- report warnings honestly;
- bundle multi-artifact outputs.

Agents should not:

- execute macros;
- send document contents to hosted AI by default;
- claim perfect arbitrary layout-preserving edits;
- treat optional worker failures as validation success;
- mutate user input files in place.
