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

### `office.context.build_packet`

Implemented cross-format deterministic tool.

Purpose: build a reusable okoffice context packet from local Word, Excel, PowerPoint, PDF, text, and data sources.

Output highlights:

```json
{
  "status": "succeeded",
  "tool": "office.context.build_packet",
  "usage": {
    "item_count": 3,
    "domains": ["deck", "sheet", "word"],
    "inspection_tools": [
      "word.inspect.document",
      "sheet.inspect.workbook",
      "deck.inspect.presentation"
    ],
    "context_packet": {
      "product": "okoffice",
      "items": [],
      "source_graph": {"node_count": 9, "edge_count": 6}
    }
  },
  "next_recommended_tools": ["office.extract.schema", "office.workflow.extract_to_sheet"]
}
```

Acceptance criteria:

- Accepts repeated local file paths from CLI, REST, MCP, and workflow runner.
- Runs local format detection and available structure inspectors without mutating inputs.
- Writes a JSON context packet only to an explicit output path.
- Includes per-file summaries, safety facts, warnings, and source graph nodes.
- Does not call a model, extract schema-shaped facts, or fetch external links.

### `office.extract.schema`

Implemented deterministic extraction tool.

Purpose: extract schema-shaped rows from an okoffice context packet with source refs, locators, confidence, and warnings.

Output highlights:

```json
{
  "status": "succeeded",
  "tool": "office.extract.schema",
  "usage": {
    "summary": {
      "field_count": 4,
      "row_count": 1,
      "source_count": 2,
      "filled_value_count": 4
    },
    "extraction": {
      "schema_name": "vendor_renewal",
      "rows": [
        {
          "row_id": "row_001",
          "values": {"vendor": "Acme Corp", "risk": "High"},
          "field_evidence": {
            "vendor": {
              "source_ref": "ctx_001#p1",
              "locator": {"kind": "word", "paragraph_id": "p_0001"},
              "confidence": 0.95
            }
          }
        }
      ]
    }
  },
  "next_recommended_tools": ["sheet.write.workbook", "office.workflow.extract_to_sheet"]
}
```

Acceptance criteria:

- Reads a local context packet JSON and a JSON schema.
- Extracts fields deterministically from local source graph text using field names and aliases.
- Returns rows, field-level evidence, source refs, locators, confidence, warnings, and an optional evidence JSON artifact.
- Does not call a model, infer unsupported values, mutate the context packet, or fetch external links.

### `pdf.inspect.document`

Current implemented PDF-domain tool.

Purpose: inspect a PDF and return agent-readable facts: page count, sizes, metadata, encryption, forms, annotations, attachments, text-layer presence, and recommendations.

Acceptance criteria:

- Works for valid PDFs.
- Returns clear errors for missing, encrypted, or invalid PDFs.
- Does not mutate input.
- Recommends parse, render, redaction, or validation tools as appropriate.

### `word.inspect.document`

Implemented deterministic DOCX tool.

Purpose: inspect a Word document package and return structure that agents can cite and edit.

Output highlights:

```json
{
  "status": "succeeded",
  "tool": "word.inspect.document",
  "usage": {
    "summary": {
      "paragraph_count": 84,
      "heading_count": 9,
      "table_count": 3,
      "comment_count": 2,
      "field_count": 4,
      "tracked_change_count": 0
    },
    "paragraphs": [
      {
        "paragraph_id": "p_0001",
        "style": "Heading 1",
        "locator": {"kind": "word", "paragraph_index": 0}
      }
    ],
    "layout": {"rendered_layout_claimed": false}
  },
  "next_recommended_tools": ["office.context.build_packet", "word.validation.document"]
}
```

Acceptance criteria:

- Reads DOCX package parts and relationships.
- Extracts headings, paragraphs, tables, comments, footnotes/endnotes where available.
- Reports styles and tracked changes.
- Detects macros only when the file/package indicates macro-enabled content.
- Does not claim final page layout unless rendered evidence exists.
- Does not execute macros, embedded code, or external relationships.

### `sheet.inspect.workbook`

Target deterministic XLSX tool.

Purpose: inspect workbook structure, formulas, tables, charts, and workbook risks.

Output highlights:

