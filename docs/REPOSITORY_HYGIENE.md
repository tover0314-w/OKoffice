# Repository Hygiene

This repository should stay clean enough for agents, contributors, and enterprises to trust the default checkout.

## Commit These

- Source code under `src/`, `packages/`, `scripts/`, and related tests.
- Public schemas, manifests, OpenAPI specs, and error-code catalogs.
- Small generated fixtures under `tests/fixtures/` when they are generated or license-safe.
- Small example assets with clear provenance and a regeneration path.
- Documentation, community files, GitHub templates, and release notes.
- Lockfiles that make local development reproducible, such as `package-lock.json`.

## Do Not Commit These

- Local output directories: `.okoffice-out/`, `.agentpdf-out/`, `/outputs/`, `/artifacts/`, `/artifact-bundles/`, `renders/`.
- Dependency directories: `node_modules/`, `.venv/`, `venv/`, `env/`.
- Build products: `dist/`, `build/`, `packages/*/dist/`, `*.tsbuildinfo`.
- Caches and reports: `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage`, `htmlcov/`, `.cache/`.
- Secrets and credentials: `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`.
- Personal agent/editor configs: `.mcp.json`, `.claude/`, `.cursor/`, `codex.local.toml`.
- Temporary data: `*.log`, `*.tmp`, `*.sqlite`, `*.db`, archives, ad hoc generated Office/PDF artifacts, benchmark dumps.

## Generated Artifacts

Generated Office/PDF artifacts should usually live under `.okoffice-out/` or the compatibility `.agentpdf-out/` directory and remain untracked.

Commit a generated artifact only when all of these are true:

- It is small enough to review and download comfortably.
- It is generated locally from committed source files or command examples.
- It is license-safe and contains no private data.
- It exists as a fixture, golden artifact, smoke-test baseline, or documentation example.
- The containing directory includes a README with the regeneration command.

`examples/generated/hello.pdf` is the current compatibility baseline example for this exception.

## Before Pushing

```bash
git status --short
python scripts/doctor.py
pytest -q
npm --workspace @okpdf/agentpdf-node test
ruff check src tests scripts
```

Review `git status --short` carefully. If a file is in a local output directory or contains machine-specific paths, do not push it.

## Dependency Review

New dependencies must be reviewed against [community/DEPENDENCY_POLICY.md](../community/DEPENDENCY_POLICY.md). Default core dependencies should avoid GPL/AGPL. Optional workers may use heavier or more restrictive dependencies only behind explicit feature flags and documentation.
