# 14 - Security and Privacy

## Threat Model

okoffice must treat every input file as untrusted. The project handles formats that commonly contain active content, embedded relationships, sensitive metadata, and confusing visual layers.

PDF risks:

- Malformed objects.
- Huge streams.
- Embedded files.
- JavaScript/actions.
- External references.
- Sensitive metadata.
- Confidential text/images.
- Deceptive overlays.
- Password protection.

Word/DOCX risks:

- Macros in macro-enabled files.
- External relationships.
- Embedded objects.
- Tracked changes exposing deleted text.
- Comments with sensitive review history.
- Hidden text and fields.
- Document variables and custom metadata.

Excel/XLSX risks:

- Macros in macro-enabled files.
- External workbook links.
- Hidden sheets, very hidden sheets, and hidden rows/columns.
- Formula injection in CSV/export paths.
- Volatile formulas.
- Circular references.
- Suspicious hardcoded numbers.
- Embedded objects and data connections.

PowerPoint/PPTX risks:

- Embedded media and objects.
- External relationships.
- Speaker notes containing sensitive text.
- Hidden slides.
- Off-slide shapes or deceptive overlays.
- Template/theme metadata.

## Local File Safety

- Restrict file access to configured roots.
- Reject path traversal.
- Reject unsafe archive/package entries.
- Avoid following symlinks unless explicitly allowed.
- Never overwrite input files by default.
- Write outputs to explicit artifact paths.
- Use temporary directories with predictable cleanup.
- Hash inputs and outputs for manifests.

## Package Safety

Office Open XML files are ZIP packages. okoffice should:

- Validate ZIP entries before extraction.
- Reject absolute paths and `..` paths.
- Enforce file count and total uncompressed size limits.
- Preserve package relationship information for audit.
- Report macros, external links, embedded files, and unusual content types.

## External Fetch Safety

URL capture and conversion should be disabled by default in OSS local mode.

If enabled:

- Block private IP ranges by default.
- Limit redirects.
- Limit file size.
- Limit content types.
- Set timeouts.
- Avoid sending credentials.
- Record fetch status, URL, content hash, and warnings.

## AI/Data Privacy

- No document should be sent to a model provider unless the user explicitly configures it.
- BYOK should be explicit.
- Cloud endpoints should be opt-in.
- Logs must avoid storing raw document text by default.
- Tool results should summarize sensitive findings without echoing secrets unless the caller requests excerpts.
- Source maps should support redaction or omission of raw text in privacy-sensitive modes.

## Redaction

Redaction must be semantic removal, not visual covering.

Format-specific rules:

- PDF: remove text/image content and verify search terms no longer remain.
- Word: remove target text plus comments, tracked changes, fields, headers/footers, footnotes/endnotes, and metadata where relevant.
- Excel: remove visible and hidden cells, formulas, comments/notes, names, external links, and hidden sheets where relevant.
- PowerPoint: remove visible/off-slide shapes, notes, comments, media refs, hidden slides, and metadata where relevant.

Every redaction workflow should write a new artifact and a verification report.

## Unlock/Decrypt Policy

`unlock_authorized` requires a valid password or key. The project must not provide password cracking or unauthorized circumvention tools.

## Metadata Removal

Metadata removal tools should remove common fields and expose verification reports.

Targets:

- PDF info dictionary and XMP metadata.
- DOCX core/app/custom properties, comments policy, tracked changes policy.
- XLSX core/app/custom properties, workbook properties, calculation metadata as appropriate.
- PPTX core/app/custom properties, presentation properties, notes/comments policy.

## Formula and Macro Policy

- Default core must not execute macros.
- Formula evaluation must be explicit and report engine/provider.
- CSV output must guard against formula injection when opened in spreadsheet apps.
- External workbook/data links should be reported and disabled unless explicitly allowed.

## Sandbox Guidance

Future hosted or optional heavy workers should run in isolated environments with:

- CPU, memory, and time limits.
- No broad filesystem access.
- Network disabled unless needed.
- Output directory isolation.
- Package extraction limits.
- Malware/scanner integration when appropriate.
- Worker capability reporting in ToolResult usage.

## Security Output Standard

Security tools should produce evidence, not just booleans:

```json
{
  "status": "succeeded",
  "tool": "office.security.inspect",
  "validation": {
    "valid": true,
    "checks": [
      {"name": "path_safety", "status": "passed"},
      {"name": "package_entries", "status": "passed"},
      {"name": "macro_detection", "status": "warning"}
    ]
  },
  "warnings": [
    "Workbook is macro-enabled; macros were not executed."
  ],
  "next_recommended_tools": ["sheet.inspect.workbook"]
}
```
