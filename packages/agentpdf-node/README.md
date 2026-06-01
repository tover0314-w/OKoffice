# @okpdf/agentpdf-node

TypeScript and Node.js client for okpdf / AgentPDF local PDF tools.

This package does not reimplement PDF processing in JavaScript. It calls the same local REST API powered by the Python core, so Node agents, web apps, and scripts get the same `ToolResult` contract as CLI and MCP users.

## Install

From this repository:

```bash
npm install
npm run build:node
```

Start the local API in another terminal:

```bash
okpdf serve --api
```

## SDK

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient({ baseUrl: "http://127.0.0.1:7331" });

const result = await client.createTextPdf({
  text: "Hello from Node",
  outputPath: ".agentpdf-out/node.pdf",
});
const report = await client.createMarkdownPdf({
  markdown: "# Agent Report\n\n- Local first\n- Styled locally",
  outputPath: ".agentpdf-out/node-report.pdf",
  stylePack: "business_report_modern",
});
const pageFacts = await client.inspectPages({
  inputPath: ".agentpdf-out/node.pdf",
  pages: "1",
  renderCheck: true,
});

await client.watermark({
  inputPath: ".agentpdf-out/node.pdf",
  text: "DRAFT",
  outputPath: ".agentpdf-out/node-draft.pdf",
});

await client.compress({
  inputPath: ".agentpdf-out/node-draft.pdf",
  outputPath: ".agentpdf-out/node-draft-compressed.pdf",
});

await client.workflowRun({
  workflow: {
    steps: [
      {
        step_id: "inspect",
        tool: "pdf.inspect.document",
        input: { path: ".agentpdf-out/node-draft-compressed.pdf" },
      },
    ],
  },
});

console.log(pageFacts.usage.pages);
console.log(result.status, result.artifacts[0]?.path);
console.log(report.usage.style_pack, report.usage.colors);
```

## CLI

```bash
agentpdf-node tools
agentpdf-node run pdf.inspect.document --payload '{"path":"report.pdf"}'
agentpdf-node inspect-pages report.pdf --pages 1 --render-check
agentpdf-node workflow-plan --goal "Chat with this PDF and cite answers" --input-path report.pdf
agentpdf-node workflow-run --payload '{"input_path":"report.pdf","steps":[{"step_id":"inspect","tool":"pdf.inspect.document","input":{"path":"<input.pdf>"}}]}' --binding '<question>=What is this report?' --dry-run
agentpdf-node workflow-report --payload '{"run_id":"wfrun_node","status":"succeeded","planned_steps":1,"executed_steps":1,"failed_steps":0,"step_results":[]}' -o workflow-report.md
agentpdf-node image-to-pdf cover.png -o cover.pdf
agentpdf-node reorder-pages cover.pdf --order 1 -o cover-reordered.pdf
agentpdf-node insert-blank-pages cover-reordered.pdf --after-page 1 --count 1 -o cover-blank.pdf
agentpdf-node compress cover-blank.pdf -o cover-compressed.pdf
agentpdf-node repair cover-compressed.pdf -o cover-repaired.pdf
agentpdf-node watermark cover.pdf --text DRAFT -o cover-draft.pdf
agentpdf-node page-numbers cover-draft.pdf -o cover-numbered.pdf
agentpdf-node validate cover-numbered.pdf --expected-pages 1
agentpdf-node render-check cover-numbered.pdf --pages 1
agentpdf-node blank-page-check cover-blank.pdf --pages all
agentpdf-node extract-images cover-numbered.pdf --pages all --out-dir cover-images
agentpdf-node parse-lite cover-numbered.pdf
agentpdf-node pdf-to-json cover-numbered.pdf -o cover.ir.json
agentpdf-node pdf-to-markdown cover-numbered.pdf -o cover.md
agentpdf-node rag-ingest cover-numbered.pdf --index cover.index.json
agentpdf-node rag-chat cover-numbered.pdf --question "What is covered?" --report-output cover-chat-report.pdf --highlight-output cover-chat-highlighted.pdf
agentpdf-node rag-query cover.index.json --query "What is covered?"
agentpdf-node rag-search cover.index.json --query "covered"
agentpdf-node rag-cite-answer cover.index.json --answer "The cover is numbered."
agentpdf-node rag-highlight-sources cover.index.json --answer "The cover is numbered." -o cover-highlighted.pdf
agentpdf-node rag-export-report cover.index.json --question "What is covered?" --answer "The cover is numbered." -o cover-rag-report.pdf
agentpdf-node create-text --text "Hello Node" -o node.pdf
agentpdf-node create-markdown --markdown-file report.md -o report.pdf
```

## Design

- REST-first client for local and future hosted API compatibility.
- Typed `ToolResult`, `Artifact`, `ValidationReport`, `ToolManifest`, and tool inputs.
- Convenience wrappers for document/page inspect, workflow planning/execution/reporting, merge, reorder, insert blank pages, compression, repair/rewrite, image-to-PDF, embedded image extraction, watermark, page numbers, text/Markdown creation, validation, render/blank checks, lite parse, and local RAG.
- Failed PDF tools still return structured failed `ToolResult` bodies instead of being hidden behind generic exceptions.
- HTTP or non-AgentPDF failures throw `AgentPDFHttpError`.
