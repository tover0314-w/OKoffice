# 27 - Integrations Guide

## Priority Order

1. Claude Code / Claude Desktop via MCP.
2. Codex and Cursor through AGENTS.md, CLI, REST, and MCP examples.
3. Kilo Code, OpenCode/OpenClaw-style skill ecosystems, OpenAI Agents, LangChain, LlamaIndex, and workflow automation platforms.
4. Hosted API integrations after the local agent contract is stable.

okoffice integrations should expose the same ToolResult contract across all clients. No integration should invent a separate response shape.

## Claude Desktop / Claude Code

Current compatibility command:

```bash
okpdf agent setup claude-code -o .mcp.json --json
```

Beta okoffice command:

```bash
okoffice agent setup claude-code -o .mcp.json --safe-root . --json
```

See `examples/agent/claude-code.mcp.json` for the generated shape.

## Cursor

Use MCP config. See:

```text
examples/mcp/cursor_mcp.json
```

## OpenAI Agents SDK

Use an MCP server or local REST API wrapper. See:

```text
examples/openai-agents/openai_agents_mcp.py
```

The target examples should include:

- Inspect a workbook.
- Extract evidence from Word/PDF into Excel.
- Generate a PowerPoint deck from workbook data.
- Verify an okoffice bundle.

## Codex

Generate a Codex-friendly local MCP config, then point Codex at the workspace `AGENTS.md` and the generated config.

Current:

```bash
okpdf agent setup codex -o codex.mcp.json --safe-root . --json
```

Beta okoffice command:

```bash
okoffice agent setup codex -o codex.mcp.json --safe-root . --json
```

The same setup is available as REST tool `agent.setup.codex`, MCP tool `agent_setup_codex`, and Node command. The okoffice CLI defaults to MCP server key `okoffice` and command `okoffice serve --mcp`; pass `--server-name agentpdf --command okpdf` for legacy configs.

## Kilo Code / OpenClaw

Current:

```bash
okpdf agent setup kilo-code -o kilo-code.mcp.json --safe-root . --json
okpdf agent setup openclaw -o openclaw.mcp.json --safe-root . --json
```

Beta okoffice commands:

```bash
okoffice agent setup kilo-code -o kilo-code.mcp.json --safe-root . --json
okoffice agent setup openclaw -o openclaw.mcp.json --safe-root . --json
```

## LangChain

Future wrapper:

```python
from okoffice.integrations.langchain import OkOfficeLoader

docs = OkOfficeLoader(["report.docx", "model.xlsx", "deck.pptx", "packet.pdf"]).load()
```

The loader should preserve native locators such as Word paragraph ids, Excel ranges, PowerPoint slide/shape ids, and PDF page/bbox refs.

## LlamaIndex

Future wrapper:

```python
from okoffice.integrations.llamaindex import OkOfficeReader

reader = OkOfficeReader(parse_mode="lite")
nodes = reader.load_data(["paper.pdf", "summary.docx", "evidence.xlsx"])
```

## n8n / Zapier / Make

Expose REST API and webhook-compatible jobs.

Suggested workflows:

- Watch folder -> inspect Office/PDF -> export bundle.
- Incoming contracts -> extract fields -> append evidence workbook.
- Workbook update -> regenerate board deck.
- Completed bundle -> notify reviewer.

## Vercel AI SDK

Use the TypeScript SDK against the local REST API from server-side tools or actions.

Target:

```ts
import { OkOfficeClient } from "@okoffice/node";

const okoffice = new OkOfficeClient({ baseUrl: process.env.OKOFFICE_BASE_URL });
const result = await okoffice.runTool("sheet.inspect.workbook", {
  file: { kind: "local_path", path: "evidence.xlsx" },
});
```

Compatibility:

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const agentpdf = new AgentPDFClient({ baseUrl: process.env.AGENTPDF_BASE_URL });
const result = await agentpdf.inspectDocument({ path: "report.pdf" });
```

## Browser/Web App

The web UI should call the same REST API and tool registry, not a separate code path. It should show:

- ToolResult JSON.
- Artifacts and download links.
- Validation reports.
- Source maps.
- Warnings and next recommended tools.
- Bundle graph when available.
