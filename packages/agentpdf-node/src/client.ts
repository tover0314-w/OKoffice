import type {
  CreateMarkdownPdfInput,
  CreateTextPdfInput,
  InspectDocumentInput,
  JsonObject,
  MergePdfInput,
  ToolManifest,
  ToolResult,
  ToolSpec,
} from "./types.js";

export type AgentPDFFetch = (input: string | URL, init?: RequestInit) => Promise<Response>;

export interface AgentPDFClientOptions {
  baseUrl?: string;
  fetch?: AgentPDFFetch;
}

export class AgentPDFHttpError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "AgentPDFHttpError";
    this.status = status;
    this.body = body;
  }
}

const DEFAULT_BASE_URL = "http://127.0.0.1:7331";

export class AgentPDFClient {
  readonly baseUrl: string;
  private readonly fetchImpl: AgentPDFFetch;

  constructor(options: AgentPDFClientOptions = {}) {
    this.baseUrl = normalizeBaseUrl(
      options.baseUrl ?? process.env.AGENTPDF_BASE_URL ?? DEFAULT_BASE_URL,
    );
    const fetchImpl = options.fetch ?? globalThis.fetch;
    if (typeof fetchImpl !== "function") {
      throw new Error("AgentPDFClient requires a fetch implementation.");
    }
    this.fetchImpl = fetchImpl.bind(globalThis) as AgentPDFFetch;
  }

  async listTools(): Promise<ToolManifest> {
    return this.getJson<ToolManifest>("/v1/tools");
  }

  async getTool(toolName: string): Promise<ToolSpec> {
    return this.getJson<ToolSpec>(`/v1/tools/${encodeURIComponent(toolName)}`);
  }

  async runTool<TUsage extends JsonObject = JsonObject>(
    toolName: string,
    payload: JsonObject,
  ): Promise<ToolResult<TUsage>> {
    return this.postJson<ToolResult<TUsage>>(
      `/v1/tools/${encodeURIComponent(toolName)}/run`,
      payload,
    );
  }

  async inspectDocument(input: InspectDocumentInput): Promise<ToolResult> {
    return this.runTool("pdf.inspect.document", { path: input.path });
  }

  async merge(input: MergePdfInput): Promise<ToolResult> {
    return this.runTool("pdf.organize.merge", {
      input_paths: input.inputPaths,
      output_path: input.outputPath,
    });
  }

  async createTextPdf(input: CreateTextPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.text_to_pdf", {
      text: input.text,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
    });
  }

  async createMarkdownPdf(input: CreateMarkdownPdfInput): Promise<ToolResult> {
    return this.runTool("pdf.convert.markdown_to_pdf", {
      markdown: input.markdown,
      output_path: input.outputPath,
      ...(input.title ? { title: input.title } : {}),
      ...(input.stylePack ? { style_pack: input.stylePack } : {}),
    });
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await this.fetchImpl(this.url(path), {
      headers: { accept: "application/json" },
    });
    return parseJsonResponse<T>(response);
  }

  private async postJson<T>(path: string, payload: JsonObject): Promise<T> {
    const response = await this.fetchImpl(this.url(path), {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return parseJsonResponse<T>(response);
  }

  private url(path: string): string {
    return `${this.baseUrl}${path}`;
  }
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const raw = await response.text();
  const body = raw ? (JSON.parse(raw) as unknown) : null;
  if (!response.ok && !isToolResult(body)) {
    throw new AgentPDFHttpError(
      `AgentPDF API request failed with HTTP ${response.status}`,
      response.status,
      body,
    );
  }
  return body as T;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function isToolResult(value: unknown): value is ToolResult {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ToolResult>;
  return (
    typeof candidate.job_id === "string" &&
    typeof candidate.status === "string" &&
    typeof candidate.tool === "string"
  );
}
