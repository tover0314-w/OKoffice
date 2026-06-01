# 15 — Testing Harness

## Test philosophy

PDF tools require more than unit tests. Use deterministic fixture PDFs, golden outputs, render checks, and artifact manifests.

## Test categories

### Unit tests

- Page range parser.
- Tool registry.
- Schema validation.
- Artifact manifest.
- Error codes.
- Style pack loading.

### Integration tests

- CLI commands.
- REST endpoints.
- MCP tools.
- Core PDF operations.
- Validation reports.

### Golden PDF tests

Use small fixture PDFs:

- `simple_text.pdf`
- `multi_page.pdf`
- `with_metadata.pdf`
- `with_annotations.pdf`
- `with_form.pdf`
- `scanned_like.pdf`
- `encrypted_known_password.pdf`
- `corrupt_repairable.pdf`
- `image_heavy.pdf`

Do not include copyrighted PDFs.

### Visual tests

Render pages and compare:

- Output page count.
- Blank pages.
- Expected watermark/page number location.
- Unexpected full-page differences.

### Security tests

- Path traversal rejected.
- Oversized files rejected by configurable limits.
- Unauthorized encrypted PDFs rejected.
- Redaction verification fails if text remains.

## Acceptance commands

Codex should make these pass:

```bash
pytest -q
agentpdf tools list --json
agentpdf inspect tests/fixtures/simple_text.pdf --json
agentpdf merge tests/fixtures/simple_text.pdf tests/fixtures/multi_page.pdf -o /tmp/merged.pdf --json
agentpdf validate /tmp/merged.pdf --json
```

## CI expectations

GitHub Actions should run:

- Python lint.
- Type check.
- Unit tests.
- Integration smoke tests.
- License/dependency scan if feasible.
- Docs link check if feasible.

## Fixture generation

Prefer generating fixture PDFs in tests using permissive libraries to avoid copyright issues.

Include a script:

```bash
python scripts/generate_fixtures.py
```
