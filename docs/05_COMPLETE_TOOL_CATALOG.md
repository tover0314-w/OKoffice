# 05 — Complete Tool Catalog

This file contains the current machine-aligned compatibility tool map. It must continue to cover every tool in `schemas/tool-manifest.full.json`.

For the okoffice product map, read `docs/38_OKOFFICE_TOOL_TAXONOMY.md` first. That document defines the target `office.*`, `word.*`, `sheet.*`, `deck.*`, and `pdf.*` surface. The table rows below remain the legacy PDF-domain manifest until the registry, CLI, MCP, REST, SDK, schemas, and tests migrate together.

## okoffice Public Taxonomy

The public okoffice surface is organized around artifact types and workflows:

- Cross-format: `office.inspect`, `office.context`, `office.extract`, `office.evidence`, `office.patch`, `office.workflow`, `office.bundle`, `office.agent.setup`.
- Word: `word.inspect`, `word.extract`, `word.create`, `word.patch`, `word.validation`, `word.review`.
- Excel: `sheet.inspect`, `sheet.extract`, `sheet.write`, `sheet.create`, `sheet.patch`, `sheet.validation`, `sheet.review`.
- PowerPoint: `deck.inspect`, `deck.extract`, `deck.compose`, `deck.create`, `deck.patch`, `deck.validation`, `deck.review`.
- PDF: `pdf.inspect`, `pdf.organize`, `pdf.convert`, `pdf.validation`, `pdf.security`, plus compatibility tools already implemented.

Do not treat the current `pdf.*` manifest as the okoffice product boundary.

## okoffice Migration Note

The current manifest contains 262 tools. During the okoffice migration, the `pdf.*` tools remain the compatibility surface while the okoffice beta tools introduce Word, Excel, PowerPoint, validation, bundle, worker, and workflow capabilities.

The target product adds an `office.*` namespace for Word, Excel, PowerPoint, PDF, evidence, validation, bundles, and cross-document workflows. The table sections below now include the implemented okoffice beta wave plus the preserved `pdf.*` compatibility surface.

Target namespace families:

- `office.context`
- `office.source`
- `office.ir`
- `office.word`
- `office.sheet`
- `office.deck`
- `office.pdf`
- `office.extract`
- `office.compose`
- `office.convert`
- `office.patch`
- `office.evidence`
- `office.validation`
- `office.workflow`
- `office.bundle`
- `office.agent.setup`

The compatibility relationship is:

```text
pdf.*          = current implemented PDF domain
office.pdf.*   = future aliases/wrappers over pdf.*
office.*       = target okoffice surface for cross-format workflows
```

Some tools can be `planned` or `cloud_only`, but names that enter the machine manifest should be stable.

## Naming rules

- Use dot namespaces: `pdf.organize.merge`.
- Use verbs that map to agent actions.
- Avoid ambiguous names.
- Keep deterministic tools separate from AI tools.
- Return uniform `ToolResult` for every operation.

## Agent-native families

These namespaces make the larger product shape explicit. Early local releases may implement only schema validation, manifest generation, deterministic subsets, or examples, but the names should be stable from day one.

### `agent.setup`

Generate local runtime configs for agent ecosystems that call the okoffice local server through MCP or REST, while keeping explicit legacy configuration options.

| Tool | Status | Description |
|---|---:|---|
| `agent.setup.claude_code` | beta | Generate a Claude Code project-level MCP config for local okoffice tools. |
| `agent.setup.codex` | beta | Generate a Codex MCP/workspace integration config for local okoffice tools. |
| `agent.setup.kilo_code` | beta | Generate a Kilo Code MCP config for local okoffice tools. |
| `agent.setup.openclaw` | beta | Generate an OpenClaw MCP config for local okoffice tools. |

### okoffice beta tools

Implemented local-first Office tools for the okoffice beta wave.

