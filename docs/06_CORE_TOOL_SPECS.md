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

Target PPTX creation tool.

Purpose: create a PowerPoint deck from claim spine, slide layouts, charts, tables, notes, and source refs.

Acceptance criteria:

- Uses a style pack layout and theme tokens.
- Produces slide ids, shape ids, and source refs.
- Includes speaker notes when required by profile.
- Validates contact sheet/render preview when available.
- Returns slide-level warnings for fit, missing evidence, or weak hierarchy.

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

### `word.validation.document`

Checks DOCX package health, styles, comments/tracked changes policy, metadata, accessibility hints, and optional render preview.

### `sheet.validation.formulas`

Checks formula references, formula errors when evaluation is available, external links, circular refs, named ranges, and chart/table bindings.

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

1. Keep `okpdf` and `pdf.*` stable.
2. Add `okoffice` CLI alias and top-level `office.inspect.file`.
3. Add deterministic DOCX/XLSX/PPTX inspect tools.
4. Add Office IR and Source Graph support for all four formats.
5. Add validation reports for Word, Excel, and PowerPoint.
6. Add `office.workflow.docset_to_sheet`.
7. Add `office.workflow.sheet_to_deck`.
8. Add `office.bundle.export` and `office.bundle.verify`.

The first milestone is not perfect Office editing. It is trustworthy structure, evidence, and validation across the formats agents already need to work with.
