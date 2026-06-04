# Contributing to OKoffice

Thank you for helping build OKoffice. The project is moving from a PDF-only identity toward local-first, agent-native Office infrastructure across Word, Excel, PowerPoint, PDF, and audit bundles.

The current runnable compatibility package is still `agentpdf` / `okpdf`. Preserve those paths unless a migration task explicitly changes them.

## Contribution Types

We welcome:

- Word, Excel, PowerPoint, PDF, and cross-format workflow tools.
- CLI, MCP, REST, Python, and TypeScript/Node SDK improvements.
- Schemas, manifests, source locators, and public tool contract refinements.
- Document IR, source graphs, evidence workflows, validation, and artifact bundles.
- Tests, fixtures, golden artifacts, and examples with clear provenance.
- Documentation, examples, translations, and GitHub repository polish.
- Security hardening, sandboxing guidance, dependency review, and validation improvements.
- Agent integrations for Codex, Claude Code/Desktop, Cursor, OpenClaw, Kilo Code, Vercel AI SDK, and other tool-call runtimes.

## Development Setup

```bash
git clone git@github.com:tover0314-w/OKoffice.git
cd OKoffice

python scripts/setup_dev.py
python scripts/doctor.py
pytest -q
okoffice --help
```

For the compatibility TypeScript/Node SDK:

```bash
npm install
npm --workspace @okpdf/agentpdf-node test
```

## Public Tool Expectations

Every public tool should:

- Return the standard `ToolResult` shape.
- Include artifacts, validation evidence, warnings, usage, and next recommended tools.
- Preserve native locators where relevant: paragraphs, tables, comments, cells, formulas, charts, slides, notes, pages, bboxes, and artifact refs.
- Use stable error codes from `schemas/error-codes.yaml`.
- Never silently mutate input files.
- Write new output artifacts to explicit paths.
- Reject path traversal and suspicious filenames.
- Document CLI, MCP, REST, expected output, error output, limitations, and dependency/license notes.
- Keep hosted/model/OCR/worker requirements behind explicit feature flags and docs.

## Pull Request Checklist

Before opening a PR:

- [ ] `python scripts/doctor.py` passes.
- [ ] `pytest -q` passes.
- [ ] `npm --workspace @okpdf/agentpdf-node test` passes when Node SDK behavior is touched.
- [ ] `ruff check src tests scripts` passes when Python code is touched.
- [ ] Public schema, manifest, or tool-status changes are documented.
- [ ] CLI, MCP, REST, and SDK examples are updated when public behavior changes.
- [ ] Generated Office/PDF artifacts include validation evidence where applicable.
- [ ] New dependencies are reviewed against `community/DEPENDENCY_POLICY.md`.
- [ ] No secrets, tokens, proprietary endpoints, private URLs, or machine-specific paths are included.
- [ ] README, translated README, and GitHub templates remain aligned when public positioning changes.

## Multilingual Docs

English is the canonical release language. `README.zh-CN.md` is the Simplified Chinese entry point.

When changing setup, safety, public contracts, examples, or repository hygiene, update translated README content in the same PR or clearly call out the follow-up. Translation rules live in [docs/i18n/README.md](docs/i18n/README.md).

## Repository Hygiene

Do not commit local output directories, dependency folders, caches, secrets, personal agent configs, build artifacts, logs, databases, or ad hoc generated Office/PDF artifacts.

Generated artifacts should normally live under `.okoffice-out/` or the compatibility `.agentpdf-out/` directory and remain untracked. Commit generated artifacts only when they are small, license-safe, reproducible, and documented. See [docs/REPOSITORY_HYGIENE.md](docs/REPOSITORY_HYGIENE.md).

## Security

Do not open public issues for vulnerabilities, exploit details, private documents, or document-leak examples. Follow [SECURITY.md](SECURITY.md).

Security-sensitive areas include:

- Office package parsing and relationship handling.
- PDF parsing and rendering.
- Path safety and filesystem access.
- Metadata removal and redaction verification.
- MCP/REST exposure.
- Optional workers, OCR, AI parse, formula engines, and external calls.

## Developer Certificate of Origin

This project may use DCO sign-off instead of a CLA.

Use:

```bash
git commit -s -m "your message"
```

The maintainer team can decide whether DCO enforcement is required before public launch.
