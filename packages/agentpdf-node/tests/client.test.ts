import assert from "node:assert/strict";
import test from "node:test";

import { AgentPDFClient } from "../src/index.js";
import type { ToolManifest, ToolResult } from "../src/index.js";
import type { AuthoringBrief, EvidenceCard, WorkflowResearchDeckRequest } from "../src/types.js";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("AgentPDFClient lists tools from the local REST API", async () => {
  const manifest: ToolManifest = {
    manifest_version: "0.1-full",
    tools: [
      {
        name: "pdf.inspect.document",
        status: "stable",
        description: "Inspect a PDF.",
        interfaces: ["cli", "mcp", "rest"],
        implemented: true,
      },
    ],
  };
  const calls: string[] = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input) => {
      calls.push(String(input));
      return jsonResponse(manifest);
    },
  });

  const result = await client.listTools();

  assert.equal(calls[0], "http://agentpdf.test/v1/tools");
  assert.equal(result.tools[0]?.name, "pdf.inspect.document");
});

test("AgentPDFClient runs text-to-PDF with the expected payload", async () => {
  const toolResult: ToolResult = {
    job_id: "job_node",
    status: "succeeded",
    tool: "pdf.convert.text_to_pdf",
    artifacts: [],
    validation: null,
    warnings: [],
    usage: { text_length: 11 },
    next_recommended_tools: ["pdf.inspect.document"],
    error: null,
  };
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test/",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.convert.text_to_pdf/run");
      assert.equal(init?.method, "POST");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse(toolResult);
    },
  });

  const result = await client.createTextPdf({
    text: "hello world",
    outputPath: "out.pdf",
    title: "Hello",
  });

  assert.deepEqual(postedBody, {
    text: "hello world",
    output_path: "out.pdf",
    title: "Hello",
  });
  assert.equal(result.tool, "pdf.convert.text_to_pdf");
});


test("AgentPDFClient exposes target profile helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const toolResult = (tool: string): ToolResult => ({
    job_id: `job_${tool}`,
    status: "succeeded",
    tool,
    artifacts: [],
    validation: null,
    warnings: [],
    usage: {},
    next_recommended_tools: [],
    error: null,
  });
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      const tool = String(input).includes("select_profile")
        ? "pdf.target.select_profile"
        : String(input).includes("validate_profile")
        ? "pdf.target.validate_profile"
        : "pdf.target.profiles";
      return jsonResponse(toolResult(tool));
    },
  });

  await client.targetProfiles({ outputPath: "profiles.json" });
  await client.selectTargetProfile({
    goal: "Create a slide deck from source evidence.",
    contextPacketPath: "context.packet.json",
    preferredProfile: "slide_deck",
    outputPath: "selected-profile.json",
  });
  await client.validateTargetProfile({
    targetProfile: { profile_id: "board_packet", layout_mode: "document" },
    outputPath: "profile.validation.json",
  });

  assert.deepEqual(calls, [
    {
      url: "http://agentpdf.test/v1/tools/pdf.target.profiles/run",
      body: { output_path: "profiles.json" },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.target.select_profile/run",
      body: {
        goal: "Create a slide deck from source evidence.",
        context_packet_path: "context.packet.json",
        preferred_profile: "slide_deck",
        output_path: "selected-profile.json",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.target.validate_profile/run",
      body: {
        target_profile: { profile_id: "board_packet", layout_mode: "document" },
        output_path: "profile.validation.json",
      },
    },
  ]);
});

test("AgentPDFClient exposes context ingest and packet helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({
        url: String(input),
        body: JSON.parse(String(init?.body)),
      });
      return jsonResponse({
        job_id: "job_context",
        status: "succeeded",
        tool: calls.length === 1 ? "pdf.context.ingest" : "pdf.context.packet",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      } satisfies ToolResult);
    },
  });

  await client.ingestContext({
    contextItem: { path: "src/service.ts", role: "code_evidence" },
    outputPath: "service.context-item.json",
  });
  await client.contextPacket({
    contextItems: [{ context_item_id: "ctx_001", type: "code", source_ref: "ctx_001" }],
    outputPath: "context.packet.json",
    title: "Agent Context",
    intent: "Compose a target PDF.",
  });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.context.ingest/run",
    "http://agentpdf.test/v1/tools/pdf.context.packet/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    context_item: { path: "src/service.ts", role: "code_evidence" },
    output_path: "service.context-item.json",
  });
  assert.deepEqual(calls[1]?.body, {
    context_items: [{ context_item_id: "ctx_001", type: "code", source_ref: "ctx_001" }],
    output_path: "context.packet.json",
    title: "Agent Context",
    intent: "Compose a target PDF.",
  });
});

test("AgentPDFClient exposes page count, page info, and security metadata helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_pdf_utility",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      } satisfies ToolResult);
    },
  });

  await client.pageCountCheck({ path: "report.pdf", expectedPages: 3 });
  await client.metadataPageInfo({ inputPath: "report.pdf", pages: "1-2" });
  await client.inspectHealth({ inputPath: "report.pdf" });
  await client.metadataUpdateOutline({
    inputPath: "report.pdf",
    outline: [{ title: "Page One", page: 1 }],
    outputPath: "report.outlined.pdf",
  });
  await client.securityRemoveMetadata({ inputPath: "report.pdf", outputPath: "report.clean.pdf" });

  assert.deepEqual(calls, [
    {
      url: "http://agentpdf.test/v1/tools/pdf.validation.page_count_check/run",
      body: { path: "report.pdf", expected_pages: 3 },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.metadata.page_info/run",
      body: { input_path: "report.pdf", pages: "1-2" },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.inspect.health/run",
      body: { input_path: "report.pdf" },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.metadata.update_outline/run",
      body: {
        input_path: "report.pdf",
        outline: [{ title: "Page One", page: 1 }],
        output_path: "report.outlined.pdf",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.security.remove_metadata/run",
      body: { input_path: "report.pdf", output_path: "report.clean.pdf" },
    },
  ]);
});

