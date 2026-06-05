# 09 - okoffice REST API Specification

## Goal

Expose local and hosted-compatible HTTP endpoints for okoffice tools. The local REST server should work without cloud accounts, API keys, billing, or managed workers.

The current REST API exposes the PDF compatibility surface. The target REST API keeps the same tool-run model while adding Office domains.

## Open-Source Local API

Recommended FastAPI structure:

```text
GET  /healthz
GET  /v1/tools
GET  /v1/tools/{tool_name}
POST /v1/tools/{tool_name}/run
GET  /v1/jobs/{job_id}
GET  /v1/artifacts/{artifact_id}
GET  /v1/artifacts/{artifact_id}/download
GET  /v1/artifact-profiles
GET  /v1/style-packs
GET  /v1/format-capabilities
```

The canonical execution endpoint stays generic:

```http
POST /v1/tools/{tool_name}/run
```

This makes CLI, MCP, REST, and SDK behavior share one runner contract.

## Example: Current PDF Compatibility Tool

```http
POST /v1/tools/pdf.organize.merge/run
```

Input:

```json
{
  "files": [
    {"kind": "local_path", "path": "a.pdf"},
    {"kind": "local_path", "path": "b.pdf"}
  ],
  "output": {"path": "merged.pdf"},
  "validate": true
}
```

Output:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "pdf.organize.merge",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

## Example: Target Workbook Inspect Tool

```http
POST /v1/tools/sheet.inspect.workbook/run
```

Input:

```json
{
  "file": {"kind": "local_path", "path": "evidence.xlsx"},
  "include_formulas": true,
  "include_charts": true,
  "include_security": true
}
```

