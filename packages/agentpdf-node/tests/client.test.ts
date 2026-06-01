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

  await client.imageToPdf({ imagePaths: ["cover.png"], outputPath: "cover.pdf" });
  await client.watermark({ inputPath: "cover.pdf", text: "CONFIDENTIAL", outputPath: "wm.pdf" });
  await client.addPageNumbers({ inputPath: "wm.pdf", outputPath: "numbered.pdf" });
  await client.validateOutput({ path: "numbered.pdf", expectedPages: 1 });

  assert.deepEqual(calls.map((call) => call.url), [
    "http://agentpdf.test/v1/tools/pdf.convert.image_to_pdf/run",
    "http://agentpdf.test/v1/tools/pdf.edit.watermark/run",
    "http://agentpdf.test/v1/tools/pdf.edit.page_numbers/run",
    "http://agentpdf.test/v1/tools/pdf.validation.validate_output/run",
  ]);
  assert.deepEqual(calls[0]?.body, {
    image_paths: ["cover.png"],
    output_path: "cover.pdf",
  });
  assert.deepEqual(calls[1]?.body, {
    input_path: "cover.pdf",
    text: "CONFIDENTIAL",
    output_path: "wm.pdf",
  });
  assert.deepEqual(calls[2]?.body, {
    input_path: "wm.pdf",
    output_path: "numbered.pdf",
  });
  assert.deepEqual(calls[3]?.body, {
    path: "numbered.pdf",
    expected_pages: 1,
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
