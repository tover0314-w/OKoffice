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
    "http://agentpdf.test/v1/tools/pdf.convert.extract_images/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.ingest/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.query/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.search/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.cite_answer/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.highlight_sources/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.export_report/run",
    "http://agentpdf.test/v1/tools/pdf.ai.rag.chat/run",
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
    input_path: "numbered.pdf",
    pages: "1",
    out_dir: "images",
  });
  assert.deepEqual(calls[16]?.body, {
    input_path: "numbered.pdf",
    index_path: "numbered.index.json",
    max_chars: 80,
  });
  assert.deepEqual(calls[17]?.body, {
    index_path: "numbered.index.json",
    query: "What is cited?",
  });
  assert.deepEqual(calls[18]?.body, {
    index_path: "numbered.index.json",
    query: "cited evidence",
  });
  assert.deepEqual(calls[19]?.body, {
    index_path: "numbered.index.json",
    answer: "cited evidence",
    top_k: 2,
  });
  assert.deepEqual(calls[20]?.body, {
    index_path: "numbered.index.json",
    answer: "cited evidence",
    output_path: "numbered-highlighted.pdf",
  });
  assert.deepEqual(calls[21]?.body, {
    index_path: "numbered.index.json",
    question: "What is cited?",
    answer: "cited evidence",
    output_path: "numbered-report.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[22]?.body, {
    input_path: "numbered.pdf",
    question: "What is cited?",
    index_path: "numbered-chat.index.json",
    report_output_path: "numbered-chat-report.pdf",
    highlight_output_path: "numbered-chat-highlighted.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[23]?.body, {
    input_path: "numbered.pdf",
    output_path: "numbered.ir.json",
  });
  assert.deepEqual(calls[24]?.body, {
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