| Tool | Status | Description |
|---|---:|---|
| `office.inspect.file` | beta | Detect Office artifact format, package health, safety markers, and recommended next tools. |
| `word.inspect.document` | beta | Inspect DOCX structure, paragraphs, headings, tables, comments, styles, sections, and safety markers. |
| `word.validation.document` | beta | Validate DOCX/DOCM package health, comments, tracked changes, metadata, accessibility hints, and render-evidence availability. |
| `word.create.report` | beta | Create an editable Word report from an evidence workbook. |
| `word.patch.plan` | beta | Preview a non-mutating Word patch transaction. |
| `word.patch.apply` | beta | Apply a Word patch transaction to a new DOCX output and validate the result. |
| `sheet.inspect.workbook` | beta | Inspect XLSX sheets, used ranges, tables, formulas, charts, named ranges, comments, hidden content, and external links. |
| `sheet.write.workbook` | beta | Write a validated evidence workbook with source map, data model, and chart plan sheets. |
| `sheet.validation.formulas` | beta | Validate workbook formulas and table/chart/model bindings with local structural checks. |
| `deck.inspect.presentation` | beta | Inspect PPTX slides, text, notes, shapes, placeholders, charts, media references, layouts, and theme metadata. |
| `deck.create.presentation` | beta | Create an editable styled PowerPoint presentation from an evidence workbook. |
| `deck.patch.apply` | beta | Apply a presentation text or theme patch transaction to a new PPTX output. |
| `deck.validation.contact_sheet` | beta | Validate contact-sheet preview availability for PPTX output. |
| `deck.validation.presentation` | beta | Validate PPTX/PPTM structure, titles, notes, media refs, themes, safety markers, and render-evidence availability. |
| `office.context.build_packet` | beta | Build a reusable cross-format context packet and source graph from local Office/PDF sources. |
| `office.extract.schema` | beta | Extract schema-shaped rows from mixed Office/PDF sources with source refs, confidence, and warnings. |
| `office.validation.package` | beta | Validate Office/PDF package structure, unsafe entries, macros, external relationships, and baseline safety markers. |
| `office.workflow.docset_to_sheet` | beta | Turn a local source document set into a validated evidence workbook with context and evidence sidecars. |
| `office.workflow.sheet_to_deck` | beta | Turn an evidence workbook into a validated editable PowerPoint deck with source refs. |
| `office.workflow.board_pack` | beta | Create a validated board pack directory containing evidence workbook, memo, deck, sidecars, optional HTML-first PDF handout, and checksum bundle. |
| `office.workers.status` | beta | Report optional worker contracts, feature flags, dependency availability, license notes, and cloud boundaries. |
| `office.bundle.export` | beta | Export local Office artifacts, manifests, validation reports, and source maps into a portable checksum bundle. |
| `office.bundle.verify` | beta | Verify an okoffice bundle manifest, included artifacts, and SHA-256 checksums. |

### `pdf.context`

Normalize heterogeneous context and create context packets.

| Tool | Status | Description |
|---|---:|---|
| `pdf.context.ingest` | beta | Normalize one PDF, image, audio/video, text, Markdown, HTML, code, CSV/JSON, web link, or data file into an agent context item with local evidence, including hashed transcript sidecar provenance for media. |
| `pdf.context.packet` | beta | Build a reusable Context Packet from raw or pre-ingested local context items with source graph metadata. |
| `pdf.context.build_packet` | beta target | Build a local Context Packet JSON with source graph metadata from text, files, and links. |
| `pdf.context.classify` | beta | Classify context items by type, role, local evidence, safety limits, likely block type, and target slots. |
| `pdf.context.image_analyze` | beta | Analyze local images with metadata and optional OCR text-region evidence. |
| `pdf.context.video_transcribe` | planned/cloud | Transcribe video and create timestamped transcript context/source nodes. |
| `pdf.context.video_keyframes` | planned/cloud | Extract keyframes and frame source refs from video. |
| `pdf.context.audio_transcribe` | planned/cloud | Transcribe audio into timestamped context/source nodes. |
| `pdf.context.web_capture` | beta | Fetch an HTTP/HTTPS page into a `web_link` context item with SSRF-safe local evidence, byte limits, text preview, and source refs. |
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
| `pdf.evidence.cite_claims` | beta | Return local citations for claims using source refs and source-map evidence. |
| `pdf.evidence.coverage_report` | beta target | Report which claims, blocks, tables, and figures have source evidence. |
| `pdf.evidence.highlight_sources` | beta target | Produce highlighted source artifacts from evidence refs. |
| `pdf.evidence.context_packet_report` | beta target | Create a validated PDF/JSON appendix summarizing context items, sources, refs, checksums, evidence, and limitations. |
| `pdf.evidence.verify_citations` | planned/cloud | Verify that generated claims are supported by cited sources. |

### `pdf.compose`

Create new PDF artifacts from context packets, target PDF profiles, composition IR, templates, and style packs.

