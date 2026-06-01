# 02 — Open-source Scope

## Open-source edition goals

The open-source edition should be genuinely useful without cloud services.

It should include:

- CLI.
- MCP server.
- Local REST API.
- Python SDK foundation.
- Docker/self-hosting path.
- Tool registry.
- Deterministic PDF operations.
- Lite parse.
- Local RAG demo.
- Document IR.
- Validation outputs.
- Example integrations.
- Complete documentation.

## Open-source deterministic tools

These should be implemented first and remain free/local:

- Inspect PDF.
- Read/update metadata.
- Merge.
- Split.
- Extract pages.
- Remove pages.
- Reorder pages.
- Rotate pages.
- Render pages to images.
- Convert images to PDF.
- Convert PDF to images.
- Basic text extraction.
- Watermark/stamp.
- Page numbers.
- Crop/resize where reliable.
- Basic compression.
- Basic repair.
- Password protect.
- Authorized decrypt/unlock.
- Remove metadata.
- Markdown/HTML to PDF.
- Output validation.

## Open-source AI-lite tools

These should work locally without paid models:

- Lite parse using text layer and simple layout heuristics.
- Chunking.
- Keyword/embedding-optional retrieval.
- RAG demo returning page citations.
- Template-based PDF creation.
- Rule-based sensitive data detection baseline.

## Future hosted or advanced features

These may be cloud-only or paid:

- Agentic parse.
- VLM OCR.
- Advanced table/chart/formula parsing.
- AI translation.
- AI PDF creation from prompt.
- AI PDF editing/regeneration.
- Hosted vector indexes.
- Batch processing at scale.
- Persistent artifacts.
- Audit logs.
- Team management.
- SSO/SAML.
- Zero data retention.
- Enterprise VPC/on-prem.

## Boundary rule

Open-source code may include interfaces and stubs for cloud features, but it must never require the hosted cloud service for deterministic local tools.

## Feature status labels

Every tool and doc page should label features as:

- `stable`
- `beta`
- `experimental`
- `planned`
- `cloud_only`

## Default license stance

Use Apache-2.0 for the core project unless maintainers decide otherwise. Avoid copyleft dependencies in default install.
