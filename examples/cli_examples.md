# okoffice CLI Examples

These examples describe the target okoffice command surface. Current runnable `okpdf` examples live in `docs/42_LEGACY_PDF_COMPATIBILITY.md`.

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

## Inspect Office Artifacts

```bash
okoffice inspect report.docx --json
okoffice inspect model.xlsx --json
okoffice inspect deck.pptx --json
okoffice inspect packet.pdf --json
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

Limitations: this first inspect pass identifies file type, checksum, package markers, macros, external relationships, and next tools. It does not yet extract full Word/Excel/PowerPoint structure.

## Build Evidence Workbook

```bash
okoffice context build \
  --file contracts/vendor-a.docx \
  --file invoices/vendor-a.pdf \
  --file notes/renewal-notes.md \
  -o .okoffice-out/vendor.context.json \
  --title "Vendor Context" \
  --intent "Prepare a board review" \
  --json
```

Current output includes `tool: office.context.build_packet`, a local context packet artifact, file/native source graph nodes, native child nodes when available, format counts, validation checks, and next recommended tools.

Current local evidence workbook flow:

```bash
okoffice workflow extract-to-sheet \
  --context-packet .okoffice-out/vendor.context.json \
  -o .okoffice-out/vendor-evidence.xlsx \
  --json
```

The workbook includes `Tables`, `Cells`, and `SourceGraph` sheets when a context packet is supplied. Row and cell records include `context_packet_id`, `source_graph_id`, and native source node refs when available.

Current schema extraction flow:

```bash
okoffice extract schema .okoffice-out/vendor.context.json \
  --schema examples/schemas/vendor-renewal.json \
  -o .okoffice-out/vendor.evidence.json \
  --json

okoffice sheet create-evidence-workbook .okoffice-out/vendor.evidence.json \
  -o .okoffice-out/vendor-evidence.xlsx \
  --json
```

## Validate Package Safety

```bash
okoffice validate package contracts/vendor-a.docx --json
```

Expected output includes `tool: office.validation.package`, package type, member counts, unsafe entry checks, macro warnings, external relationship warnings, and `mutates_inputs: false`.

## Create Deck From Workbook

```bash
okoffice deck compose-plan \
  .okoffice-out/vendor-evidence.xlsx \
  -o .okoffice-out/vendor-deck.plan.json \
  --title "Vendor Board Review" \
  --json

okoffice workflow sheet-to-deck \
  .okoffice-out/vendor-evidence.xlsx \
  -o .okoffice-out/vendor-board-deck.pptx \
  --title "Vendor Board Review" \
  --json

okoffice deck validate \
  .okoffice-out/vendor-board-deck.pptx \
  --json
```

## Create Board Pack

```bash
okoffice workflow board-pack \
  .okoffice-out/vendor-evidence.xlsx \
  .okoffice-out/vendor-board-deck.pptx \
  -o .okoffice-out/vendor-board-pack.zip \
  --title "Vendor Board Review" \
  --json

okoffice bundle verify .okoffice-out/vendor-board-pack.zip --json
```

Expected artifacts:

- `artifacts/vendor-evidence.xlsx`.
- `artifacts/vendor-board-deck.pptx`.
- `okoffice-manifest.json`.
- `okoffice-validation.json`.
- `.zip` board pack bundle.

The verify step returns `validation.status: passed` when the ZIP is readable, the manifest and validation report are present, artifact members exist, and every packaged artifact matches its recorded size and SHA-256.

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
okoffice bundle verify .okoffice-out/vendor-board-pack.zip --json
```

Target export shape:

```bash
okoffice bundle export \
  --file .okoffice-out/vendor-board-pack/vendor-evidence.xlsx \
  --file .okoffice-out/vendor-board-pack/memo.updated.docx \
  --file .okoffice-out/vendor-board-pack/vendor-board-deck.pptx \
  --file .okoffice-out/vendor-board-pack/handout.pdf \
  -o .okoffice-out/vendor-board-pack.okoffice.zip \
  --json
```

## Serve Agents

```bash
okoffice serve --mcp --safe-root .
okoffice serve --api --safe-root .
```
