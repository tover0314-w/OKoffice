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
node packages/agentpdf-node/dist/src/cli.js agent-setup-codex -o codex.mcp.json --safe-root .
node packages/agentpdf-node/dist/src/cli.js agent-setup-kilo-code -o kilo-code.mcp.json --safe-root .
node packages/agentpdf-node/dist/src/cli.js agent-setup-openclaw -o openclaw.mcp.json --safe-root .
node packages/agentpdf-node/dist/src/cli.js workflow-plan --goal "Chat with this PDF and cite answers" --input-path .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js workflow-run --payload '{"steps":[{"step_id":"inspect","tool":"pdf.inspect.document","input":{"path":"<input.pdf>"}}],"input_path":".agentpdf-out/node-report.pdf"}' --binding '<question>=What is this report?' --dry-run
node packages/agentpdf-node/dist/src/cli.js workflow-report --payload '{"run_id":"wfrun_node","status":"succeeded","planned_steps":1,"executed_steps":1,"failed_steps":0,"step_results":[]}' -o .agentpdf-out/node-workflow-report.md
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
node packages/agentpdf-node/dist/src/cli.js create-markdown --markdown-file examples/sample-documents/business_report.md -o .agentpdf-out/node-report.pdf
node packages/agentpdf-node/dist/src/cli.js create-template-packs -o .agentpdf-out/template-packs.json
node packages/agentpdf-node/dist/src/cli.js create-validate-template-pack examples/template-packs/local-agent-starter.json -o .agentpdf-out/template-pack.validation.json
node packages/agentpdf-node/dist/src/cli.js create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --data examples/create-data/agent-block-audit.json -o .agentpdf-out/board-audit.pdf
node packages/agentpdf-node/dist/src/cli.js create-from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --context-packet .agentpdf-out/context.packet.json -o .agentpdf-out/board-audit-from-context.pdf --renderer html --html-output .agentpdf-out/board-audit-from-context.html
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
node packages/agentpdf-node/dist/src/cli.js semantic-diff .agentpdf-out/node-report-v1.pdf .agentpdf-out/node-report-v2.pdf --pages 1
node packages/agentpdf-node/dist/src/cli.js version-report .agentpdf-out/node-report-v1.pdf .agentpdf-out/node-report-v2.pdf -o .agentpdf-out/node-report.version-report.md
node packages/agentpdf-node/dist/src/cli.js compare-visual-diff .agentpdf-out/node-report-v1.pdf .agentpdf-out/node-report-v2.pdf --pages 1
node packages/agentpdf-node/dist/src/cli.js visual-diff .agentpdf-out/node-report-v1.pdf .agentpdf-out/node-report-v2.pdf --max-difference-ratio 0.001
node packages/agentpdf-node/dist/src/cli.js security-redact .agentpdf-out/sensitive.pdf -o .agentpdf-out/sensitive-redacted.pdf --region '{"page":1,"bbox":[60,700,280,760],"label":"secret"}'
node packages/agentpdf-node/dist/src/cli.js security-verify-redaction .agentpdf-out/sensitive-redacted.pdf --search-term SECRET-CODE-123
node packages/agentpdf-node/dist/src/cli.js redaction-check .agentpdf-out/sensitive-redacted.pdf --search-term SECRET-CODE-123
node packages/agentpdf-node/dist/src/cli.js parse-figures .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js parse-formulas .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js parse-charts .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js parse-references .agentpdf-out/node-report-draft.pdf
node packages/agentpdf-node/dist/src/cli.js forms-create --field '{"name":"name","label":"Name","required":true}' -o .agentpdf-out/contact-form.pdf
node packages/agentpdf-node/dist/src/cli.js forms-import-data .agentpdf-out/contact-form.pdf --data '{"name":"Ada"}' -o .agentpdf-out/contact-form-filled.pdf
node packages/agentpdf-node/dist/src/cli.js forms-validate .agentpdf-out/contact-form-filled.pdf --required-field name
node packages/agentpdf-node/dist/src/cli.js ocr-scan-to-pdf assets/brand/okpdf-logo.png -o .agentpdf-out/scan.pdf
node packages/agentpdf-node/dist/src/cli.js ocr .agentpdf-out/scan.pdf --language eng
node packages/agentpdf-node/dist/src/cli.js ocr-searchable-pdf .agentpdf-out/scan.pdf -o .agentpdf-out/scan-searchable.pdf --language eng
node packages/agentpdf-node/dist/src/cli.js ocr-despeckle .agentpdf-out/scan.pdf -o .agentpdf-out/scan-despeckled.pdf
node packages/agentpdf-node/dist/src/cli.js ocr-remove-existing .agentpdf-out/scan.pdf -o .agentpdf-out/scan-no-ocr.pdf
node packages/agentpdf-node/dist/src/cli.js ocr-multilingual .agentpdf-out/scan.pdf --language eng --language chi_sim -o .agentpdf-out/scan-multilingual.pdf
node packages/agentpdf-node/dist/src/cli.js pdf-to-json .agentpdf-out/node-report-draft.pdf -o .agentpdf-out/node-report.ir.json
node packages/agentpdf-node/dist/src/cli.js pdf-to-markdown .agentpdf-out/node-report-draft.pdf -o .agentpdf-out/node-report.md
node packages/agentpdf-node/dist/src/cli.js rag-ingest .agentpdf-out/node-report-draft.pdf --index .agentpdf-out/node-report.index.json
node packages/agentpdf-node/dist/src/cli.js rag-chat .agentpdf-out/node-report-draft.pdf --question "What is this report about?" --report-output .agentpdf-out/node-chat-report.pdf --highlight-output .agentpdf-out/node-chat-highlighted.pdf
node packages/agentpdf-node/dist/src/cli.js rag-query .agentpdf-out/node-report.index.json --query "What is this report about?"
node packages/agentpdf-node/dist/src/cli.js rag-search .agentpdf-out/node-report.index.json --query "report"
node packages/agentpdf-node/dist/src/cli.js rag-cite-answer .agentpdf-out/node-report.index.json --answer "This report is local-first."
node packages/agentpdf-node/dist/src/cli.js rag-highlight-sources .agentpdf-out/node-report.index.json --answer "This report is local-first." -o .agentpdf-out/node-report-highlighted.pdf
node packages/agentpdf-node/dist/src/cli.js rag-export-report .agentpdf-out/node-report.index.json --question "What is this report about?" --answer "This report is local-first." -o .agentpdf-out/node-report-rag.pdf
node packages/agentpdf-node/dist/src/cli.js context-ingest --file src/agentpdf/compose/context.py --role code_evidence --label "Composer Source" -o .agentpdf-out/composer.context-item.json
node packages/agentpdf-node/dist/src/cli.js context-ingest --link okpdf.dev/docs/context --role citation --label "Context Docs" -o .agentpdf-out/context-docs.context-item.json
node packages/agentpdf-node/dist/src/cli.js code-snapshot src/agentpdf/compose/context.py --line-start 1 --line-end 80 --repository-root . -o .agentpdf-out/composer.snapshot.context-item.json
node packages/agentpdf-node/dist/src/cli.js data-profile examples/create-data/metrics.csv --label "Runtime Metrics" -o .agentpdf-out/metrics.profile.context-item.json
node packages/agentpdf-node/dist/src/cli.js context-image-analyze assets/brand/okpdf-logo.png --skip-ocr
node packages/agentpdf-node/dist/src/cli.js context-packet --item-json .agentpdf-out/composer.context-item.json --text "Create a technical audit PDF from pre-ingested code evidence." -o .agentpdf-out/agent.context.packet.json
node packages/agentpdf-node/dist/src/cli.js context-build --text "Create a technical audit PDF." --file README.md --link okpdf.dev/docs/context --item-json examples/context/media-items.json -o .agentpdf-out/context.packet.json
node packages/agentpdf-node/dist/src/cli.js context-classify .agentpdf-out/context.packet.json --profile technical_audit -o .agentpdf-out/context.classification.json
node packages/agentpdf-node/dist/src/cli.js target-profiles -o .agentpdf-out/target-profiles.json
node packages/agentpdf-node/dist/src/cli.js target-validate --target-profile '{"profile_id":"media_learning_deck","layout_mode":"slides","accepted_block_types":["slide","audio_reference","video_reference"],"accepted_context_types":["text","audio","video"],"validation_required":["render_check","evidence_coverage_report"]}' -o .agentpdf-out/media-learning-deck.validation.json
node packages/agentpdf-node/dist/src/cli.js compose-plan .agentpdf-out/context.packet.json --profile technical_audit -o .agentpdf-out/technical-audit.plan.json
node packages/agentpdf-node/dist/src/cli.js compose-render-ir .agentpdf-out/technical-audit.plan.json -o .agentpdf-out/technical-audit-from-ir.pdf
node packages/agentpdf-node/dist/src/cli.js compose-from-context .agentpdf-out/context.packet.json --profile technical_audit -o .agentpdf-out/technical-audit.pdf --renderer html --html-output .agentpdf-out/technical-audit.html
node packages/agentpdf-node/dist/src/cli.js render-html-package .agentpdf-out/technical-audit.html-manifest.json -o .agentpdf-out/technical-audit-rendered.pdf
node packages/agentpdf-node/dist/src/cli.js create-html-package --html "<main><h1>HTML First</h1><p>Inspectable source before PDF.</p></main>" --html-output .agentpdf-out/html-first.html --title "HTML First"
node packages/agentpdf-node/dist/src/cli.js render-html-package .agentpdf-out/html-first.html-manifest.json -o .agentpdf-out/html-first.pdf
node packages/agentpdf-node/dist/src/cli.js qa-visual-report --input .agentpdf-out/html-first.pdf --html-package-manifest .agentpdf-out/html-first.html-manifest.json --pages 1
node packages/agentpdf-node/dist/src/cli.js artifact-manifest --file .agentpdf-out/html-first.pdf --file .agentpdf-out/html-first.html --file .agentpdf-out/html-first.html-manifest.json -o .agentpdf-out/html-first.artifacts.json --title "HTML First Artifacts" --metadata workflow=html-first-createpdf
node packages/agentpdf-node/dist/src/cli.js artifact-graph --manifest .agentpdf-out/html-first.artifacts.json -o .agentpdf-out/html-first.artifact-graph.json --title "HTML First Artifact Graph"
node packages/agentpdf-node/dist/src/cli.js createpdf --html "<main><h1>CreatePDF</h1><p>HTML-first workflow with audit evidence.</p></main>" --html-output .agentpdf-out/createpdf.html --pdf-output .agentpdf-out/createpdf.pdf --artifact-dir .agentpdf-out/createpdf-audit --title "CreatePDF"
node packages/agentpdf-node/dist/src/cli.js authoring-plan --brief examples/research_deck_brief.json
node packages/agentpdf-node/dist/src/cli.js research-plan --brief examples/research_deck_brief.json
node packages/agentpdf-node/dist/src/cli.js research-source-cards --brief examples/research_deck_brief.json --sources examples/research_deck_sources.json
node packages/agentpdf-node/dist/src/cli.js research-evidence-cards --source-cards examples/research_deck_source_cards.json
node packages/agentpdf-node/dist/src/cli.js design-tokens --theme consulting --color primary_color=#123456
node packages/agentpdf-node/dist/src/cli.js workflow-research-deck --brief examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --html-output .agentpdf-out/research-deck.html --pdf-output .agentpdf-out/research-deck.pdf --artifact-dir .agentpdf-out/research-deck-artifacts --execute
node packages/agentpdf-node/dist/src/cli.js compose-from-context .agentpdf-out/context.packet.json --profile slide_deck -o .agentpdf-out/agent-review-deck.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-code-block .agentpdf-out/technical-audit.pdf --title "Risk Function" --code "def risky_total(items): return sum(items)" --language python --source-ref ctx_002 --target-slot code_review -o .agentpdf-out/technical-audit.code.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-table .agentpdf-out/technical-audit.pdf --title "Runtime Metrics" --columns metric,value --row latency_ms,42 --source-ref ctx_003 -o .agentpdf-out/technical-audit.table.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-figure .agentpdf-out/technical-audit.pdf --title "Architecture Figure" --image assets/brand/okpdf-logo.png --caption "Local visual evidence." --source-ref ctx_004 -o .agentpdf-out/technical-audit.figure.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-appendix .agentpdf-out/technical-audit.pdf --title "Source Appendix" --markdown "## Sources" --source-ref ctx_002 -o .agentpdf-out/technical-audit.appendix.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-citation .agentpdf-out/technical-audit.pdf --title "Source Citation" --source https://example.com/research --quote "Cited claim" --source-ref ctx_web -o .agentpdf-out/technical-audit.citation.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-media-reference .agentpdf-out/technical-audit.pdf --title "Meeting Audio" --media meeting.mp3 --media-kind audio --transcript-excerpt "00:00 Kickoff" --source-ref ctx_audio -o .agentpdf-out/technical-audit.media.pdf
node packages/agentpdf-node/dist/src/cli.js compose-add-slide .agentpdf-out/technical-audit.pdf --title "Review Slide" --body "Decision evidence" --source-ref ctx_slide -o .agentpdf-out/technical-audit.slide.pdf
node packages/agentpdf-node/dist/src/cli.js evidence-context-packet-report .agentpdf-out/context.packet.json -o .agentpdf-out/context-report.pdf --report-output .agentpdf-out/context-report.json
node packages/agentpdf-node/dist/src/cli.js evidence-coverage-report .agentpdf-out/technical-audit.composition.json -o .agentpdf-out/technical-audit.coverage.json
node packages/agentpdf-node/dist/src/cli.js evidence-map-sources .agentpdf-out/technical-audit.composition.json --context-packet .agentpdf-out/context.packet.json -o .agentpdf-out/technical-audit.source-map.json
node packages/agentpdf-node/dist/src/cli.js artifact-source-map --composition .agentpdf-out/technical-audit.composition.json --context-packet .agentpdf-out/context.packet.json -o .agentpdf-out/technical-audit.artifact-source-map.json --title "Technical Audit Artifact Source Map"
node packages/agentpdf-node/dist/src/cli.js evidence-cite-claims --claims .agentpdf-out/claims.json --source-map .agentpdf-out/technical-audit.source-map.json -o .agentpdf-out/technical-audit.citations.json
node packages/agentpdf-node/dist/src/cli.js patch-plan .agentpdf-out/technical-audit.pdf --operations '[{"op":"append_table","title":"Runtime Metrics","columns":["metric","value"],"rows":[["latency_ms","42"]],"source_refs":["ctx_002"],"target_slot":"findings"}]' -o .agentpdf-out/technical-audit.patch.json --composition .agentpdf-out/technical-audit.composition.json --layers .agentpdf-out/technical-audit.layers.json
node packages/agentpdf-node/dist/src/cli.js patch-preview .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit.patch-preview.json
node packages/agentpdf-node/dist/src/cli.js patch-apply .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit-patched.pdf
node packages/agentpdf-node/dist/src/cli.js patch-verify .agentpdf-out/technical-audit.patch.json .agentpdf-out/technical-audit-patched.pdf
node packages/agentpdf-node/dist/src/cli.js artifact-manifest --file .agentpdf-out/technical-audit-patched.pdf --file .agentpdf-out/context.packet.json --file .agentpdf-out/technical-audit.composition.json --file .agentpdf-out/technical-audit.coverage.json --file .agentpdf-out/technical-audit.source-map.json --file .agentpdf-out/technical-audit.artifact-source-map.json --file .agentpdf-out/technical-audit.citations.json --file .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit.artifacts.json --title "Technical Audit Artifacts" --metadata workflow=context-packet-patch
node packages/agentpdf-node/dist/src/cli.js artifact-graph --manifest .agentpdf-out/technical-audit.artifacts.json -o .agentpdf-out/technical-audit.artifact-graph.json --title "Technical Audit Artifact Graph"
node packages/agentpdf-node/dist/src/cli.js export-bundle --file .agentpdf-out/technical-audit-patched.pdf --file .agentpdf-out/context.packet.json --file .agentpdf-out/technical-audit.composition.json --file .agentpdf-out/technical-audit.coverage.json --file .agentpdf-out/technical-audit.patch.json -o .agentpdf-out/technical-audit.agentpdf-bundle.zip --title "Technical Audit Bundle" --metadata workflow=context-packet-patch
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
const kilo = await client.setupKiloCode({
  outputPath: "kilo-code.mcp.json",
  safeRoot: ".",
});
const openclaw = await client.setupOpenClaw({
  outputPath: "openclaw.mcp.json",
  safeRoot: ".",
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
const renderedDiff = await client.visualDiff({
  beforePath: ".agentpdf-out/report-v1.pdf",
  afterPath: ".agentpdf-out/report-v2.pdf",
  pages: "1",
});
const visualValidation = await client.validationVisualDiff({
  beforePath: ".agentpdf-out/report-v1.pdf",
  afterPath: ".agentpdf-out/report-v2.pdf",
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
const agentRun = await client.createAgent({
  templatePackPath: "examples/template-packs/local-agent-starter.json",
  profile: "technical_audit",
  contextPacketPath: ".agentpdf-out/context.packet.json",
  outputPath: ".agentpdf-out/board-audit-agent.pdf",
  planOutputPath: ".agentpdf-out/board-audit-agent.plan.json",
  coverageOutputPath: ".agentpdf-out/board-audit-agent.coverage.json",
  contextClassificationOutputPath: ".agentpdf-out/board-audit-agent.context-classification.json",
  contextReportOutputPath: ".agentpdf-out/board-audit-agent.context-report.pdf",
  contextReportJsonOutputPath: ".agentpdf-out/board-audit-agent.context-report.json",
  bundleOutputPath: ".agentpdf-out/board-audit-agent.agentpdf-bundle.zip",
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
const composedAudit = await client.composeFromContext({
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
const composedDeck = await client.composeFromContext({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  profile: "slide_deck",
  outputPath: ".agentpdf-out/agent-review-deck.pdf",
});
const codeBlock = await client.composeAddCodeBlock({
  inputPath: ".agentpdf-out/technical-audit.pdf",
  outputPath: ".agentpdf-out/technical-audit.code.pdf",
  title: "Risk Function",
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
const contextReport = await client.contextPacketReport({
  contextPacketPath: ".agentpdf-out/context.packet.json",
  outputPath: ".agentpdf-out/context-report.pdf",
  reportOutputPath: ".agentpdf-out/context-report.json",
  title: "Context Packet Report",
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
console.log(codeBlock.usage.compose_block);
console.log(targetCatalog.usage.profile_catalog.profile_count, targetSelection.usage.selected_profile_id, targetValidation.usage.profile_validation.is_valid);
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
- `setupClaudeCode({ outputPath, safeRoot, command, argsPrefix, serverName, scope })`
- `setupCodex({ outputPath, safeRoot, command, argsPrefix, serverName })`
- `setupKiloCode({ outputPath, safeRoot, command, argsPrefix, serverName })`
- `setupOpenClaw({ outputPath, safeRoot, command, argsPrefix, serverName })`
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
- `ingestContext({ contextItem, outputPath })`
- `contextPacket({ contextItems, outputPath, title, intent })`
- `buildContextPacket({ contextItems, outputPath, title, intent })`
- `classifyContext({ contextPacket, contextPacketPath, targetProfile, profile, outputPath })`
- `targetProfiles({ outputPath })`
- `selectTargetProfile({ goal, contextPacket, contextPacketPath, preferredProfileId, outputPath })`
- `validateTargetProfile({ targetProfile, targetProfilePath, outputPath })`
- `codeSnapshot({ path, outputPath, label, role, contextItemId, lineStart, lineEnd, repositoryRoot, includeDependencies })`
- `dataProfile({ path, outputPath, label, role, contextItemId, sheet, maxRows })`
- `contextImageAnalyze({ inputPath, languages, runOcr, engine, psm })`
- `composePlan({ contextPacket, contextPacketPath, targetProfile, profile, outputPath, stylePack, title })`
- `composeRenderIr({ composition, compositionPath, outputPath, stylePack, title })`
- `composeFromContext({ contextPacket, contextPacketPath, targetProfile, profile, outputPath, stylePack, title, renderer, htmlOutputPath })`
- `renderHtmlPackage({ packagePath, outputPath })`
- `composeAddCodeBlock({ inputPath, outputPath, title, code, language, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `composeAddTable({ inputPath, outputPath, title, columns, rows, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `composeAddFigure({ inputPath, outputPath, title, imagePath, caption, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `composeAddAppendix({ inputPath, outputPath, title, markdown, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `composeAddCitation({ inputPath, outputPath, title, source, quote, page, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `composeAddMediaReference({ inputPath, outputPath, title, mediaPath, mediaKind, transcriptExcerpt, durationSeconds, chapterCount, keyframeCount, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `composeAddSlide({ inputPath, outputPath, title, body, subtitle, code, table, imagePath, sourceRefs, blockId, targetSlot, compositionPath, layerManifestPath, manifestOutputPath })`
- `evidenceCoverageReport({ composition, compositionPath, outputPath })`
- `evidenceMapSources({ composition, compositionPath, blocks, claims, contextPacket, contextPacketPath, outputPath })`
- `evidenceCiteClaims({ claims, composition, compositionPath, sourceMap, sourceMapPath, contextPacket, contextPacketPath, outputPath })`
- `artifactSourceMap({ composition, compositionPath, sourceMap, sourceMapPath, contextPacket, contextPacketPath, artifactManifestPath, artifactPaths, outputPath, title })`
- `artifactManifest({ artifactPaths, outputPath, title, metadata })`
- `artifactGraph({ artifactManifestPath, artifactPaths, outputPath, title })`
- `patchPlan({ inputPath, operations, outputPath, compositionPath, layerManifestPath, reason })`
- `patchPreview({ patchManifest, patchManifestPath, outputPath })`
- `patchApply({ patchManifest, patchManifestPath, outputPath })`
- `patchVerify({ patchManifest, patchManifestPath, patchedPath })`
- `exportBundle({ artifactPaths, outputPath, title, metadata })`
- `verifyBundle({ bundlePath })`
- `validateOutput({ path, expectedPages })`
- `pageCountCheck({ path, expectedPages })`
- `metadataPageInfo({ inputPath, pages })`
- `securityRemoveMetadata({ inputPath, outputPath })`
- `securityRedact({ inputPath, outputPath, regions, fillColor, renderScale })`
- `securityVerifyRedaction({ inputPath, searchTerms })`
- `validationRedactionCheck({ inputPath, searchTerms })`
- `renderCheck({ path, pages })`
- `blankPageCheck({ path, pages })`
- `extractImages({ inputPath, pages, outDir })`
- `parseLite({ inputPath, pages })`
- `semanticDiff({ beforePath, afterPath, pages })`
- `compareSemanticDiff({ beforePath, afterPath, pages })`
- `versionReport({ beforePath, afterPath, outputPath, pages })`
- `compareVersionReport({ beforePath, afterPath, outputPath, pages })`
- `parseFigures({ inputPath, pages })`
- `parseFormulas({ inputPath, pages })`
- `parseCharts({ inputPath, pages })`
- `parseReferences({ inputPath, pages })`
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
