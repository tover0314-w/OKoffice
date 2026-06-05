# 40 - okoffice Agent Infrastructure

## Goal

okoffice should be easy for coding agents to discover, call, verify, and chain. The primary UX is not a GUI; it is a reliable tool surface.

## Required Surfaces

- CLI.
- MCP server.
- REST API.
- Python SDK.
- TypeScript SDK.
- JSON schema registry.
- Tool manifest.
- Artifact manifest.
- Source graph.
- Validation reports.
- Bundle export/verify.

## Agent Ecosystems

### Codex

Needs:

- workspace `AGENTS.md`;
- local MCP config;
- safe root;
- JSON-first tool outputs;
- clear implementation order docs.

Beta command:

```bash
okoffice agent setup codex -o codex.mcp.json --safe-root . --json
```

### Claude Code / Claude Desktop

Needs:

- MCP stdio config;
- concise tool descriptions;
- safe local roots;
- artifact paths;
- structured content.

Beta command:

```bash
okoffice agent setup claude-code -o .mcp.json --safe-root . --json
```

### Cursor

Needs:

- MCP config examples;
- repository-local docs;
- quick commands for inspect and workflow tasks.

### Kilo Code / OpenClaw

Needs:

- generated MCP config;
- clear tool manifest;
- explicit safe root;
- no hidden cloud behavior.

### OpenAI Agents

Needs:

- MCP or REST wrapper;
- tool schemas;
- async job support;
- artifact download strategy.

### LangChain / LlamaIndex

Needs:

- loaders/readers that preserve native locators;
- document chunks with source refs;
- optional retrieval indexes;
- no forced flattening to text.

### Vercel AI SDK / SaaS Builders

Needs:

- TypeScript REST client;
- server-side tool calling examples;
- stable ToolResult types;
- hosted/local base URL parity.

### n8n / Zapier / Make

Needs:

- REST endpoints;
- webhook-compatible job results;
- folder/watch examples;
- artifact URLs or paths.

## Agent Contract

Agents should receive:

- exact tool name;
- status;
- artifacts;
- validation;
- warnings;
- usage;
- next recommended tools;
- native locators.

Agents should not parse human stdout when JSON is available.

## Native Locators

okoffice must preserve native locators:

- Word: section id, paragraph id, run id, table id, comment id.
- Excel: workbook id, sheet name, cell, range, table id, chart id, formula refs.
- PowerPoint: slide number, slide id, shape id, placeholder id, notes id.
- PDF: page number, bbox, annotation id, form field id.
- Media: timestamp, transcript segment.
- Code: file path, symbol, line range.

## Agent Setup Tools

Target setup tools:

- `office.agent.setup.codex`
- `office.agent.setup.claude_code`
- `office.agent.setup.cursor`
- `office.agent.setup.kilo_code`
- `office.agent.setup.openclaw`
- `office.agent.setup.openai_agents`
- `office.agent.setup.langchain`
- `office.agent.setup.llamaindex`

Current compatibility setup tools may stay as `agent.setup.*`, but generated config should use the server name `okoffice` where possible.

## Behavior Guidelines For Agents

Agents should:

- inspect before editing;
- extract evidence before composing;
- preserve source refs;
- create new artifacts instead of mutating inputs;
- run validation before handoff;
- report warnings plainly;
- use bundles for multi-artifact workflows.

Agents should not:

- execute macros;
- send files to cloud without configuration;
- claim exact geometry without render evidence;
- hide worker failures;
- treat optional worker skips as validation success.

## Minimal Agent Happy Path

```text
office.inspect.file
-> office.context.build_packet
-> office.extract.schema
-> sheet.write.workbook
-> sheet.validation.formulas
-> deck.create.presentation
-> deck.validation.presentation
-> deck.validation.contact_sheet
-> office.bundle.export
-> office.bundle.verify
```
