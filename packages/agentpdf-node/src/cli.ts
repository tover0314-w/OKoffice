#!/usr/bin/env node
import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { AgentPDFClient } from "./client.js";
import type { AgentPDFFetch } from "./client.js";
import type { JsonObject, ToolResult } from "./types.js";

export interface CliRuntime {
  fetch?: AgentPDFFetch;
  stdout?: (line: string) => void;
  stderr?: (line: string) => void;
}

class UsageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UsageError";
  }
}

export async function runCli(
  argv: string[] = process.argv.slice(2),
  runtime: CliRuntime = {},
): Promise<number> {
  const args = [...argv];
  const stdout = runtime.stdout ?? ((line: string) => process.stdout.write(`${line}\n`));
  const stderr = runtime.stderr ?? ((line: string) => process.stderr.write(`${line}\n`));

  try {
    const baseUrl = takeOption(args, ["--base-url"]);
    const command = args.shift();
    if (!command || command === "--help" || command === "-h") {
      stdout(helpText());
      return 0;
    }

    const client = new AgentPDFClient({ baseUrl, fetch: runtime.fetch });
    if (command === "tools") {
      stdout(JSON.stringify(await client.listTools(), null, 2));
      return 0;
    }
    if (command === "run") {
      const toolName = args.shift();
      if (!toolName) {
        throw new UsageError("Missing tool name for run.");
      }
      const payload = parsePayload(takeRequiredOption(args, ["--payload"]));
      return emitResult(await client.runTool(toolName, payload), stdout);
    }
    if (command === "inspect") {
      const path = args.shift();
      if (!path) {
        throw new UsageError("Missing PDF path for inspect.");
      }
      return emitResult(await client.inspectDocument({ path }), stdout);
    }
    if (command === "create-text") {
      const text = takeRequiredOption(args, ["--text"]);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      const title = takeOption(args, ["--title"]);
      return emitResult(await client.createTextPdf({ text, outputPath, title }), stdout);
    }
    if (command === "create-markdown") {
      const markdown = await readMarkdownOption(args);
      const outputPath = takeRequiredOption(args, ["--output", "-o"]);
      const title = takeOption(args, ["--title"]);
      const stylePack = takeOption(args, ["--style-pack"]);
      return emitResult(
        await client.createMarkdownPdf({ markdown, outputPath, title, stylePack }),
        stdout,
      );
    }

    throw new UsageError(`Unknown command: ${command}`);
  } catch (error) {
    stderr(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

function emitResult(result: ToolResult, stdout: (line: string) => void): number {
  stdout(JSON.stringify(result, null, 2));
  return result.status === "failed" ? 1 : 0;
}

function takeRequiredOption(args: string[], names: string[]): string {
  const value = takeOption(args, names);
  if (!value) {
    throw new UsageError(`Missing required option: ${names[0]}`);
  }
  return value;
}

function takeOption(args: string[], names: string[]): string | undefined {
  const index = args.findIndex((arg) => names.includes(arg));
  if (index === -1) {
    return undefined;
  }
  const value = args[index + 1];
  if (!value) {
    throw new UsageError(`Missing value for option: ${args[index]}`);
  }
  args.splice(index, 2);
  return value;
}

function parsePayload(raw: string): JsonObject {
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new UsageError("--payload must be a JSON object.");
  }
  return parsed as JsonObject;
}

async function readMarkdownOption(args: string[]): Promise<string> {
  const inline = takeOption(args, ["--markdown"]);
  if (inline !== undefined) {
    return inline;
  }
  const markdownFile = takeOption(args, ["--markdown-file"]);
  if (markdownFile) {
    return readFile(markdownFile, "utf-8");
  }
  throw new UsageError("Missing --markdown or --markdown-file for create-markdown.");
}

function helpText(): string {
  return [
    "agentpdf-node: TypeScript/Node client for a local okpdf REST server",
    "",
    "Commands:",
    "  agentpdf-node tools [--base-url URL]",
    "  agentpdf-node run TOOL --payload '{...}' [--base-url URL]",
    "  agentpdf-node inspect PATH [--base-url URL]",
    "  agentpdf-node create-text --text TEXT -o OUT.pdf [--title TITLE]",
    "  agentpdf-node create-markdown --markdown '# Title' -o OUT.pdf",
    "  agentpdf-node create-markdown --markdown-file input.md -o OUT.pdf",
  ].join("\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runCli().then((code) => {
    process.exitCode = code;
  });
}
