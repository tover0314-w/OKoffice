# CLI Examples

```bash
agentpdf tools list
agentpdf inspect report.pdf
agentpdf merge intro.pdf body.pdf appendix.pdf -o report-final.pdf
agentpdf split report.pdf --pages 1-3 -o report-pages-1-3.pdf
agentpdf extract-pages report.pdf --pages 1-5 -o executive-summary.pdf
agentpdf remove-pages report.pdf --pages 2,4 -o cleaned.pdf
agentpdf rotate-pages report.pdf --pages all --degrees 90 -o rotated.pdf
agentpdf render report.pdf --pages 1-3 --format png --out-dir renders/
agentpdf extract-text report.pdf --pages all --json
agentpdf create text "Hello from okpdf" -o hello.pdf --json
agentpdf create markdown summary.md --style-pack plain_report -o board-report.pdf --json
agentpdf watermark report.pdf --text "Confidential" -o watermarked.pdf
agentpdf page-numbers report.pdf -o numbered.pdf
agentpdf serve --mcp
agentpdf serve --api
```
