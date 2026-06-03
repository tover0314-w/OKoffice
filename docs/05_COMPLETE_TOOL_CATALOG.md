# 05 — Complete Tool Catalog

This is the full public tool map. Some tools can be `planned` or `cloud_only`, but the namespace should be stable.

## Naming rules

- Use dot namespaces: `pdf.organize.merge`.
- Use verbs that map to agent actions.
- Avoid ambiguous names.
- Keep deterministic tools separate from AI tools.
- Return uniform `ToolResult` for every operation.

## Agent-native families

These namespaces make the larger product shape explicit. Early local releases may implement only schema validation, manifest generation, deterministic subsets, or examples, but the names should be stable from day one.

### `agent.setup`

Generate local runtime configs for agent ecosystems that call okpdf through MCP or REST.

| Tool | Status | Description |
|---|---:|---|
| `agent.setup.claude_code` | beta | Generate a Claude Code project-level MCP config for local okpdf tools. |
| `agent.setup.codex` | beta | Generate a Codex MCP/workspace integration config for local okpdf tools. |
| `agent.setup.kilo_code` | planned | Generate Kilo Code integration config. |
| `agent.setup.openclaw` | planned | Generate OpenClaw integration config. |

### `pdf.context`

Normalize heterogeneous context and create context packets.

| Tool | Status | Description |
|---|---:|---|
| `pdf.context.ingest` | beta | Normalize one PDF, image, audio/video, text, Markdown, HTML, code, CSV/JSON, web link, or data file into an agent context item with local evidence. |
| `pdf.context.packet` | beta | Build a reusable Context Packet from raw or pre-ingested local context items with source graph metadata. |
| `pdf.context.build_packet` | beta target | Build a local Context Packet JSON with source graph metadata from text, files, and links. |
| `pdf.context.classify` | beta | Classify context items by type, role, local evidence, safety limits, likely block type, and target slots. |
| `pdf.context.image_analyze` | planned/cloud | OCR/caption/image-region analysis for images and screenshots. |
| `pdf.context.video_transcribe` | planned/cloud | Transcribe video and create timestamped transcript context/source nodes. |
| `pdf.context.video_keyframes` | planned/cloud | Extract keyframes and frame source refs from video. |
| `pdf.context.audio_transcribe` | planned/cloud | Transcribe audio into timestamped context/source nodes. |
| `pdf.context.web_capture` | planned/cloud | Capture web links/pages with source refs and SSRF-safe fetching. |
| `pdf.context.code_snapshot` | beta | Create context and source refs for files, line ranges, dependency hints, and repository metadata. |
| `pdf.context.data_profile` | beta | Profile CSV/TSV/JSON/JSONL/XLSX data for report generation. |

### `pdf.target`

Choose and validate the intended PDF output type before composition.

| Tool | Status | Description |
|---|---:|---|
| `pdf.target.profiles` | beta | List built-in target PDF profiles, layout slots, accepted block types, and accepted context types. |
| `pdf.target.validate_profile` | beta | Validate required structure, style pack, layout mode, slots, and checks for a custom target profile. |
| `pdf.target.select_profile` | beta | Select a target PDF profile such as learning, resume, paper, deck, report, packet, or audit using deterministic local scoring. |

### `pdf.evidence`

Map generated content and answers back to source material. RAG is one implementation path; evidence is the broader product layer.

| Tool | Status | Description |
|---|---:|---|
| `pdf.evidence.map_sources` | beta | Normalize block or claim source refs against Context Packet evidence into a source-map report. |
| `pdf.evidence.cite_claims` | beta target | Return citations for claims using page/bbox/timestamp/file/row refs. |
| `pdf.evidence.coverage_report` | beta target | Report which claims, blocks, tables, and figures have source evidence. |
| `pdf.evidence.highlight_sources` | beta target | Produce highlighted source artifacts from evidence refs. |
| `pdf.evidence.context_packet_report` | beta target | Create a validated PDF/JSON appendix summarizing context items, sources, refs, checksums, evidence, and limitations. |
| `pdf.evidence.verify_citations` | planned/cloud | Verify that generated claims are supported by cited sources. |

### `pdf.compose`

Create new PDF artifacts from context packets, target PDF profiles, composition IR, templates, and style packs.

