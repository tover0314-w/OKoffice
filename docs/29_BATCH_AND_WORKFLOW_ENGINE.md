# 29 - Batch and Workflow Engine

## Open-Source Baseline

Batch can start as a CLI loop:

```bash
okoffice batch run workflow.yaml --input-dir ./sources --out-dir ./out
```

Compatibility commands remain available while the CLI migrates:

```bash
okpdf workflow plan --goal "Inspect this PDF and cite answers" --input-path report.pdf --json
```

The implemented `pdf.workflow.plan` tool returns a `ToolResult` with a workflow plan id, agent roles, ordered tool steps, expected JSON outputs, and an explicit cloud boundary.

The target okoffice workflow planner should also describe:

- Source Graph inputs.
- Artifact profiles.
- Office IR outputs.
- Patch transactions.
- Evidence coverage checks.
- Format-specific validation.
- Bundle manifests.
- Artifact graph updates.

## Current Local Execution

Agents can execute a concrete local workflow manifest:

```bash
okoffice workflow run examples/workflows/board-pack.yaml --json
```

Compatibility `pdf.workflow.run` executes supported local PDF-domain tools in order and returns per-step job ids, statuses, artifact ids, warnings, and next recommended tools. Target `office.workflow.run` should do the same across Word, Excel, PowerPoint, PDF, and bundles.

Runtime placeholders can be supplied through `bindings`; artifact placeholders can be generated under `artifact_dir`.

```bash
okoffice workflow run plan-result.json \
  --artifact-dir .okoffice-out/workflows/board-pack \
  --binding "<reviewer>=Finance Committee" \
  --json
```

Unresolved semantic placeholders are rejected before execution unless dry-run is used.

## Workflow Report

Workflow runs can be summarized into a structured report and optional Markdown artifact:

```bash
okoffice workflow report run-result.json -o .okoffice-out/workflows/board-pack-report.md --json
```

Target:

```bash
okoffice workflow report run-result.json -o .okoffice-out/workflow-report.md --json
```

Reports should include run status, step counts, failed step ids, tool list, warning rollup, artifact count, validation summaries, and bundle/source-map links.

## Workflow YAML Concepts

### PDF Compatibility Workflow

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

### Office Docset to Evidence Workbook

```yaml
name: vendor-contracts-to-evidence-workbook
inputs:
  sources:
    - ./contracts/*.docx
    - ./invoices/*.pdf
steps:
  - tool: office.context.build_packet
  - tool: office.ai.extract.schema
    with:
      fields:
        - vendor
        - renewal_date
        - annual_amount
  - tool: sheet.write.workbook
  - tool: sheet.validation.formulas
  - tool: office.evidence.coverage
outputs:
  workbook: ./out/vendor-evidence.xlsx
  source_map: ./out/vendor-evidence.source-map.json
```

### Evidence Workbook to Board Deck

```yaml
name: evidence-workbook-to-board-deck
inputs:
  workbook: ./out/vendor-evidence.xlsx
steps:
  - tool: sheet.inspect.workbook
  - tool: sheet.extract.tables
  - tool: deck.compose.plan
  - tool: deck.create.presentation
  - tool: deck.validation.presentation
  - tool: deck.validation.contact_sheet
outputs:
  deck: ./out/vendor-board-deck.pptx
  contact_sheet: ./out/vendor-board-deck.contact-sheet.png
```

### Board Pack Bundle

```yaml
name: board-pack
inputs:
  sources:
    - ./contracts/*.docx
    - ./invoices/*.pdf
steps:
  - tool: office.workflow.docset_to_sheet
  - tool: office.workflow.sheet_to_deck
  - tool: word.create.document
  - tool: pdf.convert.from_office_bundle
    when: optional_worker_available
  - tool: office.bundle.export
  - tool: office.bundle.verify
outputs:
  workbook: ./out/evidence.xlsx
  deck: ./out/board-deck.pptx
  memo: ./out/executive-memo.docx
  handout: ./out/board-handout.pdf
  bundle: ./out/board-pack.okoffice.zip
```

## Current Limitations

- No parallel execution yet.
- Variable substitution is limited.
- Cloud-only/model tools are rejected by the local runner.
- Office workflows are target specs until the corresponding tools are implemented.
- Context packets, Office IR, source graph, artifact graph, and bundle manifests may start schema-first.

## Future Cloud Workflow Features

- Queue.
- Retry.
- Webhooks.
- Batch reports.
- Parallelism.
- Scheduled jobs.
- Team usage accounting.
- Hosted source graph persistence.
- Hosted artifact graph persistence.
- Long-running video/image/audio workers.
- Evidence and citation verification workers.
- Enterprise audit logs and retention policies.

## Agent Integration

Agents should be able to ask for a workflow plan before executing it:

```text
office.workflow.plan -> office.workflow.run -> office.workflow.report
```

Compatibility:

```text
pdf.workflow.plan -> pdf.workflow.run -> pdf.workflow.report
```

Longer-term workflow runs should expose a complete audit trail:

- Input context packet.
- Target artifact profile.
- Input source graph.
- Step results.
- Output artifacts.
- Source maps.
- Patch manifests.
- Validation reports.
- Bundle manifest.
- Warnings and unresolved risks.
