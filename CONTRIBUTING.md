# Contributing to okpdf

Thank you for contributing. okpdf aims to become the open-source PDF infrastructure layer for AI agents, local document automation, and self-hosted workflows.

## Contribution Types

We welcome:

- Core PDF tools.
- CLI, MCP, REST, and TypeScript/Node SDK improvements.
- Schemas, manifests, and tool contract refinements.
- Document parsing, Document IR, local RAG, and evidence workflow improvements.
- Tests, generated fixtures, and golden artifacts with clear provenance.
- Documentation, examples, translations, and onboarding polish.
- Security hardening, sandboxing guidance, dependency review, and validation improvements.
- Agent integrations and workflow recipes.

## Development Setup

```bash
git clone git@github.com:tover0314-w/okpdf.git
cd okpdf
python scripts/setup_dev.py
python scripts/doctor.py
pytest -q
okpdf --help
```

For the TypeScript/Node SDK:

```bash
npm install
npm --workspace @okpdf/agentpdf-node test
```

## Public Tool Expectations

Every public tool should:

- Return the standard `ToolResult` shape.
- Include artifacts, validation evidence, warnings, usage, and next recommended tools.
- Use stable error codes from `schemas/error-codes.yaml`.
- Never silently mutate input files.
- Write new output artifacts to explicit paths.
- Reject path traversal and suspicious filenames.
- Document CLI, MCP, REST, expected output, error output, limitations, and dependency/license notes.

## Pull Request Checklist

Before opening a PR:

- [ ] `python scripts/doctor.py` passes.
- [ ] `pytest -q` passes.
- [ ] `npm --workspace @okpdf/agentpdf-node test` passes when Node SDK behavior is touched.
- [ ] `ruff check src tests scripts` passes when Python code is touched.
- [ ] Public schema or manifest changes are documented.
- [ ] CLI, MCP, REST, and Node examples are updated when public behavior changes.
- [ ] Generated PDFs include validation where applicable.
- [ ] New dependencies are reviewed against `community/DEPENDENCY_POLICY.md`.
- [ ] No secrets, tokens, proprietary endpoints, private URLs, or machine-specific paths are included.
- [ ] Documentation remains polished and readable.

## Multilingual Docs

English is the canonical release language. `README.zh-CN.md` is the Simplified Chinese entry point.

When changing setup, safety, public contracts, examples, or repository hygiene, update translated README content in the same PR or clearly call out the follow-up. Translation rules live in [docs/i18n/README.md](docs/i18n/README.md).

## Repository Hygiene

Do not commit local output directories, dependency folders, caches, secrets, personal agent configs, build artifacts, logs, databases, or ad hoc generated PDFs.

Generated PDFs should normally live under `.agentpdf-out/` and remain untracked. Commit generated PDFs only when they are small, license-safe, reproducible, and documented. See [docs/REPOSITORY_HYGIENE.md](docs/REPOSITORY_HYGIENE.md).

## Security

Do not open public issues for vulnerabilities, exploit details, private documents, or document-leak examples. Follow [SECURITY.md](SECURITY.md).

Security-sensitive areas include:

- PDF parsing and rendering.
- Path safety and filesystem access.
- Metadata removal.
- Redaction and redaction verification.
- MCP/REST exposure.
- Optional workers, OCR, AI parse, and external calls.

## Developer Certificate of Origin

This project may use DCO sign-off instead of a CLA.

Use:

```bash
git commit -s -m "your message"
```

The maintainer team can decide whether DCO enforcement is required before public launch.
