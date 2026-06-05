# 21 - UX, Documentation, and Polish

## Brand Principles

- Clear.
- Technical but not intimidating.
- Agent-first.
- Evidence-first.
- Local-first.
- Trustworthy.
- Beautiful by default.
- Honest about limitations.

okoffice should feel like serious infrastructure that still cares about the final artifact a human will open.

## README First Screen

The public README should show:

- Tagline: local-first, agent-native Office infrastructure.
- One workflow diagram.
- Quick install.
- Current compatibility note: `okoffice` / `pdf.*` are the first implemented domain.
- Target direction: `okoffice` / `office.*` for Word, Excel, PowerPoint, PDF, and bundles.
- 5 useful CLI examples.
- MCP example.
- Tool family grid.
- Open-source vs cloud boundary.
- A clear "bigger than RAG" explanation.
- Links to Office IR, Source Graph, validation, workflow, and PRD docs.
- Link to the taste-driven HTML-first deck pipeline.
- Roadmap status.

## Docs Style

Use:

- Short explanations.
- Concrete examples.
- JSON snippets.
- CLI, MCP, and REST examples for public features.
- Before/after artifacts.
- Source map and artifact lineage examples.
- Mermaid diagrams.
- Status labels.
- Warnings for hard Office/PDF tasks.
- License/dependency notes for optional workers.

Avoid:

- Claiming perfect layout-preserving edits.
- Hiding cloud-only behavior behind local examples.
- Prose-only outputs where an agent needs schema.
- PDF-only language in high-level okoffice pages.

## CLI Polish

- Use concise success summaries.
- Show validation results.
- Show output paths and checksums.
- Provide `--json` for agents.
- Include retry hints in errors.
- Keep command names predictable across formats.

Bad:

```text
Exception: failed
```

Good:

```text
Invalid range: Summary!A1:Z999 exceeds used range A1:H32.
Try: okoffice inspect evidence.xlsx --json
```

## Artifact Polish

Even OSS-generated artifacts should look good.

Word:

- Named styles.
- Clear headings.
- Captions.
- Source appendix.
- Clean metadata.

Excel:

- Tables with filters.
- Freeze panes where useful.
- Check sheets.
- Clear input/output separation.
- No formula errors.

PowerPoint:

- Clear claim spine.
- HTML preview package before PPTX export when available.
- Consistent layouts.
- Speaker notes when required.
- HTML preview and contact-sheet validation.
- Charts/tables with source refs.

PDF:

- Sensible margins.
- Readable typography.
- Proper page numbers.
- Good table styling.
- Stable page breaks.
- Render and blank-page checks.

## Example Gallery

Create examples for:

- Merge/split PDF workflow.
- Research paper RAG.
- Multi-source business report.
- Multiple DOCX/PDF sources to Excel evidence workbook.
- Excel workbook to PowerPoint board deck.
- Board pack: Word memo, workbook, deck, PDF handout, bundle.
- Contract review with redaction.
- Financial model validation.
- Training material: Word handout + deck + PDF.
- Code repository to audit packet.
- Cross-format patch transaction.
- Batch processing.

## Documentation Quality Bar

Every public feature needs:

- CLI example.
- MCP example.
- REST example.
- Expected output example.
- Error example.
- Limitations.
- License/dependency note when relevant.

The docs should let a coding agent succeed without guessing.
