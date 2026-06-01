# 29 — Batch and Workflow Engine

## Open-source baseline

Batch can start as a CLI loop:

```bash
agentpdf batch run workflow.yaml --input-dir ./pdfs --out-dir ./out
```

## Workflow YAML concept

```yaml
name: redact-and-summarize
inputs:
  folder: ./pdfs
steps:
  - tool: pdf.inspect.document
  - tool: pdf.ai.parse.lite
  - tool: pdf.ai.review.sensitive_data_detect
    when: local_or_cloud_available
  - tool: pdf.security.redact
  - tool: pdf.security.verify_redaction
  - tool: pdf.validation.validate_output
outputs:
  folder: ./out
```

## Future cloud workflow features

- Queue.
- Retry.
- Webhooks.
- Batch reports.
- Parallelism.
- Scheduled jobs.
- Team usage accounting.

## Agent integration

Agents should be able to ask for a workflow plan before executing it:

```text
pdf.workflow.plan -> pdf.workflow.run -> pdf.workflow.report
```

Workflow tools can be `planned` initially.