| Tool | Status | Description |
|---|---:|---|
| `pdf.compose.plan` | beta | Plan a context-to-target-PDF artifact with Composition IR, source refs, validation, render plan, and style constraints. |
| `pdf.compose.from_context` | beta | Compose a validated target PDF from a Context Packet and target profile with source map and evidence coverage. |
| `pdf.compose.render_ir` | beta | Render a composition plan or IR payload into a validated PDF artifact. |
| `pdf.compose.add_code_block` | beta target | Append a code evidence page to a new PDF with source refs, patch evidence, rollback metadata, and validation. |
| `pdf.compose.add_figure` | beta target | Append an image/figure evidence page to a new PDF with captions, source refs, patch evidence, rollback metadata, and validation. |
| `pdf.compose.add_table` | beta target | Append a structured table evidence page to a new PDF with source refs, patch evidence, rollback metadata, and validation. |
| `pdf.compose.add_appendix` | beta target | Append a Markdown appendix page to a new PDF with source refs, patch evidence, rollback metadata, and validation. |
| `pdf.compose.add_citation` | beta target | Append a citation evidence page to a new PDF with source refs, local citation metadata, patch evidence, rollback metadata, and validation. |
| `pdf.compose.add_media_reference` | beta target | Append an audio, video, or media reference evidence page to a new PDF with local media metadata, source refs, patch evidence, rollback metadata, and validation. |
| `pdf.compose.add_slide` | beta target | Append a slide-like evidence page to a new PDF with source refs, patch evidence, rollback metadata, and validation. |
| `pdf.compose.compile_packet` | planned/cloud | Compile multi-source evidence packets with source maps and validation. |

### `pdf.patch`

Represent agent edits as explicit patch transactions instead of opaque in-place mutations.

| Tool | Status | Description |
|---|---:|---|
| `pdf.patch.plan` | beta target | Create a structured append-only patch manifest for Markdown, code, table, image, slide, citation, media-reference, source-map, template-layer, and `regenerate_block` evidence. |
| `pdf.patch.preview` | beta target | Preview patch effects and validation requirements without mutating the input. |
| `pdf.patch.apply` | beta target | Apply a patch transaction and write a new PDF artifact. |
| `pdf.patch.verify` | beta target | Verify a patched PDF against the patch manifest. |
| `pdf.patch.rollback_manifest` | beta target | Produce rollback metadata and input artifact refs. |
| `pdf.patch.regenerate_section` | planned/cloud | Regenerate a section or page from IR with source refs and validation. |

### `pdf.present`

Generate slide-like PDF artifacts for reports, briefings, teaching, sales, and research.

| Tool | Status | Description |
|---|---:|---|
| `pdf.present.create_deck` | beta/cloud | Create a slide-like PDF deck from a context packet, target PDF profile, or composition IR. |
| `pdf.present.report_to_deck` | planned/cloud | Convert a report into concise presentation pages. |
| `pdf.present.video_to_deck` | planned/cloud | Turn video transcript/keyframes into a presentation PDF. |
| `pdf.present.paper_to_deck` | planned/cloud | Turn a paper into a cited research presentation PDF. |
| `pdf.present.speaker_notes` | planned/cloud | Generate speaker notes tied to slide pages and sources. |
| `pdf.present.handout` | beta target | Render a deck-like PDF into a printable handout/appendix format. |

### `pdf.artifacts`

Inspect artifact lineage and manifests.

| Tool | Status | Description |
|---|---:|---|
| `pdf.artifacts.manifest` | beta target | Return artifact metadata, checksums, source refs, validation links, and retention hints. |
| `pdf.artifacts.graph` | beta target | Return parent/child artifact lineage for a workflow or output. |
| `pdf.artifacts.source_map` | beta target | Return generated PDF block/page refs mapped back to sources. |
| `pdf.artifacts.export_bundle` | beta/local | Export PDF, manifests, validations, source maps, and reports as a portable audit ZIP with checksums. |
| `pdf.artifacts.verify_bundle` | beta/local | Verify a portable audit ZIP manifest, entries, and SHA-256 checksums before downstream agent use. |

## Core families

### `pdf.workflow`

