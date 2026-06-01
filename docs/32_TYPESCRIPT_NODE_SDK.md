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
node packages/agentpdf-node/dist/src/cli.js workflow-plan --goal "Chat with this PDF and cite answers" --input-path .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js workflow-run --payload '{"steps":[{"step_id":"inspect","tool":"pdf.inspect.document","input":{"path":"<input.pdf>"}}],"input_path":".agentpdf-out/node-report.pdf"}' --binding '<question>=What is this report?' --dry-run
node packages/agentpdf-node/dist/src/cli.js workflow-report --payload '{"run_id":"wfrun_node","status":"succeeded","planned_steps":1,"executed_steps":1,"failed_steps":0,"step_results":[]}' -o .agentpdf-out/node-workflow-report.md
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
node packages/agentpdf-node/dist/src/cli.js create-markdown --markdown-file examples/sample-documents/business_report.md -o .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js inspect-pages .agentpdf-out/node-report.pdf --pages 1 --render-check
node packages/agentpdf-node/dist/src/cli.js reorder-pages .agentpdf-out/node-report.pdf --order 1 -o .agentpdf-out/node-report-reordered.pdf
node packages/agentpdf-node/dist/src/cli.js insert-blank-pages .agentpdf-out/node-report-reordered.pdf --after-page 1 --count 1 -o .agentpdf-out/node-report-blank.pdf
node packages/agentpdf-node/dist/src/cli.js compress .agentpdf-out/node-report-blank.pdf -o .agentpdf-out/node-report-compressed.pdf
node packages/agentpdf-node/dist/src/cli.js repair .agentpdf-out/node-report-compressed.pdf -o .agentpdf-out/node-report-repaired.pdf
node packages/agentpdf-node/dist/src/cli.js watermark .agentpdf-out/node-report.pdf --text DRAFT -o .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js validate .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js render-check .agentpdf-out/node-report-draft.pdf --pages 1
node packages/agentpdf-node/dist/src/cli.js blank-page-check .agentpdf-out/node-report-blank.pdf --pages all
node packages/agentpdf-node/dist/src/cli.js extract-images .agentpdf-out/node-report-draft.pdf --pages all --out-dir .agentpdf-out/node-report-images
node packages/agentpdf-node/dist/src/cli.js parse-lite .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js pdf-to-json .agentpdf-out/node-report-draft.pdf -o .agentpdf-out/node-report.ir.json
node packages/agentpdf-node/dist/src/cli.js pdf-to-markdown .agentpdf-out/node-report-draft.pdf -o .agentpdf-out/node-report.md
node packages/agentpdf-node/dist/src/cli.js rag-ingest .agentpdf-out/node-report-draft.pdf --index .agentpdf-out/node-report.index.json
node packages/agentpdf-node/dist/src/cli.js rag-chat .agentpdf-out/node-report-draft.pdf --question "What is this report about?" --report-output .agentpdf-out/node-chat-report.pdf --highlight-output .agentpdf-out/node-chat-highlighted.pdf
node packages/agentpdf-node/dist/src/cli.js rag-query .agentpdf-out/node-report.index.json --query "What is this report about?"
node packages/agentpdf-node/dist/src/cli.js rag-search .agentpdf-out/node-report.index.json --query "report"
node packages/agentpdf-node/dist/src/cli.js rag-cite-answer .agentpdf-out/node-report.index.json --answer "This report is local-first."
node packages/agentpdf-node/dist/src/cli.js rag-highlight-sources .agentpdf-out/node-report.index.json --answer "This report is local-first." -o .agentpdf-out/node-report-highlighted.pdf
node packages/agentpdf-node/dist/src/cli.js rag-export-report .agentpdf-out/node-report.index.json --question "What is this report about?" --answer "This report is local-first." -o .agentpdf-out/node-report-rag.pdf
```

## SDK Example

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();

const tools = await client.listTools();
const created = await client.createMarkdownPdf({
  markdown: "# Agent Report\n\n- Local-first\n- Node-ready",
  outputPath: ".agentpdf-out/report.pdf",
  stylePack: "business_report_modern",
});
const pages = await client.inspectPages({
  inputPath: ".agentpdf-out/report.pdf",
  pages: "1",
  renderCheck: true,
});
const plan = await client.workflowPlan({
  goal: "Chat with this PDF and cite answers",
  inputPath: ".agentpdf-out/report.pdf",
});
const workflowRun = await client.workflowRun({
  workflow: {
    input_path: ".agentpdf-out/report.pdf",
    artifact_dir: ".agentpdf-out/workflows/report",
    bindings: {
      "<question>": "What does this report say?",
      "<answer>": "This report is local-first.",
    },
    steps: [
      {
        step_id: "inspect",
        tool: "pdf.inspect.document",
        input: { path: "<input.pdf>" },
      },
    ],
  },
});
const workflowReport = await client.workflowReport({
  workflowRun: workflowRun.usage.workflow_run,
  outputPath: ".agentpdf-out/workflow-report.md",
});
const numbered = await client.addPageNumbers({
  inputPath: ".agentpdf-out/report.pdf",
  outputPath: ".agentpdf-out/report-numbered.pdf",
});
await client.insertBlankPages({
  inputPath: ".agentpdf-out/report-numbered.pdf",
  afterPage: 1,
  count: 1,
  outputPath: ".agentpdf-out/report-with-blank.pdf",
});
await client.compress({
  inputPath: ".agentpdf-out/report-with-blank.pdf",
  outputPath: ".agentpdf-out/report-compressed.pdf",
});
const index = await client.ragIngest({
  inputPath: ".agentpdf-out/report-numbered.pdf",
  indexPath: ".agentpdf-out/report.index.json",
});
const chat = await client.ragChat({
  inputPath: ".agentpdf-out/report-numbered.pdf",
  question: "What is this report about?",
  reportOutputPath: ".agentpdf-out/report-chat.pdf",
  highlightOutputPath: ".agentpdf-out/report-chat-highlighted.pdf",
});
const blankPages = await client.blankPageCheck({
  path: ".agentpdf-out/report-with-blank.pdf",
  pages: "all",
});
const extractedImages = await client.extractImages({
  inputPath: ".agentpdf-out/report-numbered.pdf",
  pages: "all",
  outDir: ".agentpdf-out/report-images",
});
const matches = await client.ragSearch({
  indexPath: ".agentpdf-out/report.index.json",
  query: "report",
});
const citedAnswer = await client.ragCiteAnswer({
  indexPath: ".agentpdf-out/report.index.json",
  answer: "This report is local-first.",
});
const highlightedSources = await client.ragHighlightSources({
  indexPath: ".agentpdf-out/report.index.json",
  answer: "This report is local-first.",
  outputPath: ".agentpdf-out/report-highlighted.pdf",
});
const ragReport = await client.ragExportReport({
  indexPath: ".agentpdf-out/report.index.json",
  question: "What is this report about?",
  answer: "This report is local-first.",
  outputPath: ".agentpdf-out/report-rag.pdf",
});

console.log(tools.tools.length);
console.log(created.validation?.status);
console.log(pages.usage.pages);
console.log(plan.usage.workflow.steps.length);
console.log(workflowRun.usage.workflow_run.executed_steps);
console.log(workflowReport.usage.workflow_report.run_status);
console.log(numbered.tool);
console.log(blankPages.usage.blank_pages);
console.log(extractedImages.usage.image_count);
console.log(index.usage.chunk_count);
console.log(chat.usage.answer);
console.log(matches.usage.match_count);
console.log(citedAnswer.usage.citation_count);
console.log(highlightedSources.usage.highlighted_pages);
console.log(ragReport.usage.pages_cited);
```

