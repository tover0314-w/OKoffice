# Codex Implementation Prompts

Use these prompts to drive focused implementation sessions.

## Prompt 1 — Bootstrap

Read `AGENTS.md`, `docs/00_START_HERE_FOR_CODEX.md`, and `codex/backlog/V0_IMPLEMENTATION_ORDER.md`. Implement Step 1 only. Create the Python project structure, CLI skeleton, pyproject, and import smoke tests. Do not implement PDF tools yet. Keep the project polished and typed.

## Prompt 2 — Schemas

Implement Pydantic models for FileRef, Artifact, Job, ToolResult, ValidationReport, ToolManifest, and ErrorResponse based on the schemas in `schemas/`. Add unit tests and JSON examples.

## Prompt 3 — Tool registry

Implement the tool registry using the complete catalog. Expose `agentpdf tools list --json` and `agentpdf tools show <tool> --json`. Planned tools should be discoverable but not executable.

## Prompt 4 — Core PDF tools

Implement inspect, merge, split, extract pages, remove pages, rotate pages, and metadata read. Use safe file handling and attach validation to output PDFs.

## Prompt 5 — MCP

Implement local MCP server exposing stable tools. Return structured results and artifact references. Add Claude Desktop and Cursor examples.

## Prompt 6 — REST API

Implement FastAPI local API. Add `/healthz`, `/v1/tools`, `/v1/tools/{tool_name}`, `/v1/tools/{tool_name}/run`, and artifact download routes.

## Prompt 7 — PDF creation

Implement Markdown-to-PDF with style packs. Make the generated PDFs look clean. Add style examples and validation.

## Prompt 8 — Lite parse/RAG

Implement lite parse, chunking, local index, and query with citations. No model dependency by default.

## Prompt 9 — Polish pass

Improve README, docs, CLI errors, examples, test fixtures, and status matrix. Make the project attractive for open-source launch.