| Tool | Status | Description |
|---|---:|---|
| `pdf.workflow.plan` | beta target | Plan a local-first agent workflow with roles, steps, validation, and cloud boundary. |
| `pdf.workflow.run` | beta target | Execute a local workflow manifest and return per-step evidence. |
| `pdf.workflow.report` | beta target | Summarize workflow artifacts, warnings, validation, and step evidence. |

### `pdf.inspect`

| Tool | Status | Description |
|---|---:|---|
| `pdf.inspect.document` | stable target | Detect page count, sizes, rotations, encryption, metadata, text layer, forms, annotations, attachments, signatures, scanned pages, outlines. |
| `pdf.inspect.pages` | stable target | Return per-page dimensions, rotation, text availability, image count, object count, and renderability. |
| `pdf.inspect.permissions` | beta target | Inspect encryption and usage permissions. |
| `pdf.inspect.health` | beta target | Detect corruption, missing xref, malformed objects, huge pages, suspicious attachments, embedded JS. |

### `pdf.organize`

| Tool | Status | Description |
|---|---:|---|
| `pdf.organize.merge` | stable target | Merge multiple PDFs. |
| `pdf.organize.split` | stable target | Split PDF by page ranges, every N pages, bookmarks, or file size target. |
| `pdf.organize.extract_pages` | stable target | Extract specific pages into a new PDF. |
| `pdf.organize.remove_pages` | stable target | Remove pages. |
| `pdf.organize.reorder_pages` | stable target | Reorder pages. |
| `pdf.organize.rotate_pages` | stable target | Rotate pages. |
| `pdf.organize.duplicate_pages` | beta target | Duplicate one or more pages. |
| `pdf.organize.insert_blank_pages` | beta target | Insert blank pages. |
| `pdf.organize.insert_pdf` | beta target | Insert one PDF into another at specific positions. |
| `pdf.organize.n_up` | planned | Place multiple source pages on one output page. |
| `pdf.organize.booklet` | planned | Booklet imposition. |
| `pdf.organize.flatten_pages` | beta target | Flatten annotations/forms into page content. |

### `pdf.optimize`

| Tool | Status | Description |
|---|---:|---|
| `pdf.optimize.compress` | stable target | Compress images/streams and reduce file size. |
| `pdf.optimize.linearize` | beta target | Optimize for fast web view. |
| `pdf.optimize.repair` | beta target | Repair xref and malformed objects when possible. |
| `pdf.optimize.web_optimize` | beta target | Rewrite output for web-friendly viewing when safe. |
| `pdf.optimize.downsample_images` | beta target | Downsample embedded images. |
| `pdf.optimize.remove_unused_objects` | planned | Remove unreachable objects. |
| `pdf.optimize.subset_fonts` | planned | Subset embedded fonts when safe. |
| `pdf.optimize.to_pdfa` | planned | Convert to PDF/A where possible. |
| `pdf.optimize.validate_pdfa` | planned | Validate PDF/A compliance. |

### `pdf.convert.to_pdf`

| Tool | Status | Description |
|---|---:|---|
| `pdf.convert.image_to_pdf` | stable target | Create PDF from images. |
| `pdf.convert.markdown_to_pdf` | stable target | Render Markdown to PDF using templates. |
| `pdf.convert.html_to_pdf` | beta target | Render HTML/CSS to PDF. |
| `pdf.convert.url_to_pdf` | planned | Render URL to PDF with SSRF-safe fetch. |
| `pdf.convert.text_to_pdf` | stable target | Plain text to PDF. |
| `pdf.convert.docx_to_pdf` | planned | Office conversion, likely optional worker. |
| `pdf.convert.pptx_to_pdf` | planned | Office conversion, likely optional worker. |
| `pdf.convert.xlsx_to_pdf` | planned | Office conversion, likely optional worker. |

### `pdf.convert.from_pdf`

