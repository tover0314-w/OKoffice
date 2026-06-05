# 12 - Artifact Profiles and Style Packs

okoffice should create polished Office artifacts from mixed context while preserving evidence, validation, and format-specific quality. A style pack is no longer a PDF-only theme. It is a cross-format design and quality contract for Word documents, Excel workbooks, PowerPoint decks, PDFs, and audit bundles.

## Goal

Agents should be able to say:

```text
Use these Word and PDF sources, extract the numbers into Excel,
then create an executive PowerPoint and a board-ready PDF handout.
```

okoffice should turn that into:

- A Source Graph with evidence locators.
- A target artifact profile.
- Office IR and/or Composition IR.
- Generated artifacts.
- Validation reports for every generated file.
- A bundle manifest that links outputs back to sources.

## Artifact Profiles

An artifact profile defines the purpose, audience, structure, validation rules, and expected quality bar for an output.

Common profiles:

- `executive_memo`: Word report with concise sections, comments cleared, styles normalized, and source appendix.
- `evidence_workbook`: Excel workbook with extracted rows, source columns, confidence, formulas, filters, and validation sheet.
- `board_deck`: PowerPoint deck with executive narrative, chart slides, speaker notes, and cited appendix.
- `financial_model`: Excel workbook with assumptions, model sheets, checks, summaries, and chart output.
- `research_brief`: Word or PDF brief with citations, figures, and limitations.
- `pitch_deck`: PowerPoint deck with strong visual hierarchy and tight claim spine.
- `contract_packet`: Word/PDF bundle with clause extraction, risk notes, and redaction checks.
- `training_material`: Word handout, PowerPoint deck, and PDF export.
- `audit_bundle`: Multi-artifact package with manifest, source map, validation, and provenance.

## Style Pack Schema

A style pack defines shared visual tokens plus format-specific behavior.

```json
{
  "style_id": "executive_board_pack",
  "name": "Executive Board Pack",
  "description": "Calm executive reporting style for memo, workbook, deck, and PDF handout.",
  "tokens": {
    "colors": {
      "primary": "#155E75",
      "accent": "#D97706",
      "ink": "#111827",
      "muted": "#6B7280"
    },
    "typography": {
      "heading_font": "system-sans",
      "body_font": "system-sans",
      "base_size": 10
    },
    "spacing": {
      "density": "compact",
      "section_gap": 16
    }
  },
  "word": {
    "page_size": "A4",
    "styles": ["Title", "Heading 1", "Heading 2", "Body", "Caption", "Source Note"],
    "requires_source_appendix": true
  },
  "excel": {
    "table_style": "medium",
    "freeze_header_rows": true,
    "validation_sheet": true,
    "formula_check_sheet": true
  },
  "powerpoint": {
    "slide_size": "wide",
    "layouts": ["title", "section", "claim_chart", "table", "evidence_appendix"],
    "requires_speaker_notes": true
  },
  "pdf": {
    "page_size": "A4",
    "orientation": "portrait",
    "requires_render_check": true
  }
}
```

## Format Rules

### Word

Word outputs must be more than text dumps. They should have:

- Stable paragraph and table ids for patching.
- Named styles instead of ad hoc formatting.
- Headings, table captions, figure captions, citations, and source appendices.
- Comment/tracked-change policy.
- Metadata and privacy checks.
- Render preview evidence when a renderer is available.

### Excel

Excel outputs should be useful workbooks, not CSVs in disguise:

- Tables with filters and typed columns.
- Source-ref columns for extracted data.
- Formula cells separated from input cells.
- Named ranges for important assumptions.
- Check sheets for totals, missing fields, and formula risks.
- Charts sourced from explicit ranges.
- No formula errors before completion.

### PowerPoint

Deck outputs should follow a claim spine:

- One main claim per slide unless the profile says otherwise.
- Slide layouts chosen from the style pack.
- Speaker notes with evidence refs where needed.
- Chart/table slides linked to workbook ranges or source nodes.
- Appendix slides for citations and assumptions.
- Rendered contact-sheet validation.

### PDF

PDF remains a first-class output, especially for final handouts, immutable reports, and audit bundles:

- Page count and renderability checks.
- Blank page detection.
- Optional visual diff.
- Metadata and redaction verification when relevant.
- Source map and manifest links back to Office IR.

## Rich Block Requirements

Agent-native composition requires blocks that preserve intent and evidence:

- `claim`: statement, confidence, source refs, reviewer notes.
- `paragraph`: text, style, source refs, patch policy.
- `table`: columns, data types, source ranges, validation rules.
- `chart`: data range, chart type, title, insight, fallback image.
- `figure`: image source, caption, crop/fill rules, alt text.
- `formula`: formula text, precedents, dependents, recalculation status.
- `slide`: title, claim, layout, notes, source refs.
- `comment`: author, target locator, severity, resolution status.
- `citation`: source locator, excerpt, confidence, format.
- `appendix`: evidence cards, limitations, validation summaries.

If a block cannot fit safely, rendering should produce warnings rather than clipping or dropping content.

## Current Built-ins

The current OSS codebase implements PDF-oriented style packs:

- `plain_report`
- `business_report_modern`
- `academic_paper_basic`
- `resume_modern`
- `invoice_clean`
- `paper_ink`

These remain valid for `okpdf` and the PDF domain inside okoffice.

Target okoffice packs:

- `executive_board_pack`
- `evidence_workbook_clean`
- `board_deck_modern`
- `research_brief_pack`
- `financial_model_standard`
- `contract_review_pack`
- `training_material_pack`
- `pitch_deck_sharp`
- `audit_bundle_plain`

## Template Packs

Template packs should evolve from PDF template packages into multi-artifact packages. A pack may define:

- Supported artifact profiles.
- Field contracts and required data.
- Word section templates.
- Excel sheet/table/formula templates.
- PowerPoint slide layouts and speaker-note rules.
- PDF handout/export rules.
- Sample data and preview commands.
- Validation requirements.
- License/dependency notes.

Example:

```json
{
  "pack_id": "local-agent-board-pack",
  "profiles": ["executive_memo", "evidence_workbook", "board_deck", "audit_bundle"],
  "artifacts": {
    "word": {"template": "executive_memo"},
    "excel": {"template": "evidence_workbook"},
    "powerpoint": {"template": "board_deck"},
    "pdf": {"template": "board_handout"}
  },
  "validation": [
    "word.validation.document",
    "sheet.validation.formulas",
    "deck.validation.presentation",
    "deck.validation.contact_sheet",
    "pdf.validation.render_check",
    "office.bundle.verify"
  ]
}
```

## CLI Compatibility

Current PDF command:

```bash
okpdf create markdown examples/sample-documents/business_report.md \
  -o .agentpdf-out/business-report.pdf \
  --style-pack business_report_modern \
  --json
```

Target okoffice commands:

```bash
okoffice styles list --json

okoffice workflow docset-to-sheet \
  --file sources/vendor-a.docx \
  --file sources/vendor-b.pdf \
  --schema examples/schemas/vendor-renewal.json \
  -o .okoffice-out/evidence.xlsx \
  --json

okoffice workflow sheet-to-deck \
  --workbook .okoffice-out/evidence.xlsx \
  -o .okoffice-out/board-deck.pptx \
  --profile board_deck \
  --json

okoffice bundle export \
  --artifact .okoffice-out/evidence.xlsx \
  --artifact .okoffice-out/board-deck.pptx \
  --artifact .okoffice-out/board-handout.pdf \
  -o .okoffice-out/board-pack.okoffice.zip \
  --json
```

## Validation Contract

A style or template pack is complete only when it declares validation expectations:

- Word: package integrity, styles, comments/tracked changes, metadata, render preview, accessibility.
- Excel: package integrity, formula references, formula errors, chart/table refs, named ranges, hidden sheets, macros.
- PowerPoint: package integrity, slide count, placeholder fit, notes, media refs, contact sheet, theme consistency.
- PDF: page count, renderability, blank-page detection, metadata, redaction, optional visual diff.
- Bundle: manifest hashes, source-map coverage, artifact graph, warnings, dependency/license notes.

The design standard is "beautiful by default", but the engineering standard is "auditable by default".
