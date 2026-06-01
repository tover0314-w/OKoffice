# Maintainer Guide

## Weekly maintenance

- Review issues and PRs.
- Triage labels.
- Check failing CI.
- Review dependency updates.
- Update roadmap statuses.

## Release process

1. Ensure tests pass.
2. Update CHANGELOG.
3. Update version.
4. Run release checklist.
5. Tag release.
6. Publish package/artifacts.
7. Announce with examples.

## Labels

- `area:cli`
- `area:mcp`
- `area:api`
- `area:pdf-core`
- `area:ai`
- `area:docs`
- `area:security`
- `status:planned`
- `status:beta`
- `good first issue`
- `help wanted`

## Merge standards

- Core PDF tools require tests.
- Public API changes require docs.
- Security-sensitive changes require maintainer review.
- Dependencies require license review.