| Tool | Status | Description |
|---|---:|---|
| `pdf.convert.pdf_to_images` | stable target | Render pages to PNG/JPEG/WebP. |
| `pdf.convert.pdf_to_text` | stable target | Extract text. |
| `pdf.convert.pdf_to_markdown` | beta target | Convert document structure to Markdown. |
| `pdf.convert.pdf_to_json` | beta target | Convert to Document IR JSON. |
| `pdf.convert.pdf_to_html` | planned | Convert to HTML approximation. |
| `pdf.convert.pdf_to_docx` | planned/cloud | Convert to DOCX. |
| `pdf.convert.pdf_to_pptx` | planned/cloud | Convert to PPTX. |
| `pdf.convert.pdf_to_xlsx` | planned/cloud | Extract tables to XLSX. |
| `pdf.convert.extract_images` | stable target | Extract embedded images. |
| `pdf.convert.extract_fonts` | planned | Extract/list fonts. |
| `pdf.convert.extract_attachments` | beta target | Extract embedded attachments safely. |

### `pdf.edit`

| Tool | Status | Description |
|---|---:|---|
| `pdf.edit.add_text` | beta target | Add overlay text at coordinates. |
| `pdf.edit.add_image` | beta target | Add image at coordinates. |
| `pdf.edit.add_shape` | planned | Add rectangle/line/circle/freehand. |
| `pdf.edit.add_link` | beta target | Add link annotations. |
| `pdf.edit.add_annotation` | beta target | Add comment/sticky note. |
| `pdf.edit.highlight` | beta target | Highlight text spans or coordinates. |
| `pdf.edit.underline` | planned | Underline text spans or coordinates. |
| `pdf.edit.strikeout` | planned | Strikeout text spans or coordinates. |
| `pdf.edit.freehand_draw` | planned | Add freehand drawing paths. |
| `pdf.edit.crop` | beta target | Crop pages. |
| `pdf.edit.resize_pages` | planned | Resize pages. |
| `pdf.edit.add_margin` | planned | Add margins. |
| `pdf.edit.header_footer` | beta target | Add headers/footers. |
| `pdf.edit.page_numbers` | stable target | Add page numbers. |
| `pdf.edit.watermark` | stable target | Add text/image watermark. |
| `pdf.edit.stamp` | beta target | Add stamp overlays. |
| `pdf.edit.overlay` | beta target | Overlay PDF/page content. |
| `pdf.edit.underlay` | planned | Underlay PDF/page content. |
| `pdf.edit.flatten_annotations` | beta target | Flatten annotations. |

### `pdf.forms`

| Tool | Status | Description |
|---|---:|---|
| `pdf.forms.detect_fields` | beta target | Detect AcroForm fields. |
| `pdf.forms.fill` | beta target | Fill form fields. |
| `pdf.forms.export_data` | beta target | Export form data. |
| `pdf.forms.import_data` | planned | Import form data. |
| `pdf.forms.flatten` | beta target | Flatten filled forms. |
| `pdf.forms.create` | planned | Create form fields. |
| `pdf.forms.validate` | planned | Validate required fields and formats. |

### `pdf.security`

| Tool | Status | Description |
|---|---:|---|
| `pdf.security.protect` | planned | Encrypt/protect PDF with password. |
| `pdf.security.unlock_authorized` | planned | Decrypt with valid password only. |
| `pdf.security.encrypt` | planned | Encrypt PDF. |
| `pdf.security.decrypt_authorized` | planned | Decrypt authorized PDF with a valid password only. |
| `pdf.security.permissions` | beta target | Read/update permissions. |
| `pdf.security.redact` | beta target | True redaction, not visual cover-up. |
| `pdf.security.verify_redaction` | beta target | Verify text/images are removed. |
| `pdf.security.sign` | planned | Digital signing. |
| `pdf.security.verify_signature` | planned | Verify signatures. |
| `pdf.security.remove_metadata` | beta | Remove document metadata through the security namespace. |
| `pdf.security.sanitize` | beta target | Remove JS, attachments, external actions, metadata. |
| `pdf.security.malware_scan` | planned/cloud | Integrate scanning worker. |

### `pdf.ocr_scan`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ocr_scan.ocr` | beta target | Add OCR text layer. |
| `pdf.ocr_scan.searchable_pdf` | beta target | Generate searchable PDF. |
| `pdf.ocr_scan.deskew` | beta target | Deskew scanned pages. |
| `pdf.ocr_scan.despeckle` | planned | Remove speckles/noise. |
| `pdf.ocr_scan.auto_rotate` | beta target | Detect and rotate pages. |
| `pdf.ocr_scan.remove_existing_ocr` | planned | Remove OCR layer when needed. |
| `pdf.ocr_scan.scan_to_pdf` | planned | Images/scans to OCR PDF. |
| `pdf.ocr_scan.multilingual_ocr` | planned/cloud | Multi-language OCR. |