test("AgentPDFClient exposes PDF optimization, font, and edit helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_pdf_edit",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      } satisfies ToolResult);
    },
  });

  await client.removeUnusedObjects({ inputPath: "report.pdf", outputPath: "report.optimized.pdf" });
  await client.validatePdfa({ inputPath: "report.pdf" });
  await client.extractFonts({ inputPath: "report.pdf", pages: "1" });
  await client.addShape({
    inputPath: "report.pdf",
    outputPath: "report.shape.pdf",
    shape: "rectangle",
    page: 1,
    x: 72,
    y: 640,
    width: 120,
    height: 40,
    strokeColor: "#2563eb",
    fillColor: "#dbeafe",
  });
  await client.underline({
    inputPath: "report.shape.pdf",
    outputPath: "report.underline.pdf",
    page: 1,
    bbox: [72, 640, 180, 656],
  });
  await client.strikeout({
    inputPath: "report.underline.pdf",
    outputPath: "report.strikeout.pdf",
    page: 1,
    bbox: [72, 640, 180, 656],
  });
  await client.freehandDraw({
    inputPath: "report.strikeout.pdf",
    outputPath: "report.drawn.pdf",
    page: 1,
    points: [[72, 680], [120, 700]],
  });
  await client.resizePages({
    inputPath: "report.drawn.pdf",
    outputPath: "report.resized.pdf",
    width: 300,
    height: 400,
  });
  await client.addMargin({
    inputPath: "report.resized.pdf",
    outputPath: "report.margin.pdf",
    margin: 36,
  });
  await client.underlay({
    inputPath: "report.margin.pdf",
    outputPath: "report.underlay.pdf",
    text: "DRAFT",
  });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.optimize.remove_unused_objects/run",
    "http://agentpdf.test/v1/tools/pdf.optimize.validate_pdfa/run",
    "http://agentpdf.test/v1/tools/pdf.convert.extract_fonts/run",
    "http://agentpdf.test/v1/tools/pdf.edit.add_shape/run",
    "http://agentpdf.test/v1/tools/pdf.edit.underline/run",
    "http://agentpdf.test/v1/tools/pdf.edit.strikeout/run",
    "http://agentpdf.test/v1/tools/pdf.edit.freehand_draw/run",
    "http://agentpdf.test/v1/tools/pdf.edit.resize_pages/run",
    "http://agentpdf.test/v1/tools/pdf.edit.add_margin/run",
    "http://agentpdf.test/v1/tools/pdf.edit.underlay/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    input_path: "report.pdf",
    output_path: "report.optimized.pdf",
  });
  assert.deepEqual(calls[1]?.body, { input_path: "report.pdf" });
  assert.deepEqual(calls[2]?.body, { input_path: "report.pdf", pages: "1" });
  assert.deepEqual(calls[3]?.body, {
    input_path: "report.pdf",
    output_path: "report.shape.pdf",
    shape: "rectangle",
    page: 1,
    x: 72,
    y: 640,
    width: 120,
    height: 40,
    stroke_color: "#2563eb",
    fill_color: "#dbeafe",
  });
  assert.deepEqual(calls[4]?.body, {
    input_path: "report.shape.pdf",
    output_path: "report.underline.pdf",
    page: 1,
    bbox: [72, 640, 180, 656],
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "report.margin.pdf",
    output_path: "report.underlay.pdf",
    text: "DRAFT",
  });
});

test("AgentPDFClient exposes compare and semantic parse helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_compare_parse",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      } satisfies ToolResult);
    },
  });

  await client.semanticDiff({ beforePath: "before.pdf", afterPath: "after.pdf", pages: "1" });
  await client.versionReport({
    beforePath: "before.pdf",
    afterPath: "after.pdf",
    outputPath: "version-report.md",
  });
  await client.visualDiff({ beforePath: "before.pdf", afterPath: "after.pdf", pages: "1" });
  await client.validationVisualDiff({
    beforePath: "before.pdf",
    afterPath: "after.pdf",
    pages: "1",
    maxDifferenceRatio: 0,
  });
  await client.parseFigures({ inputPath: "report.pdf", pages: "1" });
  await client.parseFormulas({ inputPath: "report.pdf" });
  await client.parseCharts({ inputPath: "report.pdf" });
  await client.parseReferences({ inputPath: "report.pdf" });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.compare.semantic_diff/run",
    "http://agentpdf.test/v1/tools/pdf.compare.version_report/run",
    "http://agentpdf.test/v1/tools/pdf.compare.visual_diff/run",
    "http://agentpdf.test/v1/tools/pdf.validation.visual_diff/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.figures/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.formulas/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.charts/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.references/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[1]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    output_path: "version-report.md",
  });
  assert.deepEqual(calls[2]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[3]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
    max_difference_ratio: 0,
  });
  assert.deepEqual(calls[4]?.body, {
    input_path: "report.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[7]?.body, {
    input_path: "report.pdf",
  });
});

test("AgentPDFClient exposes forms and OCR helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_forms_ocr",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  await client.formsCreate({
    outputPath: "form.pdf",
    fields: [{ name: "name", label: "Name", required: true }],
  });
  await client.formsImportData({
    inputPath: "form.pdf",
    data: { name: "Ada" },
    outputPath: "filled.pdf",
  });
  await client.formsValidate({ inputPath: "filled.pdf", requiredFields: ["name"] });
  await client.ocr({ inputPath: "scan.png", languages: ["eng"], psm: 6 });
  await client.ocrSearchablePdf({
    inputPath: "scan.pdf",
    outputPath: "searchable.pdf",
    pages: "1",
    languages: ["eng"],
    dpi: 250,
  });
  await client.ocrScanToPdf({ imagePaths: ["scan.png"], outputPath: "scan.pdf" });
  await client.ocrDespeckle({ inputPath: "scan.pdf", outputPath: "despeckled.pdf" });
  await client.ocrRemoveExistingOcr({ inputPath: "scan.pdf", outputPath: "no-ocr.pdf" });
  await client.ocrMultilingual({
    inputPath: "scan.pdf",
    outputPath: "multi-ocr.pdf",
    languages: ["eng", "chi_sim"],
  });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.forms.create/run",
    "http://agentpdf.test/v1/tools/pdf.forms.import_data/run",
    "http://agentpdf.test/v1/tools/pdf.forms.validate/run",
    "http://agentpdf.test/v1/tools/pdf.ocr_scan.ocr/run",
    "http://agentpdf.test/v1/tools/pdf.ocr_scan.searchable_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.ocr_scan.scan_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.ocr_scan.despeckle/run",
    "http://agentpdf.test/v1/tools/pdf.ocr_scan.remove_existing_ocr/run",
    "http://agentpdf.test/v1/tools/pdf.ocr_scan.multilingual_ocr/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    output_path: "form.pdf",
    fields: [{ name: "name", label: "Name", required: true }],
  });
  assert.deepEqual(calls[1]?.body, {
    input_path: "form.pdf",
    data: { name: "Ada" },
    output_path: "filled.pdf",
  });
  assert.deepEqual(calls[2]?.body, {
    input_path: "filled.pdf",
    required_fields: ["name"],
  });
  assert.deepEqual(calls[3]?.body, {
    input_path: "scan.png",
    languages: ["eng"],
    psm: 6,
  });
  assert.deepEqual(calls[4]?.body, {
    input_path: "scan.pdf",
    output_path: "searchable.pdf",
    pages: "1",
    languages: ["eng"],
    dpi: 250,
  });
  assert.deepEqual(calls[5]?.body, {
    image_paths: ["scan.png"],
    output_path: "scan.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "scan.pdf",
    output_path: "multi-ocr.pdf",
    languages: ["eng", "chi_sim"],
  });
});

