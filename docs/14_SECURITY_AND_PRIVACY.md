# 14 — Security and Privacy

## Threat model

PDFs can contain:

- Malformed objects.
- Huge streams.
- Embedded files.
- JavaScript/actions.
- External references.
- Sensitive metadata.
- Confidential text/images.
- Deceptive overlays.
- Password protection.

AgentPDF must treat all input as untrusted.

## Local file safety

- Restrict file access to configured roots.
- Reject path traversal.
- Avoid following symlinks unless explicitly allowed.
- Never overwrite input files by default.
- Use temporary directories with predictable cleanup.

## External fetch safety

URL-to-PDF and PDF-from-URL should be disabled by default in OSS local mode.

If enabled:

- Block private IP ranges by default.
- Limit redirects.
- Limit file size.
- Limit content types.
- Set timeouts.
- Avoid sending credentials.

## AI/data privacy

- No document should be sent to a model provider unless the user explicitly configures it.
- BYOK should be explicit.
- Cloud endpoints should be opt-in.
- Logs must avoid storing raw document text by default.

## Redaction

Redaction must be semantic removal, not visual covering.

## Unlock/decrypt policy

`unlock_authorized` requires a valid password or key. The project must not provide password cracking or unauthorized circumvention tools.

## Metadata removal

`pdf.security.remove_metadata` should remove common metadata fields and expose a verification report.

## Sandbox guidance

Future hosted workers should run in isolated containers with:

- CPU/memory/time limits.
- No broad filesystem access.
- Network disabled unless needed.
- Output directory isolation.
- Malware/scanner integration when appropriate.
