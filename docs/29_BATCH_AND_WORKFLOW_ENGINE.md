# 29 — Batch and Workflow Engine

## Open-source baseline

Batch can start as a CLI loop:

```bash
agentpdf batch run workflow.yaml --input-dir ./pdfs --out-dir ./out
```

Agents can already ask for a local-first workflow plan:

```bash
okpdf workflow plan --goal "Chat with this PDF and cite answers" --input-path report.pdf --json
```

The implemented `pdf.workflow.plan` tool returns a `ToolResult` with a workflow plan id, agent roles, ordered tool steps, expected JSON outputs, and an explicit cloud boundary.

Agents can also execute a concrete local workflow manifest:

```bash
okpdf workflow run examples/workflows/local-rag.json --json
```

The implemented `pdf.workflow.run` tool executes supported local tools in order and returns per-step job ids, statuses, artifact ids, warnings, and next recommended tools. It accepts either a workflow manifest or the full JSON returned by `pdf.workflow.plan`.

Runtime placeholders can be supplied through `bindings`; artifact placeholders such as `<output.index.json>` can be generated under `artifact_dir`.

```bash
okpdf workflow run plan-result.json \
  --artifact-dir .agentpdf-out/workflows/chat \
  --binding "<question>=What does this PDF say?" \
  --binding "<answer>=This PDF is locally indexed." \
  --json
```

Unresolved semantic placeholders such as `<question>` are rejected before execution unless `--dry-run` is used.

Workflow runs can be summarized into a structured report and optional Markdown artifact:

```bash
okpdf workflow report run-result.json -o .agentpdf-out/workflows/chat-report.md --json
```

`pdf.workflow.report` returns run status, step counts, failed step ids, tool list, warning rollup, artifact count, and Markdown suitable for issue comments, agent handoffs, or CI logs.

Example output shape:

```json
{
  "tool": "pdf.workflow.run",
  "status": "succeeded",
  "usage": {
    "workflow_run": {
      "run_id": "wfrun_...",
      "planned_steps": 4,
      "executed_steps": 4,
      "failed_steps": 0,
      "step_results": []
    }
  }
}
```

Current limitations:

- No parallel execution yet.
- No variable substitution yet; concrete paths must be supplied before execution.
- Cloud-only/model tools are rejected by the local runner.

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

`pdf.workflow.plan`, `pdf.workflow.run`, and `pdf.workflow.report` are implemented locally. Future orchestration work should add retries, parallel execution, richer variable binding, and batch persistence.
