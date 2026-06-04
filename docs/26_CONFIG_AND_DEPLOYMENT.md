# 26 - Configuration and Deployment

## Configuration File

Target config path:

```text
.okoffice.yaml
```

Compatibility config path:

```text
.agentpdf.yaml
```

Example:

```yaml
safe_root: .
artifact_dir: .okoffice/artifacts
log_level: info
allow_url_fetch: false
allow_cloud: false
model_provider: none
max_file_size_mb: 200
max_pages: 2000
max_slides: 500
max_sheets: 200
render:
  default_dpi: 144
  enable_browser_renderer: false
office:
  allow_macros: false
  allow_external_links: false
  inspect_hidden_content: true
  formula_evaluation: structural_only
workers:
  ocr: disabled
  office_render: disabled
  office_convert: disabled
  formula_engine: disabled
security:
  reject_embedded_javascript: true
  reject_external_actions: false
  reject_unsafe_package_entries: true
```

## Environment Variables

Target:

```text
OKOFFICE_SAFE_ROOT
OKOFFICE_ARTIFACT_DIR
OKOFFICE_LOG_LEVEL
OKOFFICE_ALLOW_URL_FETCH
OKOFFICE_ALLOW_CLOUD
OKOFFICE_MODEL_PROVIDER
OKOFFICE_OPENAI_API_KEY
OKOFFICE_ANTHROPIC_API_KEY
OKOFFICE_MAX_FILE_SIZE_MB
```

Compatibility:

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

Current:

```bash
okpdf serve --api
```

Target:

```bash
okoffice serve --api --safe-root .
```

## Local MCP

Current:

```bash
okpdf serve --mcp --safe-root .
```

Target:

```bash
okoffice serve --mcp --safe-root .
```

## Docker Target

Current image:

```bash
docker build -t okpdf/local:dev .
docker run --rm -p 7331:7331 -v "$PWD:/workspace" okpdf/local:dev
curl http://127.0.0.1:7331/healthz
```

Target image:

```bash
docker build -t okoffice/local:dev .
docker run --rm -p 7331:7331 -v "$PWD:/workspace" okoffice/local:dev
curl http://127.0.0.1:7331/healthz
```

The image should default to:

```bash
okoffice serve --api --host 0.0.0.0 --port 7331 --safe-root /workspace
```

Compose:

```bash
docker compose up --build
```

## Self-Hosting Notes

- Default no network fetch.
- Default no cloud model calls.
- Default no macro execution.
- Mount only required directories.
- Configure artifact retention.
- Use separate workers for risky OCR/conversion/render tasks.
- Keep local deterministic tools free and independent from hosted billing.
- Record worker capabilities and license notes in health/config endpoints.

## Future Hosted Deployment

Hosted service should add:

- Queue.
- Worker pool.
- Object storage.
- Usage metering.
- API keys.
- Webhooks.
- Audit logs.
- Managed connectors.
- Managed Office render/conversion workers.
- Tenant/org controls.
