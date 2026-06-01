# 05 — Complete Tool Catalog

This is the full public tool map. Some tools can be `planned` or `cloud_only`, but the namespace should be stable.

## Naming rules

- Use dot namespaces: `pdf.organize.merge`.
- Use verbs that map to agent actions.
- Avoid ambiguous names.
- Keep deterministic tools separate from AI tools.
- Return uniform `ToolResult` for every operation.

## Core families

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
| `pdf.security.protect` | stable target | Encrypt/protect PDF with password. |
| `pdf.security.unlock_authorized` | stable target | Decrypt with valid password only. |
| `pdf.security.permissions` | beta target | Read/update permissions. |
| `pdf.security.redact` | beta target | True redaction, not visual cover-up. |
| `pdf.security.verify_redaction` | beta target | Verify text/images are removed. |
| `pdf.security.sign` | planned | Digital signing. |
| `pdf.security.verify_signature` | planned | Verify signatures. |
| `pdf.security.remove_metadata` | stable target | Remove document metadata. |
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
| `pdf.metadata.page_info` | stable target | Page size/rotation/info. |

### `pdf.validation`

| Tool | Status | Description |
|---|---:|---|
| `pdf.validation.validate_output` | stable target | Validate generated PDF. |
| `pdf.validation.render_check` | stable target | Ensure pages render. |
| `pdf.validation.blank_page_check` | stable target | Detect blank or near-blank pages. |
| `pdf.validation.page_count_check` | stable target | Compare expected page counts. |
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

| Tool | Status | Description |
|---|---:|---|
| `pdf.ai.rag.ingest` | beta target | Create local index/chunks. |
| `pdf.ai.rag.query` | beta target | Ask document questions with citations. |
| `pdf.ai.rag.search` | beta target | Search chunks/spans. |
| `pdf.ai.rag.cite_answer` | beta target | Return page/bbox citations. |
| `pdf.ai.rag.highlight_sources` | planned | Produce highlighted source PDF. |
| `pdf.ai.rag.export_report` | planned/cloud | Create Q&A/source report PDF. |

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
| `pdf.ai.create.from_prompt` | cloud_only | Generate PDF from prompt. |
| `pdf.ai.create.report` | beta/cloud | Create business report. |
| `pdf.ai.create.paper` | planned/cloud | Create academic paper format. |
| `pdf.ai.create.resume` | beta/cloud | Create resume. |
| `pdf.ai.create.invoice` | beta target | Template invoice. |
| `pdf.ai.create.contract` | planned/cloud | Contract template. |
| `pdf.ai.create.proposal` | planned/cloud | Proposal. |
| `pdf.ai.create.training_material` | planned/cloud | Training/education materials. |
| `pdf.ai.create.worksheet` | planned/cloud | Education worksheet. |
| `pdf.ai.create.research_brief` | planned/cloud | Research brief. |

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
