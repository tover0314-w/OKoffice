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

Future workflow plans should also be able to describe context packet inputs, target PDF profiles, source graph evidence, composition IR outputs, patch transactions, evidence coverage checks, and artifact graph updates. This keeps the workflow layer useful for agent-native document assembly, not only single-PDF tool chaining.

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
- Context packets, target PDF profiles, source graph, artifact graph, composition IR, and patch manifests are product-direction concepts; first local implementations may be schema-only or example-driven.

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

## Agent-native workflow concept

```yaml
name: context-to-board-deck
inputs:
  context:
    - ./meeting-transcript.md
    - ./metrics.csv
    - ./screenshots/
steps:
  - tool: pdf.context.packet
  - tool: pdf.target.select_profile
  - tool: pdf.compose.plan
  - tool: pdf.compose.render_ir
  - tool: pdf.evidence.coverage_report
  - tool: pdf.validation.render_check
outputs:
  pdf: ./out/board-deck.pdf
  source_map: ./out/board-deck.source-map.json
  report: ./out/board-deck.validation.json
```

Patch workflow concept:

```yaml
name: insert-code-appendix
inputs:
  pdf: ./architecture-review.pdf
  code: ./src/
steps:
  - tool: pdf.inspect.document
  - tool: pdf.context.code_snapshot
  - tool: pdf.target.select_profile
  - tool: pdf.patch.plan
  - tool: pdf.patch.preview
  - tool: pdf.patch.apply
  - tool: pdf.patch.verify
  - tool: pdf.validation.visual_diff
outputs:
  pdf: ./out/architecture-review-with-appendix.pdf
  patch_manifest: ./out/patch.json
  diff_report: ./out/diff.json
```

## Future cloud workflow features

- Queue.
- Retry.
- Webhooks.
- Batch reports.
- Parallelism.
- Scheduled jobs.
- Team usage accounting.
- Hosted context packet and source graph persistence.
- Hosted artifact graph persistence.
- Long-running video/image/audio workers.
- Evidence and citation verification workers.
- Enterprise audit logs and retention policies.

## Agent integration

Agents should be able to ask for a workflow plan before executing it:

```text
pdf.workflow.plan -> pdf.workflow.run -> pdf.workflow.report
```

`pdf.workflow.plan`, `pdf.workflow.run`, and `pdf.workflow.report` are implemented locally. Future orchestration work should add retries, parallel execution, richer variable binding, and batch persistence.

Longer-term workflow runs should expose a complete audit trail:

- Input context packet.
- Target PDF profile.
- Input source graph.
- Step results.
- Output artifacts.
- Source maps.
- Patch manifests.
- Validation reports.
- Warnings and unresolved risks.
