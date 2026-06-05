# okoffice REST API Examples

These examples describe the target okoffice REST surface. Current runnable `pdf.*` compatibility examples live in `docs/42_LEGACY_PDF_COMPATIBILITY.md`.

## Start Local API

```bash
okoffice serve --api --safe-root .
```

Compatibility server while the CLI migrates:

```bash
okpdf serve --api
```

## List Tools

```bash
curl http://127.0.0.1:7331/v1/tools
```

## Check Optional Workers

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.workers.status/run \
  -H 'Content-Type: application/json' \
  -d '{
    "feature_flags": {"libreoffice": true},
    "command_paths": {"libreoffice": "soffice"}
  }'
```

Expected output includes `tool: office.workers.status`, `usage.summary`, `usage.workers`, validation checks, license notes, and warnings for enabled workers whose executables are unavailable.

## Inspect Any Office Artifact

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.inspect.file/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "model.xlsx"}'
```

Expected output includes:

```json
{
  "status": "succeeded",
  "tool": "office.inspect.file",
  "usage": {
    "file": {"path": "model.xlsx", "sha256": "..."},
    "format": {"detected_format": "xlsx", "domain": "sheet"},
    "safety": {"macro_enabled": false, "has_external_relationships": false}
  },
  "next_recommended_tools": ["sheet.inspect.workbook", "office.context.build_packet"]
}
```

Error example: unsafe paths return `400` with `error.code: unsafe_input_rejected`.

## Inspect A Word Document

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/word.inspect.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "report.docx"}'
```

Expected output includes `usage.summary`, `usage.paragraphs`, `usage.headings`, `usage.tables`, `usage.comments`, `usage.styles`, `usage.metadata`, and native Word locators. External relationships and macro markers are warnings; macros and links are not executed.

## Inspect A Workbook

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/sheet.inspect.workbook/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "model.xlsx"}'
```

Expected output includes `usage.summary`, `usage.sheets`, `usage.tables`, `usage.formulas`, `usage.charts`, `usage.comments`, `usage.named_ranges`, `usage.package`, and native Sheet locators. Formula evaluation is reported as structural-only in the OSS core; macros and external relationships are not executed.

## Inspect A Presentation

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/deck.inspect.presentation/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "board.pptx"}'
```

Expected output includes `usage.summary`, `usage.slides`, `usage.shapes`, `usage.notes`, `usage.charts`, `usage.media`, `usage.themes`, `usage.package`, and native Deck locators. Layout is structural-only in the OSS core; macros, embedded code, and external relationships are not executed.

## Validate Package Safety

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.validation.package/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "report.docx"}'
```

Expected output includes `tool: office.validation.package`, `usage.summary`, unsafe member checks, content type checks, macro warnings, external relationship warnings, and next recommended tools.

## Build Context Packet

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.context.build_packet/run \
  -H 'Content-Type: application/json' \
  -d '{
    "files": [
      {"kind": "local_path", "path": "contracts/vendor-a.docx"},
      {"kind": "local_path", "path": "invoices/vendor-a.pdf"},
      {"kind": "local_path", "path": "metrics/vendor-model.xlsx"}
    ],
    "output_path": ".okoffice-out/vendor.context.json"
  }'
```

Expected output includes `usage.context_packet`, `usage.source_graph`, `usage.domains`, `usage.inspection_tools`, any package warnings, and an artifact for the written context packet JSON.

## Extract Schema

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.extract.schema/run \
  -H 'Content-Type: application/json' \
  -d '{
    "context_packet_path": ".okoffice-out/vendor.context.json",
    "schema": {
      "fields": [
        {"name": "vendor", "type": "string"},
        {"name": "renewal_date", "type": "string"},
        {"name": "annual_amount", "type": "number"},
        {"name": "risk", "type": "string"}
      ]
    },
    "output_path": ".okoffice-out/vendor.evidence.json"
  }'
```

Expected output includes `usage.summary`, `usage.extraction.rows`, `usage.extraction.rows[].field_evidence`, `usage.source_refs`, warnings for missing values, and an artifact for the written evidence JSON.

## Create Evidence Workbook

One-step workflow:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.workflow.docset_to_sheet/run \
  -H 'Content-Type: application/json' \
  -d '{
    "files": ["contracts/vendor-a.docx", "invoices/vendor-a.pdf", "notes/renewal-notes.md"],
    "schema": {
      "fields": [
        {"name": "vendor", "type": "string"},
        {"name": "renewal_date", "type": "string"},
        {"name": "annual_amount", "type": "number"},
        {"name": "risk", "type": "string"}
      ]
    },
    "output_path": ".okoffice-out/vendor-evidence.xlsx"
  }'
```

Manual workbook write:

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/sheet.write.workbook/run \
  -H 'Content-Type: application/json' \
  -d '{
    "evidence_path": ".okoffice-out/vendor.evidence.json",
    "output_path": ".okoffice-out/vendor-evidence.xlsx"
  }'
```

## Validate Workbook Formulas

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/sheet.validation.formulas/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".okoffice-out/vendor-evidence.xlsx"}'
```

## Create Deck

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/word.create.report/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workbook_path": ".okoffice-out/vendor-evidence.xlsx",
    "output_path": ".okoffice-out/vendor-memo.docx",
    "title": "Vendor Renewal Memo",
    "profile": "executive_memo"
  }'
```

## Validate Word Document

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/word.validation.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".okoffice-out/vendor-memo.docx"}'
```

Returns package health, comments/tracked-change policy, metadata, accessibility-hint, and skipped render-preview evidence checks.

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/deck.create.presentation/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workbook_path": ".okoffice-out/vendor-evidence.xlsx",
    "output_path": ".okoffice-out/vendor-board-deck.pptx",
    "title": "Vendor Renewal Review",
    "profile": "board_review"
  }'
```

## Validate Deck Contact Sheet

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/deck.validation.contact_sheet/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".okoffice-out/vendor-board-deck.pptx"}'
```

## Validate Deck Presentation

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/deck.validation.presentation/run \
  -H 'Content-Type: application/json' \
  -d '{"path": ".okoffice-out/vendor-board-deck.pptx"}'
```

Returns structural title, notes, media, theme, safety-marker, placeholder-overflow, and render-evidence checks for a PPTX/PPTM deck.

## Create Board Pack

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.workflow.board_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "files": [
      "contracts/vendor-a.docx",
      "invoices/vendor-a.pdf",
      "metrics/vendor-model.xlsx"
    ],
    "schema": {
      "fields": [
        {"name": "vendor", "type": "string", "aliases": ["Vendor"]},
        {"name": "renewal_date", "type": "date", "aliases": ["Renewal date"]},
        {"name": "annual_amount", "type": "number", "aliases": ["Annual amount"]}
      ]
    },
    "out_dir": ".okoffice-out/vendor-board-pack",
    "title": "Vendor Renewal Review",
    "profile": "board_review",
    "include_pdf_handout": true
  }'
```

## Verify Bundle

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.bundle.export/run \
  -H 'Content-Type: application/json' \
  -d '{
    "artifact_paths": [
      ".okoffice-out/vendor-evidence.xlsx",
      ".okoffice-out/vendor-board-deck.pptx"
    ],
    "output_path": ".okoffice-out/vendor-board-pack.okoffice.zip",
    "title": "Vendor Board Pack"
  }'
```

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.bundle.verify/run \
  -H 'Content-Type: application/json' \
  -d '{
    "bundle_path": ".okoffice-out/vendor-board-pack.okoffice.zip"
  }'
```
