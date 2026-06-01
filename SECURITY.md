# Security Policy

AgentPDF Infra processes potentially sensitive documents. Security is a core product feature.

## Supported versions

The initial pre-alpha harness has no supported production version. Once released, maintainers should maintain a table of supported versions.

## Reporting vulnerabilities

Do not open public issues for vulnerabilities. Report privately to the security contact listed by the maintainers after launch.

## Security principles

- Never trust PDF input.
- Treat PDF files as potentially malicious.
- Avoid executing embedded JavaScript, file attachments, or external references.
- Validate and sanitize file paths.
- Run heavy or risky processing in restricted workers.
- Avoid persistent storage unless explicitly requested.
- Provide metadata removal and redaction verification tools.
- Protect against zip bombs, decompression bombs, memory exhaustion, and huge-page documents.

## Sensitive capabilities

The following require careful review:

- Decryption/unlock tools: must only work for authorized users with passwords or keys.
- Redaction: must remove content, not merely cover it visually.
- Signature verification: must not overstate trust.
- OCR and AI parse: must not leak data to external providers without explicit configuration.
- URL/file fetch: must mitigate SSRF and local file exposure.
