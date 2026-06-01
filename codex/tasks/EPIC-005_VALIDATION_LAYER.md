# EPIC-005 — Validation Layer

## Goal

Ensure every generated PDF output has a validation report.

## Checks

- File exists.
- Non-zero size.
- Page count.
- Render check when available.
- Blank page check when enabled.
- SHA-256.

## Acceptance criteria

- Validation report attached to ToolResult.
- Failing validation produces actionable error/warning.
