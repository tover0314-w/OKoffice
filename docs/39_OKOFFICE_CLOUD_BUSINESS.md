# 39 - okoffice Cloud Business

## Boundary

The OSS core is local-first. It must not require hosted billing for deterministic local tools.

Cloud okoffice monetizes:

- heavy workers;
- managed connectors;
- batch scale;
- persistence;
- collaboration;
- enterprise governance;
- high-quality AI workflows.

## Free OSS

Always free locally:

- CLI, MCP, REST, SDK.
- Deterministic inspect/extract/validate basics.
- PDF compatibility tools.
- DOCX/XLSX/PPTX package inspection.
- Office IR and Source Graph schemas.
- Local artifact manifests.
- Local bundle export/verify.
- Local examples.
- Local style/template packs.

## Hosted Free Tier

Possible hosted free tier:

- small monthly credit grant;
- small file limits;
- low concurrency;
- short artifact retention;
- limited managed worker trials;
- limited connector runs;
- community support.

## Paid Wedges

### Managed Workers

- Office render/convert.
- OCR.
- Agentic parse.
- Formula recalculation.
- Chart/table understanding.
- Visual comparison.
- Contact-sheet rendering.

### Managed Intelligence

- schema extraction from large document sets;
- cited report generation;
- evidence workbook generation;
- deck generation;
- claim/citation verification;
- model review;
- contract risk review;
- redaction review.

### Persistence

- source graphs;
- artifact graphs;
- source maps;
- evidence indexes;
- bundle history;
- validation history.

### Scale

- batch workflows;
- queues;
- retries;
- high concurrency;
- large files;
- scheduled jobs;
- webhooks.

### Enterprise

- SSO/SAML;
- org/team management;
- audit logs;
- retention policies;
- zero data retention mode;
- VPC/on-prem;
- managed connectors;
- DLP/security controls;
- brand kits and templates.

## Billing Events

Suggested events:

```text
worker.office_render.completed
worker.ocr.page_processed
worker.agentic_parse.page_processed
worker.formula_recalc.workbook_processed
ai.tokens.consumed
source_graph.node_created
source_graph.gb_day
artifact.gb_day
workflow.step_completed
workflow.batch_completed
connector.file_ingested
bundle.verified
deck.generated
workbook.generated
report.generated
citation.verified
```

## Packaging

Sell outcomes, not individual low-level operations:

- Source-to-workbook API.
- Workbook-to-deck API.
- Board-pack API.
- Contract portfolio API.
- Financial review API.
- Evidence and citation API.
- Enterprise batch workflow API.

Do not monetize basic local merge/split/inspect/validate. Those are trust builders.

## Cloud Product Shape

Hosted okoffice should feel like infrastructure:

- API keys.
- Usage dashboard.
- Job queue.
- Artifact browser.
- Source graph explorer.
- Validation history.
- Team settings.
- Connector management.
- Worker capability matrix.
- Webhooks.

The cloud product should not fork the local product contract. It should run the same tool names with extra scale, persistence, and workers.
