# EPIC-000 — Repo Bootstrap

## Goal

Create the initial Python open-source project structure.

## Tasks

- Create `pyproject.toml`.
- Create package under `src/agentpdf`.
- Add CLI entrypoint.
- Add pytest configuration.
- Add README install section.
- Add import smoke test.

## Acceptance criteria

- `pip install -e .` works.
- `agentpdf --help` works.
- `pytest -q` passes.
- No cloud dependencies required.