test("AgentPDFClient exposes conversion, PDF/A, and security helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_conversion_security",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  await client.subsetFonts({ inputPath: "report.pdf", outputPath: "report.subset.pdf" });
  await client.toPdfa({ inputPath: "report.pdf", outputPath: "report.pdfa.pdf", profile: "PDF/A-2b" });
  await client.htmlToPdf({ inputPath: "page.html", outputPath: "page.pdf" });
  await client.renderHtmlPackage({ packagePath: "page.html-manifest.json", outputPath: "page.pdf" });
  await client.urlToPdf({
    url: "https://example.com",
    outputPath: "url.pdf",
    allowPrivateHosts: true,
    allowFileUrls: true,
  });
  await client.docxToPdf({ inputPath: "report.docx", outputPath: "report.pdf" });
  await client.pptxToPdf({ inputPath: "deck.pptx", outputPath: "deck.pdf" });
  await client.xlsxToPdf({ inputPath: "metrics.xlsx", outputPath: "metrics.pdf" });
  await client.pdfToHtml({ inputPath: "report.pdf", outputPath: "report.html", pages: "1" });
  await client.pdfToDocx({ inputPath: "report.pdf", outputPath: "report.docx" });
  await client.pdfToPptx({ inputPath: "report.pdf", outputPath: "report.pptx" });
  await client.pdfToXlsx({ inputPath: "report.pdf", outputPath: "report.xlsx" });
  await client.securityProtect({
    inputPath: "report.pdf",
    outputPath: "protected.pdf",
    password: "open",
    ownerPassword: "owner",
  });
  await client.securityEncrypt({ inputPath: "report.pdf", outputPath: "encrypted.pdf", password: "open" });
  await client.securityUnlockAuthorized({
    inputPath: "protected.pdf",
    outputPath: "unlocked.pdf",
    password: "open",
  });
  await client.securityDecryptAuthorized({
    inputPath: "encrypted.pdf",
    outputPath: "decrypted.pdf",
    password: "open",
  });
  await client.securitySign({
    inputPath: "report.pdf",
    outputPath: "signed.pdf",
    secret: "local-secret",
  });
  await client.securityVerifySignature({
    inputPath: "signed.pdf",
    signaturePath: "signed.pdf.signature.json",
    secret: "local-secret",
  });
  await client.securityMalwareScan({ inputPath: "report.pdf" });
  await client.securitySanitize({ inputPath: "report.pdf", outputPath: "sanitized.pdf" });
  await client.securityRedact({
    inputPath: "report.pdf",
    outputPath: "redacted.pdf",
    regions: [{ page: 1, bbox: [60, 700, 280, 760], label: "secret" }],
  });
  await client.securityVerifyRedaction({
    inputPath: "redacted.pdf",
    searchTerms: ["SECRET-CODE-123"],
  });
  await client.validationRedactionCheck({
    inputPath: "redacted.pdf",
    searchTerms: ["SECRET-CODE-123"],
  });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.optimize.subset_fonts/run",
    "http://agentpdf.test/v1/tools/pdf.optimize.to_pdfa/run",
    "http://agentpdf.test/v1/tools/pdf.convert.html_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.render.html_package/run",
    "http://agentpdf.test/v1/tools/pdf.convert.url_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.convert.docx_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pptx_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.convert.xlsx_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pdf_to_html/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pdf_to_docx/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pdf_to_pptx/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pdf_to_xlsx/run",
    "http://agentpdf.test/v1/tools/pdf.security.protect/run",
    "http://agentpdf.test/v1/tools/pdf.security.encrypt/run",
    "http://agentpdf.test/v1/tools/pdf.security.unlock_authorized/run",
    "http://agentpdf.test/v1/tools/pdf.security.decrypt_authorized/run",
    "http://agentpdf.test/v1/tools/pdf.security.sign/run",
    "http://agentpdf.test/v1/tools/pdf.security.verify_signature/run",
    "http://agentpdf.test/v1/tools/pdf.security.malware_scan/run",
    "http://agentpdf.test/v1/tools/pdf.security.sanitize/run",
    "http://agentpdf.test/v1/tools/pdf.security.redact/run",
    "http://agentpdf.test/v1/tools/pdf.security.verify_redaction/run",
    "http://agentpdf.test/v1/tools/pdf.validation.redaction_check/run",
  ]);
  assert.deepEqual(calls[1]?.body, {
    input_path: "report.pdf",
    output_path: "report.pdfa.pdf",
    profile: "PDF/A-2b",
  });
  assert.deepEqual(calls[3]?.body, {
    package_path: "page.html-manifest.json",
    output_path: "page.pdf",
  });
  assert.deepEqual(calls[4]?.body, {
    url: "https://example.com",
    output_path: "url.pdf",
    allow_private_hosts: true,
    allow_file_urls: true,
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "report.pdf",
    output_path: "report.html",
    pages: "1",
  });
  assert.deepEqual(calls[12]?.body, {
    input_path: "report.pdf",
    output_path: "protected.pdf",
    password: "open",
    owner_password: "owner",
  });
  assert.deepEqual(calls[17]?.body, {
    input_path: "signed.pdf",
    signature_path: "signed.pdf.signature.json",
    secret: "local-secret",
  });
  assert.deepEqual(calls[18]?.body, {
    input_path: "report.pdf",
  });
  assert.deepEqual(calls[19]?.body, {
    input_path: "report.pdf",
    output_path: "sanitized.pdf",
  });
  assert.deepEqual(calls[20]?.body, {
    input_path: "report.pdf",
    output_path: "redacted.pdf",
    regions: [{ page: 1, bbox: [60, 700, 280, 760], label: "secret" }],
  });
  assert.deepEqual(calls[21]?.body, {
    input_path: "redacted.pdf",
    search_terms: ["SECRET-CODE-123"],
  });
  assert.deepEqual(calls[22]?.body, {
    input_path: "redacted.pdf",
    search_terms: ["SECRET-CODE-123"],
  });
});

test("AgentPDFClient exposes context classify helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.context.classify/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_context_classify",
        status: "succeeded",
        tool: "pdf.context.classify",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: { classification_count: 2 },
        next_recommended_tools: ["pdf.compose.from_context"],
        error: null,
      } satisfies ToolResult);
    },
  });

  const result = await client.classifyContext({
    contextPacketPath: "context.packet.json",
    profile: "technical_audit",
    outputPath: "context.classification.json",
  });

  assert.equal(result.tool, "pdf.context.classify");
  assert.deepEqual(postedBody, {
    context_packet_path: "context.packet.json",
    profile: "technical_audit",
    output_path: "context.classification.json",
  });
});

test("AgentPDFClient exposes code snapshot and data profile helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_context_evidence",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      } satisfies ToolResult);
    },
  });

  await client.codeSnapshot({
    path: "src/service.ts",
    outputPath: "service.context-item.json",
    label: "Service Code",
    role: "code_evidence",
    contextItemId: "ctx_code",
    lineStart: 2,
    lineEnd: 8,
    repositoryRoot: ".",
    includeDependencies: true,
  });
  await client.dataProfile({
    path: "metrics.xlsx",
    outputPath: "metrics.context-item.json",
    label: "Workbook Metrics",
    role: "data_evidence",
    contextItemId: "ctx_data",
    sheet: "Sheet1",
    maxRows: 50,
  });
  await client.contextImageAnalyze({
    inputPath: "scan.png",
    languages: ["eng"],
    runOcr: false,
    engine: "tesseract",
    psm: 6,
  });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.context.code_snapshot/run",
    "http://agentpdf.test/v1/tools/pdf.context.data_profile/run",
    "http://agentpdf.test/v1/tools/pdf.context.image_analyze/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    path: "src/service.ts",
    output_path: "service.context-item.json",
    label: "Service Code",
    role: "code_evidence",
    context_item_id: "ctx_code",
    line_start: 2,
    line_end: 8,
    repository_root: ".",
    include_dependencies: true,
  });
  assert.deepEqual(calls[1]?.body, {
    path: "metrics.xlsx",
    output_path: "metrics.context-item.json",
    label: "Workbook Metrics",
    role: "data_evidence",
    context_item_id: "ctx_data",
    sheet: "Sheet1",
    max_rows: 50,
  });
  assert.deepEqual(calls[2]?.body, {
    input_path: "scan.png",
    languages: ["eng"],
    run_ocr: false,
    engine: "tesseract",
    psm: 6,
  });
});

