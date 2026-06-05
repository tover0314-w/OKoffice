# AGENTS.md - Codex Development Instructions

This repository is the open-source core for **okoffice**: agent-native Office infrastructure for Word, Excel, PowerPoint, PDF, bundles, and cross-document workflows.

## Mission

Build a polished, local-first, open-source Office infrastructure project that gives agents a trustworthy tool surface for reading, creating, editing, converting, validating, and composing `.docx`, `.xlsx`, `.pptx`, `.pdf`, HTML, Markdown, images, and structured data.

The product should make one workflow feel native:

```text
many source documents -> evidence-backed extraction -> workbook/model -> report/deck/PDF bundle -> validation and source map
```

PDF remains first-class as a source, validation, redaction, and delivery format, but it is not the product boundary.

## Non-negotiable Principles

1. **Full tool map from day one**: even if some tools are planned, namespaces and docs must show the complete okoffice mental model.
2. **Agent-first outputs**: tools return structured JSON, artifacts, validation reports, page/slide/sheet/range refs, bboxes when available, warnings, and next recommended actions.
3. **Local-first open source**: local CLI, MCP server, REST server, Docker, and examples must work without paid cloud.
4. **Cloud boundary is explicit**: do not implement billing, proprietary hosted logic, or hidden cloud requirements in the OSS core.
5. **License-safe core**: avoid GPL/AGPL dependencies in default core. Optional workers may use them only behind explicit feature flags and documentation.
6. **Beautiful by default**: README, examples, errors, CLI output, generated reports, workbooks, decks, and document QA reports must be polished.
7. **Document safety matters**: support sandboxing guidance, file limits, macro/embedded-object warnings, redaction verification, metadata removal, and dependency review.
8. **Every generated artifact must be validated**: PDFs, Word docs, Excel workbooks, and PowerPoint decks need structural validation, render/preview evidence when available, placeholder leakage checks, artifact manifests, and optional visual diff.

## Product Vocabulary

Use these terms consistently:

- **okoffice**: the product and open-source project direction.
- **Office artifact**: any `.docx`, `.xlsx`, `.pptx`, `.pdf`, HTML package, Markdown source, image render, or artifact bundle.
- **Office IR**: shared representation for parsed documents, sheets, decks, PDFs, and generated outputs.
- **Context packet**: heterogeneous inputs plus user intent.
- **Source graph**: provenance nodes and locators for pages, paragraphs, slides, cells, ranges, images, transcripts, and files.
- **Composition IR**: planned output structure before writing a report, workbook, deck, PDF, or bundle.
- **Patch transaction**: explicit non-mutating edit plan with preview, apply, verify, and rollback metadata.

## Recommended Implementation Order

Follow `codex/backlog/V0_IMPLEMENTATION_ORDER.md`. The backlog is okoffice-first; existing PDF work is legacy compatibility infrastructure to preserve while adding Office capabilities.

1. Add `okoffice` naming and compatibility boundaries.
2. Add okoffice manifest/namespace scaffolding.
3. Add Office IR and native source locator schemas.
4. Implement deterministic `office.inspect.file`.
5. Implement DOCX/XLSX/PPTX inspect.
6. Implement Office validation baselines.
7. Extend context packets and source graphs for Office sources.
8. Implement docset-to-sheet and sheet-to-deck workflows.
9. Implement board-pack bundle workflow.
10. Add optional workers only behind feature flags.

## Target Repository Structure

The current package is still `agentpdf` for compatibility. The target shape should migrate toward:

```text
okoffice/
  src/okoffice/
    api/
    artifacts/
    cli/
    config/
    context/
    conversion/
    core/
      pdf/
      word/
      sheet/
      deck/
    evidence/
    ir/
    mcp/
    rag/
    schemas/
    security/
    tools/
    validation/
    workflows/
    workers/
  tests/
    fixtures/
      pdf/
      docx/
      xlsx/
      pptx/
    golden/
    unit/
    integration/
  docs/
  examples/
  scripts/
  pyproject.toml
  README.md
```

Do not break the existing `agentpdf` import path until a deliberate compatibility plan exists. Do not let compatibility names define new product docs.

## Commands Codex Should Eventually Make Work

Current compatibility commands should keep working but should not be the main product examples:

```bash
python -m agentpdf.cli --help
okoffice inspect tests/fixtures/simple.pdf
okoffice merge a.pdf b.pdf -o merged.pdf
pytest -q
```

Target okoffice commands:

```bash
okoffice inspect report.docx --json
okoffice inspect workbook.xlsx --json
okoffice inspect deck.pptx --json
okoffice context build --file a.docx --file b.pdf --file metrics.xlsx -o context.json --json
okoffice extract schema context.json --schema examples/schemas/deal-review.json -o extracted.xlsx --json
okoffice sheet create-model extracted.json -o model.xlsx --json
okoffice deck create --from-workbook model.xlsx --style executive -o board-review.pptx --json
okoffice bundle export --file board-review.pptx --file board-review.pdf --file model.xlsx -o board-pack.zip --json
okoffice serve --api
okoffice serve --mcp
```

## Coding Standards

- Use typed Python.
- Use Pydantic models for public input/output.
- Prefer pure functions for deterministic document operations.
- Never silently mutate input files.
- Always write to a new output artifact unless a command is explicitly a preview-only read.
- Use stable error codes from `schemas/error-codes.yaml`.
- Make all filesystem paths explicit and safe.
- Reject path traversal and suspicious file names.
- Treat macros, embedded objects, external links, protected files, and remote assets as safety-sensitive.
- Put expensive, AI, cloud, OCR, and optional Office worker operations behind feature flags.

## Output Contract For Every Tool

Every tool should return:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "office.workflow.docset_to_deck",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

The existing `pdf.*` tools keep this same contract.

## What Not To Do

- Do not hard-code hosted service URLs.
- Do not include proprietary API keys.
- Do not make GPL/AGPL libraries part of default install.
- Do not implement unsafe unlock/decryption for unauthorized PDFs or protected Office files.
- Do not execute macros or embedded code by default.
- Do not claim perfect layout-preserving arbitrary Office/PDF edits.
- Do not return only `success: true`; always include evidence and validation.
- Do not send document contents to hosted AI/model providers by default.

## Documentation Quality Bar

Every public feature needs:

- CLI example.
- MCP example.
- REST example.
- Expected output example.
- Error example.
- Limitations.
- License/dependency note when relevant.
- Validation and preview expectations for the output artifact type.
