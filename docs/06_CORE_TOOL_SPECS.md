# 06 - okoffice Core Tool Specifications

This document describes the first stable deterministic tool surface for okoffice. The existing `pdf.*` tools remain the implemented compatibility domain. The target product adds Word, Excel, PowerPoint, cross-format workflows, and audit bundles under an `office.*` namespace.

The rule is simple: agents should be able to inspect, create, edit, validate, and connect Office artifacts without guessing about file structure or silently trusting generated output.

## Common Input Concepts

### File Reference

```json
{
  "kind": "local_path",
  "path": "./report.docx"
}
```

Future kinds may include `artifact_id`, `url`, `bytes`, `connector_file`, or `cloud_object`. Local paths must be explicit, normalized, and checked for traversal or suspicious names.

### Format

okoffice should detect and report file format, but callers may also provide an expected format:

```json
{
  "file": {"kind": "local_path", "path": "./board-pack.pptx"},
  "expected_format": "pptx"
}
```

Supported target formats:

- `pdf`
- `docx`
- `xlsx`
- `pptx`
- `csv`
- `html`
- `markdown`
- `okoffice_bundle`

### Range Syntax

User-facing indexes are 1-based unless a native format convention is clearer.

PDF pages:

- `1`
- `1-3`
- `1,3,5`
- `odd`
- `even`
- `all`

PowerPoint slides use the same syntax.

Excel ranges use workbook notation:

- `Sheet1!A1:D20`
- `Summary!A:C`
- `Model!Revenue_Table`
- `named_range:Assumptions`

Word ranges use stable document locators:

- `heading:Executive Summary`
- `paragraph:p_0042`
- `table:t_0003`
- `comment:c_0010`

## Common Output Contract

Every core tool returns:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "sheet.inspect.workbook",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

For generated artifacts, the output must include checksums, file size, format, validation summary, source refs when available, and next recommended validation or review tools.

## Context Tools

### `office.context.build_packet`

Purpose: build a local OKoffice context packet and source graph from Office-compatible files.

CLI:

```bash
okoffice context build --file memo.docx --file model.xlsx -o .okoffice-out/context.packet.json --json
```

MCP:

```python
office_context_build_packet(["memo.docx", "model.xlsx"], ".okoffice-out/context.packet.json")
```

REST:

```http
POST /v1/tools/office.context.build_packet/run
```

Input:

```json
{
  "files": ["memo.docx", "model.xlsx"],
  "output_path": ".okoffice-out/context.packet.json",
  "title": "Vendor Context",
  "intent": "Prepare board review"
}
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "office.context.build_packet",
  "validation": {"status": "passed"},
  "usage": {
    "summary": {
      "item_count": 2,
      "source_node_count": 4,
      "native_node_count": 2,
      "formats": {"docx": 1, "xlsx": 1}
    }
  }
}
```

Limitations:

- Uses deterministic local `office.inspect.file` facts and native source locators.
- Adds native source graph child nodes when local parsers can inspect them: `word.table`, `sheet.sheet`, `sheet.table`, `sheet.formula_summary`, and `deck.slide`.
- Parser-specific enrichment warnings are reported without blocking baseline context packet construction.
- Does not yet perform full Word/Excel/PowerPoint/PDF content extraction.
- Does not call hosted AI providers, fetch remote assets, or mutate inputs.

### `office.extract.schema`

Purpose: extract schema-shaped evidence from a local OKoffice context packet using deterministic local label/value matching.

CLI:

```bash
okoffice extract schema .okoffice-out/context.packet.json --schema examples/schemas/vendor-renewal.json -o .okoffice-out/evidence.json --json
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "office.extract.schema",
  "usage": {
    "summary": {
      "field_count": 4,
      "record_count": 3,
      "missing_field_count": 1
    },
    "evidence": {
      "context_packet_id": "ctxpkt_...",
      "source_graph_id": "srcgraph_...",
      "coverage": {"matched": 3, "total": 4, "ratio": 0.75}
    }
  }
}
```

Limitations:

- Uses local deterministic matching only; no hosted AI/model provider is called.
- Emits missing-field warnings instead of inventing values.
- Does not yet infer complex tables, formulas, or multi-hop claims beyond available source graph text/evidence.

### `sheet.create.evidence_workbook`

Purpose: create an auditable XLSX evidence workbook from structured records while preserving SourceRefs provenance.

CLI:

```bash
okoffice sheet create-evidence-workbook .okoffice-out/evidence.json -o .okoffice-out/evidence.xlsx --json
```