test("AgentPDFClient exposes compose plan and render IR helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_compose_ir",
        status: "succeeded",
        tool: calls.length === 1 ? "pdf.compose.plan" : "pdf.compose.render_ir",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      } satisfies ToolResult);
    },
  });

  await client.composePlan({
    contextPacketPath: "context.packet.json",
    profile: "technical_audit",
    outputPath: "composition.plan.json",
    stylePack: "paper_ink",
    title: "Technical Audit Plan",
  });
  await client.composeRenderIr({
    compositionPath: "composition.plan.json",
    outputPath: "technical-audit.pdf",
    title: "Technical Audit",
  });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.compose.plan/run",
    "http://agentpdf.test/v1/tools/pdf.compose.render_ir/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    context_packet_path: "context.packet.json",
    profile: "technical_audit",
    output_path: "composition.plan.json",
    style_pack: "paper_ink",
    title: "Technical Audit Plan",
  });
  assert.deepEqual(calls[1]?.body, {
    composition_path: "composition.plan.json",
    output_path: "technical-audit.pdf",
    title: "Technical Audit",
  });
});

test("AgentPDFClient exposes compose block helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const toolResult = (tool: string): ToolResult => ({
    job_id: `job_${tool}`,
    status: "succeeded",
    tool,
    artifacts: [],
    validation: null,
    warnings: [],
    usage: {},
    next_recommended_tools: [],
    error: null,
  });
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      const url = String(input);
      const tool = url.includes("add_table")
        ? "pdf.compose.add_table"
        : url.includes("add_figure")
          ? "pdf.compose.add_figure"
          : url.includes("add_appendix")
            ? "pdf.compose.add_appendix"
            : url.includes("add_citation")
              ? "pdf.compose.add_citation"
              : url.includes("add_media_reference")
                ? "pdf.compose.add_media_reference"
                : url.includes("add_slide")
                  ? "pdf.compose.add_slide"
                  : "pdf.compose.add_code_block";
      return jsonResponse(toolResult(tool));
    },
  });

  await client.composeAddCodeBlock({
    inputPath: "base.pdf",
    outputPath: "code.pdf",
    title: "Risk Function",
    code: "def risky_total(items):\n    return sum(items)\n",
    language: "python",
    sourceRefs: ["ctx_code"],
    blockId: "blk_code",
    targetSlot: "code_review",
  });
  await client.composeAddTable({
    inputPath: "base.pdf",
    outputPath: "table.pdf",
    title: "Runtime Metrics",
    columns: ["metric", "value"],
    rows: [["latency_ms", "42"]],
    sourceRefs: ["ctx_metrics"],
  });
  await client.composeAddFigure({
    inputPath: "base.pdf",
    outputPath: "figure.pdf",
    title: "Architecture Figure",
    imagePath: "diagram.png",
    caption: "Local visual evidence.",
    sourceRefs: ["ctx_image"],
  });
  await client.composeAddAppendix({
    inputPath: "base.pdf",
    outputPath: "appendix.pdf",
    title: "Source Appendix",
    markdown: "## Sources\n\n- ctx_code",
    sourceRefs: ["ctx_code"],
  });
  await client.composeAddCitation({
    inputPath: "base.pdf",
    outputPath: "citation.pdf",
    title: "Source Citation",
    quote: "AgentPDF keeps citation source refs auditable.",
    source: "https://example.com/research",
    page: "section 2",
    sourceRefs: ["ctx_web"],
    blockId: "blk_citation",
    targetSlot: "citations",
  });
  await client.composeAddMediaReference({
    inputPath: "base.pdf",
    outputPath: "media.pdf",
    title: "Meeting Audio",
    mediaPath: "meeting.mp3",
    mediaKind: "audio",
    transcriptExcerpt: "00:00 Kickoff",
    durationSeconds: 42.5,
    chapterCount: 1,
    sourceRefs: ["ctx_audio"],
    blockId: "blk_audio",
    targetSlot: "media_evidence",
  });
  await client.composeAddSlide({
    inputPath: "base.pdf",
    outputPath: "slide.pdf",
    title: "Review Slide",
    subtitle: "Decision evidence",
    body: ["First slide bullet.", "Second slide bullet."],
    code: "score = 42",
    sourceRefs: ["ctx_slide"],
    blockId: "blk_slide",
    targetSlot: "evidence_slide",
  });

  assert.deepEqual(calls, [
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_code_block/run",
      body: {
        input_path: "base.pdf",
        output_path: "code.pdf",
        title: "Risk Function",
        code: "def risky_total(items):\n    return sum(items)\n",
        language: "python",
        source_refs: ["ctx_code"],
        block_id: "blk_code",
        target_slot: "code_review",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_table/run",
      body: {
        input_path: "base.pdf",
        output_path: "table.pdf",
        title: "Runtime Metrics",
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"]],
        source_refs: ["ctx_metrics"],
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_figure/run",
      body: {
        input_path: "base.pdf",
        output_path: "figure.pdf",
        title: "Architecture Figure",
        image_path: "diagram.png",
        caption: "Local visual evidence.",
        source_refs: ["ctx_image"],
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_appendix/run",
      body: {
        input_path: "base.pdf",
        output_path: "appendix.pdf",
        title: "Source Appendix",
        markdown: "## Sources\n\n- ctx_code",
        source_refs: ["ctx_code"],
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_citation/run",
      body: {
        input_path: "base.pdf",
        output_path: "citation.pdf",
        title: "Source Citation",
        quote: "AgentPDF keeps citation source refs auditable.",
        source: "https://example.com/research",
        page: "section 2",
        source_refs: ["ctx_web"],
        block_id: "blk_citation",
        target_slot: "citations",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_media_reference/run",
      body: {
        input_path: "base.pdf",
        output_path: "media.pdf",
        title: "Meeting Audio",
        media_path: "meeting.mp3",
        media_kind: "audio",
        transcript_excerpt: "00:00 Kickoff",
        duration_seconds: 42.5,
        chapter_count: 1,
        source_refs: ["ctx_audio"],
        block_id: "blk_audio",
        target_slot: "media_evidence",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.compose.add_slide/run",
      body: {
        input_path: "base.pdf",
        output_path: "slide.pdf",
        title: "Review Slide",
        subtitle: "Decision evidence",
        body: ["First slide bullet.", "Second slide bullet."],
        code: "score = 42",
        source_refs: ["ctx_slide"],
        block_id: "blk_slide",
        target_slot: "evidence_slide",
      },
    },
  ]);
});

test("AgentPDFClient exposes template pack helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_template_pack",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  await client.createTemplatePacks({ outputPath: "template-packs.json" });
  await client.validateTemplatePack({
    templatePackPath: "examples/template-packs/local-agent-starter.json",
    outputPath: "template-pack.validation.json",
  });
  await client.planTemplatePack({
    templatePackPath: "examples/template-packs/local-agent-starter.json",
    profile: "technical_audit",
    contextPacketPath: "context.packet.json",
    plannedOutputPath: "board-audit.pdf",
    outputPath: "board-audit.plan.json",
  });
  await client.createAgent({
    templatePackPath: "examples/template-packs/local-agent-starter.json",
    profile: "technical_audit",
    contextPacketPath: "context.packet.json",
    outputPath: "board-audit.pdf",
    planOutputPath: "board-audit.plan.json",
    coverageOutputPath: "board-audit.coverage.json",
    contextClassificationOutputPath: "board-audit.context-classification.json",
    contextReportOutputPath: "board-audit.context-report.pdf",
    contextReportJsonOutputPath: "board-audit.context-report.json",
    bundleOutputPath: "board-audit.agentpdf-bundle.zip",
  });
  await client.createFromTemplatePack({
    templatePackPath: "examples/template-packs/local-agent-starter.json",
    templateId: "board_audit",
    colorScheme: "executive_blue",
    contextPacketPath: "context.packet.json",
    outputPath: "board-audit.pdf",
    renderer: "html",
    htmlOutputPath: "board-audit.html",
  });

  assert.deepEqual(calls, [
    {
      url: "http://agentpdf.test/v1/tools/pdf.ai.create.template_packs/run",
      body: { output_path: "template-packs.json" },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.ai.create.validate_template_pack/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        output_path: "template-pack.validation.json",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.ai.create.plan_template_pack/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        profile: "technical_audit",
        context_packet_path: "context.packet.json",
        planned_output_path: "board-audit.pdf",
        output_path: "board-audit.plan.json",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.ai.create.agent/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        profile: "technical_audit",
        context_packet_path: "context.packet.json",
        output_path: "board-audit.pdf",
        plan_output_path: "board-audit.plan.json",
        coverage_output_path: "board-audit.coverage.json",
        context_classification_output_path: "board-audit.context-classification.json",
        context_report_output_path: "board-audit.context-report.pdf",
        context_report_json_output_path: "board-audit.context-report.json",
        bundle_output_path: "board-audit.agentpdf-bundle.zip",
      },
    },
    {
      url: "http://agentpdf.test/v1/tools/pdf.ai.create.from_template_pack/run",
      body: {
        template_pack_path: "examples/template-packs/local-agent-starter.json",
        template_id: "board_audit",
        output_path: "board-audit.pdf",
        color_scheme: "executive_blue",
        context_packet_path: "context.packet.json",
        renderer: "html",
        html_output_path: "board-audit.html",
      },
    },
  ]);
});

test("AgentPDFClient exposes authoring workflow helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_authoring",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });
  const brief: AuthoringBrief = {
    topic: "Independent developers going global",
    page_count: 4,
    deliverable: "deck",
  };
  const evidenceCards: EvidenceCard[] = [
    {
      id: "ev_market",
      claim: "Mobile monetization remains strong.",
      evidence: "Revenue growth continues while downloads flatten.",
      source_title: "State of Mobile 2026",
    },
  ];

  await client.authoringPlan({ brief });
  await client.researchPlan({ brief });
  await client.researchSourceCards({
    brief,
    sources: [
      {
        title: "State of Mobile 2026",
        source_type: "report",
        summary: "Revenue growth continues while downloads flatten.",
      },
    ],
  });
  await client.researchEvidenceCards({
    sourceCards: [
      {
        id: "source_001",
        title: "State of Mobile 2026",
        summary: "Revenue growth continues while downloads flatten.",
        key_points: ["Revenue growth continues while downloads flatten."],
      },
    ],
  });
  await client.designTokens({ theme: "consulting", overrides: { primary_color: "#123456" } });
  await client.storyboardPlan({ brief, authoringPlan: { recommended_authoring_format: "html" }, evidenceCards });
  await client.pagesWrite({
    brief,
    storyboard: { storyboard_id: "storyboard_1", page_count: 1, pages: [] },
    evidenceCards,
    designTokens: { theme: "business_tech" },
  });
  await client.pagesRevise({
    pageDocument: { page_document_id: "pages_1", page_count: 1, pages: [{ page_number: 1, layout: "cover", title: "Old" }] },
    revisions: [{ page_number: 1, title: "New" }],
  });
  await client.createHtmlPackage({
    pageDocument: { page_document_id: "pages_1", page_count: 0, pages: [] },
    htmlOutputPath: "deck.html",
    title: "Independent developers going global",
  });
  await client.createHtmlPackage({
    html: "<main><h1>HTML First</h1><p>Node SDK raw HTML package.</p></main>",
    htmlOutputPath: "raw.html",
    title: "HTML First",
  });
  await client.qaVisualReport({
    inputPath: "deck.pdf",
    expectedPageCount: 4,
    htmlPackageManifestPath: "deck.html-manifest.json",
    pages: "all",
  });
  const workflowRequest: WorkflowResearchDeckRequest = {
    brief,
    evidenceCards,
    htmlOutputPath: "deck.html",
    pdfOutputPath: "deck.pdf",
    artifactDir: "workflow-artifacts",
    execute: true,
  };
  await client.workflowResearchDeck(workflowRequest);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.authoring.plan/run",
    "http://agentpdf.test/v1/tools/pdf.research.plan/run",
    "http://agentpdf.test/v1/tools/pdf.research.source_cards/run",
    "http://agentpdf.test/v1/tools/pdf.research.evidence_cards/run",
    "http://agentpdf.test/v1/tools/pdf.design.tokens/run",
    "http://agentpdf.test/v1/tools/pdf.storyboard.plan/run",
    "http://agentpdf.test/v1/tools/pdf.pages.write/run",
    "http://agentpdf.test/v1/tools/pdf.pages.revise/run",
    "http://agentpdf.test/v1/tools/pdf.create.html_package/run",
    "http://agentpdf.test/v1/tools/pdf.create.html_package/run",
    "http://agentpdf.test/v1/tools/pdf.qa.visual_report/run",
    "http://agentpdf.test/v1/tools/pdf.workflow.research_deck/run",
  ]);
  assert.deepEqual(calls[0]?.body, { brief });
  assert.deepEqual(calls[4]?.body, { theme: "consulting", overrides: { primary_color: "#123456" } });
  assert.deepEqual(calls[8]?.body, {
    page_document: { page_document_id: "pages_1", page_count: 0, pages: [] },
    html_output_path: "deck.html",
    title: "Independent developers going global",
  });
  assert.deepEqual(calls[9]?.body, {
    html: "<main><h1>HTML First</h1><p>Node SDK raw HTML package.</p></main>",
    html_output_path: "raw.html",
    title: "HTML First",
  });
  assert.deepEqual(calls[11]?.body, {
    brief,
    evidence_cards: evidenceCards,
    html_output_path: "deck.html",
    pdf_output_path: "deck.pdf",
    artifact_dir: "workflow-artifacts",
    execute: true,
  });
});

