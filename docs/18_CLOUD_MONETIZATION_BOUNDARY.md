# 18 — Cloud and Monetization Boundary

## Business model intent

The open-source project should attract users and agents. Hosted cloud services can monetize advanced resource-consuming features.

## Always-free open-source tools

Local tools should remain free:

- Merge.
- Split.
- Rotate.
- Extract pages.
- Remove pages.
- Reorder pages.
- Inspect.
- Metadata.
- Basic text extraction.
- PDF to image.
- Image to PDF.
- Basic Markdown/HTML to PDF.
- Basic watermark/page numbers.
- Basic validation.
- Lite parse.
- Local RAG demo.

## Cloud/free quota concept

A hosted free plan may include:

- Monthly basic credits.
- Small file limits.
- Low concurrency.
- Short artifact retention.
- Trial AI credits.
- Community support.

## Paid dimensions

- AI model tokens.
- Advanced OCR pages.
- Agentic parse pages.
- Hosted RAG storage.
- Batch processing.
- Large files.
- High concurrency.
- Long artifact retention.
- Webhooks.
- Team/org management.
- Audit logs.
- Enterprise security.
- VPC/on-prem.

## Suggested credit model

```text
basic deterministic operation: 0-1 credit/document
OCR: 1-3 credits/page
agentic parse: 3-10 credits/page
AI generation/edit/translation: model tokens + platform margin
RAG ingest: pages + embedding tokens
RAG query: retrieval + model tokens
storage: GB-day
```

## BYOK

Support Bring Your Own Key for model providers.

In BYOK mode:

- User pays model provider directly.
- AgentPDF may charge only platform/processing credits in cloud mode.
- Local OSS mode may use no hosted billing at all.

## OSS rule

The open-source package must not depend on hosted billing for local deterministic operations.
