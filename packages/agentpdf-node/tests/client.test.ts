import assert from "node:assert/strict";
import test from "node:test";

import { AgentPDFClient } from "../src/index.js";
import type { ToolManifest, ToolResult } from "../src/index.js";

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
      url: "http://agentpdf.test/v1/tools/pdf.security.remove_metadata/run",
      body: { input_path: "report.pdf", output_path: "report.clean.pdf" },
    },
  ]);
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
        tool: calls.length === 1 ? "pdf.context.code_snapshot" : "pdf.context.data_profile",
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

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.context.code_snapshot/run",
    "http://agentpdf.test/v1/tools/pdf.context.data_profile/run",
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
      },
    },
  ]);
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
    output_path: "compressed.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    input_path: "compressed.pdf",
    output_path: "repaired.pdf",
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "cover.pdf",
    text: "CONFIDENTIAL",
    output_path: "wm.pdf",
  });
  assert.deepEqual(calls[10]?.body, {
    input_path: "wm.pdf",
    output_path: "numbered.pdf",
  });
  assert.deepEqual(calls[11]?.body, {
    path: "numbered.pdf",
    expected_pages: 1,
  });
  assert.deepEqual(calls[12]?.body, {
    path: "numbered.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[13]?.body, {
    path: "numbered.pdf",
    pages: "1",
  });
  assert.deepEqual(calls[14]?.body, {
    input_path: "numbered.pdf",
  });
  assert.deepEqual(calls[15]?.body, {
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
  assert.deepEqual(calls[16]?.body, {
    template: "invoice",
    output_path: "invoice-preview.pdf",
  });
  assert.deepEqual(calls[17]?.body, {
  });
  assert.deepEqual(calls[18]?.body, {
    input_path: "numbered.pdf",
    pages: "1",
    out_dir: "images",
  });
  assert.deepEqual(calls[19]?.body, {
    input_path: "numbered.pdf",
    index_path: "numbered.index.json",
    max_chars: 80,
  });
  assert.deepEqual(calls[20]?.body, {
    index_path: "numbered.index.json",
    query: "What is cited?",
  });
  assert.deepEqual(calls[21]?.body, {
    index_path: "numbered.index.json",
    query: "cited evidence",
  });
  assert.deepEqual(calls[22]?.body, {
    index_path: "numbered.index.json",
    answer: "cited evidence",
    top_k: 2,
  });
  assert.deepEqual(calls[23]?.body, {
    index_path: "numbered.index.json",
    answer: "cited evidence",
    output_path: "numbered-highlighted.pdf",
  });
  assert.deepEqual(calls[24]?.body, {
    index_path: "numbered.index.json",
    question: "What is cited?",
    answer: "cited evidence",
    output_path: "numbered-report.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[25]?.body, {
    input_path: "numbered.pdf",
    question: "What is cited?",
    index_path: "numbered-chat.index.json",
    report_output_path: "numbered-chat-report.pdf",
    highlight_output_path: "numbered-chat-highlighted.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[26]?.body, {
    context_items: [
      { text: "Create a technical audit PDF.", role: "brief" },
      { path: "src/service.py", role: "code_evidence" },
    ],
    output_path: "context.packet.json",
    title: "Audit Context",
    intent: "Compose a target PDF with evidence.",
  });
  assert.deepEqual(calls[27]?.body, {
    context_packet_path: "context.packet.json",
    profile: "technical_audit",
    output_path: "technical-audit.pdf",
  });
  assert.deepEqual(calls[28]?.body, {
    composition_path: "technical-audit.composition.json",
    output_path: "technical-audit.coverage.json",
  });
  assert.deepEqual(calls[29]?.body, {
    composition_path: "technical-audit.composition.json",
    context_packet_path: "context.packet.json",
    output_path: "technical-audit.source-map.json",
  });
  assert.deepEqual(calls[30]?.body, {
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
  assert.deepEqual(calls[31]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit.patch-preview.json",
  });
  assert.deepEqual(calls[32]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    output_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[33]?.body, {
    patch_manifest_path: "technical-audit.patch.json",
    patched_path: "technical-audit-patched.pdf",
  });
  assert.deepEqual(calls[34]?.body, {
    input_path: "numbered.pdf",
    output_path: "numbered.ir.json",
  });
  assert.deepEqual(calls[35]?.body, {
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
