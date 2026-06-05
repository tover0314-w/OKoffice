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

`deck.create.presentation` remains the public convenience tool. In the current OSS beta it writes an editable PPTX directly from an outline or deck composition plan. In the target pipeline it should orchestrate the HTML-first route when the renderer/export worker is available, and fall back to the deterministic local PPTX writer only when that is the best available local path.

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

`deck.render.html` should emit:

- a self-contained HTML slide package;
- a package manifest;
- theme/style token usage;
- slide ids and DOM anchors;
- source refs for claims, charts, tables, images, and notes;
- render profile and renderer backend evidence;
- warnings for remote assets, unsafe scripts, missing alt text, overflow risk, and placeholder leakage;
- next recommended tools.

`deck.validation.html_preview` should check:

- one main claim per slide unless the profile permits otherwise;
- placeholder leakage;
- text overflow and clipped regions from browser screenshots when available;
- contrast and visual density;
- evidence coverage for claims, tables, charts, and speaker notes;
- slide rhythm, sectioning, and duplicated titles;
- asset packaging and offline renderability.

`deck.export.pptx` should convert the validated HTML/component tree into an editable PPTX and preserve:

- slide order and section ids;
- text boxes and speaker notes;
- chart/table source refs where feasible;
- image assets and alt text;
- style pack/theme metadata;
- source map links back to the HTML package and Composition IR.

## Current vs Target

Current OSS beta:

- `deck.compose.plan` creates source-mapped Composition IR and outline JSON from an evidence workbook.
- `deck.create.presentation` writes a local editable PPTX directly from an outline or plan.
- `office.workflow.sheet_to_deck` profiles a workbook and produces a PPTX through the current deterministic route.
- `deck.validate.presentation` performs package/text/placeholder/source-map checks without claiming full visual QA.

Target route:

- `deck.compose.plan` plans story and evidence.
- `deck.render.html` creates the visual preview package.
- `deck.validation.html_preview` and `deck.validation.contact_sheet` make taste and layout inspectable.
- `deck.export.pptx` produces the editable PowerPoint file after preview validation.
- `deck.create.presentation` becomes a convenience orchestrator over the target route, with explicit fallback evidence when workers are unavailable.

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
