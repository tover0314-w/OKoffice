# TypeScript and Node.js SDK

okpdf uses Python for the local PDF core and TypeScript for agent/app ergonomics. The TypeScript package lives in `packages/agentpdf-node` and talks to the local REST API.

## Why This Boundary

- PDF engines remain consistent across CLI, MCP, REST, and SDK calls.
- Node.js agents and web apps can use typed results without spawning Python directly.
- Future hosted APIs can reuse the same client shape.
- The JavaScript package stays license-safe and lightweight.

## Local Development

```bash
npm install
npm run build:node
npm test --workspace @okpdf/agentpdf-node
```

Run the local API:

```bash
agentpdf serve --api
```

Use the Node CLI:

```bash
node packages/agentpdf-node/dist/src/cli.js tools
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
node packages/agentpdf-node/dist/src/cli.js create-markdown --markdown-file examples/sample-documents/business_report.md -o .agentpdf-out/node-report.pdf
```

## SDK Example

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();

const tools = await client.listTools();
const created = await client.createMarkdownPdf({
  markdown: "# Agent Report\n\n- Local-first\n- Node-ready",
  outputPath: ".agentpdf-out/report.pdf",
});

console.log(tools.tools.length);
console.log(created.validation?.status);
```

## Current Surface

- `listTools()`
- `getTool(name)`
- `runTool(name, payload)`
- `inspectDocument({ path })`
- `merge({ inputPaths, outputPath })`
- `createTextPdf({ text, outputPath, title })`
- `createMarkdownPdf({ markdown, outputPath, title, stylePack })`

The generic `runTool()` method can call any implemented REST tool without waiting for a convenience wrapper.
