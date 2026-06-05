# 23 — Full Tool Status Matrix

Total tools specified: **241**

This matrix is the current machine-aligned `pdf.*` compatibility manifest. It should remain complete and unchanged until the okoffice tool manifest is added.

This is not the okoffice public product map. The okoffice product map lives in `docs/38_OKOFFICE_TOOL_TAXONOMY.md` and is organized around Word, Excel, PowerPoint, PDF, bundles, source graphs, validation, and workflows.

okoffice migration notes:

- `pdf.*` remains the first implemented domain and current CLI/MCP/REST compatibility surface.
- Future `office.*` tools should be added to a new okoffice manifest before they appear in this table.
- Target domains include `office.inspect.*`, `word.*`, `sheet.*`, `deck.*`, `office.context.*`, `office.evidence.*`, `office.workflow.*`, `office.validation.*`, and `office.bundle.*`.
- The intended product is multi-format Office infrastructure; this table records the currently implemented PDF-domain foundation.

Implemented okoffice target snapshot lives in `schemas/office-tool-manifest.target.json`. Current local target tools include:

| Tool | Status | OSS default |
|---|---:|---:|
| `office.agent.setup.claude_code` | beta | yes |
| `office.inspect.file` | beta | yes |
| `office.context.build_packet` | beta | yes |
| `office.extract.schema` | beta | yes |
| `office.validation.package` | beta | yes |
| `word.inspect.document` | beta | yes |
| `word.extract.tables` | beta | yes |
| `sheet.inspect.workbook` | beta | yes |
| `sheet.read.workbook` | beta | yes |
| `sheet.profile.data` | beta | yes |
| `sheet.extract.tables` | beta | yes |
| `sheet.create.evidence_workbook` | beta | yes |
| `sheet.write.workbook` | beta | yes |
| `sheet.validate.workbook` | beta | yes |
| `sheet.validation.formulas` | beta | yes |
| `deck.inspect.presentation` | beta | yes |
| `deck.compose.plan` | beta | yes |
| `deck.create.presentation` | beta | yes |
| `deck.create.from_outline` | beta | yes |
| `deck.validate.presentation` | beta | yes |
| `deck.render.html` | beta | yes |
| `deck.validation.html_preview` | beta | yes |
| `deck.export.pptx` | beta | yes |
| `deck.review.taste` | planned | yes |
| `office.workflow.extract_to_sheet` | beta | yes |
| `office.workflow.sheet_to_deck` | beta | yes |
| `office.workflow.board_pack` | beta | yes |
| `office.bundle.verify` | beta | yes |

