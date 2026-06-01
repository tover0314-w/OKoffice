# Code Review Checklist

## Product alignment

- [ ] Feature belongs to open-source scope or is clearly marked optional/cloud/planned.
- [ ] Tool name follows namespace conventions.
- [ ] Output is agent-readable.

## Code quality

- [ ] Typed public functions.
- [ ] Pydantic models for public schemas.
- [ ] No hidden global state unless justified.
- [ ] No input file mutation.
- [ ] Safe path handling.
- [ ] Stable error codes.

## PDF correctness

- [ ] Output page count tested.
- [ ] Output PDF opens.
- [ ] Render check where applicable.
- [ ] Validation report attached.
- [ ] Edge cases tested.

## Security

- [ ] No path traversal.
- [ ] No unauthorized decrypt/unlock behavior.
- [ ] No external network calls by default.
- [ ] No sensitive document text in logs by default.

## Open-source standards

- [ ] Dependency license reviewed.
- [ ] Docs updated.
- [ ] Examples updated.
- [ ] Tests added.
- [ ] Changelog updated if user-visible.
