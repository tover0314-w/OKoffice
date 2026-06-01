# Contributing to AgentPDF Infra

Thank you for contributing. This project aims to become the open-source PDF infrastructure layer for AI agents and document automation.

## Contribution types

We welcome:

- Core PDF tools.
- MCP/API/CLI improvements.
- Document parsing and IR improvements.
- Tests and fixture PDFs.
- Documentation and examples.
- Security hardening.
- Accessibility improvements.
- Language bindings.
- Integration examples for agents and workflow tools.

## Development setup

The implementation should eventually support:

```bash
git clone <repo>
cd agentpdf
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
agentpdf --help
```

Codex should create the exact command set during implementation and keep this file updated.

## Pull request checklist

Before opening a PR:

- [ ] Tests pass.
- [ ] Public schema changes are documented.
- [ ] CLI/API/MCP examples are updated.
- [ ] New output PDFs include validation.
- [ ] New dependency is reviewed against `community/DEPENDENCY_POLICY.md`.
- [ ] New feature has a status label: stable, beta, experimental, planned, or cloud_only.
- [ ] No secrets, tokens, or proprietary endpoints are included.
- [ ] Error handling uses stable error codes.
- [ ] Documentation is polished and readable.

## Developer Certificate of Origin

This project may use DCO sign-off instead of a CLA.

Use:

```bash
git commit -s -m "your message"
```

The maintainer team can decide whether DCO enforcement is required before public launch.
