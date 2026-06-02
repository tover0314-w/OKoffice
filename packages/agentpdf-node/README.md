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

const claude = await client.setupClaudeCode({
  outputPath: ".mcp.json",
  safeRoot: "${CLAUDE_PROJECT_DIR:-.}",
});
const result = await client.createTextPdf({
  text: "Hello from Node",
  outputPath: ".agentpdf-out/node.pdf",
});
const report = await client.createMarkdownPdf({
  markdown: "# Agent Report\n\n- Local first\n- Styled locally",
  outputPath: ".agentpdf-out/node-report.pdf",
  stylePack: "business_report_modern",
});
const brief = await client.createFromPrompt({
  prompt: "Create a proposal about local PDF template agents.",
  outputPath: ".agentpdf-out/node-proposal.pdf",
  template: "proposal",
  stylePack: "business_report_modern",
  colors: { primary: "#4f46e5", accent: "#f59e0b" },
});
const catalog = await client.createTemplates();
const templatePacks = await client.createTemplatePacks({
  outputPath: ".agentpdf-out/template-packs.json",
});
const packValidation = await client.validateTemplatePack({
  templatePackPath: "examples/template-packs/local-agent-starter.json",
  outputPath: ".agentpdf-out/template-pack.validation.json",
});
const packPlan = await client.planTemplatePack({
  templatePackPath: "examples/template-packs/local-agent-starter.json",
  profile: "technical_audit",
  contextPacketPath: ".agentpdf-out/context.packet.json",
  plannedOutputPath: ".agentpdf-out/board-audit.pdf",
  outputPath: ".agentpdf-out/board-audit.plan.json",
});
const agentRun = await client.createAgent({
  templatePackPath: "examples/template-packs/local-agent-starter.json",
  profile: "technical_audit",
  contextPacketPath: ".agentpdf-out/context.packet.json",
  outputPath: ".agentpdf-out/board-audit.pdf",
  planOutputPath: ".agentpdf-out/board-audit.plan.json",
  coverageOutputPath: ".agentpdf-out/board-audit.coverage.json",
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
const packet = await client.buildContextPacket({
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
const audit = await client.composeFromContext({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "technical_audit",
  outputPath: ".agentpdf-out/technical-audit.pdf",
});
const deck = await client.composeFromContext({
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
      op: "append_code_block",
      title: "Risky Function",
      language: "python",
      code: "def risky_total(items):\n    return sum(items)\n",
      source_refs: ["ctx_001"],
    },
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
console.log(brief.usage.template_id, brief.validation?.status);
console.log(catalog.usage.template_count);
console.log(audit.artifacts[0]?.path, deck.usage.slide_count, targetCatalog.usage.profile_catalog.profile_count, targetValidation.usage.profile_validation.is_valid, coverage.usage.uncovered_block_count, patch.usage.operation_count, bundle.usage.bundle_entries.length);
```

## CLI

```bash
agentpdf-node tools
agentpdf-node agent-setup-claude-code -o .mcp.json --safe-root '${CLAUDE_PROJECT_DIR:-.}'
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
agentpdf-node create-templates
agentpdf-node create-template-packs -o template-packs.json
agentpdf-node create-validate-template-pack examples/template-packs/local-agent-starter.json -o template-pack.validation.json
agentpdf-node create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --data examples/create-data/agent-block-audit.json -o board-audit.pdf
agentpdf-node create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --context-packet context.packet.json -o board-audit-from-context.pdf
agentpdf-node create-template-preview --template invoice -o invoice-preview.pdf
agentpdf-node create-from-prompt --prompt "Create a research brief about local PDF agents." -o brief.pdf --template research_brief --style-pack paper_ink --color primary=#4f46e5
agentpdf-node context-build --text "Create a technical audit PDF." --file README.md --item-json examples/context/media-items.json -o context.packet.json
agentpdf-node target-profiles -o target-profiles.json
agentpdf-node target-validate --target-profile '{"profile_id":"media_learning_deck","layout_mode":"slides","accepted_block_types":["slide","audio_reference","video_reference"],"accepted_context_types":["text","audio","video"],"validation_required":["render_check","evidence_coverage_report"]}' -o media-learning-deck.validation.json
agentpdf-node compose-from-context context.packet.json --profile technical_audit -o technical-audit.pdf
agentpdf-node compose-from-context context.packet.json --profile slide_deck -o agent-review-deck.pdf
agentpdf-node evidence-coverage-report technical-audit.composition.json -o technical-audit.coverage.json
agentpdf-node patch-plan technical-audit.pdf --operations '[{"op":"append_table","title":"Runtime Metrics","columns":["metric","value"],"rows":[["latency_ms","42"]],"source_refs":["ctx_002"],"target_slot":"findings"}]' -o technical-audit.patch.json --composition technical-audit.composition.json --layers technical-audit.layers.json
agentpdf-node patch-preview technical-audit.patch.json -o technical-audit.patch-preview.json
agentpdf-node patch-apply technical-audit.patch.json -o technical-audit-patched.pdf
agentpdf-node patch-verify technical-audit.patch.json technical-audit-patched.pdf
agentpdf-node export-bundle --file technical-audit-patched.pdf --file technical-audit.composition.json --file technical-audit.coverage.json --file technical-audit.patch.json -o technical-audit.agentpdf-bundle.zip --title "Technical Audit Bundle" --metadata workflow=context-packet-patch
agentpdf-node verify-bundle technical-audit.agentpdf-bundle.zip
```

## Design

- REST-first client for local and future hosted API compatibility.
- Typed `ToolResult`, `Artifact`, `ValidationReport`, `ToolManifest`, and tool inputs.
- Convenience wrappers for document/page inspect, workflow planning/execution/reporting, context packet building, context-to-PDF composition, template-pack creation with slot routing evidence and `.layers.json` edit manifests, evidence coverage, patch plan/preview/apply/verify, artifact bundle export/verify, merge, reorder, insert blank pages, compression, repair/rewrite, image-to-PDF, embedded image extraction, watermark, page numbers, text/Markdown/prompt-template creation, validation, render/blank checks, lite parse, and local RAG.
- Failed PDF tools still return structured failed `ToolResult` bodies instead of being hidden behind generic exceptions.
- HTTP or non-AgentPDF failures throw `AgentPDFHttpError`.