| Tool | Status | Description |
|---|---:|---|
| `pdf.compose.plan` | beta | Plan a context-to-target-PDF artifact with Composition IR, source refs, validation, render plan, and style constraints. |
| `pdf.compose.from_context` | beta | Compose a validated target PDF from a Context Packet and target profile with source map, evidence coverage, optional HTML package artifacts, local asset manifest, and HTML package validation. |
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
| `pdf.patch.plan` | beta target | Create a structured non-mutating patch manifest for Markdown, code, table, image, slide, citation, media-reference, source-map, template-layer, HTML-layer, and `regenerate_block` evidence. |
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
| `pdf.artifacts.manifest` | beta target | Return artifact metadata, checksums, source refs, HTML package refs, render profile refs, renderer backend refs, HTML layer patch refs, Context Packet refs, validation links, and retention hints. |
| `pdf.artifacts.graph` | beta target | Return parent/child artifact lineage for a workflow or output, including HTML package, render profile, renderer backend, layer, and HTML rerender patch edges. |
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
| `pdf.workflow.createpdf` | beta target | Create a validated PDF from HTML, page JSON, or a Context Packet through a local HTML-first workflow with selectable renderer backend evidence, visual QA, artifact lineage reports, and optional verified portable audit bundle export. |
| `pdf.workflow.research_deck` | beta target | Plan or execute a local research-to-deck workflow from brief and evidence cards through authoring, storyboard, page JSON, HTML package, render, and visual QA steps. |

### Authoring workflow

| Tool | Status | Description |
|---|---:|---|
| `pdf.authoring.plan` | beta | Choose the safest local source format before rendering a new PDF artifact. |
| `pdf.storyboard.plan` | beta | Create a deterministic page-by-page storyboard from a brief and optional evidence cards. |
| `pdf.pages.write` | beta | Convert storyboard pages into page JSON blocks with source footers and design tokens. |
| `pdf.create.html_package` | beta | Write a self-contained local HTML/CSS source package from page JSON, a raw HTML string, or a local HTML file. |
| `pdf.qa.visual_report` | beta | Combine page-count, renderability, blank-page, and authoring/raw HTML package manifest checks for generated PDFs. |
| `pdf.research.plan` | beta | Plan source gathering for an agent-authored PDF without performing network research in the OSS core. |
| `pdf.research.source_cards` | beta | Normalize researched sources into structured source cards for authoring workflows. |
| `pdf.research.evidence_cards` | beta | Turn source cards into evidence cards with claims, confidence, and usable page targets. |
| `pdf.insights.synthesize` | planned | Synthesize source-backed insights behind an explicit model-enabled boundary. |
| `pdf.design.tokens` | beta | Generate or select reusable design tokens for authoring source packages. |
| `pdf.pages.revise` | beta | Revise generated page JSON while preserving source references and validation evidence. |

### `pdf.inspect`

| Tool | Status | Description |
|---|---:|---|
| `pdf.inspect.document` | stable target | Detect page count, sizes, rotations, encryption, metadata, text layer, forms, annotations, attachments, signatures, scanned pages, outlines. |
| `pdf.inspect.pages` | stable target | Return per-page dimensions, rotation, text availability, image count, object count, and renderability. |
| `pdf.inspect.permissions` | beta target | Inspect encryption and usage permissions. |
| `pdf.inspect.health` | beta | Detect corruption, missing xref, malformed objects, huge pages, suspicious attachments, embedded JS. |

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
| `pdf.organize.n_up` | beta | Place multiple source pages on one output page. |
| `pdf.organize.booklet` | beta | Booklet imposition. |
| `pdf.organize.flatten_pages` | beta target | Flatten annotations/forms into page content. |

### `pdf.optimize`

| Tool | Status | Description |
|---|---:|---|
| `pdf.optimize.compress` | stable target | Compress images/streams and reduce file size. |
| `pdf.optimize.linearize` | beta target | Optimize for fast web view. |
| `pdf.optimize.repair` | beta target | Repair xref and malformed objects when possible. |
| `pdf.optimize.web_optimize` | beta target | Rewrite output for web-friendly viewing when safe. |
| `pdf.optimize.downsample_images` | beta target | Downsample embedded images. |
| `pdf.optimize.remove_unused_objects` | beta | Remove unreachable objects by rewriting reachable page-tree content. |
| `pdf.optimize.subset_fonts` | beta | Rewrite PDF and return local font-subset audit evidence. |
| `pdf.optimize.to_pdfa` | beta | Best-effort local PDF/A tagging plus validation report. |
| `pdf.optimize.validate_pdfa` | beta | Validate PDF/A compliance with local heuristic evidence. |

