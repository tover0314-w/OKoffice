# Acceptance Test Matrix

| Area | Command | Expected |
|---|---|---|
| Import | `python -c "import agentpdf"` | No error |
| CLI | `agentpdf --help` | Help shown |
| Tool registry | `agentpdf tools list --json` | JSON manifest |
| Inspect | `agentpdf inspect simple.pdf --json` | Page count and metadata |
| Merge | `agentpdf merge a.pdf b.pdf -o merged.pdf --json` | Output artifact and validation |
| Split | `agentpdf split multi.pdf --pages 1-2 -o out.pdf --json` | Output artifact and validation |
| Render | `agentpdf render simple.pdf --pages 1 --out-dir renders --json` | Image artifact |
| Validate | `agentpdf validate merged.pdf --json` | Validation report |
| MCP | `agentpdf serve --mcp` | Server starts |
| API | `agentpdf serve --api` | `/healthz` returns OK |
