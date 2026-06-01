# 30 — Product and Pricing Notes

This is not part of the OSS implementation, but the architecture should support it.

## Free forever

- Local deterministic tools.
- Local CLI/MCP/API.
- Lite parse.
- Local RAG demo.
- Community docs and examples.

## Free hosted quota

- Monthly basic credits.
- Trial AI credits.
- Low concurrency.
- Temporary artifacts.

## Paid hosted features

- Model-token-consuming AI tools.
- Advanced OCR.
- Agentic parse.
- Hosted RAG indexes.
- Batch processing.
- Persistent artifacts.
- Higher concurrency.
- Team/org controls.
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

- `basic_operation_completed`
- `ocr_page_processed`
- `agentic_parse_page_processed`
- `ai_tokens_consumed`
- `rag_index_created`
- `rag_query_completed`
- `artifact_stored`
- `batch_job_completed`