### `pdf.convert.to_pdf`

| Tool | Status | Description |
|---|---:|---|
| `pdf.convert.image_to_pdf` | stable target | Create PDF from images. |
| `pdf.convert.markdown_to_pdf` | stable target | Render Markdown to PDF using templates. |
| `pdf.convert.html_to_pdf` | beta target | Convert local HTML into a validated PDF; the current OSS converter preserves text and emits layout-approximation warnings. |
| `pdf.render.html_package` | beta | Validate a compatibility HTML package manifest, local assets, render profile safety, and requested renderer backend evidence before rendering to a validated PDF or returning structured backend-unavailable evidence. |
| `pdf.convert.url_to_pdf` | beta | Fetch URL with safety checks and convert HTML text to PDF. |
| `pdf.convert.text_to_pdf` | stable target | Plain text to PDF. |
| `pdf.convert.docx_to_pdf` | beta | Convert DOCX text to local PDF. |
| `pdf.convert.pptx_to_pdf` | beta | Convert PPTX slide text to local PDF. |
| `pdf.convert.xlsx_to_pdf` | beta | Convert XLSX rows to local PDF. |

### `pdf.convert.from_pdf`

| Tool | Status | Description |
|---|---:|---|
| `pdf.convert.pdf_to_images` | stable target | Render pages to PNG/JPEG/WebP. |
| `pdf.convert.pdf_to_text` | stable target | Extract text. |
| `pdf.convert.pdf_to_markdown` | beta target | Convert document structure to Markdown. |
| `pdf.convert.pdf_to_json` | beta target | Convert to Document IR JSON. |
| `pdf.convert.pdf_to_html` | beta | Export PDF text to simple HTML. |
| `pdf.convert.pdf_to_docx` | beta | Export PDF text to minimal DOCX. |
| `pdf.convert.pdf_to_pptx` | beta | Export PDF pages to simple text slides. |
| `pdf.convert.pdf_to_xlsx` | beta | Export page text rows to minimal XLSX. |
| `pdf.convert.extract_images` | stable target | Extract embedded images. |
| `pdf.convert.extract_fonts` | beta | Extract/list fonts. |
| `pdf.convert.extract_attachments` | beta target | Extract embedded attachments safely. |

### `pdf.edit`

| Tool | Status | Description |
|---|---:|---|
| `pdf.edit.add_text` | beta target | Add overlay text at coordinates. |
| `pdf.edit.add_image` | beta target | Add image at coordinates. |
| `pdf.edit.add_shape` | beta | Add rectangle/line/circle/freehand. |
| `pdf.edit.add_link` | beta target | Add link annotations. |
| `pdf.edit.add_annotation` | beta target | Add comment/sticky note. |
| `pdf.edit.highlight` | beta target | Highlight text spans or coordinates. |
| `pdf.edit.underline` | beta | Underline text spans or coordinates. |
| `pdf.edit.strikeout` | beta | Strikeout text spans or coordinates. |
| `pdf.edit.freehand_draw` | beta | Add freehand drawing paths. |
| `pdf.edit.crop` | beta target | Crop pages. |
| `pdf.edit.resize_pages` | beta | Resize pages. |
| `pdf.edit.add_margin` | beta | Add margins. |
| `pdf.edit.header_footer` | beta target | Add headers/footers. |
| `pdf.edit.page_numbers` | stable target | Add page numbers. |
| `pdf.edit.watermark` | stable target | Add text/image watermark. |
| `pdf.edit.stamp` | beta target | Add stamp overlays. |
| `pdf.edit.overlay` | beta target | Overlay PDF/page content. |
| `pdf.edit.underlay` | beta | Underlay PDF/page content. |
| `pdf.edit.flatten_annotations` | beta target | Flatten annotations. |

### `pdf.forms`

| Tool | Status | Description |
|---|---:|---|
| `pdf.forms.detect_fields` | beta target | Detect AcroForm fields. |
| `pdf.forms.fill` | beta target | Fill form fields. |
| `pdf.forms.export_data` | beta target | Export form data. |
| `pdf.forms.import_data` | beta | Import local JSON field data into PDF forms. |
| `pdf.forms.flatten` | beta target | Flatten filled forms. |
| `pdf.forms.create` | beta | Create local text form fields. |
| `pdf.forms.validate` | beta | Validate required fields and formats. |

