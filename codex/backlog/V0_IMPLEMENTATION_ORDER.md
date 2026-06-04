# V0 Implementation Order for Codex

Do not implement randomly. okoffice is the product. The existing `agentpdf` / `okpdf` / `pdf.*` code is a compatibility domain that should remain stable while new Office infrastructure is added.

## Step 1 - Naming and Compatibility Boundary

Implement:

- `okoffice` CLI alias that points at the existing local runner.
- README/docs language that treats `okpdf` as compatibility.
- tool discovery output that can distinguish implemented compatibility tools from target okoffice tools.

Acceptance:

```bash
okpdf tools list --json
okoffice tools list --json
pytest tests/unit/test_docs_integrity.py -q
```

`okoffice` may initially show target namespace metadata while reusing the existing runner.

## Step 2 - okoffice Manifest Skeleton

Implement:

- a target okoffice manifest or manifest section for `office.*`, `word.*`, `sheet.*`, and `deck.*`.
- status labels: `implemented`, `planned`, `optional_worker`, `cloud_only`, `legacy_compat`.
- docs that explain which tools are runnable today.

Acceptance:

- machine manifest tests still pass.
- target tools are discoverable without pretending they are executable.

## Step 3 - Office IR and Native Locators

Implement schemas for:

- Source Graph.
- Office IR.
- Word locators: section, paragraph, run, table, comment.
- Excel locators: sheet, cell, range, table, chart, formula.
- PowerPoint locators: slide, shape, placeholder, notes.
- PDF locators: page, bbox, annotation, form field.

Acceptance:

- schemas validate example JSON.
- tests cover serialization.

## Step 4 - `office.inspect.file`

Implement a deterministic file inspector.

Acceptance:

- detects PDF, DOCX, XLSX, PPTX, CSV, Markdown, HTML.
- reports file size, hash, extension, MIME type, package type, and recommended next tools.
- rejects unsafe paths.

## Step 5 - DOCX Inspect

Implement `word.inspect.document`.

Acceptance:

- reports paragraph count, headings, tables, comments, styles, sections, fields, metadata markers, tracked-change markers, and package warnings.
- does not claim rendered layout unless a render worker exists.
- returns ToolResult.

## Step 6 - XLSX Inspect

Implement `sheet.inspect.workbook`.

Acceptance:

- reports sheets, used ranges, tables, formulas, charts, named ranges, comments, hidden sheets, external links, workbook properties, and macro/package markers.
- does not execute macros.
- formula evaluation status is explicit.

## Step 7 - PPTX Inspect

Implement `deck.inspect.presentation`.

Acceptance:

- reports slide count, slide order, text blocks, notes, shapes, placeholders, charts, media refs, hidden slides, layouts, and theme metadata.
- does not claim visual fit without render/contact-sheet evidence.

## Step 8 - Office Validation Baseline

Implement:

- `office.validation.package`
- `word.validation.document`
- `sheet.validation.formulas`
- `deck.validation.presentation`

Acceptance:

- unsafe package entries fail.
- macro/external-link/embedded-object risks are warnings.
- formula/link checks are structural when no worker is configured.
- optional worker skips are structured, not silent.

## Step 9 - Context Packet for Office Sources

Extend context ingestion to support:

- DOCX text/outline/table/comment nodes.
- XLSX sheet/table/formula nodes.
- PPTX slide/text/notes nodes.
- existing PDF nodes.

Acceptance:

- source graph nodes contain native locators.
- context packet examples validate.

## Step 10 - Evidence Workbook Workflow

Implement:

- `office.extract.schema`
- `sheet.create.evidence_workbook`
- `office.workflow.docset_to_sheet`

Acceptance:

- multiple Word/PDF sources can produce an XLSX workbook with source-ref columns.
- missing fields and low confidence are warnings.
- workbook validation runs.

## Step 11 - Sheet To Deck Workflow

Implement:

- `deck.compose.plan`
- `deck.create.presentation`
- `deck.validation.contact_sheet`
- `office.workflow.sheet_to_deck`

Acceptance:

- workbook data can produce editable PPTX slides.
- slide claims cite workbook ranges or source graph nodes.
- contact-sheet validation runs or returns structured worker-unavailable evidence.

## Step 12 - Board Pack Bundle

Implement:

- `word.create.report`
- `office.workflow.board_pack`
- `office.bundle.export`
- `office.bundle.verify`

Acceptance:

- emits workbook, memo, deck, optional PDF handout, manifest, source map, validation report, and bundle.
- bundle hashes verify.

## Step 13 - Agent Setup for okoffice

Implement target setup commands:

- Codex.
- Claude Code/Desktop.
- Cursor.
- Kilo Code.
- OpenClaw.
- OpenAI Agents.

Acceptance:

- generated MCP configs use server name `okoffice`.
- compatibility configs still work.

## Step 14 - Optional Workers

Add worker contracts, not hard dependencies:

- OfficeCLI adapter.
- LibreOffice/render adapter.
- browser renderer.
- OCR.
- formula engine.
- AI provider routing.

Acceptance:

- workers are feature-flagged.
- license notes are documented.
- unavailability is returned as structured evidence.

## Step 15 - Docs and Examples Polish

Update:

- README.
- examples.
- MCP configs.
- REST examples.
- SDK examples.
- fixture docs.

Acceptance:

- examples lead with okoffice workflows.
- legacy PDF examples live in compatibility docs.
- docs and registry tests pass.
