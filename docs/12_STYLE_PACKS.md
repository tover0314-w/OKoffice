# 12 — PDF Creation and Style Packs

## Goal

AgentPDF should generate polished PDFs from many context types into clear target PDF profiles.

Context inputs may include PDFs, images, screenshots, scans, video, audio, web links, Markdown, HTML, Office-like documents, code, spreadsheets, JSON, databases, prompts, and review notes.

Target PDF profiles include:

- Business reports.
- Consulting reports.
- Academic papers.
- Learning PDFs.
- PPT/deck-like PDFs.
- Research briefs.
- Resumes.
- Invoices.
- Contracts.
- Product datasheets.
- Training materials.
- Education worksheets.
- Startup pitch handouts.
- Annual reports.
- Financial reports.
- Government/formal documents.
- Evidence packets.
- Code audit reports.
- Slide-like presentation PDFs.
- Video-derived handouts.
- Image review packets.

## Style pack schema

A style pack defines layout, fonts, colors, spacing, components, and document structure for one or more target PDF profiles.

```json
{
  "style_id": "business_report_modern",
  "name": "Business Report Modern",
  "description": "Clean board-report style with executive summary and metric cards.",
  "page": {
    "size": "A4",
    "orientation": "portrait",
    "margins": {"top": 56, "right": 56, "bottom": 56, "left": 56}
  },
  "typography": {
    "heading_font": "system-sans",
    "body_font": "system-sans",
    "base_size": 10
  },
  "components": [
    "cover",
    "toc",
    "section_header",
    "metric_card",
    "table",
    "figure",
    "code_block",
    "callout",
    "citation_list",
    "source_appendix",
    "appendix"
  ]
}
```

Style packs should support both classic document pages and slide-like pages. A style pack may define multiple layout modes:

- `report`
- `packet`
- `deck`
- `handout`
- `appendix`
- `paper`
- `resume`
- `learning`

## Rich block requirements

Agent-native composition requires blocks that are more expressive than Markdown paragraphs:

- Code blocks with language labels, file/line source refs, wrapping behavior, and overflow warnings.
- Figures and images with captions, crop/fill rules, and source refs.
- Tables with source ranges, column sizing, and numeric consistency checks.
- Charts with data source refs and image fallbacks.
- Callouts for risks, decisions, evidence, warnings, and limitations.
- Citation lists and source appendices.
- Speaker notes for slide-like PDFs.
- Review comments and approval markers for enterprise workflows.

If a block cannot fit safely, rendering should produce layout warnings rather than silently clipping important content.

## Open-source style packs

Implemented local built-in packs:

- `plain_report`
- `business_report_modern`
- `academic_paper_basic`
- `resume_modern`
- `invoice_clean`
- `paper_ink`

Planned gallery packs:

- `resume_classic`
- `contract_plain`
- `research_brief`
- `training_handout`
- `education_worksheet`
- `board_deck`
- `technical_audit`
- `evidence_packet`
- `training_slide_handout`

`pdf.convert.markdown_to_pdf` also accepts a local JSON style pack path, which lets users and agents supply custom margins, page size/orientation, typography, colors, and components without waiting for the hosted template gallery.

## Local create-agent templates

`pdf.ai.create.templates` lists the local template catalog for agents. It includes field contracts, layout slots, sample data, and the preview tool id for each template. `pdf.ai.create.template_preview` generates a real validated preview PDF from that sample data. `pdf.ai.create.from_prompt` is the local template creation agent. It chooses or accepts a template, applies optional color overrides, renders Markdown, creates a PDF with a style pack, and validates the output.

`pdf.ai.create.template_packs` adds the reusable package layer. A template pack is a local JSON file that groups template entries, base template ids, target profiles, field contracts, layout slots, supported block types, sample data, and named color schemes. Agents should validate packs with `pdf.ai.create.validate_template_pack` before calling `pdf.ai.create.from_template_pack`. This keeps the OSS core ready for future hosted template galleries while staying local and license-safe.

Implemented templates:

- `one_pager`
- `business_report`
- `research_brief`
- `proposal`
- `worksheet`
- `resume`
- `invoice`

Implemented template pack example:

- `examples/template-packs/local-agent-starter.json`

Implemented local starter templates:

- `board_audit`: technical audit / leadership packet.
- `research_brief_packet`: cited research brief.
- `evidence_packet`: source-backed evidence packet.
- `agent_resume`: ATS-friendly resume PDF.
- `client_invoice`: clean invoice PDF.
- `project_proposal`: scoped project proposal.
- `lesson_worksheet`: training worksheet.
- `media_review_deck`: slide-like media review PDF.

Template pack example:

