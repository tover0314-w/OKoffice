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
okpdf serve --api
```

Use the Node CLI:

```bash
node packages/agentpdf-node/dist/src/cli.js tools
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
node packages/agentpdf-node/dist/src/cli.js create-markdown --markdown-file examples/sample-documents/business_report.md -o .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js watermark .agentpdf-out/node-report.pdf --text DRAFT -o .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js validate .agentpdf-out/node-report-draft.pdf
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
const numbered = await client.addPageNumbers({
  inputPath: ".agentpdf-out/report.pdf",
  outputPath: ".agentpdf-out/report-numbered.pdf",
});

console.log(tools.tools.length);
console.log(created.validation?.status);
console.log(numbered.tool);
```

## Current Surface

- `listTools()`
- `getTool(name)`
- `runTool(name, payload)`
- `inspectDocument({ path })`
- `merge({ inputPaths, outputPath })`
- `imageToPdf({ imagePaths, outputPath })`
- `watermark({ inputPath, text, outputPath, pages, fontSize, opacity, angle })`
- `addPageNumbers({ inputPath, outputPath, pages, template, fontSize })`
- `createTextPdf({ text, outputPath, title })`
- `createMarkdownPdf({ markdown, outputPath, title, stylePack })`
- `validateOutput({ path, expectedPages })`

The generic `runTool()` method can call any implemented REST tool without waiting for a convenience wrapper.
