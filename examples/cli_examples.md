# okoffice CLI Examples

These examples describe the beta okoffice command surface. Compatibility `okpdf` examples live in `docs/42_LEGACY_PDF_COMPATIBILITY.md`.

## Setup

```bash
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
```

## Discover Tools

```bash
okoffice tools list --json
okoffice tools show office.workflow.board_pack --json
```

## Check Optional Workers

```bash
okoffice workers status --json
okoffice workers status --enable libreoffice --command libreoffice=soffice --json
```

Returns `office.workers.status` with disabled-by-default worker contracts for OfficeCLI, LibreOffice, browser rendering, OCR, formula calculation, and configured AI providers. Enabled workers report `available`, `missing_dependency`, or `not_configured` with validation warnings and license notes.

## Inspect Office Artifacts

```bash
okoffice inspect report.docx --json
okoffice inspect model.xlsx --json
okoffice inspect deck.pptx --json
okoffice inspect packet.pdf --json
okoffice word inspect report.docx --json
okoffice word validate-document report.docx --json
okoffice sheet inspect model.xlsx --json
okoffice deck inspect board.pptx --json
```

Current output shape:

```json
{
  "status": "succeeded",
  "tool": "office.inspect.file",
  "usage": {
    "format": {
      "detected_format": "docx",
      "domain": "word",
      "package_type": "ooxml_docx"
    },
    "safety": {
      "mutates_inputs": false,
      "macro_enabled": false,
      "has_external_relationships": false
    }
  },
  "next_recommended_tools": ["word.inspect.document", "office.context.build_packet"]
}
```

Error example:

```bash
okoffice inspect ../secret.docx --json
```

Returns `status: failed` with `error.code: unsafe_input_rejected`.

For Word structure:

```bash
okoffice word inspect report.docx --json
```

Returns `word.inspect.document` with paragraph, heading, table, comment, style, section, field, metadata, tracked-change, package warning, and Word locator facts.

`word.validation.document` returns package health, comments/tracked-change policy, metadata, accessibility-hint, and render-preview evidence checks without mutating the input or executing macros.

For workbook structure:

```bash
okoffice sheet inspect model.xlsx --json
```

Returns `sheet.inspect.workbook` with sheet, used range, table, formula, chart, comment, named range, package warning, and Sheet locator facts.

For presentation structure:

```bash
okoffice deck inspect board.pptx --json
```

Returns `deck.inspect.presentation` with slide, shape, notes, chart, media, theme, package warning, and Deck locator facts.

Limitations: `office.inspect.file` identifies file type, checksum, package markers, macros, external relationships, and next tools. `word.inspect.document` extracts DOCX structure but does not render final layout or execute macros, embedded code, or external links. `sheet.inspect.workbook` extracts XLSX/XLSM package structure but does not calculate formulas, execute macros, or fetch external workbook links. `deck.inspect.presentation` extracts PPTX/PPTM package structure but does not claim final visual fit, execute macros, or fetch external links.

## Validate Package Safety

```bash
okoffice validation package report.docx --json
okoffice validation package model.xlsx --json
okoffice validation package board.pptx --json
```

Returns `office.validation.package` with OOXML/PDF package type, member counts, unsafe ZIP entry checks, content type checks, macro warnings, external relationship warnings, and next recommended tools.

## Build Evidence Workbook

One-step workflow:

```bash
okoffice workflow docset-to-sheet \
  --file contracts/vendor-a.docx \
  --file invoices/vendor-a.pdf \
  --file notes/renewal-notes.md \
  --schema examples/schemas/vendor-renewal.json \
  -o .okoffice-out/vendor-evidence.xlsx \
  --json
```

Manual equivalent:

```bash
okoffice context build \
  --file contracts/vendor-a.docx \
  --file invoices/vendor-a.pdf \
  --file notes/renewal-notes.md \
  -o .okoffice-out/vendor.context.json \
  --json
```

Returns `office.context.build_packet` with per-file format/safety summaries, available Word/Sheet/Deck/PDF structure summaries, a cross-format source graph, warnings, and the written context packet artifact.

