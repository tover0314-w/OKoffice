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

  assert.equal(await invoke(["inspect-pages", "cover.pdf", "--pages", "1", "--render-check"]), 0);
  assert.equal(
    await invoke(["workflow-plan", "--goal", "Chat with this PDF and cite answers.", "--input-path", "cover.pdf"]),
    0,
  );
  assert.equal(
    await invoke([
      "workflow-run",
      "--payload",
      "{\"steps\":[{\"step_id\":\"inspect\",\"tool\":\"pdf.inspect.document\",\"input\":{\"path\":\"cover.pdf\"}}]}",
      "--artifact-dir",
      "workflow-artifacts",
      "--binding",
      "<question>=What is covered?",
      "--dry-run",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "workflow-report",
      "--payload",
      "{\"run_id\":\"wfrun_node\",\"status\":\"succeeded\",\"planned_steps\":1,\"executed_steps\":1,\"failed_steps\":0,\"step_results\":[]}",
      "-o",
      "workflow-report.md",
    ]),
    0,
  );
  assert.equal(await invoke(["image-to-pdf", "cover.png", "-o", "cover.pdf"]), 0);
  assert.equal(await invoke(["reorder-pages", "cover.pdf", "--order", "1", "-o", "reordered.pdf"]), 0);
  assert.equal(
    await invoke([
      "insert-blank-pages",
      "reordered.pdf",
      "--after-page",
      "1",
      "--count",
      "1",
      "-o",
      "blank.pdf",
    ]),
    0,
  );
  assert.equal(await invoke(["compress", "blank.pdf", "-o", "compressed.pdf"]), 0);
  assert.equal(await invoke(["repair", "compressed.pdf", "-o", "repaired.pdf"]), 0);
  assert.equal(
    await invoke(["watermark", "cover.pdf", "--text", "CONFIDENTIAL", "-o", "wm.pdf"]),
    0,
  );
  assert.equal(await invoke(["page-numbers", "wm.pdf", "-o", "numbered.pdf"]), 0);
  assert.equal(await invoke(["validate", "numbered.pdf", "--expected-pages", "1"]), 0);
  assert.equal(await invoke(["render-check", "numbered.pdf", "--pages", "1"]), 0);
  assert.equal(await invoke(["blank-page-check", "numbered.pdf", "--pages", "1"]), 0);
  assert.equal(await invoke(["extract-images", "numbered.pdf", "--pages", "1", "--out-dir", "images"]), 0);

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.inspect.pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.plan/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.run/run",
    "http://127.0.0.1:7331/v1/tools/pdf.workflow.report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.image_to_pdf/run",
    "http://127.0.0.1:7331/v1/tools/pdf.organize.reorder_pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.organize.insert_blank_pages/run",
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.compress/run",
    "http://127.0.0.1:7331/v1/tools/pdf.optimize.repair/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.watermark/run",
    "http://127.0.0.1:7331/v1/tools/pdf.edit.page_numbers/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.validate_output/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.render_check/run",
    "http://127.0.0.1:7331/v1/tools/pdf.validation.blank_page_check/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.extract_images/run",
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
      artifact_dir: "workflow-artifacts",
      bindings: {
        "<question>": "What is covered?",
      },
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
    pages: "1",
    out_dir: "images",
  });
});

test("runCli exposes lite parse and local RAG commands", async () => {
  const calls: Array<{ url: string; body: unknown }> = [];

  async function invoke(args: string[]): Promise<number> {
    return runCli(args, {
      fetch: async (input, init) => {
        calls.push({ url: String(input), body: JSON.parse(String(init?.body)) });
        return jsonResponse({
          job_id: "job_cli_ai",
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

  assert.equal(await invoke(["parse-lite", "report.pdf"]), 0);
  assert.equal(await invoke(["pdf-to-json", "report.pdf", "-o", "report.ir.json"]), 0);
  assert.equal(await invoke(["pdf-to-markdown", "report.pdf", "-o", "report.md"]), 0);
  assert.equal(
    await invoke(["rag-ingest", "report.pdf", "--index", "report.index.json", "--max-chars", "80"]),
    0,
  );
  assert.equal(await invoke(["rag-query", "report.index.json", "--query", "What is cited?"]), 0);
  assert.equal(await invoke(["rag-search", "report.index.json", "--query", "cited evidence"]), 0);
  assert.equal(await invoke(["rag-cite-answer", "report.index.json", "--answer", "cited evidence"]), 0);
  assert.equal(
    await invoke([
      "rag-highlight-sources",
      "report.index.json",
      "--answer",
      "cited evidence",
      "-o",
      "report-highlighted.pdf",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "rag-export-report",
      "report.index.json",
      "--question",
      "What is cited?",
      "--answer",
      "cited evidence",
      "-o",
      "report-rag.pdf",
      "--top-k",
      "2",
    ]),
    0,
  );
  assert.equal(
    await invoke([
      "rag-chat",
      "report.pdf",
      "--question",
      "What is cited?",
      "--index",
      "report-chat.index.json",
      "--report-output",
      "report-chat.pdf",
      "--highlight-output",
      "report-chat-highlighted.pdf",
      "--top-k",
      "2",
    ]),
    0,
  );

  assert.deepEqual(calls.map((call) => call.url), [
    "http://127.0.0.1:7331/v1/tools/pdf.ai.parse.lite/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_json/run",
    "http://127.0.0.1:7331/v1/tools/pdf.convert.pdf_to_markdown/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.ingest/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.query/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.search/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.cite_answer/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.highlight_sources/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.export_report/run",
    "http://127.0.0.1:7331/v1/tools/pdf.ai.rag.chat/run",
  ]);
  assert.deepEqual(calls[0]?.body, { input_path: "report.pdf" });
  assert.deepEqual(calls[1]?.body, {
    input_path: "report.pdf",
    output_path: "report.ir.json",
  });
  assert.deepEqual(calls[2]?.body, {
    input_path: "report.pdf",
    output_path: "report.md",
  });
  assert.deepEqual(calls[3]?.body, {
    input_path: "report.pdf",
    index_path: "report.index.json",
    max_chars: 80,
  });
  assert.deepEqual(calls[4]?.body, {
    index_path: "report.index.json",
    query: "What is cited?",
  });
  assert.deepEqual(calls[5]?.body, {
    index_path: "report.index.json",
    query: "cited evidence",
  });
  assert.deepEqual(calls[6]?.body, {
    index_path: "report.index.json",
    answer: "cited evidence",
  });
  assert.deepEqual(calls[7]?.body, {
    index_path: "report.index.json",
    answer: "cited evidence",
    output_path: "report-highlighted.pdf",
  });
  assert.deepEqual(calls[8]?.body, {
    index_path: "report.index.json",
    question: "What is cited?",
    answer: "cited evidence",
    output_path: "report-rag.pdf",
    top_k: 2,
  });
  assert.deepEqual(calls[9]?.body, {
    input_path: "report.pdf",
    question: "What is cited?",
    index_path: "report-chat.index.json",
    report_output_path: "report-chat.pdf",
    highlight_output_path: "report-chat-highlighted.pdf",
    top_k: 2,
  });
});