### `pdf.security`

| Tool | Status | Description |
|---|---:|---|
| `pdf.security.protect` | beta | Protect PDF with local password encryption. |
| `pdf.security.unlock_authorized` | beta | Unlock only with supplied authorized password. |
| `pdf.security.encrypt` | beta | Encrypt PDF with local password. |
| `pdf.security.decrypt_authorized` | beta | Decrypt only with supplied authorized password. |
| `pdf.security.permissions` | beta target | Read/update permissions. |
| `pdf.security.redact` | beta | Rasterize local pages and mask explicit redaction regions. |
| `pdf.security.verify_redaction` | beta | Verify supplied terms are absent from redacted PDF text and bytes. |
| `pdf.security.sign` | beta | Detached local integrity signature manifest. |
| `pdf.security.verify_signature` | beta | Verify detached local integrity signature. |
| `pdf.security.remove_metadata` | beta | Remove document metadata through the security namespace. |
| `pdf.security.sanitize` | beta | Remove JS, attachments, external actions, metadata. |
| `pdf.security.malware_scan` | beta | Local static PDF risk marker scan. |

### `pdf.ocr_scan`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ocr_scan.ocr` | beta | Run local OCR and return text regions with page numbers, bboxes, confidence, and language metadata. |
| `pdf.ocr_scan.searchable_pdf` | beta | Generate a searchable PDF by adding a local OCR text layer. |
| `pdf.ocr_scan.deskew` | beta target | Deskew scanned pages. |
| `pdf.ocr_scan.despeckle` | beta | Safe local scan rewrite with despeckle limitation warnings. |
| `pdf.ocr_scan.auto_rotate` | beta target | Detect and rotate pages. |
| `pdf.ocr_scan.remove_existing_ocr` | beta | Best-effort local OCR-layer rewrite. |
| `pdf.ocr_scan.scan_to_pdf` | beta | Images/scans to local image-only PDF. |
| `pdf.ocr_scan.multilingual_ocr` | beta | Record multilingual OCR intent and rewrite local PDF artifact. |

### `pdf.compare`

| Tool | Status | Description |
|---|---:|---|
| `pdf.compare.text_diff` | beta target | Compare text extraction. |
| `pdf.compare.visual_diff` | beta | Local rendered page visual diff with pixel-change evidence. |
| `pdf.compare.semantic_diff` | beta | Local text-layer semantic diff with heuristic change evidence. |
| `pdf.compare.version_report` | beta | Create a local Markdown version comparison report. |

### `pdf.metadata`

| Tool | Status | Description |
|---|---:|---|
| `pdf.metadata.read` | stable target | Read metadata. |
| `pdf.metadata.update` | stable target | Update metadata. |
| `pdf.metadata.remove` | stable target | Remove metadata. |
| `pdf.metadata.read_outline` | beta target | Read bookmarks/outline. |
| `pdf.metadata.update_outline` | beta | Update bookmarks/outline. |
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
| `pdf.validation.visual_diff` | beta | Validate before/after rendered pages with pixel-change thresholds. |
| `pdf.validation.redaction_check` | beta | Validation-grade redaction leak check for supplied terms. |

## AI families

### `pdf.ai.parse`

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.parse.lite` | beta target | Local text-layer + heuristic layout parser. |
| `pdf.ai.parse.agentic` | cloud_only | AI/VLM-backed complex layout parse. |
| `pdf.ai.parse.layout` | beta/cloud | Reading order, blocks, sections. |
| `pdf.ai.parse.tables` | beta/cloud | Table extraction. |
| `pdf.ai.parse.figures` | beta | Local figure caption and image-hint extraction. |
| `pdf.ai.parse.formulas` | beta | Local formula-like text extraction. |
| `pdf.ai.parse.charts` | beta | Local chart caption extraction. |
| `pdf.ai.parse.references` | beta | Local reference, URL, and DOI-like line extraction. |

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
| `pdf.ai.create.from_template_pack` | beta target | Create and validate a PDF from a local template pack entry, color scheme, optional slot-targeted `data.blocks`, or a Context Packet auto-mapped into blocks with a slot routing plan; `renderer=html` also writes an HTML package, asset manifest, and package validation evidence before rendering the PDF. |
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
