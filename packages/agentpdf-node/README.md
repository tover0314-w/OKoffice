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
const kilo = await client.setupKiloCode({
  outputPath: "kilo-code.mcp.json",
  safeRoot: ".",
});
const openclaw = await client.setupOpenClaw({
  outputPath: "openclaw.mcp.json",
  safeRoot: ".",
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
  contextClassificationOutputPath: ".agentpdf-out/board-audit.context-classification.json",
  contextReportOutputPath: ".agentpdf-out/board-audit.context-report.pdf",
  contextReportJsonOutputPath: ".agentpdf-out/board-audit.context-report.json",
  bundleOutputPath: ".agentpdf-out/board-audit.agentpdf-bundle.zip",
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
const composerItem = await client.ingestContext({
  contextItem: {
    path: "src/agentpdf/compose/context.py",
    role: "code_evidence",
    label: "Composer Source",
  },
  outputPath: ".agentpdf-out/composer.context-item.json",
});
const codeSnapshot = await client.codeSnapshot({
  path: "src/agentpdf/compose/context.py",
  outputPath: ".agentpdf-out/composer.snapshot.context-item.json",
  lineStart: 1,
  lineEnd: 80,
  repositoryRoot: ".",
});
const dataProfile = await client.dataProfile({
  path: "examples/create-data/metrics.csv",
  outputPath: ".agentpdf-out/metrics.profile.context-item.json",
  label: "Runtime Metrics",
});
const agentPacket = await client.contextPacket({
  contextItems: [
    composerItem.usage.context_item,
    { text: "Create a technical audit PDF from pre-ingested code evidence.", role: "brief" },
  ],
  outputPath: ".agentpdf-out/agent.context.packet.json",
  title: "Agent Packet",
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
const classification = await client.classifyContext({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "technical_audit",
  outputPath: ".agentpdf-out/context.classification.json",
});
const compositionPlan = await client.composePlan({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "technical_audit",
  outputPath: ".agentpdf-out/technical-audit.plan.json",
});
const renderedFromIr = await client.composeRenderIr({
  compositionPath: ".agentpdf-out/technical-audit.plan.json",
  outputPath: ".agentpdf-out/technical-audit-from-ir.pdf",
});
const targetCatalog = await client.targetProfiles({
  outputPath: ".agentpdf-out/target-profiles.json",
});
const targetSelection = await client.selectTargetProfile({
  goal: "Create a slide deck from meeting notes and source evidence.",
  contextPacketPath: ".agentpdf-out/context.packet.json",
  outputPath: ".agentpdf-out/selected-profile.json",
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
  renderer: "html",
  htmlOutputPath: ".agentpdf-out/technical-audit.html",
});
const rerenderedAudit = await client.renderHtmlPackage({
  packagePath: ".agentpdf-out/technical-audit.html-manifest.json",
  outputPath: ".agentpdf-out/technical-audit-rendered.pdf",
});
const deck = await client.composeFromContext({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "slide_deck",
  outputPath: ".agentpdf-out/agent-review-deck.pdf",
});
const codeBlock = await client.composeAddCodeBlock({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.code.pdf",
  title: "Risky Function",
  code: "def risky_total(items):\n    return sum(items)\n",
  language: "python",
  sourceRefs: ["ctx_002"],
  targetSlot: "code_review",
  compositionPath: ".agentpdf-out/technical-audit.composition.json",
});
await client.composeAddTable({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.table.pdf",
  title: "Runtime Metrics",
  columns: ["metric", "value"],
  rows: [["latency_ms", "42"], ["error_rate", "0.01"]],
  sourceRefs: ["ctx_003"],
});
await client.composeAddFigure({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.figure.pdf",
  title: "Architecture Figure",
  imagePath: "assets/brand/okpdf-logo.png",
  caption: "Local visual evidence.",
  sourceRefs: ["ctx_004"],
});
await client.composeAddAppendix({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.appendix.pdf",
  title: "Source Appendix",
  markdown: "## Sources\n\n- ctx_002\n- ctx_003\n- ctx_004",
  sourceRefs: ["ctx_002", "ctx_003", "ctx_004"],
});
await client.composeAddCitation({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.citation.pdf",
  title: "Source Citation",
  quote: "Cited claim",
  source: "https://example.com/research",
  sourceRefs: ["ctx_web"],
  targetSlot: "citations",
});
await client.composeAddMediaReference({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.media.pdf",
  title: "Meeting Audio",
  mediaPath: "meeting.mp3",
  mediaKind: "audio",
  transcriptExcerpt: "00:00 Kickoff",
  sourceRefs: ["ctx_audio"],
  targetSlot: "media_evidence",
});
await client.composeAddSlide({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.slide.pdf",
  title: "Review Slide",
  subtitle: "Decision evidence",
  body: ["Patch transactions can append slide-like evidence pages."],
  sourceRefs: ["ctx_slide"],
  targetSlot: "evidence_slide",
});
const coverage = await client.evidenceCoverageReport({
  compositionPath: ".agentpdf-out/technical-audit.composition.json",
  outputPath: ".agentpdf-out/technical-audit.coverage.json",
});
const sourceMap = await client.evidenceMapSources({
  compositionPath: ".agentpdf-out/technical-audit.composition.json",
  contextPacketPath: ".agentpdf-out/context.packet.json",
  outputPath: ".agentpdf-out/technical-audit.source-map.json",
});
const artifactSourceMap = await client.artifactSourceMap({
  compositionPath: ".agentpdf-out/technical-audit.composition.json",
  contextPacketPath: ".agentpdf-out/context.packet.json",
  outputPath: ".agentpdf-out/technical-audit.artifact-source-map.json",
  title: "Technical Audit Artifact Source Map",
});
const citations = await client.evidenceCiteClaims({
  claims: [
    {
      claim_id: "claim_latency",
      text: "Runtime metrics include latency evidence.",
      source_refs: ["ctx_002"],
    },
  ],
  sourceMapPath: ".agentpdf-out/technical-audit.source-map.json",
  outputPath: ".agentpdf-out/technical-audit.citations.json",
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
const artifactManifest = await client.artifactManifest({
  artifactPaths: [
    ".agentpdf-out/technical-audit-patched.pdf",
    ".agentpdf-out/technical-audit.composition.json",
    ".agentpdf-out/technical-audit.coverage.json",
    ".agentpdf-out/technical-audit.source-map.json",
    ".agentpdf-out/technical-audit.artifact-source-map.json",
    ".agentpdf-out/technical-audit.citations.json",
    ".agentpdf-out/technical-audit.patch.json",
  ],
  outputPath: ".agentpdf-out/technical-audit.artifacts.json",
  title: "Technical Audit Artifacts",
  metadata: { workflow: "context-packet-patch", agent: "node" },
});
const artifactGraph = await client.artifactGraph({
  artifactManifestPath: ".agentpdf-out/technical-audit.artifacts.json",
  outputPath: ".agentpdf-out/technical-audit.artifact-graph.json",
  title: "Technical Audit Artifact Graph",
});
await client.patchPlan({
  inputPath: ".agentpdf-out/board-audit.pdf",
  operations: [
    {
      op: "regenerate_block",
      title: "Regenerated Runtime Metrics Summary",
      replacement_markdown:
        "## Regenerated Runtime Metrics Summary\n\nRegenerated from ctx_metrics with layer evidence.",
      source_refs: ["ctx_metrics"],
      layer_id: "layer_blk_agent_table",
      block_id: "blk_agent_table",
      target_slot: "findings",
    },
  ],
  outputPath: ".agentpdf-out/board-audit.regenerate.patch.json",
  compositionPath: ".agentpdf-out/board-audit.composition.json",
  layerManifestPath: ".agentpdf-out/board-audit.layers.json",
  reason: "Regenerate a template block with layer evidence.",
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
const renderedDiff = await client.visualDiff({
  beforePath: ".agentpdf-out/node-v1.pdf",
  afterPath: ".agentpdf-out/node-v2.pdf",
  pages: "1",
});
const visualValidation = await client.validationVisualDiff({
  beforePath: ".agentpdf-out/node-v1.pdf",
  afterPath: ".agentpdf-out/node-v2.pdf",
  maxDifferenceRatio: 0.001,
});
const redacted = await client.securityRedact({
  inputPath: ".agentpdf-out/sensitive.pdf",
  outputPath: ".agentpdf-out/sensitive-redacted.pdf",
  regions: [{ page: 1, bbox: [60, 700, 280, 760], label: "secret" }],
});
const redactionVerified = await client.securityVerifyRedaction({
  inputPath: ".agentpdf-out/sensitive-redacted.pdf",
  searchTerms: ["SECRET-CODE-123"],
});
const redactionCheck = await client.validationRedactionCheck({
  inputPath: ".agentpdf-out/sensitive-redacted.pdf",
  searchTerms: ["SECRET-CODE-123"],
});
const form = await client.formsCreate({
  outputPath: ".agentpdf-out/contact-form.pdf",
  fields: [{ name: "name", label: "Name", required: true }],
});
const filledForm = await client.formsImportData({
  inputPath: ".agentpdf-out/contact-form.pdf",
  data: { name: "Ada" },
  outputPath: ".agentpdf-out/contact-form-filled.pdf",
});
const formValidation = await client.formsValidate({
  inputPath: ".agentpdf-out/contact-form-filled.pdf",
  requiredFields: ["name"],
});
const scan = await client.ocrScanToPdf({
  imagePaths: ["assets/brand/okpdf-logo.png"],
  outputPath: ".agentpdf-out/scan.pdf",
});
const ocrText = await client.ocr({
  inputPath: ".agentpdf-out/scan.pdf",
  languages: ["eng"],
});
const searchableScan = await client.ocrSearchablePdf({
  inputPath: ".agentpdf-out/scan.pdf",
  outputPath: ".agentpdf-out/scan-searchable.pdf",
  languages: ["eng"],
});
const preparedScan = await client.ocrMultilingual({
  inputPath: ".agentpdf-out/scan.pdf",
  outputPath: ".agentpdf-out/scan-multilingual.pdf",
  languages: ["eng", "chi_sim"],
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
console.log(audit.artifacts[0]?.path, deck.usage.slide_count, codeBlock.usage.compose_block, targetCatalog.usage.profile_catalog.profile_count, targetSelection.usage.selected_profile_id, targetValidation.usage.profile_validation.is_valid, coverage.usage.uncovered_block_count, patch.usage.operation_count, bundle.usage.bundle_entries.length);
```

## CLI

```bash
agentpdf-node tools
agentpdf-node agent-setup-claude-code -o .mcp.json --safe-root '${CLAUDE_PROJECT_DIR:-.}'
agentpdf-node agent-setup-codex -o codex.mcp.json --safe-root .
agentpdf-node agent-setup-kilo-code -o kilo-code.mcp.json --safe-root .
agentpdf-node agent-setup-openclaw -o openclaw.mcp.json --safe-root .
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
agentpdf-node semantic-diff cover-v1.pdf cover-v2.pdf --pages 1
agentpdf-node version-report cover-v1.pdf cover-v2.pdf -o cover.version-report.md
agentpdf-node compare-visual-diff cover-v1.pdf cover-v2.pdf --pages 1
agentpdf-node visual-diff cover-v1.pdf cover-v2.pdf --max-difference-ratio 0.001
agentpdf-node security-redact sensitive.pdf -o sensitive-redacted.pdf --region '{"page":1,"bbox":[60,700,280,760],"label":"secret"}'
agentpdf-node security-verify-redaction sensitive-redacted.pdf --search-term SECRET-CODE-123
agentpdf-node redaction-check sensitive-redacted.pdf --search-term SECRET-CODE-123
agentpdf-node parse-figures cover-numbered.pdf
agentpdf-node parse-formulas cover-numbered.pdf
agentpdf-node parse-charts cover-numbered.pdf
agentpdf-node parse-references cover-numbered.pdf
agentpdf-node forms-create --field '{"name":"name","label":"Name","required":true}' -o contact-form.pdf
agentpdf-node forms-import-data contact-form.pdf --data '{"name":"Ada"}' -o contact-form-filled.pdf
agentpdf-node forms-validate contact-form-filled.pdf --required-field name
agentpdf-node ocr-scan-to-pdf cover.png -o scan.pdf
agentpdf-node ocr scan.pdf --language eng
agentpdf-node ocr-searchable-pdf scan.pdf -o scan-searchable.pdf --language eng
agentpdf-node ocr-despeckle scan.pdf -o scan-despeckled.pdf
agentpdf-node ocr-remove-existing scan.pdf -o scan-no-ocr.pdf
agentpdf-node ocr-multilingual scan.pdf --language eng --language chi_sim -o scan-multilingual.pdf
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
agentpdf-node create-agent examples/template-packs/local-agent-starter.json --profile technical_audit --context-packet context.packet.json -o board-audit-agent.pdf --plan-output board-audit-agent.plan.json --coverage-output board-audit-agent.coverage.json --context-classification-output board-audit-agent.context-classification.json --context-report-output board-audit-agent.context-report.pdf --context-report-json-output board-audit-agent.context-report.json --bundle-output board-audit-agent.agentpdf-bundle.zip
agentpdf-node create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --data examples/create-data/agent-block-audit.json -o board-audit.pdf
agentpdf-node create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --context-packet context.packet.json -o board-audit-from-context.pdf --renderer html --html-output board-audit-from-context.html
agentpdf-node create-template-preview --template invoice -o invoice-preview.pdf
agentpdf-node create-from-prompt --prompt "Create a research brief about local PDF agents." -o brief.pdf --template research_brief --style-pack paper_ink --color primary=#4f46e5
agentpdf-node context-ingest --file src/agentpdf/compose/context.py --role code_evidence --label "Composer Source" -o composer.context-item.json
agentpdf-node context-ingest --link okpdf.dev/docs/context --role citation --label "Context Docs" -o context-docs.context-item.json
agentpdf-node code-snapshot src/agentpdf/compose/context.py --line-start 1 --line-end 80 --repository-root . -o composer.snapshot.context-item.json
agentpdf-node data-profile examples/create-data/metrics.csv --label "Runtime Metrics" -o metrics.profile.context-item.json
agentpdf-node context-image-analyze assets/brand/okpdf-logo.png --skip-ocr
agentpdf-node context-packet --item-json composer.context-item.json --text "Create a technical audit PDF from pre-ingested code evidence." -o agent.context.packet.json
agentpdf-node context-build --text "Create a technical audit PDF." --file README.md --link okpdf.dev/docs/context --item-json examples/context/media-items.json -o context.packet.json
agentpdf-node context-classify context.packet.json --profile technical_audit -o context.classification.json
agentpdf-node target-profiles -o target-profiles.json
agentpdf-node target-validate --target-profile '{"profile_id":"media_learning_deck","layout_mode":"slides","accepted_block_types":["slide","audio_reference","video_reference"],"accepted_context_types":["text","audio","video"],"validation_required":["render_check","evidence_coverage_report"]}' -o media-learning-deck.validation.json
agentpdf-node compose-plan context.packet.json --profile technical_audit -o technical-audit.plan.json
agentpdf-node compose-render-ir technical-audit.plan.json -o technical-audit-from-ir.pdf
agentpdf-node compose-from-context context.packet.json --profile technical_audit -o technical-audit.pdf --renderer html --html-output technical-audit.html
agentpdf-node render-html-package technical-audit.html-manifest.json -o technical-audit-rendered.pdf
agentpdf-node create-html-package --html "<main><h1>HTML First</h1><p>Inspectable source before PDF.</p></main>" --html-output html-first.html --title "HTML First"
agentpdf-node render-html-package html-first.html-manifest.json -o html-first.pdf
agentpdf-node qa-visual-report --input html-first.pdf --html-package-manifest html-first.html-manifest.json --pages 1
agentpdf-node artifact-manifest --file html-first.pdf --file html-first.html --file html-first.html-manifest.json -o html-first.artifacts.json --title "HTML First Artifacts" --metadata workflow=html-first-createpdf
agentpdf-node artifact-graph --manifest html-first.artifacts.json -o html-first.artifact-graph.json --title "HTML First Artifact Graph"
agentpdf-node authoring-plan --brief examples/research_deck_brief.json
agentpdf-node research-plan --brief examples/research_deck_brief.json
agentpdf-node research-source-cards --brief examples/research_deck_brief.json --sources examples/research_deck_sources.json
agentpdf-node research-evidence-cards --source-cards examples/research_deck_source_cards.json
agentpdf-node design-tokens --theme consulting --color primary_color=#123456
agentpdf-node workflow-research-deck --brief examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --html-output research-deck.html --pdf-output research-deck.pdf --artifact-dir research-deck-artifacts --execute
agentpdf-node compose-from-context context.packet.json --profile slide_deck -o agent-review-deck.pdf
agentpdf-node compose-add-code-block technical-audit.pdf --title "Risk Function" --code "def risky_total(items): return sum(items)" --language python --source-ref ctx_002 --target-slot code_review -o technical-audit.code.pdf
agentpdf-node compose-add-table technical-audit.pdf --title "Runtime Metrics" --columns metric,value --row latency_ms,42 --source-ref ctx_003 -o technical-audit.table.pdf
agentpdf-node compose-add-figure technical-audit.pdf --title "Architecture Figure" --image assets/brand/okpdf-logo.png --caption "Local visual evidence." --source-ref ctx_004 -o technical-audit.figure.pdf
agentpdf-node compose-add-appendix technical-audit.pdf --title "Source Appendix" --markdown "## Sources" --source-ref ctx_002 -o technical-audit.appendix.pdf
agentpdf-node compose-add-citation technical-audit.pdf --title "Source Citation" --source https://example.com/research --quote "Cited claim" --source-ref ctx_web -o technical-audit.citation.pdf
agentpdf-node compose-add-media-reference technical-audit.pdf --title "Meeting Audio" --media meeting.mp3 --media-kind audio --transcript-excerpt "00:00 Kickoff" --source-ref ctx_audio -o technical-audit.media.pdf
agentpdf-node compose-add-slide technical-audit.pdf --title "Review Slide" --body "Decision evidence" --source-ref ctx_slide -o technical-audit.slide.pdf
agentpdf-node evidence-context-packet-report context.packet.json -o context-report.pdf --report-output context-report.json
agentpdf-node evidence-coverage-report technical-audit.composition.json -o technical-audit.coverage.json
agentpdf-node evidence-map-sources technical-audit.composition.json --context-packet context.packet.json -o technical-audit.source-map.json
agentpdf-node artifact-source-map --composition technical-audit.composition.json --context-packet context.packet.json -o technical-audit.artifact-source-map.json --title "Technical Audit Artifact Source Map"
agentpdf-node evidence-cite-claims --claims claims.json --source-map technical-audit.source-map.json -o technical-audit.citations.json
agentpdf-node patch-plan technical-audit.pdf --operations '[{"op":"append_table","title":"Runtime Metrics","columns":["metric","value"],"rows":[["latency_ms","42"]],"source_refs":["ctx_002"],"target_slot":"findings"}]' -o technical-audit.patch.json --composition technical-audit.composition.json --layers technical-audit.layers.json
agentpdf-node patch-preview technical-audit.patch.json -o technical-audit.patch-preview.json
agentpdf-node patch-apply technical-audit.patch.json -o technical-audit-patched.pdf
agentpdf-node patch-verify technical-audit.patch.json technical-audit-patched.pdf
agentpdf-node artifact-manifest --file technical-audit-patched.pdf --file context.packet.json --file technical-audit.composition.json --file technical-audit.coverage.json --file technical-audit.source-map.json --file technical-audit.artifact-source-map.json --file technical-audit.citations.json --file technical-audit.patch.json -o technical-audit.artifacts.json --title "Technical Audit Artifacts" --metadata workflow=context-packet-patch
agentpdf-node artifact-graph --manifest technical-audit.artifacts.json -o technical-audit.artifact-graph.json --title "Technical Audit Artifact Graph"
agentpdf-node export-bundle --file technical-audit-patched.pdf --file context.packet.json --file technical-audit.composition.json --file technical-audit.coverage.json --file technical-audit.patch.json -o technical-audit.agentpdf-bundle.zip --title "Technical Audit Bundle" --metadata workflow=context-packet-patch
agentpdf-node verify-bundle technical-audit.agentpdf-bundle.zip
```

## Design

- REST-first client for local and future hosted API compatibility.
- Typed `ToolResult`, `Artifact`, `ValidationReport`, `ToolManifest`, and tool inputs.
- Convenience wrappers for Claude Code, Codex, Kilo Code, and OpenClaw setup, document/page inspect, workflow planning/execution/reporting, context ingest, code snapshots, data profiles, context packet building, context classification, target profile catalog/selection/validation, composition planning, IR rendering, context packet PDF/JSON audit reports, context-to-PDF composition, one-step append-only compose blocks for code/table/figure/appendix evidence, template-pack creation with slot routing evidence and `.layers.json` edit manifests, evidence coverage, artifact source map, manifest, and graph generation, patch plan/preview/apply/verify, artifact bundle export/verify, merge, reorder, insert blank pages, compression, repair/rewrite, image-to-PDF, embedded image extraction, watermark, page numbers, metadata page info, security metadata removal/redaction/verification, text/Markdown/prompt-template creation, validation/page-count checks, render/blank/redaction checks, lite parse, semantic parse hints, local semantic diff/version reports, and local RAG.
- Failed PDF tools still return structured failed `ToolResult` bodies instead of being hidden behind generic exceptions.
- HTTP or non-AgentPDF failures throw `AgentPDFHttpError`.
