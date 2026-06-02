# 02 - Open-source Scope

## Open-source edition goals

The open-source edition should be genuinely useful without cloud services.

It should include:

- CLI.
- MCP server.
- Local REST API.
- Python SDK foundation.
- TypeScript/Node SDK.
- Docker/self-hosting path.
- Tool registry.
- Deterministic PDF operations.
- Lite parse.
- Local RAG/evidence demo.
- Document IR.
- Composition IR schema direction.
- Context packet, target PDF profile, source graph, and artifact manifest direction.
- Patch transaction manifest direction.
- Validation outputs.
- Example integrations.
- Complete documentation.

The open-source core should make developers believe the larger agent-native PDF platform is real, even before hosted multimodal workers exist.

## Open-source deterministic tools

These should be implemented first and remain free/local:

- Inspect PDF.
- Page-level inspection.
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
- Markdown/HTML/text/JSON to PDF where deterministic.
- Output validation.

## Open-source agent-native baseline

These capabilities should exist locally as schemas, manifests, deterministic tools, examples, or lightweight implementations:

- Context packet model for PDFs, images, video, audio, links, text, Markdown, HTML, code, CSV/JSON, and manually supplied prompts/review notes.
- Target PDF profile model for learning PDFs, resumes, papers, deck-like PDFs, reports, packets, audits, worksheets, and formal documents.
- Source graph model for provenance and evidence refs derived from context packets.
- Artifact lineage model linking inputs, outputs, validations, manifests, and reports.
- Document IR for parsed PDFs.
- Composition IR for generated reports, packets, appendices, and slide-like PDFs.
- Local style packs and templates that support headings, tables, figures, code blocks, callouts, citations, appendices, and page/slide layouts.
- Patch transaction manifests for planned PDF edits.
- Workflow recipes that show inspect -> compose/operate -> verify -> report.
- Evidence reports that map claims or generated blocks back to source refs when available.

The local version may use simple heuristics and deterministic rendering. It should still expose the shape of the larger platform.

## Open-source AI-lite tools

These should work locally without paid models:

- Lite parse using text layer and simple layout heuristics.
- Chunking.
- Keyword/embedding-optional retrieval.
- Evidence search returning page citations.
- RAG demo returning page citations.
- Template-based PDF creation.
- Rule-based sensitive data detection baseline.
- Local context packet examples for image/text/Markdown/code/data/link inputs.

RAG is a support capability, not the product center. The broader local goal is evidence-backed document assembly and verification.

## Future hosted or advanced features

These may be cloud-only or paid:

- Agentic parse.
- VLM OCR.
- Advanced table/chart/formula parsing.
- Video transcription and keyframe extraction.
- Audio transcription.
- Advanced image understanding.
- Web capture at scale.
- AI translation.
- AI PDF creation from prompts, context packets, and target PDF profiles.
- AI PDF editing/regeneration.
- Hosted context packet, source graph, and artifact graph.
- Hosted vector/evidence indexes.
- Batch processing at scale.
- Persistent artifacts.
- Audit logs.
- Team management.
- SSO/SAML.
- Zero data retention.
- Enterprise VPC/on-prem.

## Boundary rule

Open-source code may include interfaces, schemas, manifests, examples, and stubs for cloud features, but it must never require the hosted cloud service for deterministic local tools.

If a local tool requires cloud, expose it as a separate `cloud_only` or optional worker tool rather than hiding it behind the same deterministic command.

## Feature status labels

Every tool and doc page should label features as:

- `stable`
- `beta`
- `experimental`
- `planned`
- `cloud_only`

## Default license stance

Use Apache-2.0 for the core project unless maintainers decide otherwise. Avoid copyleft dependencies in default install.

Optional workers must be named explicitly, documented with license notes, and gated by install extras or feature flags.
