# Local Agent Integration

okpdf's first implementation priority is local agent-callable PDF tooling. Cloud workers can be added later, but the local CLI, MCP server, and REST API must remain useful without paid services, hosted URLs, or proprietary keys.

## Fast Setup

```bash
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
```

## Local MCP Server

Run AgentPDF as a stdio MCP server:

```bash
okpdf serve --mcp --safe-root .
```

For HTTP-compatible MCP clients:

```bash
okpdf serve --mcp --transport streamable-http --safe-root .
```

## Claude Desktop / Claude Code Style Config

```json
{
  "mcpServers": {
    "agentpdf": {
      "command": "okpdf",
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
    "command": "okpdf",
    "args": ["serve", "--mcp", "--safe-root", "."]
  }
}
```

## Exposed Local Tools

- `agentpdf_tool_manifest`
- `pdf_inspect_document`
- `pdf_inspect_pages`
- `pdf_workflow_plan`
- `pdf_workflow_run`
- `pdf_workflow_report`
- `pdf_merge`
- `pdf_split`
- `pdf_extract_pages`
- `pdf_remove_pages`
- `pdf_rotate_pages`
- `pdf_reorder_pages`
- `pdf_insert_blank_pages`
- `pdf_optimize_compress`
- `pdf_optimize_repair`
- `pdf_image_to_pdf`
- `pdf_watermark`
- `pdf_add_page_numbers`
- `pdf_create_text`
- `pdf_create_markdown`
- `pdf_render_pages`
- `pdf_extract_images`
- `pdf_extract_text`
- `pdf_pdf_to_json`
- `pdf_pdf_to_markdown`
- `pdf_metadata_read`
- `pdf_metadata_update`
- `pdf_metadata_remove`
- `pdf_validate_output`
- `pdf_render_check`
- `pdf_blank_page_check`
- `pdf_ai_parse_lite`
- `pdf_ai_rag_ingest`
- `pdf_ai_rag_chat`
- `pdf_ai_rag_cite_answer`
- `pdf_ai_rag_export_report`
- `pdf_ai_rag_highlight_sources`
- `pdf_ai_rag_query`
- `pdf_ai_rag_search`

Each tool returns the same AgentPDF `ToolResult` JSON used by the CLI.

## Local REST API

Run the local HTTP API:

```bash
okpdf serve --api
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

Example page inspection request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.pages/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "1-3", "render_check": true}'
```

Example workflow planning request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.plan/run \
  -H 'Content-Type: application/json' \
  -d '{"goal": "Chat with this PDF and cite answers", "input_path": "report.pdf"}'
```

Example workflow execution request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.run/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow": {
      "input_path": "report.pdf",
      "artifact_dir": ".agentpdf-out/workflows/chat",
      "bindings": {
        "<question>": "What does this PDF say?",
        "<answer>": "This PDF is locally indexed."
      },
      "steps": [
        {"step_id": "inspect", "tool": "pdf.inspect.document", "input": {"path": "<input.pdf>"}},
        {"step_id": "index", "tool": "pdf.ai.rag.ingest", "input": {"input_path": "<input.pdf>", "index_path": "<output.index.json>"}},
        {"step_id": "answer", "tool": "pdf.ai.rag.query", "input": {"index_path": "<output.index.json>", "query": "<question>"}}
      ]
    }
  }'
```

Example workflow report request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.workflow.report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workflow_run": {
      "run_id": "wfrun_123",
      "status": "succeeded",
      "planned_steps": 1,
      "executed_steps": 1,
      "failed_steps": 0,
      "step_results": [
        {"step_id": "inspect", "tool": "pdf.inspect.document", "status": "succeeded"}
      ]
    },
    "output_path": ".agentpdf-out/workflow-report.md"
  }'
```

Example text extraction request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_text/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "all"}'
```

Example embedded image extraction request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.extract_images/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "pages": "all", "out_dir": "extracted-images"}'
```

Example one-shot local PDF chat request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.chat/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "report.pdf", "question": "What does this report describe?", "report_output_path": "report-chat.pdf", "highlight_output_path": "report-highlighted.pdf"}'
```

Example citation support request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.cite_answer/run \
  -H 'Content-Type: application/json' \
  -d '{"index_path": "report.index.json", "answer": "The report describes local evidence."}'
```

Example highlighted source request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.highlight_sources/run \
  -H 'Content-Type: application/json' \
  -d '{"index_path": "report.index.json", "answer": "The report describes local evidence.", "output_path": "report-highlighted.pdf"}'
```

Example cited answer report request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.rag.export_report/run \
  -H 'Content-Type: application/json' \
  -d '{"index_path": "report.index.json", "question": "What does the report describe?", "answer": "The report describes local evidence.", "output_path": "report-rag.pdf"}'
```

Example PDF creation request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.convert.markdown_to_pdf/run \
  -H 'Content-Type: application/json' \
  -d '{"markdown": "# Agent Report\n\n- Created locally", "output_path": "agent-report.pdf"}'
```

Example compression request:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.optimize.compress/run \
  -H 'Content-Type: application/json' \
  -d '{"input_path": "agent-report.pdf", "output_path": "agent-report-compressed.pdf"}'
```

## TypeScript / Node.js Agents

Node agents should use the TypeScript package in `packages/agentpdf-node` and call the REST API instead of reimplementing PDF processing:

```bash
npm install
npm run build:node
okpdf serve --api
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o node.pdf
node packages/agentpdf-node/dist/src/cli.js compress node.pdf -o node-compressed.pdf
```

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();
const result = await client.runTool("pdf.convert.markdown_to_pdf", {
  markdown: "# Agent Report\n\n- Created from Node",
  output_path: "agent-report.pdf",
});
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
