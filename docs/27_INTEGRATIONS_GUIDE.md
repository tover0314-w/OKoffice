# 27 — Integrations Guide

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

Expose TypeScript SDK and MCP server for agent workflows.

## Browser/web app

The web UI should call the same REST API and tool registry, not a separate code path.
