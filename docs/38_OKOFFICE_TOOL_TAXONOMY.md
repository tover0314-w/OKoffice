# 38 - okoffice Tool Taxonomy

## Naming Principle

Use format-native namespaces for format-specific tools and `office.*` for cross-format workflows.

Target examples:

```text
office.inspect.file
word.inspect.document
sheet.inspect.workbook
deck.inspect.presentation
pdf.inspect.document
office.workflow.board_pack
office.bundle.verify
```

Existing `pdf.*` tools remain legacy compatibility names until the machine manifest and adapters migrate.

## Common Tool Result

Every tool returns:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "office.workflow.board_pack",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

## Cross-Format Namespaces

### `office.inspect`

- `office.inspect.file`: detect format, package health, security markers, recommended next tools.
- `office.inspect.batch`: inspect many files and return a portfolio summary.

### `office.context`

- `office.context.ingest`: normalize one source into a source graph node.
- `office.context.build_packet`: build a reusable context packet from files, text, links, and sidecars.
- `office.context.classify`: classify source roles and likely extraction routes.

### `office.extract`

- `office.extract.schema`: extract fields from mixed sources into structured rows.
- `office.extract.claims`: extract cited claims.
- `office.extract.entities`: extract cited entities and dates.
- `office.extract.obligations`: contract-oriented obligation extraction.

### `office.evidence`

- `office.evidence.map_sources`: map generated blocks/rows/slides back to sources.
- `office.evidence.coverage`: report source coverage and unsupported claims.
- `office.evidence.verify_citations`: verify cited locators and excerpts.

### `office.patch`

- `office.patch.plan`: plan non-mutating edits across formats.
- `office.patch.preview`: preview patch effects.
- `office.patch.apply`: write a new patched artifact.
- `office.patch.verify`: validate patch output and lineage.

### `office.workflow`

- `office.workflow.docset_to_sheet`
- `office.workflow.sheet_to_deck`
- `office.workflow.board_pack`
- `office.workflow.review_and_patch`
- `office.workflow.redaction_packet`

### `office.bundle`

- `office.bundle.export`
- `office.bundle.verify`: verify OKoffice board pack manifests, validation reports, artifact members, byte sizes, and SHA-256 checksums.
- `office.bundle.graph`
- `office.bundle.report`

### `office.agent.setup`

- `office.agent.setup.codex`
- `office.agent.setup.claude_code`
- `office.agent.setup.cursor`
- `office.agent.setup.kilo_code`
- `office.agent.setup.openclaw`
- `office.agent.setup.openai_agents`

## Word Tools

Inspect/extract:

- `word.inspect.document`
- `word.extract.text`
- `word.extract.outline`
- `word.extract.tables`
- `word.extract.comments`
- `word.extract.revisions`
- `word.extract.fields`
- `word.extract.styles`

Create/edit:

- `word.create.document`
- `word.create.report`
- `word.create.memo`
- `word.patch.paragraph`
- `word.patch.table`
- `word.patch.comment`

Validate/review:

- `word.validation.package`
- `word.validation.document`
- `word.validation.metadata`
- `word.validation.accessibility`
- `word.review.claims`
- `word.review.style`

## Excel Tools

Inspect/extract:

- `sheet.inspect.workbook`
- `sheet.extract.sheets`
- `sheet.extract.tables`
- `sheet.extract.formulas`
- `sheet.extract.charts`
- `sheet.extract.named_ranges`
- `sheet.extract.comments`
- `sheet.extract.pivots`

Create/edit:

- `sheet.create.workbook`
- `sheet.create.evidence_workbook`
- `sheet.create.financial_model`
- `sheet.patch.cells`
- `sheet.patch.table`
- `sheet.patch.formulas`
- `sheet.patch.chart`

Validate/review:

- `sheet.validation.package`
- `sheet.validation.formulas`
- `sheet.validation.model_checks`
- `sheet.validation.external_links`
- `sheet.review.model`
- `sheet.review.number_consistency`

## PowerPoint Tools

Deck creation follows a taste-driven HTML-first target route:

```text
deck.compose.plan
-> deck.render.html
-> deck.validation.html_preview
-> deck.validation.contact_sheet
-> deck.export.pptx
-> deck.validate.presentation
```

`deck.create.presentation` is the public convenience command. The current beta implementation writes PPTX directly from an outline or composition plan. The target implementation should orchestrate the HTML preview/export route and report explicit fallback evidence when optional workers are unavailable.

Inspect/extract:

- `deck.inspect.presentation`
- `deck.extract.slides`
- `deck.extract.text`
- `deck.extract.notes`
- `deck.extract.shapes`
- `deck.extract.media`
- `deck.extract.charts`
- `deck.extract.theme`

Create/edit:

- `deck.compose.plan`
- `deck.render.html`
- `deck.export.pptx`
- `deck.create.presentation`
- `deck.create.board_deck`
- `deck.patch.slide`
- `deck.patch.shape`
- `deck.patch.notes`
- `deck.patch.chart`

Validate/review:

- `deck.validation.package`
- `deck.validation.html_preview`
- `deck.validation.contact_sheet`
- `deck.validation.placeholders`
- `deck.validation.notes`
- `deck.review.taste`
- `deck.review.story`
- `deck.review.claims`

## PDF Tools

PDF remains a first-class format domain:

- `pdf.inspect.document`
- `pdf.inspect.pages`
- `pdf.organize.merge`
- `pdf.organize.split`
- `pdf.convert.to_images`
- `pdf.convert.from_images`
- `pdf.validation.render_check`
- `pdf.validation.blank_page_check`
- `pdf.security.redact`
- `pdf.security.verify_redaction`

New PDF work should support okoffice workflows unless it is required for compatibility, safety, or validation.

## First Implementation Wave

Build in this order:

1. `office.inspect.file`
2. `word.inspect.document`
3. `sheet.inspect.workbook`
4. `deck.inspect.presentation`
5. `office.context.build_packet`
6. `office.extract.schema`
7. `sheet.create.evidence_workbook` (beta local writer with SourceRefs sheet)
8. `sheet.validation.formulas` (beta structural formula QA)
9. `deck.compose.plan` (beta source-mapped deck plan)
10. `deck.render.html` (beta HTML slide preview package)
11. `deck.validation.html_preview` (beta package/source validation; screenshot taste checks remain planned)
12. `deck.validation.contact_sheet`
13. `deck.export.pptx` (beta editable PowerPoint export through the local outline route)
14. `deck.create.presentation` (beta direct PPTX writer now, target orchestrator)
15. `word.create.report`
16. `office.bundle.export`
17. `office.bundle.verify`

This wave favors reliable inspect/extract/validate workflows before ambitious editing.
