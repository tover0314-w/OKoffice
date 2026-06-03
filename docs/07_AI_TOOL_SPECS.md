# 07 — AI Tool Specifications

The open-source project should expose AI-oriented tool namespaces while making local/free and cloud/paid boundaries clear.

AI tools are not the product by themselves. They support the larger agent-native loop:

```text
understand context -> choose target PDF profile -> compose/operate on PDF artifacts -> verify evidence -> report results
```

RAG is one evidence technique, not the main product surface. The broader goal is context-backed target PDF creation, patching, review, and verification.

## Agent-native AI layers

### Context understanding

Future AI workers may normalize video, audio, image, scanned, web links/pages, documents, code, and data context into source graph nodes.

Examples:

- Video transcript segments and keyframes.
- Image OCR regions and captions.
- Chart/table/formula interpretations.
- Code file and line-range summaries.
- Spreadsheet/table profiles.

Every derived node should include provenance, confidence, warnings, and source locators such as page/bbox, timestamp, file/line, row/range, or URL fragment.

### Target and composition assistance

AI may help select target PDF profiles and plan learning PDFs, resumes, papers, reports, packets, handouts, and slide-like PDFs from context packets. The output should be target profile + composition IR + source refs, not only prose.

Allowed outputs:

- Proposed document outline.
- Block list with source refs.
- Slide rhythm and speaker notes.
- Figure/table/code block placement.
- Appendix plan.
- Validation requirements.

### Patch assistance

AI may help plan edits to existing PDFs, but execution should use explicit patch transactions where possible.

Allowed outputs:

- Patch manifest.
- Target block/page/bbox refs.
- Template layer refs from `.layers.json`: `layer_id`, `block_id`, `target_slot`, estimated anchors, and edit policies.
- Replacement blocks.
- Source refs for inserted or rewritten content.
- Required validation checks.

Do not claim arbitrary lossless in-place body text editing. The current local patch baseline is append-only; when regeneration or precise layout-preserving replacement is required, return that fact explicitly.

### Verification assistance

AI may help detect unsupported claims, inconsistent numbers, weak citations, risky redactions, accessibility issues, and semantic changes. These checks should complement deterministic validation, not replace it.

## Two-tier parse model

### `pdf.ai.parse.lite`

Local, free, open-source.

- Uses existing text layer.
- Uses simple page geometry and heuristics.
- Produces Document IR.
- Best for clean, digital PDFs.
- Does not require model tokens.

Current baseline:

- Implemented in local Python core.
- Emits Document IR in the standard `ToolResult.usage.document_ir` field.
- Uses page-level bboxes when precise spans are unavailable.
- Returns warnings for pages without text-layer blocks.

### `pdf.ai.parse.agentic`

Future cloud or advanced optional mode.

- Uses OCR/VLM/LLM as needed.
- Handles charts, complex tables, multi-column layouts, formulas, scans.
- Returns confidence, bboxes, and warnings.
- Token-consuming and likely paid.

## `pdf.ai.rag.ingest`

### Purpose

Turn PDF into searchable chunks with page and bbox citations.

### Open-source baseline

- Use lite parse.
- Chunk by headings/page/paragraph.
- Store local JSON index.
- Support keyword or optional local embedding provider.

Current baseline:

- Implemented with local keyword chunks.
- Stores `index.json`-compatible JSON when a directory path is provided.
- Each chunk stores `chunk_id`, `page_number`, `bbox`, text, source block id, and normalized tokens.

### Input

```json
{
  "file": {"kind": "local_path", "path": "paper.pdf"},
  "index_path": "./.agentpdf/indexes/paper",
  "chunking": {
    "strategy": "page_paragraph",
    "max_chars": 1200,
    "overlap_chars": 120
  },
  "embedding": {
    "provider": "none"
  }
}
```

### Output

```json
{
  "index_id": "idx_local_paper",
  "chunk_count": 83,
  "pages_indexed": 12,
  "citation_mode": "page_bbox_optional"
}
```

## `pdf.ai.rag.query`

### Purpose

Answer questions with evidence.

### Input

```json
{
  "index": {"kind": "local_path", "path": "./.agentpdf/indexes/paper"},
  "query": "What are the main contributions?",
  "top_k": 5,
  "answer_mode": "extractive"
}
```

### Output

```json
{
  "answer": "The paper contributes ...",
  "citations": [
    {
      "page": 3,
      "bbox": [72, 140, 510, 220],
      "text": "...",
      "confidence": 0.82
    }
  ]
}
```

