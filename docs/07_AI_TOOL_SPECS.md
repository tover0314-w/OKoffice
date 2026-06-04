# 07 - okoffice AI and Agent Tool Specifications

okoffice should expose AI-oriented tools for Office workflows without making model output the source of truth. The core product is agent-native Office infrastructure: deterministic tools, structured artifacts, validation evidence, and provenance across PDF, Word, Excel, and PowerPoint.

The AI loop is:

```text
collect sources -> normalize source graph -> parse Office/PDF structures
-> plan target artifact -> execute deterministic transforms
-> validate every output -> return evidence and next actions
```

The current implementation still exposes the `pdf.ai.*` namespace. During the migration, those tools are the PDF-domain compatibility layer. The target okoffice namespace is `office.ai.*`, with `office.pdf.ai.*` available as an aliasing bridge when useful.

## Boundary

AI workers may propose structure, classify content, map evidence, rank templates, draft copy, explain formulas, or suggest patch operations. They must not silently mutate source files, invent citations, claim exact geometry that was not measured, or bypass format-specific validation.

Every AI-assisted tool must return the same `ToolResult` envelope used by deterministic tools:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "office.workflow.docset_to_sheet",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

## AI Layers

### Source Understanding

AI may help normalize mixed source material into a Source Graph:

- PDF pages, text blocks, bboxes, annotations, signatures, attachments, and render evidence.
- Word paragraphs, headings, tables, comments, tracked changes, styles, sections, and fields.
- Excel worksheets, tables, formulas, named ranges, charts, pivots, comments, data validation, and workbook-level metadata.
- PowerPoint slides, placeholders, shapes, speaker notes, media, transitions, charts, and theme tokens.
- Web pages, screenshots, images, audio/video transcripts, code snapshots, CSV/JSON data, and connector documents.

Every derived node should include source locator, confidence, extraction method, warnings, and provenance. Locators must use the native coordinate system of the source:

- PDF: page number and optional bbox.
- Word: paragraph/table/run/comment ids and optional rendered page/bbox evidence.
- Excel: sheet name, table name, cell/range address, formula refs, chart ids.
- PowerPoint: slide number, shape id, placeholder id, notes region, optional screenshot bbox.
- Media: timestamp or transcript segment.
- Code: file path, symbol, and line range.

### Target Planning

AI may help choose the output artifact profile and produce an execution plan. The output should be structured, not prose-only:

- Target artifact type: `pdf`, `docx`, `xlsx`, `pptx`, or `bundle`.
- Artifact profile: report, board deck, evidence workbook, financial model, research brief, contract packet, training material, pitch deck, audit bundle.
- Office IR or Composition IR.
- Source refs for each claim, table, chart, paragraph, slide, or formula.
- Validation requirements and known limitations.
- Recommended deterministic tools.

### Patch Assistance

AI may propose edits, but execution should use explicit patch manifests. A patch proposal should name the target object and the policy that permits editing:

```json
{
  "operation": "replace_paragraph",
  "target": {
    "format": "docx",
    "paragraph_id": "p_0042",
    "source_ref": "src_contract_1:p_0042"
  },
  "replacement": {
    "markdown": "Updated renewal language..."
  },
  "validation_required": ["word.render_check", "word.style_check", "office.evidence.coverage"]
}
```

Do not claim arbitrary lossless body-text editing for opaque PDFs. If the source is HTML-first or template-generated and includes layer evidence, okoffice may rerender from editable source. Otherwise it should create a new artifact with transparent patch evidence.

### Verification Assistance

AI may help identify unsupported claims, inconsistent numbers, weak citations, risky redactions, inaccessible layouts, broken formulas, and slide/story problems. These checks complement deterministic validators; they do not replace them.

## Target Namespaces

### `office.ai.parse.lite`

Local, free, and deterministic-first.

Purpose: produce a normalized Office IR from clean digital PDF/DOCX/XLSX/PPTX files.

Baseline behavior:

- PDF: uses current `pdf.ai.parse.lite`.
- Word: extracts headings, paragraphs, tables, comments, styles, fields, and relationships from DOCX packages.
- Excel: extracts workbook structure, sheets, tables, values, formulas, named ranges, charts, and comments without evaluating macros.
- PowerPoint: extracts slide tree, placeholders, text, notes, shapes, media refs, charts, and theme references.
- Emits warnings when layout, formulas, scans, macros, or media require optional workers.

### `office.ai.parse.agentic`

Optional advanced mode for OCR, VLM, complex tables, chart interpretation, formula explanation, scan handling, and semantic layout recovery. This may be cloud-backed or configured through optional local workers.

It must disclose model/provider usage, token cost when applicable, confidence, and unsupported regions.

### `office.ai.extract.schema`

Extract structured fields from mixed Office/PDF sources into a caller-provided JSON schema.

Example:

