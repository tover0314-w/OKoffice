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
node packages/agentpdf-node/dist/src/cli.js agent-setup-claude-code -o .mcp.json --safe-root '${CLAUDE_PROJECT_DIR:-.}'
node packages/agentpdf-node/dist/src/cli.js workflow-plan --goal "Chat with this PDF and cite answers" --input-path .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js workflow-run --payload '{"steps":[{"step_id":"inspect","tool":"pdf.inspect.document","input":{"path":"<input.pdf>"}}],"input_path":".agentpdf-out/node-report.pdf"}' --binding '<question>=What is this report?' --dry-run
node packages/agentpdf-node/dist/src/cli.js workflow-report --payload '{"run_id":"wfrun_node","status":"succeeded","planned_steps":1,"executed_steps":1,"failed_steps":0,"step_results":[]}' -o .agentpdf-out/node-workflow-report.md
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
node packages/agentpdf-node/dist/src/cli.js create-markdown --markdown-file examples/sample-documents/business_report.md -o .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js create-template-packs -o .agentpdf-out/template-packs.json
node packages/agentpdf-node/dist/src/cli.js create-validate-template-pack examples/template-packs/local-agent-starter.json -o .agentpdf-out/template-pack.validation.json
node packages/agentpdf-node/dist/src/cli.js create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --data examples/create-data/agent-block-audit.json -o .agentpdf-out/board-audit.pdf
node packages/agentpdf-node/dist/src/cli.js create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --context-packet .agentpdf-out/context.packet.json -o .agentpdf-out/board-audit-from-context.pdf
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
node packages/agentpdf-node/dist/src/cli.js context-build --text "Create a technical audit PDF." --file README.md --item-json examples/context/media-items.json -o .agentpdf-out/context.packet.json
node packages/agentpdf-node/dist/src/cli.js target-profiles -o .agentpdf-out/target-profiles.json
node packages/agentpdf-node/dist/src/cli.js target-validate --target-profile '{"profile_id":"media_learning_deck","layout_mode":"slides","accepted_block_types":["slide","audio_reference","video_reference"],"accepted_context_types":["text","audio","video"],"validation_required":["render_check","evidence_coverage_report"]}' -o .agentpdf-out/media-learning-deck.validation.json
node packages/agentpdf-node/dist/src/cli.js compose-from-context .agentpdf-out/context.packet.json --profile technical_audit -o .agentpdf-out/technical-audit.pdf
node packages/agentpdf-node/dist/src/cli.js compose-from-context .agentpdf-out/context.packet.json --profile slide_deck -o .agentpdf-out/agent-review-deck.pdf
node packages/agentpdf-node/dist/src/cli.js evidence-coverage-report .agentpdf-out/technical-audit.composition.json -o .agentpdf-out/technical-audit.coverage.json
node packages/agentpdf-node/dist/src/cli.js patch-plan .agentpdf-out/technical-audit.pdf --operations '[{"op":"append_table","title":"Runtime Metrics","columns":["metric","value"],"rows":[["latency_ms","42"]],"source_refs":["ctx_002"],"target_slot":"findings"}]' -o .agentpdf-out/technical-audit.patch.json --composition .agentpdf-out/technical-audit.composition.json --layers .agentpdf-out/technical-audit.layers.json
node packages/agentpdf-node/dist/src/cli.js patch-preview .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit.patch-preview.json
node packages/agentpdf-node/dist/src/cli.js patch-apply .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit-patched.pdf
node packages/agentpdf-node/dist/src/cli.js patch-verify .agentpdf-out/technical-audit.patch.json .agentpdf-out/technical-audit-patched.pdf
node packages/agentpdf-node/dist/src/cli.js export-bundle --file .agentpdf-out/technical-audit-patched.pdf --file .agentpdf-out/technical-audit.composition.json --file .agentpdf-out/technical-audit.coverage.json --file .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit.agentpdf-bundle.zip --title "Technical Audit Bundle" --metadata workflow=context-packet-patch
```

## SDK Example

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();

const tools = await client.listTools();
const claude = await client.setupClaudeCode({
  outputPath: ".mcp.json",
  safeRoot: "${CLAUDE_PROJECT_DIR:-.}",
});
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
const createdBrief = await client.createFromPrompt({
  prompt: "Create a research brief about local PDF agents.",
  outputPath: ".agentpdf-out/agent-brief.pdf",
  template: "research_brief",
  stylePack: "paper_ink",
  colors: { primary: "#4f46e5", accent: "#f59e0b" },
});
const createCatalog = await client.createTemplates();
const templatePacks = await client.createTemplatePacks({
  outputPath: ".agentpdf-out/template-packs.json",
});
const packValidation = await client.validateTemplatePack({
  templatePackPath: "examples/template-packs/local-agent-starter.json",
  outputPath: ".agentpdf-out/template-pack.validation.json",
});
const boardAudit = await client.createFromTemplatePack({
  templatePackPath: "examples/template-packs/local-agent-starter.json",
  templateId: "board_audit",
  colorScheme: "executive_blue",
  outputPath: ".agentpdf-out/board-audit.pdf",
  data: {
    title: "Agent Block Audit",
    blocks: [
      {
        block_id: "blk_agent_code",
        type: "code",
        title: "Risky Function",
        target_slot: "evidence",
        language: "python",
        code: "def risky_total(items):\n    return sum(items)\n",
        source_refs: ["ctx_code"],
      },
      {
        block_id: "blk_agent_table",
        type: "table",
        title: "Runtime Metrics",
        target_slot: "findings",
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"]],
        source_refs: ["ctx_metrics"],
      },
      {
        block_id: "blk_agent_image",
        type: "image",
        title: "Architecture Figure",
        target_slot: "evidence",
        path: "assets/brand/okpdf-logo.png",
        caption: "Local visual evidence rendered from an agent-supplied image block.",
        source_refs: ["path://assets/brand/okpdf-logo.png"],
      },
      {
        block_id: "blk_agent_citation",
        type: "citation",
        title: "Reference Note",
        target_slot: "recommendations",
        quote: "Local outputs need evidence, validation, and portable audit artifacts.",
        source: "https://okpdf.local/docs/local-agent-integration",
        page: "local",
        source_refs: ["https://okpdf.local/docs/local-agent-integration"],
      },
    ],
  },
});
const invoicePreview = await client.createTemplatePreview({
  template: "invoice",
  outputPath: ".agentpdf-out/invoice-preview.pdf",
});
const contextPacket = await client.buildContextPacket({
  contextItems: [
    { text: "Create a technical audit PDF.", role: "brief" },
    { path: "src/agentpdf/compose/context.py", role: "code_evidence" },
    {
      table: {
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"], ["error_rate", "0.01"]],
      },
      role: "data_evidence",
      label: "Runtime Metrics",
    },
    { path: "assets/brand/okpdf-logo.png", role: "image_evidence" },
    {
      path: "examples/media/meeting-audio.mp3",
      role: "audio_context",
      label: "Meeting Audio",
      transcript: "00:00 Kickoff\n00:12 Decision: keep the local worker boundary explicit.",
      duration_seconds: 42.5,
      chapters: [
        { start_seconds: 0, title: "Kickoff" },
        { start_seconds: 12, title: "Decision" },
      ],
    },
    {
      path: "examples/media/training-video.mp4",
      role: "video_context",
      label: "Training Video",
      transcript: "00:00 Dashboard tour\n00:20 Export demo",
      duration_seconds: 84,
      keyframes: [{ timestamp_seconds: 20, label: "Export screen" }],
    },
    { path: "README.md", role: "project_context" },
  ],
  outputPath: ".agentpdf-out/context.packet.json",
  title: "Audit Context",
});
const targetCatalog = await client.targetProfiles({
  outputPath: ".agentpdf-out/target-profiles.json",
});
const targetValidation = await client.validateTargetProfile({
  targetProfile: {
    profile_id: "media_learning_deck",
    layout_mode: "slides",
    accepted_block_types: ["slide", "audio_reference", "video_reference"],
    accepted_context_types: ["text", "audio", "video"],
    validation_required: ["render_check", "evidence_coverage_report"],
  },
  outputPath: ".agentpdf-out/media-learning-deck.validation.json",
});
const composedAudit = await client.composeFromContext({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "technical_audit",
  outputPath: ".agentpdf-out/technical-audit.pdf",
});
const composedDeck = await client.composeFromContext({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "slide_deck",
  outputPath: ".agentpdf-out/agent-review-deck.pdf",
});
const coverage = await client.evidenceCoverageReport({
  compositionPath: ".agentpdf-out/technical-audit.composition.json",
  outputPath: ".agentpdf-out/technical-audit.coverage.json",
});
const patch = await client.patchPlan({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  operations: [
    {
      op: "append_table",
      title: "Runtime Metrics",
      columns: ["metric", "value"],
      rows: [["latency_ms", "42"], ["error_rate", "0.01"]],
      source_refs: ["ctx_002"],
    },
    {
      op: "append_image",
      title: "Architecture Figure",
      path: "assets/brand/okpdf-logo.png",
      caption: "Local visual evidence rendered into the patched PDF.",
      source_refs: ["ctx_003"],
    },
    {
      op: "append_slide",
      title: "Agent Review Appendix",
      body: ["Patch transactions can append slide-like evidence pages."],
      source_refs: ["ctx_001", "ctx_002", "ctx_003"],
    },
  ],
  outputPath: ".agentpdf-out/technical-audit.patch.json",
  compositionPath: ".agentpdf-out/technical-audit.composition.json",
  reason: "Append structured evidence appendix.",
});
await client.patchPreview({
  patchManifestPath: ".agentpdf-out/technical-audit.patch.json",
  outputPath: ".agentpdf-out/technical-audit.patch-preview.json",
});
await client.patchApply({
  patchManifestPath: ".agentpdf-out/technical-audit.patch.json",
  outputPath: ".agentpdf-out/technical-audit-patched.pdf",
});
await client.patchVerify({
  patchManifestPath: ".agentpdf-out/technical-audit.patch.json",
  patchedPath: ".agentpdf-out/technical-audit-patched.pdf",
});
const bundle = await client.exportBundle({
  artifactPaths: [
    ".agentpdf-out/technical-audit-patched.pdf",
    ".agentpdf-out/technical-audit.composition.json",
    ".agentpdf-out/technical-audit.coverage.json",
    ".agentpdf-out/technical-audit.patch.json",
  ],
  outputPath: ".agentpdf-out/technical-audit.agentpdf-bundle.zip",
  title: "Technical Audit Bundle",
  metadata: { workflow: "context-packet-patch", agent: "codex" },
});
const bundleVerification = await client.verifyBundle({
  bundlePath: ".agentpdf-out/technical-audit.agentpdf-bundle.zip",
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
console.log(createdBrief.usage.template_id);
console.log(createCatalog.usage.template_count);
console.log(composedAudit.artifacts[0]?.path);
console.log(composedDeck.usage.slide_count);
console.log(targetCatalog.usage.profile_catalog.profile_count, targetValidation.usage.profile_validation.is_valid);
console.log(coverage.usage.uncovered_block_count);
console.log(patch.usage.operation_count);
console.log(bundle.usage.bundle_entries.length);
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
- `createFromPrompt({ prompt, outputPath, template, stylePack, colors, data, title })`
- `createTemplates()`
- `createTemplatePacks({ outputPath })`
- `validateTemplatePack({ templatePack, templatePackPath, outputPath })`
- `createFromTemplatePack({ templatePack, templatePackPath, templateId, outputPath, colorScheme, data, contextPacket, contextPacketPath, title, prompt, stylePack })`
  returns the PDF plus `.composition.json` and `.layers.json` artifacts. The layer manifest gives Node agents stable block/layer ids, target slots, source refs, estimated normalized-page anchors, and edit policies.
- `createTemplatePreview({ template, outputPath, stylePack, colors, data })`
- `buildContextPacket({ contextItems, outputPath, title, intent })`
- `composeFromContext({ contextPacket, contextPacketPath, targetProfile, profile, outputPath, stylePack, title })`
- `evidenceCoverageReport({ composition, compositionPath, outputPath })`
- `patchPlan({ inputPath, operations, outputPath, compositionPath, layerManifestPath, reason })`
- `patchPreview({ patchManifest, patchManifestPath, outputPath })`
- `patchApply({ patchManifest, patchManifestPath, outputPath })`
- `patchVerify({ patchManifest, patchManifestPath, patchedPath })`
- `exportBundle({ artifactPaths, outputPath, title, metadata })`
- `verifyBundle({ bundlePath })`
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
