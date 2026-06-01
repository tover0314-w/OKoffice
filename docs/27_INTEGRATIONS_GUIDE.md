# 27 — Integrations Guide

## Priority Order

1. Claude Code / Claude Desktop via MCP.
2. Codex and Cursor through AGENTS.md, CLI, REST, and MCP examples.
3. KiloCode, OpenCode/OpenClaw-style skill ecosystems, OpenAI Agents, LangChain, LlamaIndex, and workflow automation platforms.
4. Hosted API integrations after the local agent contract is stable.

## Claude Desktop / Claude Code

Use MCP stdio config. See `examples/mcp/claude_desktop_config.json`.

## Cursor

Use MCP config. See `examples/mcp/cursor_mcp.json`.

## OpenAI Agents SDK

Use an MCP server or local REST API wrapper. See `examples/openai-agents/openai_agents_mcp.py`.

## Codex

Codex should read `AGENTS.md` and use CLI/API/MCP examples to implement and test the project.

## LangChain

Future wrapper:

```python
from agentpdf.integrations.langchain import AgentPDFLoader

docs = AgentPDFLoader("report.pdf").load()
```

## LlamaIndex

Future wrapper:

```python
from agentpdf.integrations.llamaindex import AgentPDFReader

reader = AgentPDFReader(parse_mode="lite")
nodes = reader.load_data("paper.pdf")
```

## n8n / Zapier / Make

Expose REST API and webhook-compatible jobs.

## Vercel AI SDK

Use `@okpdf/agentpdf-node` against the local REST API from server-side tools or actions:

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const agentpdf = new AgentPDFClient({ baseUrl: process.env.AGENTPDF_BASE_URL });
const result = await agentpdf.inspectDocument({ path: "report.pdf" });
```

## Browser/web app

The web UI should call the same REST API and tool registry, not a separate code path.
