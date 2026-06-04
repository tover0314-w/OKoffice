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

## Example: Target Cross-Format Workflow

```http
POST /v1/tools/office.workflow.docset_to_sheet/run
```

Input:

```json
{
  "sources": [
    {"kind": "local_path", "path": "sources/vendor-a.docx"},
    {"kind": "local_path", "path": "sources/vendor-b.pdf"}
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
- Source map artifact.
- Extraction validation report.
- Warnings for missing/low-confidence fields.
- Next recommended tools such as `sheet.validation.formulas` or `office.workflow.sheet_to_deck`.

## Example: Implemented Board Pack Verification

```http
POST /v1/tools/office.bundle.verify/run
```

Input:

```json
{
  "bundle_path": ".okoffice-out/vendor-board-pack.zip"
}
```

Output highlights:

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
  },
  "next_recommended_tools": [
    "office.artifacts.source_map",
    "office.context.build_packet",
    "office.workflow.extract_to_sheet"
  ]
}
```

If a member is tampered with, the HTTP request still returns a `ToolResult` with `status: succeeded` and `validation.status: failed`, so callers can inspect exact mismatch evidence. Unreadable or non-ZIP inputs return `status: failed` with `error.code: unsupported_file_type`.

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
