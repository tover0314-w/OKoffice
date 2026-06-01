# CLI Examples

```bash
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list
okpdf inspect report.pdf
okpdf merge intro.pdf body.pdf appendix.pdf -o report-final.pdf
okpdf split report.pdf --pages 1-3 -o report-pages-1-3.pdf
okpdf extract-pages report.pdf --pages 1-5 -o executive-summary.pdf
okpdf remove-pages report.pdf --pages 2,4 -o cleaned.pdf
okpdf rotate-pages report.pdf --pages all --degrees 90 -o rotated.pdf
okpdf image-to-pdf cover.png page-2.jpg -o scan.pdf --json
okpdf watermark scan.pdf --text "CONFIDENTIAL" -o scan-watermarked.pdf --json
okpdf page-numbers scan-watermarked.pdf --template "Page {page} of {total}" -o scan-numbered.pdf --json
okpdf render report.pdf --pages 1-3 --format png --out-dir renders/
okpdf extract-text report.pdf --pages all --json
okpdf create text "Hello from okpdf" -o hello.pdf --json
okpdf create markdown summary.md --style-pack plain_report -o board-report.pdf --json
okpdf validate scan-numbered.pdf --expected-pages 2 --json
okpdf serve --mcp
okpdf serve --api
```