```bash
okoffice extract schema .okoffice-out/vendor.context.json \
  --schema examples/schemas/vendor-renewal.json \
  -o .okoffice-out/vendor.evidence.json \
  --json
```

Returns `office.extract.schema` with schema-shaped rows, per-field evidence, source refs, warnings for missing values, and a written evidence JSON artifact.

```bash
okoffice sheet write-workbook .okoffice-out/vendor.evidence.json \
  -o .okoffice-out/vendor-evidence.xlsx \
  --json
```

```bash
okoffice sheet validate-formulas .okoffice-out/vendor-evidence.xlsx --json
```

## Create Deck From Workbook

```bash
okoffice deck create \
  --from-workbook .okoffice-out/vendor-evidence.xlsx \
  --profile board_review \
  --title "Vendor Renewal Review" \
  -o .okoffice-out/vendor-board-deck.pptx \
  --json

okoffice deck validate-contact-sheet .okoffice-out/vendor-board-deck.pptx --json
okoffice deck validate-presentation .okoffice-out/vendor-board-deck.pptx --json
```

`deck.validation.presentation` returns structural title, notes, media, theme, safety, placeholder-overflow, and render-evidence checks. It does not execute macros, fetch remote links, or claim rendered visual fit without a local renderer.

## Create Board Pack

```bash
okoffice workflow board-pack \
  --file contracts/vendor-a.docx \
  --file invoices/vendor-a.pdf \
  --file metrics/vendor-model.xlsx \
  --schema examples/schemas/vendor-renewal.json \
  --out-dir .okoffice-out/vendor-board-pack \
  --title "Vendor Renewal Review" \
  --include-pdf-handout \
  --json
```

Expected artifacts:

- `.okoffice-out/vendor-board-pack/evidence.xlsx` evidence workbook.
- `.okoffice-out/vendor-board-pack/evidence.context.json` context packet.
- `.okoffice-out/vendor-board-pack/evidence.evidence.json` extracted evidence.
- `.okoffice-out/vendor-board-pack/memo.docx` executive memo.
- `.okoffice-out/vendor-board-pack/board-deck.pptx` board deck.
- `.okoffice-out/vendor-board-pack/handout.html` HTML-first PDF source.
- `.okoffice-out/vendor-board-pack/handout.pdf` validated PDF handout.
- `.okoffice-out/vendor-board-pack/handout.qa.json` PDF validation evidence.
- `.okoffice-out/vendor-board-pack/board-pack.okoffice.zip` checksum bundle.

## Patch And Verify

```bash
okoffice patch plan .okoffice-out/vendor-board-pack/memo.docx \
  --request "Clarify the renewal risk wording in the executive summary." \
  -o .okoffice-out/vendor-board-pack/memo.patch.json \
  --json

okoffice patch preview .okoffice-out/vendor-board-pack/memo.patch.json \
  -o .okoffice-out/vendor-board-pack/memo.patch-preview.json \
  --json

okoffice patch apply .okoffice-out/vendor-board-pack/memo.patch.json \
  -o .okoffice-out/vendor-board-pack/memo.updated.docx \
  --json

okoffice patch verify .okoffice-out/vendor-board-pack/memo.patch.json \
  .okoffice-out/vendor-board-pack/memo.updated.docx \
  --json
```

## Bundle

```bash
okoffice bundle export \
  --file .okoffice-out/vendor-board-pack/vendor-evidence.xlsx \
  --file .okoffice-out/vendor-board-pack/memo.updated.docx \
  --file .okoffice-out/vendor-board-pack/vendor-board-deck.pptx \
  --file .okoffice-out/vendor-board-pack/handout.pdf \
  -o .okoffice-out/vendor-board-pack.okoffice.zip \
  --json

okoffice bundle verify .okoffice-out/vendor-board-pack.okoffice.zip --json
```

## Serve Agents

```bash
okoffice serve --mcp --safe-root .
okoffice serve --api --safe-root .
```