```bash
okpdf create template-packs -o .agentpdf-out/template-packs.json --json
okpdf create validate-template-pack examples/template-packs/local-agent-starter.json \
  -o .agentpdf-out/template-pack.validation.json \
  --json
okpdf create plan-template-pack examples/template-packs/local-agent-starter.json \
  --target-profile technical_audit \
  --context-packet context.packet.json \
  --planned-output .agentpdf-out/board-audit.pdf \
  -o .agentpdf-out/board-audit.plan.json \
  --json
okpdf create agent examples/template-packs/local-agent-starter.json \
  --target-profile technical_audit \
  --context-packet context.packet.json \
  -o .agentpdf-out/board-audit.pdf \
  --plan-output .agentpdf-out/board-audit.plan.json \
  --coverage-output .agentpdf-out/board-audit.coverage.json \
  --context-classification-output .agentpdf-out/board-audit.context-classification.json \
  --context-report-output .agentpdf-out/board-audit.context-report.pdf \
  --context-report-json-output .agentpdf-out/board-audit.context-report.json \
  --bundle-output .agentpdf-out/board-audit.agentpdf-bundle.zip \
  --json
okpdf create from-template-pack examples/template-packs/local-agent-starter.json \
  --template board_audit \
  --color-scheme executive_blue \
  --data examples/create-data/agent-block-audit.json \
  -o .agentpdf-out/board-audit.pdf \
  --json
okpdf evidence coverage-report .agentpdf-out/board-audit.composition.json \
  -o .agentpdf-out/board-audit.coverage.json \
  --json
```

`pdf.ai.create.plan_template_pack` is the local create-agent planning step for template packs. It ranks candidate templates from the target profile and Context Packet, then returns `create_payload`, `preview_payload`, candidate scores, matched/unsupported block types, and validation requirements. `pdf.ai.create.agent` runs that plan through Context Packet classification, Context Packet report generation, PDF creation, render-check, blank-page check, evidence coverage, and optional bundle export/verification in one local call. `pdf.ai.create.from_template_pack` writes the PDF plus sibling `.composition.json` and `.layers.json` artifacts. The composition artifact includes `composition_ir`, `source_map`, `evidence_coverage`, `slot_routing_plan`, the selected `target_profile`, and template pack metadata so agents can immediately run coverage reports and patch planning against generated template outputs. The layer manifest validates against `schemas/template-layer-manifest.schema.json` and gives each block a stable layer id, target slot, source refs, source kinds, estimated normalized-page anchor, and edit policy. `pdf.patch.plan` can consume this file through `--layers` / `layer_manifest_path`; operations may cite `layer_id`, `block_id`, or `target_slot`, and the patch manifest records matched `layer_evidence`. Layer edit policies are enforced during planning: matched layers must be editable and the requested patch operation must map to an allowed operation such as `append_to_slot`, `annotate`, or `regenerate_block`. The local `regenerate_block` operation uses those layer refs plus `replacement_markdown` to append an audited regenerated block appendix to a new PDF artifact; it does not claim in-place layout-preserving edits or mutate the original block. When `data.blocks` is supplied, each block keeps its own `block_id`, `type`, `target_slot`, and `source_refs`; supported block types are `section`, `code`, `table`, `image`, `slide`, `audio_reference`, `video_reference`, `media_reference`, and `citation`. Agents can pass `--context-packet` / `context_packet_path` instead of hand-writing blocks; okpdf maps context text, code, tables, images, web links, PDFs, and media into target-profile-aware template blocks while preserving packet source refs. Document profiles route media to `audio_reference`, `video_reference`, or `media_reference` slots such as `media_evidence`; slide profiles can keep media as slide blocks. The slot routing plan records route ids, accepted/warning status, supported block type checks, slot-known facts, target profile compatibility, candidate target-profile slots, and routing reasons for every generated block. Image blocks validate the referenced local file and store `image_evidence` with width, height, and MIME type; Context Packet image items additionally carry `visual_evidence` with aspect ratio, average color, non-white ratio, blank detection, and perceptual hash.

Structured renderers:

- `invoice`: `invoice_number`, `client` or `bill_to`, `due_date`, `items[]`, `payment_notes`, `total`.
- `resume`: `name`, `headline`, `contact`, `summary`, `skills[]`, `experience[]`.
- `worksheet`: `learning_goal`, `questions[]`, `checklist[]`.
- `proposal`: `client`, `problem`, `approach`, `deliverables`, `timeline`.

Preview example:

```bash
okpdf create preview invoice \
  -o .agentpdf-out/invoice-preview.pdf \
  --json
```

Example:

```bash
okpdf create from-prompt "Create a worksheet about validating generated PDFs." \
  -o .agentpdf-out/worksheet.pdf \
  --template worksheet \
  --style-pack paper_ink \
  --color primary=#4f46e5 \
  --color accent=#f59e0b \
  --json
```

Invoice data example:

```bash
okpdf create from-prompt "Create an invoice for okpdf local template work." \
  -o .agentpdf-out/invoice.pdf \
  --template invoice \
  --data examples/create-data/invoice.json \
  --json
```

## AI generation boundary

Open-source deterministic mode:

```text
Markdown/HTML/JSON + style pack -> PDF
```

Future AI mode:

```text
context packet + target PDF profile -> composition IR with source refs -> styled PDF
```

Composition and style systems should make the generated PDF traceable. Blocks should preserve source refs through rendering so evidence reports can map final pages back to the original context.

## UX requirements

Generated PDFs should include:

- Consistent spacing.
- Good typography.
- Proper page breaks.
- Optional cover page.
- Optional table of contents.
- Headers/footers.
- Page numbers.
- Source refs and citation pages where applicable.
- Code block overflow handling.
- Figure/table captions.
- Optional speaker notes for presentation PDFs.
- Validation report.

## Template examples

See `examples/style-packs/`.