test("AgentPDFClient exposes artifact bundle export helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.artifacts.export_bundle/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_bundle",
        status: "succeeded",
        tool: "pdf.artifacts.export_bundle",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.exportBundle({
    artifactPaths: ["report.pdf", "report.composition.json"],
    outputPath: "report.agentpdf-bundle.zip",
    title: "Report Bundle",
    metadata: { agent: "codex" },
  });

  assert.equal(result.tool, "pdf.artifacts.export_bundle");
  assert.deepEqual(postedBody, {
    artifact_paths: ["report.pdf", "report.composition.json"],
    output_path: "report.agentpdf-bundle.zip",
    title: "Report Bundle",
    metadata: { agent: "codex" },
  });
});

test("AgentPDFClient exposes artifact manifest helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.artifacts.manifest/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_artifact_manifest",
        status: "succeeded",
        tool: "pdf.artifacts.manifest",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.artifactManifest({
    artifactPaths: ["report.pdf", "report.composition.json", "report.coverage.json"],
    outputPath: "report.artifacts.json",
    title: "Report Artifact Manifest",
    metadata: { agent: "codex" },
  });

  assert.equal(result.tool, "pdf.artifacts.manifest");
  assert.deepEqual(postedBody, {
    artifact_paths: ["report.pdf", "report.composition.json", "report.coverage.json"],
    output_path: "report.artifacts.json",
    title: "Report Artifact Manifest",
    metadata: { agent: "codex" },
  });
});