Output highlights:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "sheet.inspect.workbook",
  "artifacts": [],
  "validation": {"valid": true},
  "warnings": [],
  "usage": {
    "sheet_count": 4,
    "formula_count": 127,
    "chart_count": 2,
    "has_macros": false
  },
  "next_recommended_tools": ["sheet.validation.formulas"]
}
```

## Example: Target Formula Validation Tool

```http
POST /v1/tools/sheet.validation.formulas/run
```

Input:

```json
{
  "path": ".okoffice-out/vendor-evidence.xlsx"
}
```

Output includes `validation.status`, `usage.summary`, `usage.issues`, `usage.formula_evaluation`, warnings for structural risks, and next recommended tools.

## Example: Target Package Validation Tool

```http
POST /v1/tools/office.validation.package/run
```

Input:

```json
{
  "path": "report.docx"
}
```

Output includes package type, member counts, unsafe ZIP entry checks, `[Content_Types].xml` status, macro/external-relationship warnings, and next recommended tools. The validator does not execute macros, fetch external relationships, or mutate the input file.

## Example: Target Word Report Creation Tool

```http
POST /v1/tools/word.create.report/run
```

Input:

```json
{
  "workbook_path": ".okoffice-out/vendor-evidence.xlsx",
  "output_path": ".okoffice-out/vendor-memo.docx",
  "title": "Vendor Renewal Memo",
  "profile": "executive_memo"
}
```

Output includes a DOCX artifact, row/source-ref summaries, a report manifest, and structural validation from `word.inspect.document`.

## Example: Target Word Document Validation Tool

```http
POST /v1/tools/word.validation.document/run
```

Input:

```json
{
  "path": ".okoffice-out/vendor-memo.docx"
}
```

Output includes `tool: word.validation.document`, package validation evidence, comments/tracked-change policy checks, metadata checks, accessibility hints, and skipped render-preview evidence when no local DOCX renderer is configured.

## Example: Target Deck Creation Tool

```http
POST /v1/tools/deck.create.presentation/run
```

Input:

```json
{
  "workbook_path": ".okoffice-out/vendor-evidence.xlsx",
  "output_path": ".okoffice-out/vendor-board-deck.pptx",
  "title": "Vendor Renewal Review",
  "profile": "board_review"
}
```

Output includes a PPTX artifact, slide ids, row-level source refs, speaker notes with citations, structural validation from `deck.inspect.presentation`, and a skipped `contact_sheet_preview` check when no local render worker is configured.

## Example: Target Contact-Sheet Validation Tool

```http
POST /v1/tools/deck.validation.contact_sheet/run
```

Input:

```json
{
  "path": ".okoffice-out/vendor-board-deck.pptx"
}
```

Output includes `validation.status: skipped`, the deck inspection summary, and explicit worker-unavailable evidence when no local PPTX contact-sheet renderer is configured.

## Example: Target Presentation Validation Tool

```http
POST /v1/tools/deck.validation.presentation/run
```

Input:

```json
{
  "path": ".okoffice-out/vendor-board-deck.pptx"
}
```

Output includes `tool: deck.validation.presentation`, `usage.summary`, title and notes policy checks with Deck locators, media/theme/safety markers, `placeholder_overflow.status: structural_only`, and skipped render-evidence checks when no local renderer is configured.

## Example: Target Sheet-To-Deck Workflow

```http
POST /v1/tools/office.workflow.sheet_to_deck/run
```

Input:

```json
{
  "workbook_path": ".okoffice-out/vendor-evidence.xlsx",
  "output_path": ".okoffice-out/vendor-board-deck.pptx",
  "title": "Vendor Renewal Review",
  "profile": "board_review"
}
```

Output includes step summaries for `sheet.inspect.workbook`, `sheet.validation.formulas`, `deck.create.presentation`, `deck.inspect.presentation`, `deck.validation.presentation`, and `deck.validation.contact_sheet`, plus the generated PPTX artifact and validation report.

## Example: Target Board-Pack Workflow

```http
POST /v1/tools/office.workflow.board_pack/run
```

Input:

```json
{
  "files": [
    "contracts/vendor-a.docx",
    "invoices/vendor-a.pdf"
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
  "include_pdf_handout": true,
  "pdf_renderer_backend": "auto"
}
```

Output includes generated `evidence.xlsx`, `evidence.context.json`, `evidence.evidence.json`, `memo.docx`, `board-deck.pptx`, optional `handout.html`, optional `handout.pdf`, handout QA/manifest evidence, and `board-pack.okoffice.zip` artifacts, plus validation from each step and final bundle verification status.

## Example: Target Bundle Export Tool

```http
POST /v1/tools/office.bundle.export/run
```

Input:

```json
{
  "artifact_paths": [
    ".okoffice-out/vendor-evidence.xlsx",
    ".okoffice-out/vendor-board-deck.pptx"
  ],
  "output_path": ".okoffice-out/vendor-board-pack.okoffice.zip",
  "title": "Vendor Board Pack"
}
```

Output includes the bundle artifact, manifest metadata, included artifact paths, and checksum lines.

## Example: Target Bundle Verify Tool

```http
POST /v1/tools/office.bundle.verify/run
```

Input:

```json
{
  "bundle_path": ".okoffice-out/vendor-board-pack.okoffice.zip"
}
```

Output includes checksum verification status, missing artifacts, duplicate bundle paths, and validation checks.

## Example: Optional Worker Status Tool

```http
POST /v1/tools/office.workers.status/run
```

Input:

```json
{
  "feature_flags": {
    "libreoffice": true,
    "ocr": false
  },
  "command_paths": {
    "libreoffice": "soffice"
  }
}
```

Output includes `usage.summary`, `usage.workers`, `usage.office.worker_contracts`, validation checks for each optional worker, license notes, cloud-boundary flags, and warnings for enabled workers whose dependencies are unavailable.

## Example: Target Cross-Format Workflow

```http
POST /v1/tools/office.workflow.docset_to_sheet/run
```

Input:

```json
{
  "files": [
    "sources/vendor-a.docx",
    "sources/vendor-b.pdf"
  ],
  "schema": {
    "fields": [
      {"name": "vendor", "type": "string"},
      {"name": "renewal_date", "type": "string"},
      {"name": "annual_amount", "type": "number"}
    ]
  },
  "output_path": ".okoffice-out/vendor-evidence.xlsx",
  "evidence_required": true
}
```

Output should include:

- Workbook artifact.
- Context packet sidecar artifact.
- Evidence JSON sidecar artifact.
- Source map sheet in the workbook.
- Extraction validation report.
- Workbook formula validation report.
- Warnings for missing/low-confidence fields.
- Next recommended tools such as `sheet.validation.formulas` or `office.workflow.sheet_to_deck`.

## Hosted API Compatibility

Design the local API so it can later support:

- API keys.
- Rate limits.
- Credits.
- Async jobs.
- Webhooks.
- Artifact retention.
- Signed download URLs.
- Team/org IDs.
- Managed connectors.
- Managed Office conversion/render workers.

Do not require these in the open-source local server.

## OpenAPI

A draft OpenAPI spec is provided at:

```text
schemas/openapi.yaml
```

The okoffice migration should keep OpenAPI generated from the same public schemas used by CLI, MCP, and SDK clients.

## Errors

Use a consistent error format:

```json
{
  "error": {
    "code": "invalid_range",
    "message": "Range Summary!A1:Z999 exceeds the detected used range Summary!A1:H32.",
    "details": {
      "sheet": "Summary",
      "used_range": "A1:H32",
      "requested_range": "A1:Z999"
    },
    "retry_hint": "Call sheet.inspect.workbook first, then provide a valid range."
  }
}
```

## Local Server Rules

- Local server defaults to loopback.
- Safe root is required or inferred from the working directory.
- URL fetch, AI providers, browser rendering, OCR, formula recalculation, and Office conversion workers are opt-in.
- Uploaded/generated artifacts should be stored under an explicit artifact directory.
- Binary downloads happen through artifact endpoints, not in tool JSON.
- Tool JSON must remain agent-readable and small enough for MCP/LLM use.