Current baseline provides extractive answers and cited chunks. Generative answers require configured model provider or cloud.

## `pdf.ai.rag.search`

### Purpose

Search local indexed chunks and return cited matches without composing an answer.

### Output

```json
{
  "matches": [
    {
      "chunk_id": "chunk_000001",
      "page_number": 1,
      "bbox": [0, 0, 612, 792],
      "text": "...",
      "score": 0.75
    }
  ]
}
```

Current baseline is local keyword search over chunks created by `pdf.ai.rag.ingest`.

## `pdf.ai.rag.chat`

### Purpose

Ask a local PDF in one tool call and return an extractive answer, page/bbox citations, a cited PDF answer report, and a highlighted source PDF.

### Input

```json
{
  "input_path": "./paper.pdf",
  "question": "What does this document say about local deployment?",
  "index_path": "./paper.index.json",
  "report_output_path": "./paper-chat-report.pdf",
  "highlight_output_path": "./paper-chat-highlighted.pdf",
  "top_k": 5,
  "style_pack": "business_report_modern"
}
```

If output paths are omitted, the local runner creates them under `.agentpdf-out/rag-chat/<job>/`.

### Output

```json
{
  "answer": "No cloud key required.",
  "citation_count": 1,
  "pages_cited": [1],
  "report_path": "./paper-chat-report.pdf",
  "highlighted_path": "./paper-chat-highlighted.pdf"
}
```

Current baseline is local and extractive. It chains `ingest`, `query`, `export_report`, and `highlight_sources` while preserving each artifact and step result for agents.

## `pdf.ai.rag.cite_answer`

### Purpose

Map an existing answer back to local page and bbox evidence from an okpdf RAG index.

### Input

```json
{
  "index_path": "./.agentpdf/indexes/paper/index.json",
  "answer": "The document says no cloud key is required.",
  "top_k": 5
}
```

### Output

```json
{
  "citation_mode": "page_bbox",
  "citation_count": 2,
  "citations": [
    {
      "chunk_id": "chunk_000004",
      "page_number": 1,
      "bbox": [0, 0, 612, 792],
      "text": "No cloud key required.",
      "score": 0.8
    }
  ]
}
```

Current baseline is local and extractive: it ranks stored chunks against the supplied answer and returns supporting citations. It does not generate or rewrite the answer.

## `pdf.ai.rag.highlight_sources`

### Purpose

Create a highlighted copy of the source PDF from local page/bbox citations.

### Input

```json
{
  "index_path": "./.agentpdf/indexes/paper/index.json",
  "answer": "The document says no cloud key is required.",
  "output_path": "./paper-highlighted.pdf",
  "top_k": 5,
  "highlight_color": "fff59d"
}
```

`query` can be supplied instead of `answer` when the caller wants to highlight search matches.

### Output

```json
{
  "citation_count": 2,
  "highlighted_pages": [1],
  "output_path": "./paper-highlighted.pdf",
  "citations": []
}
```

Current baseline is local and deterministic. It copies the source PDF from the RAG index, adds PDF highlight annotations for matched citation bboxes, writes a new PDF artifact, and validates the generated PDF.

## `pdf.ai.rag.export_report`

### Purpose

Create a cited PDF answer report from a local RAG index.

### Input

```json
{
  "index_path": "./.agentpdf/indexes/paper/index.json",
  "question": "What does the document say about local deployment?",
  "answer": "The document says no cloud key is required.",
  "output_path": "./paper-rag-report.pdf",
  "top_k": 5,
  "include_citations": true,
  "style_pack": "plain_report"
}
```

If `answer` is omitted, the local query tool produces an extractive answer first.

### Output

```json
{
  "output_path": "./paper-rag-report.pdf",
  "citation_count": 2,
  "pages_cited": [1],
  "answer_mode": "provided_answer_with_local_citations"
}
```

Current baseline is local and deterministic. It writes a new PDF artifact containing the question, answer, source metadata, citation snippets, page numbers, bboxes, and limitations, then validates the generated PDF.

## `pdf.ai.create.*`

PDF creation supports a local deterministic create-agent baseline first. Hosted model generation remains a later layer.

### `pdf.ai.create.from_prompt`

Local, open-source, deterministic:

