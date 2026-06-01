# EPIC-002 — Tool Registry

## Goal

Implement agent-readable tool discovery.

## Requirements

- Load full manifest.
- Mark tools by status.
- Map implemented tools to callables.
- Return `tool_not_implemented` for planned tools.
- CLI: `agentpdf tools list` and `agentpdf tools show`.

## Acceptance criteria

- Full catalog visible.
- Stable tools callable.
- Planned tools not falsely advertised as implemented.
