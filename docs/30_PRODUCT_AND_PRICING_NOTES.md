# 30 - Product and Pricing Notes

This is not part of the OSS implementation, but the architecture should support it.

## Free Forever

- Local deterministic PDF tools.
- Local deterministic DOCX/XLSX/PPTX inspect and validation tools.
- Local CLI/MCP/API.
- Python and TypeScript SDK access to local APIs.
- Lite parse.
- Local RAG/evidence demo.
- Local Source Graph and Office IR schemas.
- Local artifact profiles and style packs.
- Local patch manifests for deterministic workflows.
- Local bundle export/verify.
- Community docs and examples.

## Free Hosted Quota

- Monthly basic credits.
- Trial AI credits.
- Trial OCR/image/video credits.
- Low concurrency.
- Temporary artifacts.
- Temporary source graphs and artifact graphs.
- Limited managed connector runs.
- Community support.

## Paid Hosted Features

- Model-token-consuming AI tools.
- Advanced OCR.
- Agentic parse.
- Video transcription and keyframes.
- Audio transcription.
- Image understanding.
- Advanced table/chart/formula understanding.
- Managed Office render/conversion workers.
- Formula recalculation/QA at scale.
- Hosted RAG/evidence indexes.
- Hosted source graphs.
- Hosted artifact graphs.
- Source-backed Word report generation.
- Evidence-backed Excel workbook generation.
- High-quality PowerPoint deck generation with HTML preview, contact-sheet QA, and editable PPTX export.
- Board-pack bundle workflows.
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

## Billing Events to Design For

Classic document processing:

- `basic_operation_completed`
- `ocr_page_processed`
- `agentic_parse_page_processed`
- `ai_tokens_consumed`
- `rag_index_created`
- `rag_query_completed`
- `artifact_stored`
- `batch_job_completed`

Agent-native Office workflows:

- `source_graph_node_created`
- `source_graph_stored`
- `office_ir_created`
- `word_report_created`
- `excel_workbook_created`
- `excel_formula_validation_completed`
- `powerpoint_deck_created`
- `deck_html_preview_rendered`
- `deck_pptx_exported`
- `deck_contact_sheet_rendered`
- `board_pack_created`
- `bundle_exported`
- `bundle_verified`

Multimodal and verification:

- `video_minute_transcribed`
- `video_keyframe_extracted`
- `audio_minute_transcribed`
- `image_region_analyzed`
- `chart_or_table_understood`
- `composition_plan_created`
- `patch_preview_created`
- `patch_applied`
- `patch_verified`
- `evidence_coverage_checked`
- `citation_verified`
- `artifact_graph_exported`

## Packaging Notes

The paid product should sell outcomes, not isolated low-level operations:

- Parse and evidence API.
- Source-to-workbook API.
- Source-to-report API.
- Source-to-deck API.
- Board-pack API.
- Verified edit/patch API.
- Batch workflow API.
- Enterprise audit and retention.

Basic local merge/split/inspect/validate/create operations should remain free and should function as developer adoption, not the pricing center.
