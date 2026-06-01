# CLI Examples

```bash
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list
okpdf inspect report.pdf
okpdf inspect-pages report.pdf --pages 1-3 --render-check --json
okpdf workflow plan --goal "Chat with this PDF and cite answers" --input-path report.pdf --json
okpdf workflow run examples/workflows/local-rag.json --dry-run --json
okpdf workflow run plan-result.json --artifact-dir workflow-artifacts --binding "<question>=What are the risks?" --binding "<answer>=The report discusses revenue risk." --json
okpdf workflow report run-result.json -o workflow-report.md --json
okpdf merge intro.pdf body.pdf appendix.pdf -o report-final.pdf
okpdf split report.pdf --pages 1-3 -o report-pages-1-3.pdf
okpdf extract-pages report.pdf --pages 1-5 -o executive-summary.pdf
okpdf remove-pages report.pdf --pages 2,4 -o cleaned.pdf
okpdf rotate-pages report.pdf --pages all --degrees 90 -o rotated.pdf
okpdf reorder-pages report.pdf --order 3,1,2 -o reordered.pdf --json
okpdf insert-blank-pages reordered.pdf --after-page 1 --count 2 -o with-blanks.pdf --json
okpdf compress with-blanks.pdf -o with-blanks-compressed.pdf --json
okpdf repair with-blanks-compressed.pdf -o with-blanks-repaired.pdf --json
okpdf image-to-pdf cover.png page-2.jpg -o scan.pdf --json
okpdf create markdown examples/sample-documents/business_report.md -o board-report.pdf --style-pack business_report_modern --json
okpdf watermark scan.pdf --text "CONFIDENTIAL" -o scan-watermarked.pdf --json
okpdf page-numbers scan-watermarked.pdf --template "Page {page} of {total}" -o scan-numbered.pdf --json
okpdf render report.pdf --pages 1-3 --format png --out-dir renders/
okpdf extract-images report.pdf --pages all --out-dir extracted-images/ --json
okpdf extract-text report.pdf --pages all --json
okpdf create text "Hello from okpdf" -o hello.pdf --json
okpdf create markdown summary.md --style-pack plain_report -o board-report.pdf --json
okpdf validate scan-numbered.pdf --expected-pages 2 --json
okpdf render-check scan-numbered.pdf --pages 1 --json
okpdf blank-page-check with-blanks.pdf --pages all --json
okpdf parse-lite board-report.pdf --json
okpdf pdf-to-json board-report.pdf -o board-report.ir.json --json
okpdf pdf-to-markdown board-report.pdf -o board-report.md --json
okpdf rag ingest board-report.pdf --index board-report.index.json --json
okpdf rag chat board-report.pdf --question "What is the report about?" --report-output board-report-chat.pdf --highlight-output board-report-chat-highlighted.pdf --json
okpdf rag query board-report.index.json --query "What is the report about?" --json
okpdf rag search board-report.index.json --query "revenue risk" --json
okpdf rag cite-answer board-report.index.json --answer "The report discusses revenue risk." --json
okpdf rag highlight-sources board-report.index.json --answer "The report discusses revenue risk." -o board-report-highlighted.pdf --json
okpdf rag export-report board-report.index.json --question "What is the report about?" --answer "The report discusses revenue risk." -o board-report-rag.pdf --json
okpdf serve --mcp
okpdf serve --api
```
