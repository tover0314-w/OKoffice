# 09 — REST API Specification

## Goal

Expose local and hosted-compatible HTTP endpoints.

## Open-source local API

Recommended FastAPI structure:

```text
GET  /healthz
GET  /v1/tools
GET  /v1/tools/{tool_name}
POST /v1/tools/{tool_name}/run
GET  /v1/jobs/{job_id}
GET  /v1/artifacts/{artifact_id}
GET  /v1/artifacts/{artifact_id}/download
```

## Tool run endpoint

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
  "warnings": []
}
```

## Hosted API compatibility

Design local API so it can later support:

- API keys.
- Rate limits.
- Credits.
- Async jobs.
- Webhooks.
- Artifact retention.
- Signed download URLs.
- Team/org IDs.

Do not require these in the open-source local server.

## OpenAPI

A draft OpenAPI spec is provided at `schemas/openapi.yaml`.

## Errors

Use a consistent error format:

```json
{
  "error": {
    "code": "invalid_page_range",
    "message": "Page range 10-20 exceeds page count 8.",
    "details": {
      "page_count": 8,
      "range": "10-20"
    },
    "retry_hint": "Call pdf.inspect.document first, then provide a valid range."
  }
}
```