MCP:

```python
sheet_create_evidence_workbook({"records": [...]}, ".okoffice-out/evidence.xlsx")
```

REST:

```http
POST /v1/tools/sheet.create.evidence_workbook/run
```

Input:

```json
{
  "data": {
    "records": [
      {
        "source_path": "memo.docx",
        "source_format": "docx",
        "table_id": "table_1",
        "source_row_index": 1,
        "values": ["Vendor A", "250000"],
        "source_refs": [{"document_path": "memo.docx", "table_index": 1, "row_index": 1}]
      }
    ]
  },
  "output_path": ".okoffice-out/evidence.xlsx"
}
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "sheet.create.evidence_workbook",
  "artifacts": [{"path": ".okoffice-out/evidence.xlsx"}],
  "validation": {"status": "passed"},
  "usage": {
    "summary": {
      "record_count": 1,
      "column_count": 2,
      "source_ref_count": 1
    },
    "workbook": {"sheets": ["Workbook", "SourceRefs"]}
  },
  "next_recommended_tools": ["sheet.inspect.workbook", "sheet.validate.workbook", "deck.compose.plan"]
}
```

Error example:

```json
{
  "status": "failed",
  "tool": "sheet.create.evidence_workbook",
  "error": {
    "code": "unsafe_input_rejected",
    "message": "sheet.create.evidence_workbook requires at least one record or table row."
  }
}
```

Limitations and dependency notes:

- Runs locally with the default XLSX writer; it does not require hosted workers, model calls, Microsoft Office, LibreOffice, or GPL/AGPL dependencies.
- Writes a new output artifact and never mutates source files.
- Produces structural workbook evidence and SourceRefs sheets; it does not yet create charts, formulas, pivot tables, or styled financial models.
- Call `sheet.validate.workbook` and optionally `deck.compose.plan` before handing the artifact to a downstream deck/report workflow.

## Core Inspect Tools

### `office.inspect.file`

Purpose: identify a local file, detect format, inspect package health, and recommend next tools.

Output highlights:

```json
{
  "status": "succeeded",
  "tool": "office.inspect.file",
  "usage": {
    "file": {
      "extension": ".xlsx",
      "size_bytes": 42811,
      "sha256": "..."
    },
    "format": {
      "detected_format": "xlsx",
      "domain": "sheet",
      "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "package_type": "ooxml_xlsx"
    },
    "safety": {
      "mutates_inputs": false,
      "macro_enabled": false,
      "has_external_relationships": false
    }
  },
  "next_recommended_tools": ["sheet.inspect.workbook", "office.context.build_packet"]
}
```

Acceptance criteria:

- Does not mutate input.
- Rejects unsafe paths.
- Detects format mismatch.
- Reports package and security facts.
- Returns stable error codes.
- Uses only Python standard library ZIP/XML-adjacent checks plus existing core dependencies.
- Does not yet extract complete Word, Excel, or PowerPoint structure.

### `pdf.inspect.document`

Current implemented PDF-domain tool.

Purpose: inspect a PDF and return agent-readable facts: page count, sizes, metadata, encryption, forms, annotations, attachments, text-layer presence, and recommendations.

Acceptance criteria:

- Works for valid PDFs.
- Returns clear errors for missing, encrypted, or invalid PDFs.
- Does not mutate input.
- Recommends parse, render, redaction, or validation tools as appropriate.

### `word.inspect.document`

Target deterministic DOCX tool.

Purpose: inspect a Word document package and return structure that agents can cite and edit.

Output highlights:

```json
{
  "paragraph_count": 84,
  "heading_count": 9,
  "table_count": 3,
  "comment_count": 2,
  "tracked_changes": {"present": false},
  "styles": ["Title", "Heading 1", "Normal", "Caption"],
  "sections": [
    {"section_id": "s_0001", "title": "Executive Summary", "paragraph_refs": ["p_0001", "p_0002"]}
  ],
  "recommended_next_tools": ["word.validation.package", "word.extract.tables"]
}
```

Acceptance criteria:

- Reads DOCX package parts and relationships.
- Extracts headings, paragraphs, tables, comments, footnotes/endnotes where available.
- Reports styles and tracked changes.
- Detects macros only when the file/package indicates macro-enabled content.
- Does not claim final page layout unless rendered evidence exists.

### `sheet.inspect.workbook`

Target deterministic XLSX tool.

Purpose: inspect workbook structure, formulas, tables, charts, and workbook risks.

Output highlights:

