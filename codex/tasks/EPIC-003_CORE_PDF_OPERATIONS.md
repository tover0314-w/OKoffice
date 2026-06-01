# EPIC-003 — Core PDF Operations

## Goal

Implement first deterministic PDF tools.

## Tools

- inspect.
- merge.
- split.
- extract pages.
- remove pages.
- rotate pages.
- metadata read/update.

## Acceptance criteria

- Tests with fixture PDFs.
- Outputs include artifacts and validation.
- Input files are not mutated.
- Invalid page ranges produce stable errors.
