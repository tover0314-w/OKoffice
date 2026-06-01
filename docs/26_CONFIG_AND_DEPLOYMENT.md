# 26 — Configuration and Deployment

## Configuration file

Recommended config path:

```text
.agentpdf.yaml
```

Example:

```yaml
safe_root: .
artifact_dir: .agentpdf/artifacts
log_level: info
allow_url_fetch: false
allow_cloud: false
model_provider: none
max_file_size_mb: 200
max_pages: 2000
render:
  default_dpi: 144
security:
  reject_embedded_javascript: true
  reject_external_actions: false
```

## Environment variables

```text
AGENTPDF_SAFE_ROOT
AGENTPDF_ARTIFACT_DIR
AGENTPDF_LOG_LEVEL
AGENTPDF_ALLOW_URL_FETCH
AGENTPDF_ALLOW_CLOUD
AGENTPDF_MODEL_PROVIDER
AGENTPDF_OPENAI_API_KEY
AGENTPDF_ANTHROPIC_API_KEY
AGENTPDF_MAX_FILE_SIZE_MB
```

## Local API

```bash
okpdf serve --api
```

## Local MCP

```bash
okpdf serve --mcp --safe-root .
```

## Docker target

```bash
docker run --rm -p 7331:7331 -v "$PWD:/workspace" agentpdf/agentpdf:latest serve --api --safe-root /workspace
```

## Self-hosting notes

- Default no network fetch.
- Default no cloud model calls.
- Mount only required directories.
- Configure artifact retention.
- Use separate workers for risky OCR/conversion tasks.

## Future hosted deployment

Hosted service should add:

- Queue.
- Worker pool.
- Object storage.
- Usage metering.
- API keys.
- Webhooks.
- Audit logs.
