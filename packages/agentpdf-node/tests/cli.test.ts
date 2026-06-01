import assert from "node:assert/strict";
import test from "node:test";

import { runCli } from "../src/cli.js";
import type { ToolResult } from "../src/index.js";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("runCli sends generic tool payloads to the local API", async () => {
  const toolResult: ToolResult = {
    job_id: "job_cli",
    status: "succeeded",
    tool: "pdf.convert.text_to_pdf",
    artifacts: [],
    validation: null,
    warnings: [],
    usage: {},
    next_recommended_tools: [],
    error: null,
  };
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    [
      "--base-url",
      "http://agentpdf.test",
      "run",
      "pdf.convert.text_to_pdf",
      "--payload",
      "{\"text\":\"hello\",\"output_path\":\"out.pdf\"}",
    ],
    {
      fetch: async (_input, init) => {
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse(toolResult);
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    },
  );

  assert.equal(code, 0);
  assert.deepEqual(postedBody, { text: "hello", output_path: "out.pdf" });
  assert.equal(JSON.parse(output[0] ?? "{}").tool, "pdf.convert.text_to_pdf");
});

test("runCli exposes a convenient create-text command", async () => {
  const output: string[] = [];
  let postedBody: unknown;

  const code = await runCli(
    ["create-text", "--text", "Hello Node", "-o", "node.pdf"],
    {
      fetch: async (_input, init) => {
        postedBody = JSON.parse(String(init?.body));
        return jsonResponse({
          job_id: "job_create_text",
          status: "succeeded",
          tool: "pdf.convert.text_to_pdf",
          artifacts: [],
          validation: null,
          warnings: [],
          usage: {},
          next_recommended_tools: [],
          error: null,
        });
      },
      stdout: (line) => output.push(line),
      stderr: (line) => output.push(`ERR:${line}`),
    },
  );

  assert.equal(code, 0);
  assert.deepEqual(postedBody, { text: "Hello Node", output_path: "node.pdf" });
  assert.equal(JSON.parse(output[0] ?? "{}").status, "succeeded");
});

test("runCli exposes high-frequency PDF utility commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_util",
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
      stdout: () => undefined,
      stderr: () => undefined,
    });
  }

  assert.equal(await invoke(["image-to-pdf", "cover.png", "-o", "cover.pdf"]), 0);
  assert.equal(
    await invoke(["watermark", "cover.pdf", "--text", "CONFIDENTIAL", "-o", "wm.pdf"]),
    0,
  );
  assert.equal(await invoke(["page-numbers", "wm.pdf", "-o", "numbered.pdf"]), 0);
  assert.equal(await invoke(["validate", "numbered.pdf", "--expected-pages", "1"]), 0);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.convert.image_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.watermark/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.page_numbers/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.validate_output/run",
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
