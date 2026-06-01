# AGENTS.md — Codex Development Instructions

This repository is a development harness for building the open-source edition of **AgentPDF Infra**.

## Mission

Build a polished, open-source, agent-native PDF infrastructure project that provides a complete tool surface for PDF operations and AI document workflows.

The open-source project must be high-quality enough to attract developers, agents, and enterprises before the hosted cloud product exists.

## Non-negotiable principles

1. **Full tool map from day one**: even if some tools are planned, namespaces and docs must be complete.
2. **Agent-first outputs**: tools return structured JSON, artifacts, validation reports, page numbers, bboxes, warnings, and next recommended actions.
3. **Local-first open source**: local CLI, MCP server, REST server, and Docker must work without paid cloud.
4. **Cloud boundary is explicit**: do not implement billing or proprietary hosted logic in the OSS core.
5. **License-safe core**: avoid GPL/AGPL dependencies in default core. Optional workers may use them only behind explicit feature flags and documentation.
6. **Beautiful by default**: README, examples, errors, CLI output, and generated reports must be polished.
7. **PDF safety matters**: support sandboxing guidance, file limits, redaction verification, metadata removal, and dependency review.
8. **Every generated PDF must be validated**: page count, renderability, blank page detection, output manifest, and optional visual diff.

## Recommended implementation order

Follow `codex/backlog/V0_IMPLEMENTATION_ORDER.md`.

1. Bootstrap repo structure.
2. Implement schemas and tool registry.
3. Implement artifact/job/validation models.
4. Implement CLI skeleton.
5. Implement deterministic PDF core operations.
6. Implement MCP server exposing stable tools.
7. Implement local REST server.
8. Implement render/inspect/extract.
9. Implement markdown/html-to-PDF creation path.
10. Implement lite parse and local RAG demo.
11. Add docs site polish and examples.

## Target repository structure

```text
agentpdf/
  src/agentpdf/
    __init__.py
    api/
    artifacts/
    cli/
    config/
    core/
    ir/
    mcp/
    rag/
    schemas/
    security/
    tools/
    validation/
    workers/
  tests/
    fixtures/
    golden/
    unit/
    integration/
  docs/
  examples/
  scripts/
  pyproject.toml
  README.md
```

## Commands Codex should make work

```bash
python -m agentpdf.cli --help
agentpdf inspect tests/fixtures/simple.pdf
agentpdf merge a.pdf b.pdf -o merged.pdf
agentpdf split report.pdf --pages 1-3 -o out.pdf
agentpdf render report.pdf --pages 1 --format png --out-dir ./renders
agentpdf serve --api
agentpdf serve --mcp
pytest -q
```

## Coding standards

- Use typed Python.
- Use Pydantic models for public input/output.
- Prefer pure functions for PDF operations.
- Never silently mutate input files.
- Always write to a new output artifact.
- Use stable error codes from `schemas/error-codes.yaml`.
- Make all filesystem paths explicit and safe.
- Reject path traversal and suspicious file names.
- Put expensive/AI/cloud operations behind feature flags.

## Output contract for every tool

Every tool should return:

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "pdf.organize.merge",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

## What not to do

- Do not hard-code hosted service URLs.
- Do not include proprietary API keys.
- Do not make GPL/AGPL libraries part of default install.
- Do not implement unsafe unlock/decryption for unauthorized PDFs.
- Do not claim perfect layout-preserving body text edits.
- Do not return only `success: true`; always include evidence and validation.

## Documentation quality bar

Every public feature needs:

- CLI example.
- MCP example.
- REST example.
- Expected output example.
- Error example.
- Limitations.
- License/dependency note when relevant.