- Inputs: `prompt`, `output_path`, optional `template`, optional `style_pack`, optional JSON `data`, optional `title`.
- Built-in templates: `one_pager`, `business_report`, `research_brief`, `proposal`, `worksheet`, `resume`, `invoice`.
- Built-in style packs include `paper_ink`, `business_report_modern`, `resume_modern`, and `invoice_clean`.
- Color overrides accept `primary`, `accent`, and `text` hex values, for example `--color primary=#4f46e5`.
- The tool selects a template from the prompt when no template is supplied, renders Markdown, creates a PDF, validates the PDF, and returns the generated Markdown plus an agent plan.
- `invoice`, `resume`, `worksheet`, and `proposal` have structured renderers for common JSON fields. The output includes `template_renderer` so agents can tell whether a specialized renderer or the generic sections renderer was used.

### `pdf.ai.create.templates`

Local template discovery for agents. It returns template ids, names, default sections, default style packs, field contracts, layout slots, sample data, preview tool ids, style pack metadata, supported color keys, and `cloud_required: false`.

### `pdf.ai.create.template_packs`

Local template pack discovery for agents. A template pack groups reusable templates, required/optional fields, layout slots, supported agent block types, target profiles, color schemes, sample data, and license metadata. This is the OSS boundary for future hosted template galleries.

The starter pack includes local templates for technical audits, research briefs, evidence packets, resumes, invoices, proposals, worksheets, and media review decks. These are deterministic OSS templates; future hosted galleries can add more templates without changing the local tool contract.

### `pdf.ai.create.validate_template_pack`

Validates a local template pack before use. The validation report includes pack id, template count, field contracts, layout slots, supported block types, color scheme ids, warnings, errors, and whether each template is agent-ready.

### `pdf.ai.create.plan_template_pack`

Plans a local create call from a template pack, optional Target PDF Profile, and optional Context Packet. It scores candidate templates by target-profile match and context block-type coverage, selects a color scheme, and returns a `create_payload` that can be passed directly to `pdf.ai.create.from_template_pack`. The optional output artifact validates against `schemas/template-pack-plan.schema.json`.

### `pdf.ai.create.agent`

Runs the local deterministic create agent in one call: template-pack planning, Context Packet classification when context is supplied, PDF creation, render-check, blank-page check, Context Packet reporting, and evidence coverage report. The result includes `usage.create_agent_run`, which records the ordered tool chain, selected template, selected color scheme, output PDF, composition artifact, template layer manifest artifact, plan artifact, context classification artifact, coverage artifact, nested ToolResult evidence, `slot_routing_plan`, `template_layer_manifest`, and `evidence_coverage`. The run object validates against `schemas/create-agent-run.schema.json`.

### `pdf.ai.create.from_template_pack`

Creates a validated PDF from a template pack entry. The agent selects `template_id` and optional `color_scheme`; okpdf resolves the base local template, applies sample or supplied `data`, renders the PDF, validates it, and returns the nested create result. Agents can set `renderer=html` plus optional `html_output_path` to create an auditable HTML package first, copy safe local assets into a sibling assets directory, write an asset manifest and package validation report, then render that package into the final PDF. Supplied `data.blocks` can include `section`, `code`, `table`, `image`, `slide`, `audio_reference`, `video_reference`, `media_reference`, and `citation` blocks with `target_slot` and `source_refs`; these render into the PDF and are recorded in the sibling composition source map. Agents can also pass `context_packet_path` or `context_packet` to auto-map packet items into target-profile-aware template blocks: text/document/PDF items become sections, code becomes code blocks, inline tables become tables, images become embedded image blocks, web links become citations, document-profile media becomes `audio_reference`, `video_reference`, or `media_reference`, and slide profiles can keep media as slide blocks. The result includes `slot_routing_plan`, an agent-readable placement report with route ids, target slots, source refs, template block-type checks, target profile block compatibility, candidate target-profile slots, slot-known facts, and routing reasons. It also writes a sibling `.layers.json` artifact validating against `schemas/template-layer-manifest.schema.json`; each layer maps a rendered block to its slot, source refs, source kinds, estimated normalized-page anchor, and edit policy for patch/edit agents. `pdf.patch.plan` can use those layer refs for append-only notes or `regenerate_block` operations that append an audited regenerated block appendix to a new PDF artifact without mutating the original block. Image blocks validate the local image path and record dimensions and MIME type as block evidence; citation blocks can map URL refs as `web_link` source evidence.

### `pdf.ai.create.template_preview`

