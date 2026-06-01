# EPIC-008 — REST API

## Goal

Expose local FastAPI server.

## Endpoints

- `/healthz`
- `/v1/tools`
- `/v1/tools/{tool_name}`
- `/v1/tools/{tool_name}/run`
- `/v1/jobs/{job_id}`
- `/v1/artifacts/{artifact_id}`

## Acceptance criteria

- OpenAPI docs generated.
- Stable tools runnable through API.
