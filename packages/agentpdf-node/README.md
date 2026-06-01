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
agentpdf serve --api
```

## SDK

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient({ baseUrl: "http://127.0.0.1:7331" });

const result = await client.createTextPdf({
  text: "Hello from Node",
  outputPath: ".agentpdf-out/node.pdf",
});

console.log(result.status, result.artifacts[0]?.path);
```

## CLI

```bash
agentpdf-node tools
agentpdf-node run pdf.inspect.document --payload '{"path":"report.pdf"}'
agentpdf-node create-text --text "Hello Node" -o node.pdf
agentpdf-node create-markdown --markdown-file report.md -o report.pdf
```

## Design

- REST-first client for local and future hosted API compatibility.
- Typed `ToolResult`, `Artifact`, `ValidationReport`, `ToolManifest`, and tool inputs.
- Failed PDF tools still return structured failed `ToolResult` bodies instead of being hidden behind generic exceptions.
- HTTP or non-AgentPDF failures throw `AgentPDFHttpError`.