```json
{
  "sheet_count": 4,
  "sheets": [
    {"name": "Summary", "used_range": "A1:H32", "table_count": 1, "formula_count": 18}
  ],
  "named_ranges": ["RevenueAssumptions"],
  "charts": [{"sheet": "Summary", "chart_id": "chart_0001"}],
  "formula_summary": {"count": 127, "errors_detected": 0, "external_refs": 0},
  "recommended_next_tools": ["sheet.validation.formulas", "sheet.extract.tables"]
}
```

Acceptance criteria:

- Reads XLSX package and worksheet XML.
- Reports sheets, used ranges, tables, formulas, charts, comments, named ranges, and external links.
- Does not execute macros.
- Formula evaluation is explicit; if not available, report structural inspection only.

### `deck.inspect.presentation`

Target deterministic PPTX tool.

Purpose: inspect slide structure, theme, notes, media refs, charts, and shape locators.

Output highlights:

```json
{
  "slide_count": 12,
  "theme": {"name": "Office Theme"},
  "slides": [
    {"slide_number": 1, "title": "Q2 Results", "shape_count": 7, "has_notes": true}
  ],
  "media": [{"kind": "image", "slide_number": 4, "relationship_id": "rId5"}],
  "recommended_next_tools": ["deck.validation.contact_sheet"]
}
```

Acceptance criteria:

- Reads PPTX package parts and relationships.
- Extracts slide order, layouts, placeholders, text, notes, charts, images, and embedded media refs.
- Reports missing title/notes/style warnings.
- Does not claim visual fit without render evidence.

## Core Creation Tools

### `pdf.convert.markdown_to_pdf`

Current implemented PDF-domain tool.

Purpose: create a validated PDF from Markdown/HTML-first inputs and a style pack.

Acceptance criteria:

- Writes a new output artifact.
- Produces page count, render check, blank-page check, and output manifest.
- Supports built-in and local JSON style packs.
- Does not silently clip content without warnings.

### `word.create.document`

Target DOCX creation tool.

Purpose: create a Word document from Office IR, Markdown, or structured sections.

Acceptance criteria:

- Uses named styles.
- Preserves source refs in companion metadata.
- Supports tables, captions, citations, comments, and appendices.
- Writes validation report and package manifest.
- Supports render preview when a renderer is configured.

### `sheet.create.workbook`

Target XLSX creation tool.

Purpose: create a workbook from extracted rows, tables, formulas, charts, and validation rules.

Acceptance criteria:

- Creates tables with typed columns and filters.
- Separates inputs, calculations, checks, and outputs when the profile requires it.
- Adds source-ref columns for extracted evidence.
- Writes formula validation and workbook manifest.
- Does not create hidden assumptions without recording them.

### `deck.create.presentation`

Current OSS implementation.

Purpose: create a local editable presentation from a structured outline or deck composition plan.

Current beta behavior: writes an editable PPTX directly with the deterministic local writer.

Target behavior: orchestrates the taste-driven HTML-first route when the required workers are available:

```text
deck.compose.plan -> deck.render.html -> deck.validation.html_preview
-> deck.validation.contact_sheet -> deck.export.pptx -> deck.validate.presentation
```

CLI:

```bash
okoffice deck create-presentation .okoffice-out/deck.plan.json -o .okoffice-out/board-review.pptx --json
```

MCP:

```python
deck_create_presentation({"outline": {"slides": []}}, ".okoffice-out/board-review.pptx")
```

REST:

```http
POST /v1/tools/deck.create.presentation/run
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "deck.create.presentation",
  "validation": {"status": "passed"},
  "usage": {
    "summary": {"slide_count": 3, "total_bullet_count": 5},
    "input": {"source": "composition_plan"},
    "presentation": {"format": "pptx"},
    "creation_route": {"route": "direct_pptx_fallback", "html_preview_used": false}
  },
  "next_recommended_tools": ["deck.inspect.presentation", "deck.validate.presentation", "office.workflow.board_pack"]
}
```

Limitations:

- Uses the deterministic local PPTX writer and does not require hosted AI, Office, LibreOffice, or rendering workers.
- Accepts a direct `outline` or a `deck.compose.plan` JSON payload containing `outline`.
- Produces an editable PPTX with text slides; advanced style packs, charts, theme tokens, speaker notes, contact sheets, HTML preview packages, and visual render QA remain future enhancements.

### `deck.render.html`

Current OSS beta implementation.