```json
{
  "sources": [
    {"kind": "local_path", "path": "contracts/vendor-a.docx"},
    {"kind": "local_path", "path": "invoices/vendor-a.pdf"}
  ],
  "schema": {
    "type": "object",
    "properties": {
      "vendor": {"type": "string"},
      "renewal_date": {"type": "string"},
      "annual_amount": {"type": "number"}
    },
    "required": ["vendor", "annual_amount"]
  },
  "evidence_required": true
}
```

Output should include extracted rows, source refs, confidence, missing fields, and recommended validation.

### `office.ai.rag.*`

RAG becomes evidence search across an Office bundle, not only a PDF chat feature.

Target tools:

- `office.ai.rag.ingest`: index source graph nodes from PDF/DOCX/XLSX/PPTX and sidecar context.
- `office.ai.rag.search`: return cited matches without generating prose.
- `office.ai.rag.query`: produce extractive or configured generative answers with evidence.
- `office.ai.rag.cite_answer`: verify answer spans against source refs.
- `office.ai.rag.export_report`: create a cited report artifact.

The current `pdf.ai.rag.*` tools remain the PDF-only compatibility surface.

### `office.ai.create.*`

AI-assisted creation should produce Office IR and deterministic render payloads.

Target tools:

- `office.ai.create.document`: create a Word report from source graph and style profile.
- `office.ai.create.workbook`: create an Excel workbook from extracted evidence, formulas, tables, and charts.
- `office.ai.create.deck`: create a PowerPoint deck from claims, evidence, chart plans, and a deck profile.
- `office.ai.create.pdf`: create a PDF deliverable through the current PDF domain.
- `office.ai.create.bundle`: create a multi-artifact package with manifest, source map, and validation reports.

Creation tools should return source coverage, missing-evidence warnings, layout/render checks, and next recommended review tools.

### `office.ai.review.*`

Review tools operate across formats:

- `office.ai.review.claims`: unsupported or weakly sourced claims.
- `office.ai.review.numbers`: mismatched figures across documents, sheets, and slides.
- `office.ai.review.formulas`: formula risk, broken references, suspicious hardcodes, circular refs.
- `office.ai.review.deck_story`: slide logic, audience fit, hierarchy, and notes coverage.
- `office.ai.review.document_quality`: Word report structure, comments, styles, accessibility, and metadata.
- `office.ai.review.security`: sensitive data, metadata, macro presence, external links, redaction safety.

## Hero Workflows

### `office.workflow.docset_to_sheet`

Turn multiple Word/PDF sources into a cited Excel workbook.

```text
office.context.build_packet
-> office.ai.extract.schema
-> sheet.create.workbook
-> sheet.validation.formulas
-> office.evidence.coverage
```

### `office.workflow.sheet_to_deck`

Turn a workbook into an executive PowerPoint deck.

```text
sheet.inspect.workbook
-> sheet.extract.tables
-> deck.compose.plan
-> deck.create.presentation
-> deck.validation.render_check
```

### `office.workflow.docset_to_board_pack`

Turn mixed source docs into a workbook, PPT deck, Word memo, and final PDF bundle.

```text
office.context.build_packet
-> office.ai.extract.schema
-> sheet.create.workbook
-> deck.create.presentation
-> word.create.report
-> office.bundle.export
-> office.bundle.verify
```

## Worker Tiers

### Tier 0: deterministic OSS

No model dependency. Uses package parsing, XML/relationship inspection, render checks, manifest generation, and safe filesystem rules.

### Tier 1: optional local workers

Feature-flagged OCR, local embeddings, chart/table helpers, browser rendering, LibreOffice-compatible conversions, or document screenshot services. License notes must be explicit.

### Tier 2: configured AI providers

LLM/VLM/OCR providers configured by the user. No proprietary hosted URLs or keys are baked into the OSS core.

### Tier 3: future hosted okoffice

Managed workers, enterprise queues, connectors, billing, and governance. This boundary must remain outside the OSS core.

## Compatibility Map

| Current PDF tool | Target okoffice role |
|---|---|
| `pdf.ai.parse.lite` | `office.ai.parse.lite` for PDF sources |
| `pdf.ai.rag.ingest` | `office.ai.rag.ingest` on PDF source nodes |
| `pdf.ai.rag.query` | `office.ai.rag.query` with PDF citations |
| `pdf.ai.create.from_prompt` | `office.ai.create.pdf` compatibility path |
| `pdf.ai.create.from_template_pack` | PDF renderer behind `office.ai.create.bundle` |
| `pdf.ai.review.sensitive_data_detect` | `office.ai.review.security` for PDF sources |

## Failure Model

AI-assisted tools should fail loudly and helpfully:

```json
{
  "status": "failed",
  "error": {
    "code": "worker_unavailable",
    "message": "The requested chart interpretation worker is not configured.",
    "details": {
      "requested_worker": "vision.chart_interpreter",
      "fallback_available": "sheet.extract.tables"
    }
  },
  "warnings": [
    "Workbook formulas were inspected structurally but not recalculated."
  ],
  "next_recommended_tools": ["sheet.inspect.workbook"]
}
```

The agent should always know what is missing, what evidence was produced, and which deterministic tool can safely run next.