Local template preview for agents. It uses the template catalog's sample data unless custom `data` is supplied, creates a real PDF through the local create agent, validates the result, and returns the nested `create_result` evidence. This is the local equivalent of trying a template before committing to a production artifact.

CLI example:

```bash
okpdf create templates --json
```

CLI example:

```bash
okpdf create template-packs -o .agentpdf-out/template-packs.json --json
okpdf create validate-template-pack examples/template-packs/local-agent-starter.json \
  -o .agentpdf-out/template-pack.validation.json \
  --json
okpdf create plan-template-pack examples/template-packs/local-agent-starter.json \
  --target-profile technical_audit \
  --context-packet .agentpdf-out/context.packet.json \
  --planned-output .agentpdf-out/board-audit.pdf \
  -o .agentpdf-out/board-audit.plan.json \
  --json
okpdf create agent examples/template-packs/local-agent-starter.json \
  --target-profile technical_audit \
  --context-packet .agentpdf-out/context.packet.json \
  -o .agentpdf-out/board-audit.pdf \
  --plan-output .agentpdf-out/board-audit.plan.json \
  --coverage-output .agentpdf-out/board-audit.coverage.json \
  --context-classification-output .agentpdf-out/board-audit.context-classification.json \
  --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json \
  --template board_audit \
  --color-scheme executive_blue \
  --data examples/create-data/agent-block-audit.json \
  -o .agentpdf-out/board-audit.pdf \
  --renderer html \
  --html-output .agentpdf-out/board-audit.html \
  --json
```

CLI example:

```bash
okpdf create preview invoice \
  -o .agentpdf-out/invoice-preview.pdf \
  --json
```

CLI example:

```bash
okpdf create from-prompt "Create a research brief about local PDF agents." \
  -o .agentpdf-out/research-brief.pdf \
  --template research_brief \
  --style-pack paper_ink \
  --color primary=#4f46e5 \
  --color accent=#f59e0b \
  --json
```

REST example:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.from_prompt/run \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Create a proposal about local PDF template agents.","output_path":"proposal.pdf","template":"proposal","style_pack":"business_report_modern"}'
```

Preview REST example:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.ai.create.template_preview/run \
  -H 'Content-Type: application/json' \
  -d '{"template":"invoice","output_path":"invoice-preview.pdf"}'
```

Structured invoice CLI example:

```bash
okpdf create from-prompt "Create an invoice for okpdf local template work." \
  -o .agentpdf-out/invoice.pdf \
  --template invoice \
  --data examples/create-data/invoice.json \
  --json
```

Expected output includes:

```json
{
  "tool": "pdf.ai.create.from_prompt",
  "status": "succeeded",
  "usage": {
    "template_id": "research_brief",
    "template_renderer": "generic",
    "style_pack": "paper_ink",
    "agent_plan": {"cloud_required": false}
  },
  "validation": {"status": "passed"}
}
```

Preview output includes:

```json
{
  "tool": "pdf.ai.create.template_preview",
  "status": "succeeded",
  "usage": {
    "template_id": "invoice",
    "data_source": "template_sample_data",
    "create_result": {"tool": "pdf.ai.create.from_prompt"}
  },
  "validation": {"status": "passed"}
}
```

Limitations:

- This is not a hidden cloud LLM call.
- It does not claim arbitrary design generation.
- It creates polished, template-backed PDFs from local deterministic rules and optional structured data.

### Future AI Mode

Cloud/BYOK/optional:

- Prompt-to-PDF.
- Context packets to learning PDFs, resumes, papers, summary reports, evidence packets, training handouts, and presentation PDFs.
- Video/audio/image/document/code/link/data context to PDF artifacts.
- Brand/style transformation.
- Model-generated content.
- Composition IR planning with source refs.
- Target PDF profile selection.
- Speaker notes and appendix generation.

The generated artifact must still pass through rendering, validation, and evidence coverage checks.

## `pdf.ai.edit.*`

Separate safe edits from AI regeneration.

### Safe deterministic edits

Use `pdf.edit.*` tools.

### AI regeneration edits

Pipeline:

```text
PDF -> parse IR -> transform content/style -> render new PDF -> validate -> diff report
```

Never promise arbitrary lossless in-place PDF body text editing.

## AI model provider design

Open-source project may support:

- `none`: no model, deterministic only.
- `byok`: user-configured model keys.
- `local`: local model provider.
- `cloud`: future hosted AgentPDF service.

Public code should not include private API keys or hard-coded hosted endpoints.
