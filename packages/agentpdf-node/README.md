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

await client.watermark({
  inputPath: ".agentpdf-out/node.pdf",
  text: "DRAFT",
  outputPath: ".agentpdf-out/node-draft.pdf",
});

console.log(result.status, result.artifacts[0]?.path);
```

## CLI

```bash
agentpdf-node tools
agentpdf-node run pdf.inspect.document --payload '{"path":"report.pdf"}'
agentpdf-node image-to-pdf cover.png -o cover.pdf
agentpdf-node watermark cover.pdf --text DRAFT -o cover-draft.pdf
agentpdf-node page-numbers cover-draft.pdf -o cover-numbered.pdf
agentpdf-node validate cover-numbered.pdf --expected-pages 1
agentpdf-node create-text --text "Hello Node" -o node.pdf
agentpdf-node create-markdown --markdown-file report.md -o report.pdf
```

## Design

- REST-first client for local and future hosted API compatibility.
- Typed `ToolResult`, `Artifact`, `ValidationReport`, `ToolManifest`, and tool inputs.
- Convenience wrappers for inspect, merge, image-to-PDF, watermark, page numbers, text/Markdown creation, and validation.
- Failed PDF tools still return structured failed `ToolResult` bodies instead of being hidden behind generic exceptions.
- HTTP or non-AgentPDF failures throw `AgentPDFHttpError`.