test("AgentPDFClient exposes artifact graph helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.artifacts.graph/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_artifact_graph",
        status: "succeeded",
        tool: "pdf.artifacts.graph",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.artifactGraph({
    artifactManifestPath: "report.artifacts.json",
    artifactPaths: ["report.pdf", "report.composition.json"],
    outputPath: "report.artifact-graph.json",
    title: "Report Artifact Graph",
  });

  assert.equal(result.tool, "pdf.artifacts.graph");
  assert.deepEqual(postedBody, {
    artifact_manifest_path: "report.artifacts.json",
    artifact_paths: ["report.pdf", "report.composition.json"],
    output_path: "report.artifact-graph.json",
    title: "Report Artifact Graph",
  });
});

test("AgentPDFClient exposes artifact source map helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.artifacts.source_map/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_artifact_source_map",
        status: "succeeded",
        tool: "pdf.artifacts.source_map",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.artifactSourceMap({
    compositionPath: "report.composition.json",
    contextPacketPath: "context.packet.json",
    artifactManifestPath: "report.artifacts.json",
    outputPath: "report.artifact-source-map.json",
    title: "Report Artifact Source Map",
  });

  assert.equal(result.tool, "pdf.artifacts.source_map");
  assert.deepEqual(postedBody, {
    composition_path: "report.composition.json",
    context_packet_path: "context.packet.json",
    artifact_manifest_path: "report.artifacts.json",
    output_path: "report.artifact-source-map.json",
    title: "Report Artifact Source Map",
  });
});

test("AgentPDFClient exposes compare and semantic parse helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_compare_parse",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  await client.compareSemanticDiff({ beforePath: "before.pdf", afterPath: "after.pdf", pages: "1" });
  await client.compareVersionReport({
    beforePath: "before.pdf",
    afterPath: "after.pdf",
    outputPath: "version-report.md",
  });
  await client.compareVisualDiff({ beforePath: "before.pdf", afterPath: "after.pdf", pages: "1" });
  await client.parseFigures({ inputPath: "report.pdf", pages: "1" });
  await client.parseFormulas({ inputPath: "report.pdf" });
  await client.parseCharts({ inputPath: "report.pdf" });
  await client.parseReferences({ inputPath: "report.pdf" });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.compare.semantic_diff/run",
    "http://agentpdf.test/v1/tools/pdf.compare.version_report/run",
    "http://agentpdf.test/v1/tools/pdf.compare.visual_diff/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.figures/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.formulas/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.charts/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.references/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[1]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    output_path: "version-report.md",
  });
  assert.deepEqual(calls[2]?.body, {
    before_path: "before.pdf",
    after_path: "after.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[3]?.body, {
    input_path: "report.pdf",
    pages: "1",
  });
});

test("AgentPDFClient exposes context packet report helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.evidence.context_packet_report/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_context_report",
        status: "succeeded",
        tool: "pdf.evidence.context_packet_report",
        artifacts: [],
        validation: { status: "passed", checks: [] },
        warnings: [],
        usage: { context_packet_id: "ctxpkt_test", source_ref_count: 2 },
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.contextPacketReport({
    contextPacketPath: "context.packet.json",
    outputPath: "context-report.pdf",
    reportOutputPath: "context-report.json",
    title: "Context Report",
    stylePack: "paper_ink",
  });

  assert.equal(result.tool, "pdf.evidence.context_packet_report");
  assert.deepEqual(postedBody, {
    context_packet_path: "context.packet.json",
    output_path: "context-report.pdf",
    report_output_path: "context-report.json",
    title: "Context Report",
    style_pack: "paper_ink",
  });
});

test("AgentPDFClient exposes artifact bundle verify helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/pdf.artifacts.verify_bundle/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_bundle_verify",
        status: "succeeded",
        tool: "pdf.artifacts.verify_bundle",
        artifacts: [],
        validation: { status: "passed", checks: [], warnings: [] },
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.verifyBundle({
    bundlePath: "report.agentpdf-bundle.zip",
  });

  assert.equal(result.tool, "pdf.artifacts.verify_bundle");
  assert.deepEqual(postedBody, {
    bundle_path: "report.agentpdf-bundle.zip",
  });
});

test("AgentPDFClient exposes Claude Code agent setup helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/agent.setup.claude_code/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_agent_setup",
        status: "succeeded",
        tool: "agent.setup.claude_code",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.setupClaudeCode({
    outputPath: ".mcp.json",
    safeRoot: "${CLAUDE_PROJECT_DIR:-.}",
    command: "python",
    argsPrefix: ["-m", "agentpdf.cli"],
    scope: "project",
  });

  assert.equal(result.tool, "agent.setup.claude_code");
  assert.deepEqual(postedBody, {
    output_path: ".mcp.json",
    safe_root: "${CLAUDE_PROJECT_DIR:-.}",
    command: "python",
    args_prefix: ["-m", "agentpdf.cli"],
    scope: "project",
  });
});

test("AgentPDFClient exposes Codex agent setup helper", async () => {
  let postedBody: unknown;
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      assert.equal(String(input), "http://agentpdf.test/v1/tools/agent.setup.codex/run");
      postedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        job_id: "job_codex_setup",
        status: "succeeded",
        tool: "agent.setup.codex",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const result = await client.setupCodex({
    outputPath: "codex.mcp.json",
    safeRoot: ".",
    command: "python",
    argsPrefix: ["-m", "agentpdf.cli"],
    serverName: "agentpdf",
  });

  assert.equal(result.tool, "agent.setup.codex");
  assert.deepEqual(postedBody, {
    output_path: "codex.mcp.json",
    safe_root: ".",
    command: "python",
    args_prefix: ["-m", "agentpdf.cli"],
    server_name: "agentpdf",
  });
});

test("AgentPDFClient exposes Kilo Code and OpenClaw setup helpers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      const body = JSON.parse(String(init?.body));
      calls.push({ url: String(input), body });
      return jsonResponse({
        job_id: "job_agent_setup",
        status: "succeeded",
        tool: body.output_path === "kilo-code.mcp.json" ? "agent.setup.kilo_code" : "agent.setup.openclaw",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  const kilo = await client.setupKiloCode({
    outputPath: "kilo-code.mcp.json",
    safeRoot: ".",
    command: "python",
    argsPrefix: ["-m", "agentpdf.cli"],
  });
  const openclaw = await client.setupOpenClaw({
    outputPath: "openclaw.mcp.json",
    safeRoot: ".",
    serverName: "agentpdf",
  });

  assert.equal(kilo.tool, "agent.setup.kilo_code");
  assert.equal(openclaw.tool, "agent.setup.openclaw");
  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/agent.setup.kilo_code/run",
    "http://agentpdf.test/v1/tools/agent.setup.openclaw/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    output_path: "kilo-code.mcp.json",
    safe_root: ".",
    command: "python",
    args_prefix: ["-m", "agentpdf.cli"],
  });
  assert.deepEqual(calls[1]?.body, {
    output_path: "openclaw.mcp.json",
    safe_root: ".",
    server_name: "agentpdf",
  });
});