```json
{
  "tool": "sheet.inspect.workbook",
  "status": "succeeded",
  "usage": {
    "summary": {
      "sheet_count": 4,
      "formula_count": 127,
      "chart_count": 2,
      "external_link_count": 0
    },
    "sheets": [
      {
        "name": "Summary",
        "used_range": "A1:H32",
        "table_count": 1,
        "formula_count": 18,
        "locator": {"kind": "sheet", "sheet": "Summary"}
      }
    ],
    "formula_evaluation": {
      "status": "structural_only",
      "evaluated": false
    }
  },
  "next_recommended_tools": ["sheet.validation.formulas", "office.context.build_packet"]
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
  "tool": "deck.inspect.presentation",
  "status": "succeeded",
  "usage": {
    "summary": {
      "slide_count": 12,
      "shape_count": 84,
      "chart_count": 2,
      "media_count": 6
    },
    "slides": [
      {
        "slide_number": 1,
        "title": "Q2 Results",
        "shape_count": 7,
        "has_notes": true,
        "locator": {"kind": "deck", "slide": 1, "slide_id": "256"}
      }
    ],
    "themes": [{"name": "Office Theme"}],
    "layout": {"rendered_layout_claimed": false}
  },
  "next_recommended_tools": ["deck.validation.presentation", "office.context.build_packet"]
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

### `word.create.report`

Current beta DOCX report creation tool.

Purpose: create an editable Word memo/report from an okoffice evidence workbook.

Acceptance criteria:

- Reads the `Evidence` and `SourceMap` workbook sheets.
- Writes a new `.docx` artifact and never mutates the input workbook.
- Includes populated evidence fields and row-level source refs.
- Returns a report manifest, row summaries, artifact metadata, and validation checks.
- Reopens the generated document with `word.inspect.document` as structural validation evidence.
- Does not execute macros, fetch remote relationships, or claim rendered layout fit without a renderer.

### `sheet.write.workbook`

Current beta XLSX evidence workbook writer.

Purpose: create a local `.xlsx` workbook from `office.extract.schema` evidence JSON.

Acceptance criteria:

- Writes a new XLSX artifact and never mutates evidence/source inputs.
- Creates an `Evidence` table from extracted field rows.
- Creates a `SourceMap` table with field, row id, source ref, source type, locator, confidence, and excerpt.
- Returns artifact metadata, workbook manifest, validation checks, warnings, usage summary, and next recommended tools.
- Reopens the generated workbook with `sheet.inspect.workbook` as structural validation evidence.
- Does not calculate formulas, create charts, execute macros, fetch remote links, or hide assumptions.

### `deck.create.presentation`

Current beta PPTX creation tool.

Purpose: create an editable PowerPoint deck from an okoffice evidence workbook.

Acceptance criteria:

- Reads the `Evidence` and `SourceMap` workbook sheets.
- Writes a new `.pptx` artifact and never mutates the input workbook.
- Creates a title slide and one evidence slide per workbook row.
- Produces slide ids, shape ids, row ids, and row-level source refs.
- Includes source refs in speaker notes for evidence slides.
- Reopens the generated deck with `deck.inspect.presentation` as structural validation evidence.
- Returns a skipped `contact_sheet_preview` validation check when no local render worker is configured.
- Does not execute macros, fetch remote relationships, create chart objects, or claim perfect visual fit.

### `deck.validation.contact_sheet`

Current beta PPTX preview validation tool.

Purpose: verify that a deck can be inspected and report whether local contact-sheet preview evidence is available.

Acceptance criteria:

- Reopens the PPTX with `deck.inspect.presentation`.
- Returns slide count and deck inspection evidence.
- Returns `validation.status = skipped` when no local contact-sheet renderer is configured.
- Provides an explicit skipped worker check instead of silently omitting preview evidence.
- Does not upload the presentation, execute macros, or claim rendered visual fit without a renderer.

## Core Workflow Tools

### `office.workflow.board_pack`

Current beta cross-format board-pack workflow.

Purpose: turn local source documents into a validated board-pack directory containing an evidence workbook, context and evidence sidecars, editable memo, editable deck, optional HTML-first PDF handout, and checksum bundle.

Input highlights:

```json
{
  "files": ["contracts/vendor-a.docx", "invoices/vendor-a.pdf"],
  "schema": {
    "fields": [
      {"name": "vendor", "type": "string", "aliases": ["Vendor"]},
      {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"]}
    ]
  },
  "out_dir": ".okoffice-out/vendor-board-pack",
  "title": "Vendor Renewal Review",
  "profile": "board_review",
  "include_pdf_handout": true,
  "pdf_renderer_backend": "auto"
}
```

Output highlights:

```json
{
  "tool": "office.workflow.board_pack",
  "status": "succeeded",
  "artifacts": [
    {"path": ".okoffice-out/vendor-board-pack/evidence.xlsx"},
    {"path": ".okoffice-out/vendor-board-pack/memo.docx"},
    {"path": ".okoffice-out/vendor-board-pack/board-deck.pptx"},
    {"path": ".okoffice-out/vendor-board-pack/handout.pdf"},
    {"path": ".okoffice-out/vendor-board-pack/board-pack.okoffice.zip"}
  ],
  "usage": {
    "summary": {
      "workbook_rows": 1,
      "memo_paragraphs": 6,
      "deck_slides": 2,
      "pdf_handout_status": "passed",
      "bundle_validation_status": "passed",
      "contact_sheet_status": "skipped"
    }
  }
}
```

Acceptance criteria:

- Runs `office.workflow.docset_to_sheet`, `word.create.report`, `office.workflow.sheet_to_deck`, optional `pdf.workflow.createpdf`, `office.bundle.export`, and `office.bundle.verify`.
- Writes all generated artifacts under the explicit output directory and never mutates source files.
- Includes `evidence.context.json` and `evidence.evidence.json` sidecars for provenance and extraction review.
- Returns per-step summaries, warnings, validation checks, artifact metadata, and next recommended tools.
- Preserves explicit skipped status for optional contact-sheet render evidence when no local renderer is configured.
- Creates the PDF handout only when `include_pdf_handout` is explicitly true, using the local HTML-first `pdf.workflow.createpdf` path with HTML, PDF, QA, artifact manifest, artifact graph, and bundle evidence.

### `office.workers.status`

Current beta optional worker contract and availability tool.

Purpose: report local optional worker contracts before an agent relies on conversion, rendering, OCR, formula calculation, or configured AI providers.

Input highlights:

```json
{
  "feature_flags": {
    "libreoffice": true
  },
  "command_paths": {
    "libreoffice": "soffice"
  }
}
```

Output highlights:

```json
{
  "tool": "office.workers.status",
  "status": "succeeded",
  "usage": {
    "summary": {
      "worker_count": 6,
      "enabled_count": 1,
      "available_count": 0,
      "missing_dependency_count": 1,
      "cloud_required_count": 1,
      "default_core_dependency_count": 0
    }
  },
  "warnings": [
    "LibreOffice worker is enabled but its executable was not found."
  ]
}
```

Acceptance criteria:

- Reports OfficeCLI, LibreOffice, browser renderer, OCR, formula engine, and configured AI provider contracts.
- Defaults every optional worker to disabled and keeps default core dependency count at zero.
- Accepts explicit feature flags and command overrides without requiring cloud accounts or hosted URLs.
- Returns validation warnings when an enabled local worker is missing its dependency or provider configuration.
- Includes license notes, cloud-required flags, and expected output evidence for every worker.

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

Current beta Office/PDF package baseline validator.

Purpose: validate package structure and common safety markers before an agent trusts or mutates an Office artifact.

Acceptance criteria:

- Accepts DOCX/DOCM, XLSX/XLSM, PPTX/PPTM, and PDF paths.
- Fails unsafe ZIP member names and missing OOXML `[Content_Types].xml`.
- Warns on macro markers and external relationships without executing or fetching them.
- Returns package summary, validation checks, warnings, and next recommended tools as ToolResult JSON.
- Does not mutate inputs, execute macros, fetch remote relationships, or claim rendered layout quality.

### `word.validation.document`

Current beta DOCX/DOCM document validator.

Purpose: validate Word document structure and safety markers before an agent trusts a DOCX/DOCM file as a source or deliverable.

CLI:

```bash
okoffice word validate-document memo.docx --json
```

MCP:

```python
word_validate_document("memo.docx")
```

REST:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/word.validation.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "memo.docx"}'
```

Expected output includes `tool: word.validation.document`, `usage.summary`, `usage.comments_policy`, `usage.tracked_changes_policy`, `usage.metadata`, `usage.styles`, `usage.accessibility_hints`, `usage.render_evidence`, package validation evidence, Word inspection evidence, warnings, validation checks, and next recommended tools.

Acceptance criteria:

- Runs `office.validation.package` before trusting the DOCX/DOCM package.
- Reopens the document with `word.inspect.document` for paragraph, heading, table, comment, style, field, tracked-change, metadata, package, and Word locator evidence.
- Warns on unresolved comments, tracked changes, missing metadata title, missing heading structure, macros, and external relationships.
- Returns `render_evidence.status = skipped` when no local DOCX render preview worker is configured.
- Does not mutate inputs, execute macros, fetch remote relationship targets, or claim rendered layout fidelity.

Error example: invalid or unsafe DOCX/DOCM packages return `status: failed` with the underlying `office.validation.package` or `word.inspect.document` error.

Limitations: this is a structural baseline. A configured local Office render worker is needed for page-layout, overflow, and visual preview evidence.

### `sheet.validation.formulas`

Current beta XLSX formula validator.

Purpose: validate workbook formulas with local structural checks before an agent uses the workbook as a source or delivery artifact.

Acceptance criteria:

- Reuses local workbook inspection and rejects invalid/unsafe packages through that path.
- Reports formula inventory, external formula references, cached formula error values, missing cached values, and potential self references.
- Reports named-range, table, and chart binding inventory.
- Returns `formula_evaluation.status = structural_only` and a skipped worker check when no formula calculation worker is configured.
- Treats formula risks, macros, and external workbook relationships as warnings, not silent success.
- Does not execute macros, fetch external workbook links, or claim formula values were recalculated.

### `deck.validation.presentation`

Current beta PPTX/PPTM presentation validator.

Purpose: validate presentation structure and safety markers before an agent trusts a deck as a deliverable or workflow source.

CLI:

```bash
okoffice deck validate-presentation board-review.pptx --json
```

MCP:

```python
deck_validate_presentation("board-review.pptx")
```

REST:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/deck.validation.presentation/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "board-review.pptx"}'
```

Expected output includes `tool: deck.validation.presentation`, `usage.summary`, `usage.title_checks`, `usage.notes_policy`, `usage.media_refs`, `usage.theme_consistency`, `usage.placeholder_overflow`, `usage.render_evidence`, warnings, validation checks, and next recommended tools.

Acceptance criteria:

- Reuses `deck.inspect.presentation` and never mutates the input package.
- Reports slide count, missing titles, slides without speaker notes, shape/chart/media/theme counts, macro markers, and external relationships.
- Returns native Deck locators for title and notes warnings.
- Returns `placeholder_overflow.status = structural_only` because visual overflow needs a render/layout worker.
- Returns a skipped `contact_sheet_render_evidence` check when no local PPTX contact-sheet renderer is configured.
- Does not execute macros, fetch remote relationship targets, or claim rendered layout fidelity.

Error example: invalid PPTX/PPTM packages return `status: failed` with the inspection error code, usually `unsupported_file_type` or `unsafe_input_rejected`.

Limitations: this is a structural baseline. Use `deck.validation.contact_sheet` or an optional local render worker for visual preview evidence.

### `pdf.validation.render_check`

Current implemented PDF-domain validator. Every generated PDF must pass renderability, page count, blank-page checks, and manifest requirements.

## Bundle Tools

### `office.bundle.export`

Current beta bundle export tool.

Purpose: package multiple artifacts, source maps, validation reports, and manifests into one portable audit bundle.

Acceptance criteria:

- Reuses the local artifact bundle engine.
- Writes a new `.zip`/`.okoffice.zip` artifact and never mutates included files.
- Includes a bundle manifest, sanitized artifact paths, and SHA-256 checksum file.
- Adds okoffice product metadata while preserving local compatibility with existing bundle verification.
- Returns canonical `tool: office.bundle.export`.

### `office.bundle.verify`

Current beta bundle verification tool.

Purpose: verify checksums, artifact presence, source refs, validation reports, and dependency/license notes.

Acceptance criteria:

- Reuses the local artifact bundle verifier.
- Bundle verification is local-first.
- Missing artifacts or hash mismatches fail.
- Warnings remain visible to agents.
- Bundle does not include secrets or proprietary cloud state.
- Returns canonical `tool: office.bundle.verify`.

## First Migration Milestones

1. Keep `okpdf` and `pdf.*` stable.
2. Add `okoffice` CLI alias and top-level `office.inspect.file`.
3. Add deterministic DOCX/XLSX/PPTX inspect tools.
4. Add Office IR and Source Graph support for all four formats.
5. Add validation reports for Word, Excel, and PowerPoint.
6. Add `office.workflow.docset_to_sheet`.
7. Add `office.workflow.sheet_to_deck`.
8. Add `office.workflow.board_pack`.
9. Add `office.bundle.export` and `office.bundle.verify`.

The first milestone is not perfect Office editing. It is trustworthy structure, evidence, and validation across the formats agents already need to work with.
