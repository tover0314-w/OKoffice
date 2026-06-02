# CLI Examples

```bash
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list
okpdf agent setup claude-code -o .mcp.json --json
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
okpdf create templates --json
okpdf create template-packs -o template-packs.json --json
okpdf create validate-template-pack examples/template-packs/local-agent-starter.json -o template-pack.validation.json --json
okpdf create plan-template-pack examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json --planned-output board-audit.pdf -o board-audit.plan.json --json
okpdf create agent examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json -o board-audit.pdf --plan-output board-audit.plan.json --coverage-output board-audit.coverage.json --json
okpdf create agent examples/template-packs/local-agent-starter.json --target-profile resume_pdf -o agent-resume.pdf --plan-output agent-resume.plan.json --coverage-output agent-resume.coverage.json --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue -o board-audit.pdf --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --data examples/create-data/agent-block-audit.json -o board-audit-blocks.pdf --json
okpdf evidence coverage-report board-audit.composition.json -o board-audit.coverage.json --json
okpdf patch plan board-audit.pdf --operations examples/patch-operations/layer-aware-reviewer-note.json -o board-audit.patch.json --composition board-audit.composition.json --layers board-audit.layers.json --reason "Append verified template-pack layer evidence." --json
okpdf patch apply board-audit.patch.json -o board-audit-patched.pdf --json
okpdf patch verify board-audit.patch.json board-audit-patched.pdf --json
okpdf artifacts export-bundle --file board-audit-patched.pdf --file board-audit.composition.json --file board-audit.coverage.json --file board-audit.patch.json -o board-audit.agentpdf-bundle.zip --title "Board Audit Bundle" --metadata workflow=template-pack-patch --json
okpdf artifacts verify-bundle board-audit.agentpdf-bundle.zip --json
okpdf create preview invoice -o invoice-preview.pdf --json
okpdf create from-prompt "Create a worksheet about validating generated PDFs." -o worksheet.pdf --template worksheet --style-pack paper_ink --color primary=#4f46e5 --color accent=#f59e0b --json
okpdf create from-prompt "Create an invoice for okpdf local template work." -o invoice.pdf --template invoice --data examples/create-data/invoice.json --json
okpdf create from-prompt "Create a resume for an agent infrastructure engineer." -o resume.pdf --template resume --data examples/create-data/resume.json --json
okpdf context build --text "Create a technical audit PDF from code, metrics, visual evidence, project docs, and media context." --file src/agentpdf/compose/context.py --file examples/create-data/metrics.csv --file assets/brand/okpdf-logo.png --file examples/sample-documents/business_report.md --item-json examples/context/media-items.json -o context.packet.json --title "Audit Context" --json
okpdf create plan-template-pack examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json --planned-output board-audit-from-context.pdf -o board-audit-from-context.plan.json --json
okpdf create agent examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json -o board-audit-agent.pdf --plan-output board-audit-agent.plan.json --coverage-output board-audit-agent.coverage.json --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --context-packet context.packet.json -o board-audit-from-context.pdf --json
okpdf target profiles -o target-profiles.json --json
okpdf target validate --profile-json examples/target-profiles/media-learning-deck.json -o media-learning-deck.validation.json --json
okpdf compose from-context context.packet.json --profile technical_audit -o technical-audit.pdf --json
okpdf compose from-context context.packet.json --profile slide_deck -o agent-review-deck.pdf --json
okpdf compose from-context context.packet.json --profile-json examples/target-profiles/media-learning-deck.json -o media-learning-deck.pdf --json
okpdf evidence coverage-report technical-audit.composition.json -o technical-audit.coverage.json --json
okpdf patch plan technical-audit.pdf --operations examples/patch-operations/reviewer-note.json -o technical-audit.patch.json --composition technical-audit.composition.json --reason "Add reviewer note appendix." --json
okpdf patch preview technical-audit.patch.json -o technical-audit.patch-preview.json --json
okpdf patch apply technical-audit.patch.json -o technical-audit-patched.pdf --json
okpdf patch verify technical-audit.patch.json technical-audit-patched.pdf --json
okpdf artifacts export-bundle --file technical-audit-patched.pdf --file technical-audit.composition.json --file technical-audit.coverage.json --file technical-audit.patch.json -o technical-audit.agentpdf-bundle.zip --title "Technical Audit Bundle" --metadata workflow=context-packet-patch --json
okpdf artifacts verify-bundle technical-audit.agentpdf-bundle.zip --json
okpdf patch plan technical-audit.pdf --operations examples/patch-operations/structured-appendix.json -o technical-audit.structured.patch.json --composition technical-audit.composition.json --reason "Append code, table, image, and slide evidence." --json
okpdf watermark scan.pdf --text "CONFIDENTIAL" -o scan-watermarked.pdf --json
okpdf page-numbers scan-watermarked.pdf --template "Page {page} of {total}" -o scan-numbered.pdf --json
okpdf render report.pdf --pages 1-3 --format png --out-dir renders/
okpdf extract-images report.pdf --pages all --out-dir extracted-images/ --json
okpdf extract-text report.pdf --pages all --json
okpdf create text "Hello from okpdf" -o hello.pdf --json
okpdf create markdown summary.md --style-pack plain_report -o board-report.pdf --json
okpdf create from-prompt "Create a research brief about local PDF template agents." -o research-brief.pdf --template research_brief --style-pack paper_ink --color primary=#4f46e5 --json
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
