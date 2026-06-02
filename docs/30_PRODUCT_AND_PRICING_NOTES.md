# 30 - Product and Pricing Notes

This is not part of the OSS implementation, but the architecture should support it.

## Free forever

- Local deterministic tools.
- Local CLI/MCP/API.
- Python and TypeScript SDK access to local APIs.
- Lite parse.
- Local RAG/evidence demo.
- Local context packet, target PDF profile, source graph, and composition IR schemas.
- Local patch manifests for deterministic workflows.
- Local style packs and examples.
- Community docs and examples.

## Free hosted quota

- Monthly basic credits.
- Trial AI credits.
- Trial OCR/image/video credits.
- Low concurrency.
- Temporary artifacts.
- Temporary context packets and source graphs.
- Community support.

## Paid hosted features

- Model-token-consuming AI tools.
- Advanced OCR.
- Agentic parse.
- Video transcription and keyframes.
- Audio transcription.
- Image understanding.
- Advanced table/chart/formula understanding.
- Hosted RAG/evidence indexes.
- Hosted context packets and source graphs.
- Hosted artifact graphs.
- Context-backed target PDF composition planning.
- High-quality report/deck rendering.
- Patch preview and verification.
- Batch processing.
- Persistent artifacts.
- Higher concurrency.
- Team/org controls.
- Brand kits and enterprise templates.
- Webhooks.
- Audit logs.
- Enterprise deployment.

## Plans

### Free

For trial and community users.

### Starter

For individual agent builders.

### Pro

For teams and SaaS builders.

### Growth

For high-volume workflows.

### Enterprise

For regulated/private deployments.

## Billing events to design for

Classic document processing:

- `basic_operation_completed`
- `ocr_page_processed`
- `agentic_parse_page_processed`
- `ai_tokens_consumed`
- `rag_index_created`
- `rag_query_completed`
- `artifact_stored`
- `batch_job_completed`

Agent-native multimodal and verification:

- `context_packet_created`
- `target_profile_selected`
- `source_graph_node_created`
- `source_graph_stored`
- `video_minute_transcribed`
- `video_keyframe_extracted`
- `audio_minute_transcribed`
- `image_region_analyzed`
- `chart_or_table_understood`
- `composition_plan_created`
- `composition_ir_rendered`
- `presentation_pdf_created`
- `patch_preview_created`
- `patch_applied`
- `patch_verified`
- `evidence_coverage_checked`
- `citation_verified`
- `artifact_graph_exported`

## Packaging notes

The paid product should sell outcomes, not isolated low-level operations:

- Parse and evidence API.
- Source-to-report API.
- Source-to-deck API.
- Verified PDF edit API.
- Batch workflow API.
- Enterprise audit and retention.

Basic merge/split/convert should remain free and should function as developer adoption, not the pricing center.
