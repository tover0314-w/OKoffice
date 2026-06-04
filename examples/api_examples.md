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

## Inspect A Workbook

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/sheet.inspect.workbook/run \
  -H 'Content-Type: application/json' \
  -d '{
    "file": {"kind": "local_path", "path": "model.xlsx"},
    "include_formulas": true,
    "include_charts": true,
    "include_security": true
  }'
```

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

## Create Evidence Workbook

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/sheet.create.evidence_workbook/run \
  -H 'Content-Type: application/json' \
  -d '{
    "evidence_path": ".okoffice-out/vendor.evidence.json",
    "output_path": ".okoffice-out/vendor-evidence.xlsx",
    "style_pack": "evidence_workbook_clean"
  }'
```

## Create Deck

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.workflow.sheet_to_deck/run \
  -H 'Content-Type: application/json' \
  -d '{
    "workbook_path": ".okoffice-out/vendor-evidence.xlsx",
    "output_path": ".okoffice-out/vendor-board-deck.pptx",
    "title": "Vendor Board Review"
  }'
```

## Validate Deck

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/deck.validate.presentation/run \
  -H 'Content-Type: application/json' \
  -d '{
    "path": ".okoffice-out/vendor-board-deck.pptx"
  }'
```

## Create Board Pack

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.workflow.board_pack/run \
  -H 'Content-Type: application/json' \
  -d '{
    "files": [
      ".okoffice-out/vendor-evidence.xlsx",
      ".okoffice-out/vendor-board-deck.pptx"
    ],
    "output_path": ".okoffice-out/vendor-board-pack.zip",
    "title": "Vendor Board Review"
  }'
```

## Verify Bundle

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/office.bundle.verify/run \
  -H 'Content-Type: application/json' \
  -d '{
    "bundle_path": ".okoffice-out/vendor-board-pack.zip"
  }'
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
      "hash_mismatch_count": 0
    }
  }
}
```
