# 43 - Taste-Driven HTML-First Deck Pipeline

## Why This Exists

OKoffice deck generation should not be framed as "write a PPTX file as soon as possible." A deck is a visual argument. Agents need an inspectable intermediate artifact where story, evidence, layout, rhythm, typography, contrast, and visual density can be reviewed before an editable PowerPoint file is handed off.

The target OKoffice deck chain is:

```text
evidence workbook / source graph
-> deck.compose.plan
-> deck.render.html
-> deck.validation.html_preview
-> deck.validation.contact_sheet
-> deck.export.pptx
-> deck.validate.presentation
-> office.bundle.export
```

`deck.create.presentation` remains the public convenience tool. In the current OSS beta, the HTML-first route exists as explicit tools: `deck.render.html`, `deck.validation.html_preview`, and `deck.export.pptx`. The convenience writer still writes an editable PPTX directly from an outline or deck composition plan; future orchestration should call the HTML-first route when that is the best available local path and report direct PPTX creation as fallback evidence.

## External Research Notes

Microsoft's Office Agent material is a useful product signal, not a dependency requirement:

- Microsoft's Office Agent article describes the deck system as taste-driven development, meaning the agent's output is judged by narrative and visual quality, not just syntactic completion.
- The same article describes a presentation pipeline where specialized agents produce HTML5 slides and then convert them into PowerPoint's editable format.
- Microsoft Office Add-ins use web technologies such as HTML, CSS, and JavaScript, which supports a practical browser-preview layer for Office workflows.
- The PowerPoint JavaScript API exposes PowerPoint-aware operations such as presentation and slide creation, but that API surface does not remove the need for preview, validation, provenance, and local/cloud boundary controls in OKoffice.

Relevant sources:

- [Office Agent - "taste-driven" multi-agent system for Microsoft 365 Copilot](https://techcommunity.microsoft.com/blog/microsoft365copilotblog/office-agent-%E2%80%93-%E2%80%9Ctaste-driven%E2%80%9D-multi-agent-system-for-microsoft-365-copilot/4457397)
- [Microsoft Source Asia Office Agent article](https://news.microsoft.com/source/asia/2025/09/30/office-agent-%E6%89%93%E9%80%A0%E5%93%81%E5%91%B3%E9%A9%B1%E5%8A%A8%E7%9A%84%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E7%B3%BB%E7%BB%9F%EF%BC%8C%E5%85%A8%E9%9D%A2/?lang=zh-hans)
- [Office Add-ins platform overview](https://learn.microsoft.com/en-us/office/dev/add-ins/overview/office-add-ins)
- [PowerPoint add-ins and JavaScript API overview](https://learn.microsoft.com/en-us/office/dev/add-ins/powerpoint/powerpoint-add-ins)

## Product Contract

The HTML-first deck layer is not a marketing demo. It is an agent-native artifact with structured evidence.

The current `deck.render.html` beta emits:

- a self-contained HTML slide package;
- a package manifest;
- theme/style token usage;
- slide ids and DOM anchors;
- source refs for claims, charts, tables, images, and notes;
- render profile and local package evidence;
- warnings for unsafe scripts, remote assets, and placeholder leakage;
- next recommended tools.

The current `deck.validation.html_preview` beta checks:

- placeholder leakage;
- manifest presence;
- slide DOM anchors;
- unsafe script tags;
- remote or file asset references;
- offline renderability markers.

The current `deck.export.pptx` beta converts the HTML package manifest back through the local outline exporter and preserves:

- slide order and section ids;
- text boxes and speaker notes;
- source map links back to the HTML package and Composition IR.

Planned optional-worker enhancements should add browser screenshot checks, contact sheets, overflow detection, contrast/density scoring, image/alt-text preservation, richer style/theme transfer, and true HTML/component-tree to editable PPTX export.

## Current vs Target

Current OSS beta:

- `deck.compose.plan` creates source-mapped Composition IR and outline JSON from an evidence workbook.
- `deck.render.html` creates a self-contained HTML preview package with a manifest, DOM anchors, and source refs.
- `deck.validation.html_preview` validates package integrity, offline asset discipline, script absence, and placeholder leakage.
- `deck.export.pptx` writes editable PPTX through the local outline exporter and records HTML package lineage.
- `deck.create.presentation` writes a local editable PPTX directly from an outline or plan.
- `office.workflow.sheet_to_deck` profiles a workbook and produces a PPTX through the current deterministic route.
- `deck.validate.presentation` performs package/text/placeholder/source-map checks without claiming full visual QA.

Next target route:

- `deck.compose.plan` plans story and evidence.
- `deck.render.html` grows richer visual/component metadata.
- `deck.validation.html_preview` and `deck.validation.contact_sheet` make taste, screenshots, overflow, and layout inspectable.
- `deck.export.pptx` upgrades from local outline export to richer HTML/component-tree conversion.
- `deck.create.presentation` becomes a convenience orchestrator over the HTML-first route, with explicit fallback evidence when workers are unavailable.

## Tool Naming

Use these names consistently:

- `deck.compose.plan`: story/evidence planning; no PPTX mutation.
- `deck.render.html`: HTML slide package generation.
- `deck.validation.html_preview`: HTML/package/taste validation.
- `deck.validation.contact_sheet`: rendered screenshot/contact-sheet validation.
- `deck.export.pptx`: validated HTML/component tree to editable PPTX.
- `deck.create.presentation`: public convenience create command; current beta direct writer, target orchestrator.
- `deck.create.from_outline`: lower-level compatibility writer for direct outline-to-PPTX.

## Cloud Boundary

The local OSS core can write deterministic HTML packages and direct PPTX fallbacks. Heavy preview/export work may require optional workers:

- browser renderer for HTML screenshots and contact sheets;
- OfficeCLI or compatible Office worker for advanced PPTX export/editing;
- LibreOffice or another conversion worker for PPTX/PDF render checks;
- model/VLM workers for taste review only when explicitly configured.

Worker absence must return structured skip evidence. It must not be hidden behind `success: true`.
