# CLI Examples

```bash
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list
okpdf agent setup claude-code -o .mcp.json --json
okpdf agent setup codex -o codex.mcp.json --safe-root . --json
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
okpdf create agent examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json -o board-audit.pdf --plan-output board-audit.plan.json --coverage-output board-audit.coverage.json --context-classification-output board-audit.context-classification.json --context-report-output board-audit.context-report.pdf --context-report-json-output board-audit.context-report.json --bundle-output board-audit.agentpdf-bundle.zip --json
okpdf create agent examples/template-packs/local-agent-starter.json --target-profile resume_pdf -o agent-resume.pdf --plan-output agent-resume.plan.json --coverage-output agent-resume.coverage.json --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue -o board-audit.pdf --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --data examples/create-data/agent-block-audit.json -o board-audit-blocks.pdf --json
okpdf evidence coverage-report board-audit.composition.json -o board-audit.coverage.json --json
okpdf artifacts source-map --composition board-audit.composition.json -o board-audit.artifact-source-map.json --title "Board Audit Artifact Source Map" --json
okpdf patch plan board-audit.pdf --operations examples/patch-operations/layer-aware-reviewer-note.json -o board-audit.patch.json --composition board-audit.composition.json --layers board-audit.layers.json --reason "Append verified template-pack layer evidence." --json
okpdf patch plan board-audit.pdf --operations examples/patch-operations/regenerate-layer-block.json -o board-audit.regenerate.patch.json --composition board-audit.composition.json --layers board-audit.layers.json --reason "Regenerate a template block with layer evidence." --json
okpdf patch apply board-audit.patch.json -o board-audit-patched.pdf --json
okpdf patch verify board-audit.patch.json board-audit-patched.pdf --json
okpdf artifacts manifest --file board-audit-patched.pdf --file board-audit.composition.json --file board-audit.coverage.json --file board-audit.artifact-source-map.json --file board-audit.patch.json -o board-audit.artifacts.json --title "Board Audit Artifacts" --metadata workflow=template-pack-patch --json
okpdf artifacts graph --manifest board-audit.artifacts.json -o board-audit.artifact-graph.json --title "Board Audit Artifact Graph" --json
okpdf artifacts export-bundle --file board-audit-patched.pdf --file board-audit.composition.json --file board-audit.coverage.json --file board-audit.patch.json -o board-audit.agentpdf-bundle.zip --title "Board Audit Bundle" --metadata workflow=template-pack-patch --json
okpdf artifacts verify-bundle board-audit.agentpdf-bundle.zip --json
okpdf create preview invoice -o invoice-preview.pdf --json
okpdf create from-prompt "Create a worksheet about validating generated PDFs." -o worksheet.pdf --template worksheet --style-pack paper_ink --color primary=#4f46e5 --color accent=#f59e0b --json
okpdf create from-prompt "Create an invoice for okpdf local template work." -o invoice.pdf --template invoice --data examples/create-data/invoice.json --json
okpdf create from-prompt "Create a resume for an agent infrastructure engineer." -o resume.pdf --template resume --data examples/create-data/resume.json --json
okpdf create html-package --html "<main><h1>HTML First</h1><p>Inspectable source before PDF.</p></main>" -o html-first.html --title "HTML First" --json
okpdf render-html-package html-first.html-manifest.json -o html-first.pdf --json
okpdf qa visual-report html-first.pdf --html-package-manifest html-first.html-manifest.json --pages 1 --json
okpdf artifacts manifest --file html-first.pdf --file html-first.html --file html-first.html-manifest.json -o html-first.artifacts.json --title "HTML First Artifacts" --metadata workflow=html-first-createpdf --json
okpdf artifacts graph --manifest html-first.artifacts.json -o html-first.artifact-graph.json --title "HTML First Artifact Graph" --json
okpdf createpdf --html "<main><h1>CreatePDF</h1><p>HTML-first workflow with audit evidence.</p></main>" --html-output createpdf.html --pdf-output createpdf.pdf --artifact-dir createpdf-audit --title "CreatePDF" --json
okpdf context ingest --file src/agentpdf/compose/context.py --role code_evidence --label "Composer Source" -o composer.context-item.json --json
okpdf context code-snapshot src/agentpdf/compose/context.py --line-start 1 --line-end 80 --repository-root . -o composer.snapshot.context-item.json --json
okpdf context data-profile examples/create-data/metrics.csv --label "Runtime Metrics" -o metrics.profile.context-item.json --json
okpdf context image-analyze assets/brand/okpdf-logo.png --skip-ocr --json
okpdf context packet --item-json composer.context-item.json --text "Create a technical audit PDF from pre-ingested code evidence." -o agent.context.packet.json --title "Agent Packet" --json
okpdf context build --text "Create a technical audit PDF from code, metrics, visual evidence, project docs, web links, and media context." --file src/agentpdf/compose/context.py --file examples/create-data/metrics.csv --file assets/brand/okpdf-logo.png --file examples/sample-documents/business_report.md --link okpdf.dev/docs/context --item-json examples/context/media-items.json -o context.packet.json --title "Audit Context" --json
okpdf context classify context.packet.json --profile technical_audit -o context.classification.json --json
okpdf evidence context-packet-report context.packet.json -o context-report.pdf --report-output context-report.json --json
okpdf create plan-template-pack examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json --planned-output board-audit-from-context.pdf -o board-audit-from-context.plan.json --json
okpdf create agent examples/template-packs/local-agent-starter.json --target-profile technical_audit --context-packet context.packet.json -o board-audit-agent.pdf --plan-output board-audit-agent.plan.json --coverage-output board-audit-agent.coverage.json --context-classification-output board-audit-agent.context-classification.json --context-report-output board-audit-agent.context-report.pdf --context-report-json-output board-audit-agent.context-report.json --bundle-output board-audit-agent.agentpdf-bundle.zip --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json --template board_audit --color-scheme executive_blue --context-packet context.packet.json -o board-audit-from-context.pdf --renderer html --html-output board-audit-from-context.html --json
okpdf target profiles -o target-profiles.json --json
okpdf target validate --profile-json examples/target-profiles/media-learning-deck.json -o media-learning-deck.validation.json --json
okpdf compose plan context.packet.json --profile technical_audit -o technical-audit.plan.json --json
okpdf compose render-ir technical-audit.plan.json -o technical-audit-from-ir.pdf --json
okpdf compose from-context context.packet.json --profile technical_audit -o technical-audit.pdf --renderer html --html-output technical-audit.html --json
okpdf render-html-package technical-audit.html-manifest.json -o technical-audit-rendered.pdf --json
okpdf authoring plan examples/research_deck_brief.json --json
okpdf research plan examples/research_deck_brief.json --json
okpdf research source-cards --brief examples/research_deck_brief.json --sources examples/research_deck_sources.json --json
okpdf research evidence-cards --source-cards examples/research_deck_source_cards.json --json
okpdf design tokens --theme consulting --color primary_color=#123456 --json
okpdf workflow research-deck examples/research_deck_brief.json --evidence-cards examples/research_deck_evidence.json --html-output research-deck.html --pdf-output research-deck.pdf --artifact-dir research-deck-artifacts --execute --json
okpdf compose from-context context.packet.json --profile slide_deck -o agent-review-deck.pdf --json
okpdf compose from-context context.packet.json --profile-json examples/target-profiles/media-learning-deck.json -o media-learning-deck.pdf --json
okpdf compose add-code-block technical-audit.pdf --title "Risk Function" --code "def risky_total(items): return sum(items)" --language python --source-ref ctx_002 --target-slot code_review -o technical-audit.code.pdf --json
okpdf compose add-table technical-audit.pdf --title "Runtime Metrics" --columns metric,value --row latency_ms,42 --row error_rate,0.01 --source-ref ctx_003 --target-slot evidence_table -o technical-audit.table.pdf --json
okpdf compose add-figure technical-audit.pdf --title "Architecture Figure" --image assets/brand/okpdf-logo.png --caption "Local visual evidence." --source-ref ctx_004 -o technical-audit.figure.pdf --json
okpdf compose add-appendix technical-audit.pdf --title "Source Appendix" --markdown "## Sources\n\n- ctx_002\n- ctx_003\n- ctx_004" --source-ref ctx_002 --source-ref ctx_003 -o technical-audit.appendix.pdf --json
okpdf compose add-citation technical-audit.pdf --title "Source Citation" --quote "Cited claim text." --source https://example.com/research --source-ref ctx_web --target-slot citations -o technical-audit.citation.pdf --json
okpdf compose add-media-reference technical-audit.pdf --title "Meeting Audio" --media meeting.mp3 --media-kind audio --transcript-excerpt "00:00 Kickoff" --source-ref ctx_audio --target-slot media_evidence -o technical-audit.media.pdf --json
okpdf compose add-slide technical-audit.pdf --title "Review Slide" --body "Decision evidence" --source-ref ctx_slide --target-slot evidence_slide -o technical-audit.slide.pdf --json
okpdf evidence coverage-report technical-audit.composition.json -o technical-audit.coverage.json --json
okpdf evidence map-sources technical-audit.composition.json --context-packet context.packet.json -o technical-audit.source-map.json --json
okpdf artifacts source-map --composition technical-audit.composition.json --context-packet context.packet.json -o technical-audit.artifact-source-map.json --title "Technical Audit Artifact Source Map" --json
okpdf evidence cite-claims claims.json --source-map technical-audit.source-map.json -o technical-audit.citations.json --json
okpdf patch plan technical-audit.pdf --operations examples/patch-operations/reviewer-note.json -o technical-audit.patch.json --composition technical-audit.composition.json --reason "Add reviewer note appendix." --json
okpdf patch preview technical-audit.patch.json -o technical-audit.patch-preview.json --json
okpdf patch apply technical-audit.patch.json -o technical-audit-patched.pdf --json
okpdf patch verify technical-audit.patch.json technical-audit-patched.pdf --json
okpdf artifacts manifest --file technical-audit-patched.pdf --file context.packet.json --file technical-audit.composition.json --file technical-audit.coverage.json --file technical-audit.source-map.json --file technical-audit.artifact-source-map.json --file technical-audit.citations.json --file technical-audit.patch.json -o technical-audit.artifacts.json --title "Technical Audit Artifacts" --metadata workflow=context-packet-patch --json
okpdf artifacts graph --manifest technical-audit.artifacts.json -o technical-audit.artifact-graph.json --title "Technical Audit Artifact Graph" --json
okpdf artifacts export-bundle --file technical-audit-patched.pdf --file context.packet.json --file technical-audit.composition.json --file technical-audit.coverage.json --file technical-audit.patch.json -o technical-audit.agentpdf-bundle.zip --title "Technical Audit Bundle" --metadata workflow=context-packet-patch --json
okpdf artifacts verify-bundle technical-audit.agentpdf-bundle.zip --json
okpdf patch plan technical-audit.pdf --operations examples/patch-operations/structured-appendix.json -o technical-audit.structured.patch.json --composition technical-audit.composition.json --reason "Append code, table, image, citation, media, and slide evidence." --json
okpdf watermark scan.pdf --text "CONFIDENTIAL" -o scan-watermarked.pdf --json
okpdf page-numbers scan-watermarked.pdf --template "Page {page} of {total}" -o scan-numbered.pdf --json
okpdf render report.pdf --pages 1-3 --format png --out-dir renders/
okpdf extract-images report.pdf --pages all --out-dir extracted-images/ --json
okpdf extract-text report.pdf --pages all --json
okpdf metadata page-info report.pdf --pages 1-3 --json
okpdf security remove-metadata report.pdf -o report.no-metadata.pdf --json
okpdf security redact sensitive.pdf -o sensitive.redacted.pdf --region '{"page":1,"bbox":[60,700,280,760],"label":"secret"}' --json
okpdf security verify-redaction sensitive.redacted.pdf --search-term SECRET-CODE-123 --json
okpdf redaction-check sensitive.redacted.pdf --search-term SECRET-CODE-123 --json
okpdf create text "Hello from okpdf" -o hello.pdf --json
okpdf create markdown summary.md --style-pack plain_report -o board-report.pdf --json
okpdf create from-prompt "Create a research brief about local PDF template agents." -o research-brief.pdf --template research_brief --style-pack paper_ink --color primary=#4f46e5 --json
okpdf validate scan-numbered.pdf --expected-pages 2 --json
okpdf page-count-check scan-numbered.pdf --expected-pages 2 --json
okpdf render-check scan-numbered.pdf --pages 1 --json
okpdf blank-page-check with-blanks.pdf --pages all --json
okpdf parse-lite board-report.pdf --json
okpdf compare semantic-diff board-report-v1.pdf board-report-v2.pdf --pages 1 --json
okpdf compare version-report board-report-v1.pdf board-report-v2.pdf -o board-report.version-report.md --json
okpdf compare visual-diff board-report-v1.pdf board-report-v2.pdf --pages 1 --json
okpdf visual-diff board-report-v1.pdf board-report-v2.pdf --max-difference-ratio 0.001 --json
okpdf parse-figures board-report.pdf --json
okpdf parse-formulas board-report.pdf --json
okpdf parse-charts board-report.pdf --json
okpdf parse-references board-report.pdf --json
okpdf forms create -o contact-form.pdf --field '{"name":"name","label":"Name","required":true}' --json
okpdf forms import-data contact-form.pdf --data '{"name":"Ada"}' -o contact-form-filled.pdf --json
okpdf forms validate contact-form-filled.pdf --required-field name --json
okpdf ocr scan-to-pdf cover.png -o scan.pdf --json
okpdf ocr despeckle scan.pdf -o scan-despeckled.pdf --json
okpdf ocr remove-existing scan.pdf -o scan-no-ocr.pdf --json
okpdf ocr multilingual scan.pdf -o scan-multilingual.pdf --language eng --language chi_sim --json
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
