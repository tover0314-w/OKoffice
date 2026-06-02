# 18 - Cloud and Monetization Boundary

## Business model intent

The open-source project should attract users, agents, developers, and enterprises. Hosted cloud services can monetize advanced resource-consuming features, operational convenience, scale, persistence, and enterprise controls.

The intended shape is similar to agent-infra SaaS products: the local core is free and useful, while the hosted service adds API keys, free quotas, paid plans, persistence, concurrency, advanced AI workers, multimodal context processing, artifact graphs, and operational convenience.

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
- Basic Markdown/HTML/text/JSON to PDF.
- Basic watermark/page numbers.
- Basic validation.
- Lite parse.
- Local RAG/evidence demo.
- Local style packs and templates.
- Local context packet, target PDF profile, source graph, and composition IR schemas.
- Local patch manifests where deterministic.

## Cloud/free quota concept

A hosted free plan may include:

- Monthly basic credits.
- Small file limits.
- Low concurrency.
- Short artifact retention.
- Trial AI credits.
- Trial OCR/image/video credits.
- Temporary hosted source graphs.
- Community support.

## Paid dimensions

Classic document processing:

- AI model tokens.
- Advanced OCR pages.
- Agentic parse pages.
- Hosted RAG/evidence storage.
- Batch processing.
- Large files.
- High concurrency.
- Long artifact retention.

Agent-native multimodal processing:

- Video transcription minutes.
- Video keyframe extraction.
- Audio transcription minutes.
- Image understanding/OCR regions.
- Chart/table/formula understanding.
- Web capture at scale.
- Context packet, target PDF profile, source graph creation, and persistence.
- Artifact graph persistence.
- Source map generation and storage.
- Composition IR planning.
- High-quality PDF/deck rendering.
- Patch previews and verification.
- Evidence coverage verification.

Team and enterprise:

- Webhooks.
- Team/org management.
- Audit logs.
- Usage analytics.
- Brand kits and enterprise templates.
- Template gallery and SEO landing pages for PDF creation workflows.
- Enterprise security.
- SSO/SAML.
- Zero data retention.
- VPC/on-prem.

## Suggested credit model

```text
basic deterministic operation: 0-1 credit/document
OCR: 1-3 credits/page
agentic parse: 3-10 credits/page
image understanding: 1-5 credits/image or detected region
video transcription: credits/minute
video keyframes: credits/minute or frame batch
audio transcription: credits/minute
AI generation/edit/translation: model tokens + platform margin
composition planning: source count + model tokens + platform margin
PDF/deck rendering: pages + complexity + validation checks
patch verification: changed pages + validation checks
RAG/evidence ingest: pages + embedding tokens
RAG/evidence query: retrieval + model tokens
context/source graph storage: context items + source nodes + GB-day
artifact storage: GB-day
batch workflow: step credits + concurrency multiplier
```

## BYOK

Support Bring Your Own Key for model providers.

In BYOK mode:

- User pays model provider directly.
- AgentPDF may charge only platform/processing credits in cloud mode.
- Local OSS mode may use no hosted billing at all.

## OSS rule

The open-source package must not depend on hosted billing for local deterministic operations.

Cloud features must be additive. If a local tool requires cloud, expose it as a separate `cloud_only` or optional worker tool rather than hiding it behind the same deterministic command.

## Commercial wedge

Do not try to monetize basic PDF operations. They are adoption and trust builders.

The stronger paid wedges are:

- Hosted agentic parse with evidence output.
- Video/image/audio/document/code/link context-to-PDF pipelines.
- Source-backed report and presentation generation.
- Batch workflow orchestration.
- Persistent context packet, source graph, and artifact graph.
- Citation/source coverage verification.
- Enterprise audit, retention, and private deployment controls.