Purpose: turn deck Composition IR, outline JSON, or a `deck.compose.plan` artifact into a self-contained HTML slide preview package that agents and humans can inspect before PPTX export.

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "deck.render.html",
  "artifacts": [{"kind": "html", "path": ".okoffice-out/board-review.html"}],
  "validation": {"status": "passed"},
  "usage": {
    "summary": {"slide_count": 4},
    "html_package": {
      "manifest_path": ".okoffice-out/board-review.html-manifest.json",
      "offline_assets": true,
      "slide_dom_anchor_count": 4
    }
  },
  "next_recommended_tools": ["deck.validation.html_preview", "deck.validation.contact_sheet", "deck.export.pptx"]
}
```

Acceptance criteria:

- Writes a new HTML artifact and package manifest.
- Preserves slide ids, source refs, style tokens, and DOM anchors.
- Rejects unsafe remote assets, scripts, file URLs, and path traversal.
- Emits placeholder, overflow-risk, contrast, and missing-alt-text warnings.
- Does not write PPTX directly.

### `deck.export.pptx`

Current OSS beta implementation.

Purpose: convert a validated HTML slide package or component tree into an editable PPTX while preserving lineage back to the deck plan and HTML preview.

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "deck.export.pptx",
  "validation": {"status": "passed"},
  "usage": {
    "summary": {"slide_count": 4},
    "export": {
      "source_format": "html_slide_package",
      "output_format": "pptx",
      "source_map_path": ".okoffice-out/board-review.deck-source-map.json"
    }
  },
  "next_recommended_tools": ["deck.validate.presentation", "office.workflow.board_pack"]
}
```

Acceptance criteria:

- Writes a new PPTX and never mutates the HTML package or source workbook.
- Preserves slide order and source-map links through the HTML manifest.
- Uses the local HTML manifest and outline to produce editable text PPTX slides; full component-tree/layout-perfect export remains a future optional worker.
- Emits route metadata as `html_manifest_to_editable_pptx_baseline` and writes a `.deck-source-map.json` sidecar.

### `deck.compose.plan`

Current OSS implementation.

Purpose: compose source-mapped, deck-specific Composition IR and outline JSON from a local evidence workbook without writing a PPTX.

CLI:

```bash
okoffice deck compose-plan .okoffice-out/evidence.xlsx -o .okoffice-out/deck.plan.json --title "Board Review" --json
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "deck.compose.plan",
  "usage": {
    "summary": {
      "slide_count": 4,
      "source_coverage": {"status": "complete"}
    },
    "composition_ir": {
      "schema": "okoffice.deck.composition",
      "kind": "deck.composition",
      "slides": [
        {"slide_type": "sheet_snapshot", "claims": [], "source_refs": []}
      ]
    },
    "outline": {"slides": []}
  }
}
```

Acceptance criteria:

- Reads a bounded workbook profile and SourceRefs provenance sheet.
- Produces slide plans, claims, workbook ranges, and source refs for agent review.
- Optionally writes JSON plan output; never writes or mutates PPTX.
- Does not call hosted AI providers or infer unsupported chart/design layout.
- Recommends target `deck.render.html`, `deck.validation.html_preview`, `deck.export.pptx`, convenience `deck.create.presentation`, compatibility `deck.create.from_outline`, validation, and board-pack tools.

## Core Edit and Patch Tools

### `office.patch.plan`

Purpose: plan a non-destructive edit across PDF, DOCX, XLSX, or PPTX.

Output should include:

- Target artifact and format.
- Target locator.
- Operation type.
- Replacement payload.
- Source refs.
- Validation requirements.
- Rollback/lineage plan.

### `office.patch.apply`

Purpose: apply an approved patch plan to a new output artifact.

Acceptance criteria:

- Never mutates the input file.
- Writes a new artifact.
- Returns patch manifest and validation report.
- Fails if the target locator is stale or ambiguous.

Format-specific examples:

- Word: replace paragraph, append section, update table, resolve comment.
- Excel: update cell/range/table, add validation sheet, add chart, insert formula.
- PowerPoint: replace text box, update chart data, add slide, update notes.
- PDF: append note, regenerate from editable HTML/template source, redact through PDF safety tools.

## Core Validation Tools

### `office.validation.package`

Validates ZIP/package structure, relationships, content types, and unsafe entries.

Current OSS implementation:

- Validates OOXML ZIP readability and member names.
- Requires `[Content_Types].xml`.
- Warns on macro markers and external relationships.
- Provides a PDF baseline through `office.inspect.file`.
- Does not execute macros, embedded code, or remote assets.

### `word.validation.document`

