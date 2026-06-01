# Local Agent Integration

AgentPDF's first implementation priority is local agent-callable PDF tooling. Cloud workers can be added later, but the local CLI, MCP server, and REST API must remain useful without paid services, hosted URLs, or proprietary keys.

## Local MCP Server

Run AgentPDF as a stdio MCP server:

```bash
agentpdf serve --mcp --safe-root .
```

For HTTP-compatible MCP clients:

```bash
agentpdf serve --mcp --transport streamable-http --safe-root .
```

## Claude Desktop / Claude Code Style Config

```json
{
  "mcpServers": {
    "agentpdf": {
      "command": "agentpdf",
      "args": ["serve", "--mcp", "--safe-root", "."]
    }
  }
}
```

## Codex / Agent Runtime Pattern

Use the same stdio MCP command from any agent runtime that supports MCP:

```json
{
  "agentpdf": {
    "command": "agentpdf",
    "args": ["serve", "--mcp", "--safe-root", "."]
  }
}
```

## Exposed Local Tools

- `agentpdf_tool_manifest`
- `pdf_inspect_document`
- `pdf_merge`
- `pdf_split`
- `pdf_extract_pages`
- `pdf_remove_pages`
- `pdf_rotate_pages`
- `pdf_create_text`
- `pdf_create_markdown`
- `pdf_render_pages`
- `pdf_extract_text`
- `pdf_metadata_read`
- `pdf_metadata_update`
- `pdf_metadata_remove`

Each tool returns the same AgentPDF `ToolResult` JSON used by the CLI.

## Local REST API

Run the local HTTP API:

```bash
agentpdf serve --api
```

Useful endpoints:

- `GET /healthz`
- `GET /v1/tools`
- `GET /v1/tools/{tool_name}`
- `POST /v1/tools/{tool_name}/run`
- `GET /v1/jobs/{job_id}`
- `GET /v1/artifacts/{artifact_id}`
- `GET /v1/artifacts/{artifact_id}/download`

Example inspect request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "report.pdf"}'
```

Example text extraction request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_text/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "all"}'
```

Example PDF creation request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.markdown_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{"markdown": "# Agent Report\n\n- Created locally", "output_path": "agent-report.pdf"}'
```

## Open-Source PDF Project Patterns To Borrow

AgentPDF should continue studying projects such as pdf-craft and other mature PDF/OCR/document-processing systems. The patterns to borrow are architectural:

- Local-first processing for privacy and repeatability.
- Clear handler boundaries for PDF reading, rendering, OCR, extraction, and output writing.
- Optional heavyweight workers with explicit dependency and model/cache locations.
- Per-page warnings and partial-failure reporting instead of opaque failures.
- Deterministic artifact manifests for generated files.
- Cloud/model integration as a layer above the local core, never hidden inside local deterministic tools.

Do not copy implementation code without a license review. Default core dependencies must avoid GPL/AGPL.

## Cloud Boundary

Future cloud integration should be exposed through separate tools or workers, for example `pdf.ai.parse.agentic` or hosted batch processing. Local tools should continue to work offline and should return `cloud_only` or `tool_not_implemented` for capabilities that require hosted services.
