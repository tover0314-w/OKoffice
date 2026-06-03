# 19 - Dependency and License Policy

## Goal

Keep the default open-source core commercially usable, safe, and easy to adopt.

## Recommended default license

Apache-2.0.

## Dependency categories

### Allowed by default, subject to review

- MIT.
- BSD.
- Apache-2.0.
- ISC.
- MPL-2.0 with careful review.

### Caution

- LGPL: review linking and distribution obligations.
- GPL: avoid in the default core.
- AGPL: avoid in the default core and hosted service unless legal review approves.
- Custom model or data licenses: review carefully.

## Optional workers

Some high-value tools may depend on libraries with restrictive licenses. These can be:

- Optional extras.
- Separate containers.
- Disabled by default.
- Clearly documented.
- Excluded from commercial hosted core until reviewed.

## License metadata

Every dependency should include:

- Package name.
- Version range.
- License.
- Purpose.
- Default or optional.
- Risk note.

## AI models

Do not bundle model weights unless the license permits redistribution and commercial use.

## Fixture PDFs

Do not include copyrighted sample PDFs. Generate fixtures or use public-domain or permissively licensed examples with attribution.
