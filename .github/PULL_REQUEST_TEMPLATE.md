# Pull Request

## Summary

<!-- What changed, and why? Keep this crisp. -->

## Type

- [ ] Bug fix
- [ ] New Office/PDF tool surface
- [ ] Workflow / agent integration
- [ ] Documentation / examples / repo UI
- [ ] Schema / API contract
- [ ] Security hardening
- [ ] Refactor / maintenance

## Domains touched

- [ ] `office.*` cross-format workflows
- [ ] `word.*`
- [ ] `sheet.*`
- [ ] `deck.*`
- [ ] `pdf.*` compatibility
- [ ] Agent setup / MCP / REST
- [ ] Docs / examples / translations
- [ ] GitHub metadata / release hygiene

## Interfaces touched

- [ ] CLI
- [ ] MCP
- [ ] REST API / OpenAPI
- [ ] Python core
- [ ] TypeScript / Node SDK
- [ ] Schemas / manifests
- [ ] Docs / examples
- [ ] CI / packaging

## OKoffice contract checks

- [ ] Public tools return the standard `ToolResult` shape.
- [ ] Outputs include artifacts, validation evidence, warnings, usage, and next recommended tools.
- [ ] Native source refs are preserved where relevant: paragraphs, tables, cells, formulas, slides, pages, bboxes, or artifact refs.
- [ ] Generated Office/PDF artifacts are written to new output paths and never silently mutate inputs.
- [ ] New errors use stable codes from `schemas/error-codes.yaml`.
- [ ] Path handling rejects traversal and suspicious filenames where applicable.
- [ ] New dependencies were reviewed against `community/DEPENDENCY_POLICY.md`.
- [ ] Hosted/model/OCR/worker behavior is behind explicit feature flags or documentation.
- [ ] No secrets, private URLs, proprietary endpoints, or local-only machine paths are included.

## Documentation

- [ ] README / docs updated when public behavior changed.
- [ ] CLI example updated.
- [ ] MCP example updated.
- [ ] REST example updated.
- [ ] Expected output or error example updated.
- [ ] Limitations and dependency/license notes updated.
- [ ] Translations updated or a translation follow-up is noted.

## Verification

```bash
python scripts/doctor.py
pytest -q
npm --workspace @okoffice/okoffice-node test
ruff check src tests scripts
```

## Artifacts

<!-- Attach before/after Office/PDF files, validation reports, render images, or screenshots when useful. Explain how to regenerate committed examples. -->
