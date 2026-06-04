# 00 - Start Here for Codex

This repository is now directed toward **okoffice**: local-first, agent-native Office infrastructure for Word, Excel, PowerPoint, PDF, bundles, and cross-document workflows.

Read these files first, in order:

1. `README.md`
2. `AGENTS.md`
3. `docs/37_OKOFFICE_PRODUCT_STRATEGY.md`
4. `docs/38_OKOFFICE_TOOL_TAXONOMY.md`
5. `docs/40_OKOFFICE_AGENT_INFRA.md`
6. `docs/41_OKOFFICE_IMPLEMENTATION_PLAN.md`
7. `docs/42_LEGACY_PDF_COMPATIBILITY.md`
8. `docs/36_OKOFFICE_AGENT_NATIVE_OFFICE_INFRA_PRD.md`
9. `docs/03_ARCHITECTURE.md`
10. `docs/11_DOCUMENT_IR_SPEC.md`
11. `codex/backlog/V0_IMPLEMENTATION_ORDER.md`

## Primary Objective

Build okoffice as the open-source tool layer agents use to inspect, extract, create, edit, validate, cite, and bundle Office artifacts.

The current runnable implementation is the PDF compatibility domain. Treat it as existing infrastructure to preserve, not as the future product boundary.

## What To Build Next

Prioritize:

- okoffice naming and namespace scaffolding.
- Office IR and Source Graph schemas.
- native locators for Word, Excel, PowerPoint, and PDF.
- deterministic `.docx`, `.xlsx`, and `.pptx` inspect tools.
- format-specific validation tools.
- `docset_to_sheet`, `sheet_to_deck`, and `board_pack` workflows.
- agent setup and manifest surfaces for multiple coding agents.

Do not spend the next phase adding unrelated PDF-only utility breadth unless it supports okoffice workflows, safety, validation, or compatibility.

## Product Shape

The first public okoffice release should make this workflow unmistakable:

```text
understand sources -> extract evidence -> model data -> compose artifact -> verify -> export bundle
```

## Acceptance Bar

The repository should look polished enough that a developer can star it, run the local compatibility tools, and clearly see the path to a complete agent-native Office workflow system.

Each new public capability needs:

- CLI example.
- MCP example.
- REST example.
- expected ToolResult output.
- error example.
- limitations.
- validation expectations.
- license/dependency notes where relevant.