test("AgentPDFClient exposes high-frequency PDF utility wrappers", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async (input, init) => {
      calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
      return jsonResponse({
        job_id: "job_util",
        status: "succeeded",
        tool: calls.at(-1)?.url.split("/v1/tools/")[1]?.split("/run")[0] ?? "unknown",
        artifacts: [],
        validation: null,
        warnings: [],
        usage: {},
        next_recommended_tools: [],
        error: null,
      });
    },
  });

  await client.inspectPages({ inputPath: "cover.pdf", pages: "1", renderCheck: true });
  await client.workflowPlan({ goal: "Chat with this PDF and cite answers.", inputPath: "cover.pdf" });
  await client.workflowRun({
    workflow: {
      steps: [{ step_id: "inspect", tool: "pdf.inspect.document", input: { path: "cover.pdf" } }],
    },
    dryRun: true,
  });
  await client.workflowReport({
    workflowRun: {
      run_id: "wfrun_node",
      status: "succeeded",
      planned_steps: 1,
      executed_steps: 1,
      failed_steps: 0,
      step_results: [],
    },
    outputPath: "workflow-report.md",
  });
  await client.imageToPdf({ imagePaths: ["cover.png"], outputPath: "cover.pdf" });
  await client.reorderPages({ inputPath: "cover.pdf", order: "1", outputPath: "reordered.pdf" });
  await client.insertBlankPages({
    inputPath: "reordered.pdf",
    afterPage: 1,
    count: 1,
    outputPath: "blank.pdf",
  });
  await client.nUp({ inputPath: "blank.pdf", perSheet: 2, outputPath: "n-up.pdf" });
  await client.booklet({ inputPath: "blank.pdf", outputPath: "booklet.pdf" });
  await client.compress({ inputPath: "blank.pdf", outputPath: "compressed.pdf" });
  await client.repair({ inputPath: "compressed.pdf", outputPath: "repaired.pdf" });
  await client.watermark({ inputPath: "cover.pdf", text: "CONFIDENTIAL", outputPath: "wm.pdf" });
  await client.addPageNumbers({ inputPath: "wm.pdf", outputPath: "numbered.pdf" });
  await client.validateOutput({ path: "numbered.pdf", expectedPages: 1 });
  await client.renderCheck({ path: "numbered.pdf", pages: "1" });
  await client.blankPageCheck({ path: "numbered.pdf", pages: "1" });
  await client.parseLite({ inputPath: "numbered.pdf" });
  await client.createFromPrompt({
    prompt: "Create a research brief about local PDF templates.",
    outputPath: "brief.pdf",
    template: "research_brief",
    stylePack: "paper_ink",
    colors: {
      primary: "#4f46e5",
      accent: "#f59e0b",
    },
    data: {
      sections: [{ heading: "Templates", body: "Agents can create PDFs locally." }],
    },
  });
  await client.createTemplatePreview({ template: "invoice", outputPath: "invoice-preview.pdf" });
  await client.createTemplates();
  await client.extractImages({ inputPath: "numbered.pdf", pages: "1", outDir: "images" });
  await client.ragIngest({
    inputPath: "numbered.pdf",
    indexPath: "numbered.index.json",
    maxChars: 80,
  });
  await client.ragQuery({ indexPath: "numbered.index.json", query: "What is cited?" });
  await client.ragSearch({ indexPath: "numbered.index.json", query: "cited evidence" });
  await client.ragCiteAnswer({ indexPath: "numbered.index.json", answer: "cited evidence", topK: 2 });
  await client.ragHighlightSources({
    indexPath: "numbered.index.json",
    answer: "cited evidence",
    outputPath: "numbered-highlighted.pdf",
  });
  await client.ragExportReport({
    indexPath: "numbered.index.json",
    question: "What is cited?",
    answer: "cited evidence",
    outputPath: "numbered-report.pdf",
    topK: 2,
  });
  await client.ragChat({
    inputPath: "numbered.pdf",
    question: "What is cited?",
    indexPath: "numbered-chat.index.json",
    reportOutputPath: "numbered-chat-report.pdf",
    highlightOutputPath: "numbered-chat-highlighted.pdf",
    topK: 2,
  });
  await client.buildContextPacket({
    contextItems: [
      { text: "Create a technical audit PDF.", role: "brief" },
      { path: "src/service.py", role: "code_evidence" },
    ],
    outputPath: "context.packet.json",
    title: "Audit Context",
    intent: "Compose a target PDF with evidence.",
  });
  await client.composeFromContext({
    contextPacketPath: "context.packet.json",
    profile: "technical_audit",
    outputPath: "technical-audit.pdf",
    renderer: "html",
    htmlOutputPath: "technical-audit.html",
  });
  await client.evidenceCoverageReport({
    compositionPath: "technical-audit.composition.json",
    outputPath: "technical-audit.coverage.json",
  });
  await client.evidenceMapSources({
    compositionPath: "technical-audit.composition.json",
    contextPacketPath: "context.packet.json",
    outputPath: "technical-audit.source-map.json",
  });
  await client.evidenceCiteClaims({
    claims: [
      {
        claim_id: "claim_latency",
        text: "Runtime metrics include latency evidence.",
        source_refs: ["ctx_002"],
      },
    ],
    sourceMapPath: "technical-audit.source-map.json",
    outputPath: "technical-audit.citations.json",
  });
  await client.patchPlan({
    inputPath: "technical-audit.pdf",
    operations: [
      {
        op: "append_table",
        title: "Runtime Metrics",
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"]],
        source_refs: ["ctx_002"],
      },
    ],
    outputPath: "technical-audit.patch.json",
    compositionPath: "technical-audit.composition.json",
    layerManifestPath: "technical-audit.layers.json",
    reason: "Append structured evidence.",
  });
  await client.patchPreview({
    patchManifestPath: "technical-audit.patch.json",
    outputPath: "technical-audit.patch-preview.json",
  });
  await client.patchApply({
    patchManifestPath: "technical-audit.patch.json",
    outputPath: "technical-audit-patched.pdf",
  });
  await client.patchVerify({
    patchManifestPath: "technical-audit.patch.json",
    patchedPath: "technical-audit-patched.pdf",
  });
  await client.pdfToJson({ inputPath: "numbered.pdf", outputPath: "numbered.ir.json" });
  await client.pdfToMarkdown({ inputPath: "numbered.pdf", outputPath: "numbered.md" });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.inspect.pages/run",
    "http://agentpdf.test/v1/tools/pdf.workflow.plan/run",
    "http://agentpdf.test/v1/tools/pdf.workflow.run/run",
    "http://agentpdf.test/v1/tools/pdf.workflow.report/run",
    "http://agentpdf.test/v1/tools/pdf.convert.image_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.organize.reorder_pages/run",
    "http://agentpdf.test/v1/tools/pdf.organize.insert_blank_pages/run",
    "http://agentpdf.test/v1/tools/pdf.organize.n_up/run",
    "http://agentpdf.test/v1/tools/pdf.organize.booklet/run",
    "http://agentpdf.test/v1/tools/pdf.optimize.compress/run",
    "http://agentpdf.test/v1/tools/pdf.optimize.repair/run",
    "http://agentpdf.test/v1/tools/pdf.edit.watermark/run",
    "http://agentpdf.test/v1/tools/pdf.edit.page_numbers/run",
    "http://agentpdf.test/v1/tools/pdf.validation.validate_output/run",
    "http://agentpdf.test/v1/tools/pdf.validation.render_check/run",
    "http://agentpdf.test/v1/tools/pdf.validation.blank_page_check/run",
    "http://agentpdf.test/v1/tools/pdf.ai.parse.lite/run",
    "http://agentpdf.test/v1/tools/pdf.ai.create.from_prompt/run",
    "http://agentpdf.test/v1/tools/pdf.ai.create.template_preview/run",
    "http://agentpdf.test/v1/tools/pdf.ai.create.templates/run",
    "http://agentpdf.test/v1/tools/pdf.convert.extract_images/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.ingest/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.query/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.search/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.cite_answer/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.highlight_sources/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.export_report/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.chat/run",
    "http://agentpdf.test/v1/tools/pdf.context.build_packet/run",
    "http://agentpdf.test/v1/tools/pdf.compose.from_context/run",
    "http://agentpdf.test/v1/tools/pdf.evidence.coverage_report/run",
    "http://agentpdf.test/v1/tools/pdf.evidence.map_sources/run",
    "http://agentpdf.test/v1/tools/pdf.evidence.cite_claims/run",
    "http://agentpdf.test/v1/tools/pdf.patch.plan/run",
    "http://agentpdf.test/v1/tools/pdf.patch.preview/run",
    "http://agentpdf.test/v1/tools/pdf.patch.apply/run",
    "http://agentpdf.test/v1/tools/pdf.patch.verify/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pdf_to_json/run",
    "http://agentpdf.test/v1/tools/pdf.convert.pdf_to_markdown/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    input_path: "cover.pdf",
    pages: "1",
    render_check: true,
  });
  assert.deepEqual(calls[1]?.body, {
    goal: "Chat with this PDF and cite answers.",
    input_path: "cover.pdf",
  });
  assert.deepEqual(calls[2]?.body, {
    workflow: {
      steps: [{ step_id: "inspect", tool: "pdf.inspect.document", input: { path: "cover.pdf" } }],
    },
    dry_run: true,
  });
  assert.deepEqual(calls[3]?.body, {
    workflow_run: {
      run_id: "wfrun_node",
      status: "succeeded",
      planned_steps: 1,
      executed_steps: 1,
      failed_steps: 0,
      step_results: [],
    },
    output_path: "workflow-report.md",
  });
  assert.deepEqual(calls[4]?.body, {
    image_paths: ["cover.png"],
    output_path: "cover.pdf",
  });
  assert.deepEqual(calls[5]?.body, {
    input_path: "cover.pdf",
    order: "1",
    output_path: "reordered.pdf",
  });
  assert.deepEqual(calls[6]?.body, {
    input_path: "reordered.pdf",
    after_page: 1,
    count: 1,
    output_path: "blank.pdf",
  });
  assert.deepEqual(calls[7]?.body, {
    input_path: "blank.pdf",
    per_sheet: 2,
    output_path: "n-up.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "blank.pdf",
    output_path: "booklet.pdf",
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "blank.pdf",
    output_path: "compressed.pdf",
  });
  assert.deepEqual(calls[10]?.body, {
    input_path: "compressed.pdf",
    output_path: "repaired.pdf",
  });
  assert.deepEqual(calls[11]?.body, {
    input_path: "cover.pdf",
    text: "CONFIDENTIAL",
    output_path: "wm.pdf",
  });
  assert.deepEqual(calls[12]?.body, {
    input_path: "wm.pdf",
    output_path: "numbered.pdf",
  });
  assert.deepEqual(calls[13]?.body, {
    path: "numbered.pdf",
    expected_pages: 1,
  });
  assert.deepEqual(calls[14]?.body, {
    path: "numbered.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[15]?.body, {
    path: "numbered.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[16]?.body, {
    input_path: "numbered.pdf",
  });
  assert.deepEqual(calls[17]?.body, {
    prompt: "Create a research brief about local PDF templates.",
    output_path: "brief.pdf",
    template: "research_brief",
    style_pack: "paper_ink",
    colors: {
      primary: "#4f46e5",
      accent: "#f59e0b",
    },
    data: {
      sections: [{ heading: "Templates", body: "Agents can create PDFs locally." }],
    },
  });
  assert.deepEqual(calls[18]?.body, {
    template: "invoice",
    output_path: "invoice-preview.pdf",
  });
  assert.deepEqual(calls[19]?.body, {
  });
  assert.deepEqual(calls[20]?.body, {
    input_path: "numbered.pdf",
    pages: "1",
    out_dir: "images",
  });
  assert.deepEqual(calls[21]?.body, {
    input_path: "numbered.pdf",
    index_path: "numbered.index.json",
    max_chars: 80,
  });
  assert.deepEqual(calls[22]?.body, {
    index_path: "numbered.index.json",
    query: "What is cited?",
  });
  assert.deepEqual(calls[23]?.body, {
    index_path: "numbered.index.json",
    query: "cited evidence",
  });
  assert.deepEqual(calls[24]?.body, {
    index_path: "numbered.index.json",
    answer: "cited evidence",
    top_k: 2,
  });
  assert.deepEqual(calls[25]?.body, {
    index_path: "numbered.index.json",
    answer: "cited evidence",
    output_path: "numbered-highlighted.pdf",
  });
  assert.deepEqual(calls[26]?.body, {
    index_path: "numbered.index.json",
    question: "What is cited?",
    answer: "cited evidence",
    output_path: "numbered-report.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[27]?.body, {
    input_path: "numbered.pdf",
    question: "What is cited?",
    index_path: "numbered-chat.index.json",
    report_output_path: "numbered-chat-report.pdf",
    highlight_output_path: "numbered-chat-highlighted.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[28]?.body, {
    context_items: [
      { text: "Create a technical audit PDF.", role: "brief" },
      { path: "src/service.py", role: "code_evidence" },
    ],
    output_path: "context.packet.json",
    title: "Audit Context",
    intent: "Compose a target PDF with evidence.",
  });
  assert.deepEqual(calls[29]?.body, {
    context_packet_path: "context.packet.json",
    profile: "technical_audit",
    output_path: "technical-audit.pdf",
    renderer: "html",
    html_output_path: "technical-audit.html",
  });
  assert.deepEqual(calls[30]?.body, {
    composition_path: "technical-audit.composition.json",
    output_path: "technical-audit.coverage.json",
  });
  assert.deepEqual(calls[31]?.body, {
    composition_path: "technical-audit.composition.json",
    context_packet_path: "context.packet.json",
    output_path: "technical-audit.source-map.json",
  });
  assert.deepEqual(calls[32]?.body, {
    claims: [
      {
        claim_id: "claim_latency",
        text: "Runtime metrics include latency evidence.",
        source_refs: ["ctx_002"],
      },
    ],
    source_map_path: "technical-audit.source-map.json",
    output_path: "technical-audit.citations.json",
  });
  assert.deepEqual(calls[33]?.body, {
    input_path: "technical-audit.pdf",
    operations: [
      {
        op: "append_table",
        title: "Runtime Metrics",
        columns: ["metric", "value"],
        rows: [["latency_ms", "42"]],
        source_refs: ["ctx_002"],
      },
    ],
    output_path: "technical-audit.patch.json",
    composition_path: "technical-audit.composition.json",
    layer_manifest_path: "technical-audit.layers.json",
    reason: "Append structured evidence.",
  });
  assert.deepEqual(calls[34]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit.patch-preview.json",
  });
  assert.deepEqual(calls[35]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[36]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    patched_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[37]?.body, {
    input_path: "numbered.pdf",
    output_path: "numbered.ir.json",
  });
  assert.deepEqual(calls[38]?.body, {
    input_path: "numbered.pdf",
    output_path: "numbered.md",
  });
});

test("AgentPDFClient returns failed ToolResult bodies instead of hiding them", async () => {
  const failed: ToolResult = {
    job_id: "job_failed",
    status: "failed",
    tool: "pdf.inspect.document",
    artifacts: [],
    validation: null,
    warnings: ["Input file not found"],
    usage: {},
    next_recommended_tools: [],
    error: { code: "file_not_found", message: "Input file not found" },
  };
  const client = new AgentPDFClient({
    baseUrl: "http://agentpdf.test",
    fetch: async () => jsonResponse(failed, 400),
  });

  const result = await client.inspectDocument({ path: "missing.pdf" });

  assert.equal(result.status, "failed");
  assert.equal(result.error?.code, "file_not_found");
});