## Current Surface

- `listTools()`
- `getTool(name)`
- `runTool(name, payload)`
- `inspectDocument({ path })`
- `inspectPages({ inputPath, pages, renderCheck })`
- `workflowPlan({ goal, inputPath })`
- `workflowRun({ workflow, dryRun })`
- `workflowReport({ workflowRun, outputPath })`
- `merge({ inputPaths, outputPath })`
- `reorderPages({ inputPath, order, outputPath })`
- `insertBlankPages({ inputPath, afterPage, outputPath, count })`
- `compress({ inputPath, outputPath })`
- `repair({ inputPath, outputPath })`
- `imageToPdf({ imagePaths, outputPath })`
- `watermark({ inputPath, text, outputPath, pages, fontSize, opacity, angle })`
- `addPageNumbers({ inputPath, outputPath, pages, template, fontSize })`
- `createTextPdf({ text, outputPath, title })`
- `createMarkdownPdf({ markdown, outputPath, title, stylePack })`
- `validateOutput({ path, expectedPages })`
- `renderCheck({ path, pages })`
- `blankPageCheck({ path, pages })`
- `extractImages({ inputPath, pages, outDir })`
- `parseLite({ inputPath, pages })`
- `pdfToJson({ inputPath, outputPath, pages })`
- `pdfToMarkdown({ inputPath, outputPath, pages })`
- `ragIngest({ inputPath, indexPath, pages, maxChars, overlapChars })`
- `ragChat({ inputPath, question, indexPath, reportOutputPath, highlightOutputPath, pages, topK, maxChars, overlapChars, stylePack, highlightColor })`
- `ragQuery({ indexPath, query, topK })`
- `ragSearch({ indexPath, query, topK })`
- `ragCiteAnswer({ indexPath, answer, topK })`
- `ragHighlightSources({ indexPath, outputPath, answer, query, topK, highlightColor })`
- `ragExportReport({ indexPath, outputPath, question, answer, topK, includeCitations, title, stylePack })`

The generic `runTool()` method can call any implemented REST tool without waiting for a convenience wrapper.