### `pdf.compare`

| Tool | Status | Description |
|---|---:|---|
| `pdf.compare.text_diff` | beta target | Compare text extraction. |
| `pdf.compare.visual_diff` | beta target | Rendered page visual diff. |
| `pdf.compare.semantic_diff` | planned/cloud | AI-assisted semantic diff. |
| `pdf.compare.version_report` | planned | Create version comparison report. |

### `pdf.metadata`

| Tool | Status | Description |
|---|---:|---|
| `pdf.metadata.read` | stable target | Read metadata. |
| `pdf.metadata.update` | stable target | Update metadata. |
| `pdf.metadata.remove` | stable target | Remove metadata. |
| `pdf.metadata.read_outline` | beta target | Read bookmarks/outline. |
| `pdf.metadata.update_outline` | planned | Update bookmarks/outline. |
| `pdf.metadata.read_links` | beta target | Read links. |
| `pdf.metadata.read_attachments` | beta target | Read attachments. |
| `pdf.metadata.page_info` | beta | Page size/rotation/info. |

### `pdf.validation`

| Tool | Status | Description |
|---|---:|---|
| `pdf.validation.validate_output` | stable target | Validate generated PDF. |
| `pdf.validation.render_check` | stable target | Ensure pages render. |
| `pdf.validation.blank_page_check` | stable target | Detect blank or near-blank pages. |
| `pdf.validation.page_count_check` | beta | Compare expected page counts. |
| `pdf.validation.text_layer_check` | beta target | Check text extraction. |
| `pdf.validation.visual_diff` | beta target | Compare before/after render. |
| `pdf.validation.redaction_check` | beta target | Verify redaction. |

## AI families

### `pdf.ai.parse`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.parse.lite` | beta target | Local text-layer + heuristic layout parser. |
| `pdf.ai.parse.agentic` | cloud_only | AI/VLM-backed complex layout parse. |
| `pdf.ai.parse.layout` | beta/cloud | Reading order, blocks, sections. |
| `pdf.ai.parse.tables` | beta/cloud | Table extraction. |
| `pdf.ai.parse.figures` | planned/cloud | Figure detection and captions. |
| `pdf.ai.parse.formulas` | planned/cloud | Formula extraction. |
| `pdf.ai.parse.charts` | planned/cloud | Chart understanding. |
| `pdf.ai.parse.references` | planned/cloud | Research references extraction. |

### `pdf.ai.rag`

RAG tools are useful evidence helpers, but the broader product layer is `pdf.evidence`.

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.rag.ingest` | beta target | Create local index/chunks. |
| `pdf.ai.rag.chat` | beta target | One-shot local PDF question answering with citations, report, and highlights. |
| `pdf.ai.rag.query` | beta target | Ask document questions with citations. |
| `pdf.ai.rag.search` | beta target | Search chunks/spans. |
| `pdf.ai.rag.cite_answer` | beta target | Return page/bbox citations. |
| `pdf.ai.rag.highlight_sources` | beta target | Produce highlighted source PDF from local RAG citations. |
| `pdf.ai.rag.export_report` | beta target | Create cited Q&A/source PDF report from a local RAG index. |

### `pdf.ai.extract`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.extract.schema` | beta/cloud | Extract structured fields by schema. |
| `pdf.ai.extract.invoice` | planned/cloud | Invoice extraction. |
| `pdf.ai.extract.contract_terms` | planned/cloud | Contract terms extraction. |
| `pdf.ai.extract.resume` | planned/cloud | Resume extraction. |
| `pdf.ai.extract.financial_tables` | planned/cloud | Financial table extraction. |
| `pdf.ai.extract.research_claims` | planned/cloud | Research claim extraction. |
| `pdf.ai.extract.action_items` | planned/cloud | Action items extraction. |

### `pdf.ai.translate`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.translate.document` | cloud_only | Translate PDF. |
| `pdf.ai.translate.bilingual_pdf` | cloud_only | Create bilingual PDF. |
| `pdf.ai.translate.with_glossary` | cloud_only | Glossary-aware translation. |
| `pdf.ai.translate.tables` | cloud_only | Table-aware translation. |
| `pdf.ai.translate.annotations` | cloud_only | Translate annotations. |

