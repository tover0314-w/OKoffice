# Pull Request

## Summary

<!-- What changed, and why? Keep this crisp. -->

## Type

- [ ] Bug fix
- [ ] Feature or tool surface
- [ ] Documentation / examples
- [ ] Schema / API contract
- [ ] Security hardening
- [ ] Refactor / maintenance

## Interfaces touched

- [ ] CLI
- [ ] MCP
- [ ] REST API / OpenAPI
- [ ] Python core
- [ ] TypeScript / Node SDK
- [ ] Schemas / manifests
- [ ] Docs / examples
- [ ] Docker / deployment

## AgentPDF checks

- [ ] Tool outputs return the standard `ToolResult` shape.
- [ ] Generated PDFs are written to new output paths and never mutate inputs.
- [ ] Generated PDFs include validation evidence where applicable.
- [ ] New errors use stable codes from `schemas/error-codes.yaml`.
- [ ] Path handling rejects traversal and suspicious filenames where applicable.
- [ ] New dependencies were reviewed against `community/DEPENDENCY_POLICY.md`.
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
npm --workspace @okpdf/agentpdf-node test
ruff check src tests scripts
```

## Artifacts

<!-- Attach before/after PDFs, validation reports, render images, or screenshots for PDF-generating changes. Explain how to regenerate committed examples. -->
