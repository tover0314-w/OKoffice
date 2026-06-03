# 27 — Integrations Guide

## Priority Order

1. Claude Code / Claude Desktop via MCP.
2. Codex and Cursor through AGENTS.md, CLI, REST, and MCP examples.
3. Kilo Code, OpenCode/OpenClaw-style skill ecosystems, OpenAI Agents, LangChain, LlamaIndex, and workflow automation platforms.
4. Hosted API integrations after the local agent contract is stable.

## Claude Desktop / Claude Code

Generate a project-level MCP stdio config:

```bash
okpdf agent setup claude-code -o .mcp.json --json
```

See `examples/agent/claude-code.mcp.json` for the generated shape.

## Cursor

Use MCP config. See `examples/mcp/cursor_mcp.json`.

## OpenAI Agents SDK

Use an MCP server or local REST API wrapper. See `examples/openai-agents/openai_agents_mcp.py`.

## Codex

Generate a Codex-friendly local MCP config, then point Codex at the workspace `AGENTS.md` and the generated config:

```bash
okpdf agent setup codex -o codex.mcp.json --safe-root . --json
```

The same setup is available as REST tool `agent.setup.codex`, MCP tool `agent_setup_codex`, and Node command `agentpdf-node agent-setup-codex`.

## Kilo Code / OpenClaw

Generate local MCP configs for Kilo Code or OpenClaw-style runtimes:

```bash
okpdf agent setup kilo-code -o kilo-code.mcp.json --safe-root . --json
okpdf agent setup openclaw -o openclaw.mcp.json --safe-root . --json
```

The same setup is available as REST tools `agent.setup.kilo_code` and `agent.setup.openclaw`, MCP tools `agent_setup_kilo_code` and `agent_setup_openclaw`, and Node commands `agentpdf-node agent-setup-kilo-code` and `agentpdf-node agent-setup-openclaw`.

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
