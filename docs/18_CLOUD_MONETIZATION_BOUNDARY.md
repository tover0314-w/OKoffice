# 18 - Cloud and Monetization Boundary

## Business Model Intent

The open-source project should attract users, agents, developers, and enterprises before the hosted product exists. Hosted okoffice can monetize advanced resource-consuming features, operational convenience, scale, persistence, managed connectors, and enterprise controls.

The intended shape is agent-infra SaaS:

- Local core is free, useful, and trustworthy.
- Hosted service adds API keys, quotas, persistence, concurrency, managed workers, advanced AI, artifact graphs, and governance.
- The OSS core never depends on hosted billing for local deterministic operations.

## Always-Free Open-Source Tools

Local deterministic tools should remain free:

- PDF inspect, merge, split, rotate, reorder, extract, metadata, render, validation, and basic creation.
- DOCX package inspect, text/table/comment/style extraction, metadata checks, and validation.
- XLSX package inspect, sheet/table/formula/chart/named-range extraction, external-link detection, and validation.
- PPTX package inspect, slide/shape/notes/media/theme extraction, and validation.
- Source Graph and Office IR schemas.
- Local artifact manifests and bundle verification.
- Local style packs and template packs.
- Local patch manifests where deterministic.
- Local evidence/RAG demo where no paid model is required.
- CLI, MCP, REST, Docker, and SDK integration.

## Cloud/Free Quota Concept

A hosted free plan may include:

- Monthly basic credits.
- Small file limits.
- Low concurrency.
- Short artifact retention.
- Trial AI credits.
- Trial OCR/image/video credits.
- Temporary hosted source graphs.
- Limited managed connector usage.
- Community support.

## Paid Dimensions

Classic document processing:

- Advanced OCR pages.
- Agentic parse pages.
- Hosted RAG/evidence storage.
- Batch processing.
- Large files.
- High concurrency.
- Long artifact retention.
- High-fidelity Office conversion/render workers.
- Formula recalculation and workbook QA at scale.

Agent-native Office processing:

- Word/PDF source extraction at scale.
- Excel model generation and validation.
- Taste-driven PowerPoint deck generation with HTML preview, contact-sheet QA, and editable PPTX export.
- Board-pack and audit-bundle workflows.
- Managed source maps and artifact graphs.
- Citation/source coverage verification.
- Patch previews and verification.
- Brand kits, template galleries, and enterprise style packs.

Multimodal processing:

- Video transcription minutes.
- Video keyframe extraction.
- Audio transcription minutes.
- Image understanding/OCR regions.
- Chart/table/formula understanding.
- Web capture at scale.

Team and enterprise:

- Webhooks.
- Team/org management.
- Audit logs.
- Usage analytics.
- SSO/SAML.
- Zero data retention.
- Private deployment/VPC/on-prem.
- Connector governance.
- Retention/legal hold policies.

## Suggested Credit Model

```text
basic deterministic operation: 0-1 credit/document
OCR: 1-3 credits/page
agentic parse: 3-10 credits/page
Office high-fidelity render/convert: pages/slides/sheets + complexity
Deck HTML preview/export: slides + visual QA complexity
formula recalculation/QA: workbook size + formula count
image understanding: 1-5 credits/image or detected region
video transcription: credits/minute
video keyframes: credits/minute or frame batch
audio transcription: credits/minute
AI generation/edit/translation: model tokens + platform margin
composition planning: source count + model tokens + platform margin
deck/report generation: slides/pages + model/render/HTML preview/export/validation checks
patch verification: changed objects + validation checks
RAG/evidence ingest: source nodes + embedding tokens
RAG/evidence query: retrieval + model tokens
context/source graph storage: context items + source nodes + GB-day
artifact storage: GB-day
batch workflow: step credits + concurrency multiplier
```

## BYOK

Support Bring Your Own Key for model providers.

In BYOK mode:

- User pays model provider directly.
- Hosted okoffice may charge only platform/processing credits.
- Local OSS mode uses no hosted billing at all.

## OSS Rule

The open-source package must not depend on hosted billing for local deterministic operations.

Cloud features must be additive. If a capability requires cloud or a proprietary worker, expose it as a separate `cloud_only` or optional-worker tool rather than hiding it behind the same deterministic command.

## Commercial Wedge

Do not try to monetize basic local PDF/Word/Excel/PowerPoint operations. They are adoption and trust builders.

The stronger paid wedges are:

- Hosted agentic parse with evidence output.
- Managed Office conversion/render workers.
- Source-backed report, workbook, and presentation generation.
- Batch workflow orchestration.
- Persistent source graphs and artifact graphs.
- Citation/source coverage verification.
- Managed connectors and enterprise governance.
- Private deployment controls.
