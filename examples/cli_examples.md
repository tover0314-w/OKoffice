# CLI Examples

```bash
agentpdf tools list
agentpdf inspect report.pdf
agentpdf merge intro.pdf body.pdf appendix.pdf -o report-final.pdf
agentpdf split report.pdf --pages 1-3,4-10 --out-dir parts/
agentpdf extract report.pdf --pages 1-5 -o executive-summary.pdf
agentpdf remove-pages report.pdf --pages 2,4 -o cleaned.pdf
agentpdf rotate report.pdf --pages all --degrees 90 -o rotated.pdf
agentpdf render report.pdf --pages 1-3 --format png --out-dir renders/
agentpdf text report.pdf --pages all -o report.txt
agentpdf create --from summary.md --style business_report_modern -o board-report.pdf
agentpdf watermark report.pdf --text "Confidential" -o watermarked.pdf
agentpdf page-numbers report.pdf -o numbered.pdf
agentpdf validate report-final.pdf
agentpdf serve --mcp
agentpdf serve --api --port 7331
```