### `pdf.ai.create`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.create.from_prompt` | beta target | Local prompt-to-template PDF creation with validation. |
| `pdf.ai.create.template_preview` | beta target | Generate and validate a local preview PDF for a creation template. |
| `pdf.ai.create.templates` | beta target | List local creation templates, style packs, and color keys. |
| `pdf.ai.create.template_packs` | beta target | List reusable local template packs with templates, fields, target profiles, supported block types, and color schemes. |
| `pdf.ai.create.validate_template_pack` | beta target | Validate a local template pack contract, including layout slots and supported agent blocks. |
| `pdf.ai.create.plan_template_pack` | beta target | Recommend a local template-pack create payload from a target profile and Context Packet. |
| `pdf.ai.create.agent` | beta target | Run the local create agent: plan a template, classify Context Packet routing, create the PDF, write a Context Packet report, render-check, blank-check, write coverage evidence, and optionally export/verify an audit bundle. |
| `pdf.ai.create.from_template_pack` | beta target | Create and validate a PDF from a local template pack entry, color scheme, optional slot-targeted `data.blocks`, or a Context Packet auto-mapped into blocks with a slot routing plan. |
| `pdf.ai.create.report` | beta/cloud | Dedicated report creation endpoint; local report templates are available through `pdf.ai.create.from_prompt`. |
| `pdf.ai.create.paper` | planned/cloud | Create academic paper format. |
| `pdf.ai.create.resume` | beta/cloud | Dedicated resume endpoint; local structured resume templates are available through `pdf.ai.create.from_prompt`. |
| `pdf.ai.create.invoice` | beta target | Dedicated invoice endpoint; local structured invoice templates are available through `pdf.ai.create.from_prompt`. |
| `pdf.ai.create.contract` | planned/cloud | Contract template. |
| `pdf.ai.create.proposal` | planned/cloud | Dedicated proposal endpoint; local proposal templates are available through `pdf.ai.create.from_prompt`. |
| `pdf.ai.create.training_material` | planned/cloud | Training/education materials. |
| `pdf.ai.create.worksheet` | planned/cloud | Dedicated worksheet endpoint; local worksheet templates are available through `pdf.ai.create.from_prompt`. |
| `pdf.ai.create.research_brief` | planned/cloud | Dedicated research brief endpoint; local research brief templates are available through `pdf.ai.create.from_prompt`. |
| `pdf.ai.create.source_report` | planned/cloud | Generate a source-backed report from multimodal inputs. |
| `pdf.ai.create.presentation_pdf` | planned/cloud | Generate a slide-like PDF presentation with citations and speaker notes. |
| `pdf.ai.create.evidence_packet` | planned/cloud | Generate a review packet with sources, claims, and verification reports. |

### `pdf.ai.edit`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.edit.rewrite_section` | cloud_only | Rewrite content and regenerate page/document. |
| `pdf.ai.edit.simplify_language` | cloud_only | Simplify content. |
| `pdf.ai.edit.formalize` | cloud_only | Formal tone conversion. |
| `pdf.ai.edit.shorten` | cloud_only | Shorten content. |
| `pdf.ai.edit.expand` | cloud_only | Expand content. |
| `pdf.ai.edit.restyle` | cloud_only | Change visual style. |
| `pdf.ai.edit.regenerate_page` | cloud_only | Regenerate page from IR. |
| `pdf.ai.edit.convert_style` | cloud_only | Convert document to style pack. |

### `pdf.ai.review`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.review.proofread` | cloud_only | Proofread document. |
| `pdf.ai.review.compliance_check` | cloud_only | Compliance review. |
| `pdf.ai.review.contract_risk_review` | cloud_only | Contract risk review. |
| `pdf.ai.review.citation_check` | cloud_only | Citation verification. |
| `pdf.ai.review.consistency_check` | cloud_only | Check consistency. |
| `pdf.ai.review.sensitive_data_detect` | beta/cloud | Detect sensitive info. |
| `pdf.ai.review.accessibility_check` | beta target | Accessibility baseline. |
| `pdf.ai.review.brand_check` | cloud_only | Brand/style compliance. |
