export type JsonObject = Record<string, unknown>;

export type ToolRunStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface AgentPDFError {
  code: string;
  message: string;
  details?: JsonObject | null;
}

export interface Artifact {
  artifact_id: string;
  path: string;
  mime_type: string;
  size_bytes?: number | null;
  sha256?: string | null;
  source_tool?: string | null;
  page_count?: number | null;
  created_at?: string | null;
  retention_hint?: string | null;
}

export interface ValidationCheck {
  name: string;
  status: "passed" | "failed" | "warning" | "skipped";
  details?: JsonObject;
  message?: string | null;
}

export interface ValidationReport {
  status: "passed" | "failed" | "warning" | "skipped";
  checks: ValidationCheck[];
  page_count?: number | null;
  warnings?: string[];
}

export interface ToolResult<TUsage extends JsonObject = JsonObject> {
  job_id: string;
  status: ToolRunStatus;
  tool: string;
  artifacts: Artifact[];
  validation?: ValidationReport | null;
  warnings: string[];
  usage: TUsage;
  next_recommended_tools: string[];
  data?: JsonObject | null;
  error?: AgentPDFError | null;
}

export interface ToolSpec {
  name: string;
  status: string;
  description: string;
  category?: string | null;
  interfaces: string[];
  input_schema?: JsonObject | null;
  output_schema?: JsonObject | null;
  implemented: boolean;
}

export interface ToolManifest {
  manifest_version: string;
  tools: ToolSpec[];
}

export interface InspectDocumentInput {
  path: string;
}

export interface InspectPagesInput {
  inputPath: string;
  pages?: string;
  renderCheck?: boolean;
}

export interface WorkflowPlanInput {
  goal: string;
  inputPath?: string;
}

export interface WorkflowRunInput {
  workflow: JsonObject;
  dryRun?: boolean;
}

export interface WorkflowReportInput {
  workflowRun: JsonObject;
  outputPath?: string;
}

export interface MergePdfInput {
  inputPaths: string[];
  outputPath: string;
}

export interface ReorderPagesInput {
  inputPath: string;
  order: string;
  outputPath: string;
}

export interface InsertBlankPagesInput {
  inputPath: string;
  afterPage: number;
  outputPath: string;
  count?: number;
}

export interface OptimizePdfInput {
  inputPath: string;
  outputPath: string;
}

export interface ImageToPdfInput {
  imagePaths: string[];
  outputPath: string;
}

export interface WatermarkInput {
  inputPath: string;
  text: string;
  outputPath: string;
  pages?: string;
  fontSize?: number;
  opacity?: number;
  angle?: number;
}

export interface PageNumbersInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
  template?: string;
  fontSize?: number;
}

export interface CreateTextPdfInput {
  text: string;
  outputPath: string;
  title?: string;
}

export interface CreateMarkdownPdfInput {
  markdown: string;
  outputPath: string;
  title?: string;
  stylePack?: string;
}

export interface ValidateOutputInput {
  path: string;
  expectedPages?: number;
}

export interface RenderCheckInput {
  path: string;
  pages?: string;
}

export interface ExtractImagesInput {
  inputPath: string;
  pages?: string;
  outDir?: string;
}

export interface BlankPageCheckInput {
  path: string;
  pages?: string;
}

export interface ParseLiteInput {
  inputPath: string;
  pages?: string;
}

export interface RagIngestInput {
  inputPath: string;
  indexPath: string;
  pages?: string;
  maxChars?: number;
  overlapChars?: number;
}

export interface RagQueryInput {
  indexPath: string;
  query: string;
  topK?: number;
}

export interface RagChatInput {
  inputPath: string;
  question: string;
  indexPath?: string;
  reportOutputPath?: string;
  highlightOutputPath?: string;
  pages?: string;
  topK?: number;
  maxChars?: number;
  overlapChars?: number;
  stylePack?: string;
  highlightColor?: string;
}

export interface RagSearchInput {
  indexPath: string;
  query: string;
  topK?: number;
}

export interface RagCiteAnswerInput {
  indexPath: string;
  answer: string;
  topK?: number;
}

export interface RagHighlightSourcesInput {
  indexPath: string;
  outputPath: string;
  answer?: string;
  query?: string;
  topK?: number;
  highlightColor?: string;
}

export interface RagExportReportInput {
  indexPath: string;
  outputPath: string;
  question: string;
  answer?: string;
  topK?: number;
  includeCitations?: boolean;
  title?: string;
  stylePack?: string;
}

export interface PdfToJsonInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}

export interface PdfToMarkdownInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}