Checks DOCX package health, styles, comments/tracked changes policy, metadata, accessibility hints, and optional render preview.

### `sheet.validation.formulas`

Purpose: structurally validate workbook formulas without recalculating them.

CLI:

```bash
okoffice sheet validate-formulas .okoffice-out/evidence.xlsx --json
```

MCP:

```python
sheet_validate_formulas(".okoffice-out/evidence.xlsx")
```

REST:

```http
POST /v1/tools/sheet.validation.formulas/run
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "sheet.validation.formulas",
  "validation": {"status": "warning"},
  "usage": {
    "summary": {
      "sheet_count": 2,
      "formula_count": 4,
      "formula_error_count": 1,
      "broken_ref_count": 1,
      "external_ref_count": 1,
      "volatile_formula_count": 1
    },
    "engine": {"evaluation": "structural_only", "recalculated": false}
  },
  "next_recommended_tools": ["sheet.validate.workbook", "sheet.profile.data", "deck.compose.plan"]
}
```

Error example:

```json
{
  "status": "failed",
  "tool": "sheet.validation.formulas",
  "error": {
    "code": "unsupported_file_type",
    "message": "sheet.validation.formulas requires an XLSX-compatible OOXML package."
  }
}
```

Limitations and dependency notes:

- Runs locally with deterministic OOXML parsing; it does not require Microsoft Excel, LibreOffice, cloud workers, or model calls.
- Detects formula cells, cached error values, `#REF!`, external workbook refs, volatile functions, and simple cell/range precedents.
- Does not recalculate formulas, resolve named ranges, detect circular references, or validate chart/table bindings yet.
- Use optional formula worker/recalculation backends later when exact evaluated values are required.

### `deck.validation.presentation`

Checks slide count, missing titles, placeholder overflow warnings, notes policy, media refs, theme consistency, and contact-sheet render evidence.

### `pdf.validation.render_check`

Current implemented PDF-domain validator. Every generated PDF must pass renderability, page count, blank-page checks, and manifest requirements.

## Bundle Tools

### `office.bundle.export`

Purpose: package multiple artifacts, source maps, validation reports, and manifests into one portable audit bundle.

### `office.bundle.verify`

Purpose: verify checksums, artifact presence, source refs, validation reports, and dependency/license notes.

Current OSS implementation verifies OKoffice board pack ZIPs created by `office.workflow.board_pack`.

CLI:

```bash
okoffice bundle verify .okoffice-out/board-pack.zip --json
```

MCP:

```python
office_bundle_verify(".okoffice-out/board-pack.zip")
```

REST:

```http
POST /v1/tools/office.bundle.verify/run
```

Input:

```json
{
  "bundle_path": ".okoffice-out/board-pack.zip"
}
```

Expected output highlights:

```json
{
  "status": "succeeded",
  "tool": "office.bundle.verify",
  "validation": {"status": "passed"},
  "usage": {
    "summary": {
      "manifest_file_count": 2,
      "verified_file_count": 2,
      "missing_file_count": 0,
      "hash_mismatch_count": 0,
      "size_mismatch_count": 0
    }
  }
}
```

Error example:

```json
{
  "status": "failed",
  "tool": "office.bundle.verify",
  "error": {
    "code": "unsupported_file_type",
    "message": "OKoffice board pack is not a readable ZIP file."
  }
}
```

Limitations:

- Verifies the ZIP, `okoffice-manifest.json`, `okoffice-validation.json`, artifact member presence, byte size, and SHA-256.
- Does not re-parse packaged DOCX/XLSX/PPTX/PDF contents; run format-specific validators before creating the board pack.
- Does not execute macros, fetch remote assets, or call hosted services.

Acceptance criteria:

- Bundle verification is local-first.
- Missing artifacts or hash mismatches fail.
- Warnings remain visible to agents.
- Bundle does not include secrets or proprietary cloud state.

## First Migration Milestones

1. Keep `okoffice` and `pdf.*` stable.
2. Add `okoffice` CLI alias and top-level `office.inspect.file`.
3. Add deterministic DOCX/XLSX/PPTX inspect tools.
4. Add Office IR and Source Graph support for all four formats.
5. Add validation reports for Word, Excel, and PowerPoint.
6. Add `office.workflow.docset_to_sheet`.
7. Add `office.workflow.sheet_to_deck`.
8. Add `office.bundle.export` and `office.bundle.verify`.

The first milestone is not perfect Office editing. It is trustworthy structure, evidence, and validation across the formats agents already need to work with.