| Tool | Category | Status | OSS default |
|---|---|---:|---:|
| `agent.setup.claude_code` | agent | beta | yes |
| `agent.setup.codex` | agent | beta | yes |
| `agent.setup.kilo_code` | agent | beta | yes |
| `agent.setup.openclaw` | agent | beta | yes |
| `pdf.context.ingest` | context | beta | yes |
| `pdf.context.packet` | context | beta | yes |
| `pdf.context.build_packet` | context | beta | yes |
| `pdf.context.classify` | context | beta | yes |
| `pdf.context.image_analyze` | context | beta | yes |
| `pdf.context.video_transcribe` | context | planned/cloud | no |
| `pdf.context.video_keyframes` | context | planned/cloud | no |
| `pdf.context.audio_transcribe` | context | planned/cloud | no |
| `pdf.context.web_capture` | context | beta | yes |
| `pdf.context.code_snapshot` | context | beta | yes |
| `pdf.context.data_profile` | context | beta | yes |
| `pdf.target.profiles` | target | beta | yes |
| `pdf.target.validate_profile` | target | beta | yes |
| `pdf.target.select_profile` | target | beta | yes |
| `pdf.evidence.map_sources` | evidence | beta | yes |
| `pdf.evidence.cite_claims` | evidence | beta | yes |
| `pdf.evidence.coverage_report` | evidence | beta | yes |
| `pdf.evidence.highlight_sources` | evidence | beta | no |
| `pdf.evidence.context_packet_report` | evidence | beta | yes |
| `pdf.evidence.verify_citations` | evidence | planned/cloud | no |
| `pdf.compose.plan` | compose | beta | yes |
| `pdf.compose.from_context` | compose | beta | yes |
| `pdf.compose.render_ir` | compose | beta | yes |
| `pdf.compose.add_code_block` | compose | beta | yes |
| `pdf.compose.add_figure` | compose | beta | yes |
| `pdf.compose.add_table` | compose | beta | yes |
| `pdf.compose.add_appendix` | compose | beta | yes |
| `pdf.compose.add_citation` | compose | beta | yes |
| `pdf.compose.add_media_reference` | compose | beta | yes |
| `pdf.compose.add_slide` | compose | beta | yes |
| `pdf.compose.compile_packet` | compose | planned/cloud | no |
| `pdf.patch.plan` | patch | beta | yes |
| `pdf.patch.preview` | patch | beta | yes |
| `pdf.patch.apply` | patch | beta | yes |
| `pdf.patch.verify` | patch | beta | yes |
| `pdf.patch.rollback_manifest` | patch | beta | no |
| `pdf.patch.regenerate_section` | patch | planned/cloud | no |
| `pdf.present.create_deck` | present | beta/cloud | no |
| `pdf.present.report_to_deck` | present | planned/cloud | no |
| `pdf.present.video_to_deck` | present | planned/cloud | no |
| `pdf.present.paper_to_deck` | present | planned/cloud | no |
| `pdf.present.speaker_notes` | present | planned/cloud | no |
| `pdf.present.handout` | present | beta | yes |
| `pdf.artifacts.manifest` | artifacts | beta | yes |
| `pdf.artifacts.graph` | artifacts | beta | yes |
| `pdf.artifacts.source_map` | artifacts | beta | yes |
| `pdf.artifacts.export_bundle` | artifacts | beta/local | yes |
| `pdf.artifacts.verify_bundle` | artifacts | beta/local | yes |
| `pdf.workflow.plan` | workflow | beta | yes |
| `pdf.workflow.run` | workflow | beta | yes |
| `pdf.workflow.report` | workflow | beta | yes |
| `pdf.workflow.createpdf` | workflow | beta | yes |
| `pdf.workflow.research_deck` | workflow | beta | yes |
| `pdf.authoring.plan` | authoring | beta | yes |
| `pdf.storyboard.plan` | authoring | beta | yes |
| `pdf.pages.write` | authoring | beta | yes |
| `pdf.create.html_package` | authoring | beta | yes |
| `pdf.qa.visual_report` | validation | beta | yes |
| `pdf.research.plan` | research | beta | yes |
| `pdf.research.source_cards` | research | beta | yes |
| `pdf.research.evidence_cards` | research | beta | yes |
| `pdf.insights.synthesize` | insights | planned | no |
| `pdf.design.tokens` | authoring | beta | yes |
| `pdf.pages.revise` | authoring | beta | yes |
| `pdf.inspect.document` | inspect | stable | yes |
| `pdf.inspect.pages` | inspect | stable | yes |
| `pdf.inspect.permissions` | inspect | beta | yes |
| `pdf.inspect.health` | inspect | beta | yes |
| `pdf.organize.merge` | organize | stable | yes |
| `pdf.organize.split` | organize | stable | yes |
| `pdf.organize.extract_pages` | organize | stable | yes |
| `pdf.organize.remove_pages` | organize | stable | yes |
| `pdf.organize.reorder_pages` | organize | stable | yes |
| `pdf.organize.rotate_pages` | organize | stable | yes |
| `pdf.organize.duplicate_pages` | organize | beta | yes |
| `pdf.organize.insert_blank_pages` | organize | beta | yes |
| `pdf.organize.insert_pdf` | organize | beta | yes |
| `pdf.organize.n_up` | organize | beta | yes |
| `pdf.organize.booklet` | organize | beta | yes |
| `pdf.organize.flatten_pages` | organize | beta | yes |
| `pdf.optimize.compress` | optimize | stable | yes |
| `pdf.optimize.linearize` | optimize | beta | yes |
| `pdf.optimize.repair` | optimize | beta | yes |
| `pdf.optimize.web_optimize` | optimize | beta | yes |
| `pdf.optimize.downsample_images` | optimize | beta | yes |
| `pdf.optimize.remove_unused_objects` | optimize | beta | yes |
| `pdf.optimize.subset_fonts` | optimize | beta | yes |
| `pdf.optimize.to_pdfa` | optimize | beta | yes |
| `pdf.optimize.validate_pdfa` | optimize | beta | yes |
| `pdf.convert.image_to_pdf` | convert_to_pdf | stable | yes |
| `pdf.convert.markdown_to_pdf` | convert_to_pdf | stable | yes |
| `pdf.convert.html_to_pdf` | convert_to_pdf | beta | yes |
| `pdf.render.html_package` | render | beta | yes |
| `pdf.convert.url_to_pdf` | convert_to_pdf | beta | yes |
| `pdf.convert.text_to_pdf` | convert_to_pdf | stable | yes |
| `pdf.convert.docx_to_pdf` | convert_to_pdf | beta | yes |
| `pdf.convert.pptx_to_pdf` | convert_to_pdf | beta | yes |
| `pdf.convert.xlsx_to_pdf` | convert_to_pdf | beta | yes |
| `pdf.convert.pdf_to_images` | convert_from_pdf | stable | yes |
| `pdf.convert.pdf_to_text` | convert_from_pdf | stable | yes |
| `pdf.convert.pdf_to_markdown` | convert_from_pdf | beta | yes |
| `pdf.convert.pdf_to_json` | convert_from_pdf | beta | yes |
| `pdf.convert.pdf_to_html` | convert_from_pdf | beta | yes |
| `pdf.convert.pdf_to_docx` | convert_from_pdf | beta | yes |
| `pdf.convert.pdf_to_pptx` | convert_from_pdf | beta | yes |
| `pdf.convert.pdf_to_xlsx` | convert_from_pdf | beta | yes |
| `pdf.convert.extract_images` | convert_from_pdf | stable | yes |
| `pdf.convert.extract_fonts` | convert_from_pdf | beta | yes |
| `pdf.convert.extract_attachments` | convert_from_pdf | beta | yes |
| `pdf.edit.add_text` | edit | beta | yes |
| `pdf.edit.add_image` | edit | beta | yes |
| `pdf.edit.add_shape` | edit | beta | yes |
| `pdf.edit.add_link` | edit | beta | yes |
| `pdf.edit.add_annotation` | edit | beta | yes |
| `pdf.edit.highlight` | edit | beta | yes |
| `pdf.edit.underline` | edit | beta | yes |
| `pdf.edit.strikeout` | edit | beta | yes |
| `pdf.edit.freehand_draw` | edit | beta | yes |
| `pdf.edit.crop` | edit | beta | yes |
| `pdf.edit.resize_pages` | edit | beta | yes |
| `pdf.edit.add_margin` | edit | beta | yes |
| `pdf.edit.header_footer` | edit | beta | yes |
| `pdf.edit.page_numbers` | edit | stable | yes |
| `pdf.edit.watermark` | edit | stable | yes |
| `pdf.edit.stamp` | edit | beta | yes |
| `pdf.edit.overlay` | edit | beta | yes |
| `pdf.edit.underlay` | edit | beta | yes |
| `pdf.edit.flatten_annotations` | edit | beta | yes |
| `pdf.forms.detect_fields` | forms | beta | yes |
| `pdf.forms.fill` | forms | beta | yes |
| `pdf.forms.export_data` | forms | beta | yes |
| `pdf.forms.import_data` | forms | beta | yes |
| `pdf.forms.flatten` | forms | beta | yes |
| `pdf.forms.create` | forms | beta | yes |
| `pdf.forms.validate` | forms | beta | yes |
| `pdf.security.protect` | security | beta | yes |
| `pdf.security.unlock_authorized` | security | beta | yes |
| `pdf.security.encrypt` | security | beta | yes |
| `pdf.security.decrypt_authorized` | security | beta | yes |
| `pdf.security.permissions` | security | beta | yes |
| `pdf.security.redact` | security | beta | yes |
| `pdf.security.verify_redaction` | security | beta | yes |
| `pdf.security.sign` | security | beta | yes |
| `pdf.security.verify_signature` | security | beta | yes |
| `pdf.security.remove_metadata` | security | beta | yes |
| `pdf.security.sanitize` | security | beta | yes |
| `pdf.security.malware_scan` | security | beta | yes |
| `pdf.ocr_scan.ocr` | ocr_scan | beta | yes |
| `pdf.ocr_scan.searchable_pdf` | ocr_scan | beta | yes |
| `pdf.ocr_scan.deskew` | ocr_scan | beta | yes |
| `pdf.ocr_scan.despeckle` | ocr_scan | beta | yes |
| `pdf.ocr_scan.auto_rotate` | ocr_scan | beta | yes |
| `pdf.ocr_scan.remove_existing_ocr` | ocr_scan | beta | yes |
| `pdf.ocr_scan.scan_to_pdf` | ocr_scan | beta | yes |
| `pdf.ocr_scan.multilingual_ocr` | ocr_scan | beta | yes |
| `pdf.compare.text_diff` | compare | beta | yes |
| `pdf.compare.visual_diff` | compare | beta | yes |
| `pdf.compare.semantic_diff` | compare | beta | yes |
| `pdf.compare.version_report` | compare | beta | yes |
| `pdf.metadata.read` | metadata | stable | yes |
| `pdf.metadata.update` | metadata | stable | yes |
| `pdf.metadata.remove` | metadata | stable | yes |
| `pdf.metadata.read_outline` | metadata | beta | yes |
| `pdf.metadata.update_outline` | metadata | beta | yes |
| `pdf.metadata.read_links` | metadata | beta | yes |
| `pdf.metadata.read_attachments` | metadata | beta | yes |
| `pdf.metadata.page_info` | metadata | beta | yes |
| `pdf.validation.validate_output` | validation | stable | yes |
| `pdf.validation.render_check` | validation | stable | yes |
| `pdf.validation.blank_page_check` | validation | stable | yes |
| `pdf.validation.page_count_check` | validation | beta | yes |
| `pdf.validation.text_layer_check` | validation | beta | yes |
| `pdf.validation.visual_diff` | validation | beta | yes |
| `pdf.validation.redaction_check` | validation | beta | yes |
| `pdf.ai.parse.lite` | ai_parse | beta | yes |
| `pdf.ai.parse.agentic` | ai_parse | cloud_only | no |
| `pdf.ai.parse.layout` | ai_parse | beta | yes |
| `pdf.ai.parse.tables` | ai_parse | beta | yes |
| `pdf.ai.parse.figures` | ai_parse | beta | yes |
| `pdf.ai.parse.formulas` | ai_parse | beta | yes |
| `pdf.ai.parse.charts` | ai_parse | beta | yes |
| `pdf.ai.parse.references` | ai_parse | beta | yes |
| `pdf.ai.rag.ingest` | ai_rag | beta | yes |
| `pdf.ai.rag.chat` | ai_rag | beta | yes |
| `pdf.ai.rag.query` | ai_rag | beta | yes |
| `pdf.ai.rag.search` | ai_rag | beta | yes |
| `pdf.ai.rag.cite_answer` | ai_rag | beta | yes |
| `pdf.ai.rag.highlight_sources` | ai_rag | beta | yes |
| `pdf.ai.rag.export_report` | ai_rag | beta | yes |
| `pdf.ai.extract.schema` | ai_extract | cloud_only | no |
| `pdf.ai.extract.invoice` | ai_extract | cloud_only | no |
| `pdf.ai.extract.contract_terms` | ai_extract | cloud_only | no |
| `pdf.ai.extract.resume` | ai_extract | cloud_only | no |
| `pdf.ai.extract.financial_tables` | ai_extract | cloud_only | no |
| `pdf.ai.extract.research_claims` | ai_extract | cloud_only | no |
| `pdf.ai.extract.action_items` | ai_extract | cloud_only | no |
| `pdf.ai.translate.document` | ai_translate | cloud_only | no |
| `pdf.ai.translate.bilingual_pdf` | ai_translate | cloud_only | no |
| `pdf.ai.translate.with_glossary` | ai_translate | cloud_only | no |
| `pdf.ai.translate.tables` | ai_translate | cloud_only | no |
| `pdf.ai.translate.annotations` | ai_translate | cloud_only | no |
| `pdf.ai.create.from_prompt` | ai_create | beta | yes |
| `pdf.ai.create.template_preview` | ai_create | beta | yes |
| `pdf.ai.create.templates` | ai_create | beta | yes |
| `pdf.ai.create.template_packs` | ai_create | beta | yes |
| `pdf.ai.create.validate_template_pack` | ai_create | beta | yes |
| `pdf.ai.create.plan_template_pack` | ai_create | beta | yes |
| `pdf.ai.create.agent` | ai_create | beta | yes |
| `pdf.ai.create.from_template_pack` | ai_create | beta | yes |
| `pdf.ai.create.report` | ai_create | cloud_only | no |
| `pdf.ai.create.paper` | ai_create | cloud_only | no |
| `pdf.ai.create.resume` | ai_create | cloud_only | no |
| `pdf.ai.create.invoice` | ai_create | beta | yes |
| `pdf.ai.create.contract` | ai_create | cloud_only | no |
| `pdf.ai.create.proposal` | ai_create | cloud_only | no |
| `pdf.ai.create.training_material` | ai_create | cloud_only | no |
| `pdf.ai.create.worksheet` | ai_create | cloud_only | no |
| `pdf.ai.create.research_brief` | ai_create | cloud_only | no |
| `pdf.ai.create.source_report` | ai_create | cloud_only | no |
| `pdf.ai.create.presentation_pdf` | ai_create | cloud_only | no |
| `pdf.ai.create.evidence_packet` | ai_create | cloud_only | no |
| `pdf.ai.edit.rewrite_section` | ai_edit | cloud_only | no |
| `pdf.ai.edit.simplify_language` | ai_edit | cloud_only | no |
| `pdf.ai.edit.formalize` | ai_edit | cloud_only | no |
| `pdf.ai.edit.shorten` | ai_edit | cloud_only | no |
| `pdf.ai.edit.expand` | ai_edit | cloud_only | no |
| `pdf.ai.edit.restyle` | ai_edit | cloud_only | no |
| `pdf.ai.edit.regenerate_page` | ai_edit | cloud_only | no |
| `pdf.ai.edit.convert_style` | ai_edit | cloud_only | no |
| `pdf.ai.review.proofread` | ai_review | cloud_only | no |
| `pdf.ai.review.compliance_check` | ai_review | cloud_only | no |
| `pdf.ai.review.contract_risk_review` | ai_review | cloud_only | no |
| `pdf.ai.review.citation_check` | ai_review | cloud_only | no |
| `pdf.ai.review.consistency_check` | ai_review | cloud_only | no |
| `pdf.ai.review.sensitive_data_detect` | ai_review | beta | yes |
| `pdf.ai.review.accessibility_check` | ai_review | beta | yes |
| `pdf.ai.review.brand_check` | ai_review | cloud_only | no |
