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

export interface SetupClaudeCodeInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
  scope?: "project" | "local" | "user";
}

export interface SetupCodexInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
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

export interface BuildContextPacketInput {
  contextItems: JsonObject[];
  outputPath: string;
  title?: string;
  intent?: string;
}

export interface IngestContextInput {
  contextItem: JsonObject;
  outputPath?: string;
}

export interface ContextPacketInput {
  contextItems: JsonObject[];
  outputPath: string;
  title?: string;
  intent?: string;
}

export interface ClassifyContextInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath?: string;
}

export interface CodeSnapshotInput {
  path: string;
  outputPath?: string;
  label?: string;
  role?: string;
  contextItemId?: string;
  lineStart?: number;
  lineEnd?: number;
  repositoryRoot?: string;
  includeDependencies?: boolean;
}

export interface DataProfileInput {
  path: string;
  outputPath?: string;
  label?: string;
  role?: string;
  contextItemId?: string;
  sheet?: string;
  maxRows?: number;
}

export interface ComposeFromContextInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath: string;
  stylePack?: string;
  title?: string;
}

export interface ComposePlanInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath?: string;
  stylePack?: string;
  title?: string;
}

export interface ComposeRenderIrInput {
  composition?: JsonObject;
  compositionPath?: string;
  outputPath: string;
  stylePack?: string;
  title?: string;
}

export interface ComposeBlockInputBase {
  inputPath: string;
  outputPath: string;
  title: string;
  sourceRefs?: string[];
  blockId?: string;
  targetSlot?: string;
  compositionPath?: string;
  layerManifestPath?: string;
  manifestOutputPath?: string;
}

export interface ComposeAddCodeBlockInput extends ComposeBlockInputBase {
  code: string;
  language?: string;
}

export interface ComposeAddTableInput extends ComposeBlockInputBase {
  columns: string[];
  rows: string[][];
}

export interface ComposeAddFigureInput extends ComposeBlockInputBase {
  imagePath: string;
  caption?: string;
}

export interface ComposeAddAppendixInput extends ComposeBlockInputBase {
  markdown: string;
}

export interface ComposeAddCitationInput extends ComposeBlockInputBase {
  source: string;
  quote?: string;
  page?: string;
}

export interface ComposeAddMediaReferenceInput extends ComposeBlockInputBase {
  mediaPath: string;
  mediaKind?: "audio" | "video" | "media" | string;
  transcriptExcerpt?: string;
  durationSeconds?: number;
  chapterCount?: number;
  keyframeCount?: number;
}

export interface ComposeAddSlideInput extends ComposeBlockInputBase {
  body?: string[];
  subtitle?: string;
  code?: string;
  table?: JsonObject;
  imagePath?: string;
}

export interface TargetProfilesInput {
  outputPath?: string;
}

export interface SelectTargetProfileInput {
  goal?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  preferredProfile?: string;
  profile?: string;
  outputPath?: string;
}

export interface ValidateTargetProfileInput {
  targetProfile?: JsonObject | string;
  profile?: string;
  outputPath?: string;
}

export interface EvidenceCoverageReportInput {
  composition?: JsonObject;
  compositionPath?: string;
  outputPath?: string;
}

export interface EvidenceMapSourcesInput {
  composition?: JsonObject;
  compositionPath?: string;
  blocks?: JsonObject[];
  claims?: JsonObject[];
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  outputPath?: string;
}

export interface ContextPacketReportInput {
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  outputPath: string;
  reportOutputPath?: string;
  title?: string;
  stylePack?: string;
}

export interface ExportBundleInput {
  artifactPaths: string[];
  outputPath: string;
  title?: string;
  metadata?: JsonObject;
}

export interface VerifyBundleInput {
  bundlePath: string;
}

export interface PatchPlanInput {
  inputPath: string;
  operations: JsonObject[];
  outputPath: string;
  compositionPath?: string;
  layerManifestPath?: string;
  reason?: string;
}

export interface PatchPreviewInput {
  patchManifest?: JsonObject;
  patchManifestPath?: string;
  outputPath?: string;
}

export interface PatchApplyInput {
  patchManifest?: JsonObject;
  patchManifestPath?: string;
  outputPath: string;
}

export interface PatchVerifyInput {
  patchManifest?: JsonObject;
  patchManifestPath?: string;
  patchedPath: string;
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

export interface CreateFromPromptInput {
  prompt: string;
  outputPath: string;
  template?: string;
  stylePack?: string;
  colors?: Record<string, string>;
  data?: JsonObject;
  title?: string;
}

export interface CreateTemplatePreviewInput {
  template: string;
  outputPath: string;
  stylePack?: string;
  colors?: Record<string, string>;
  data?: JsonObject;
}

export interface CreateTemplatePacksInput {
  outputPath?: string;
}

export interface ValidateTemplatePackInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  outputPath?: string;
}

export interface PlanTemplatePackInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  plannedOutputPath?: string;
  outputPath?: string;
  preferredTemplateId?: string;
  preferredColorScheme?: string;
}

export interface CreateAgentInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  targetProfile?: JsonObject | string;
  profile?: string;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  outputPath: string;
  planOutputPath?: string;
  coverageOutputPath?: string;
  contextClassificationOutputPath?: string;
  contextReportOutputPath?: string;
  contextReportJsonOutputPath?: string;
  bundleOutputPath?: string;
  preferredTemplateId?: string;
  preferredColorScheme?: string;
  title?: string;
  prompt?: string;
  stylePack?: string;
}

export interface CreateFromTemplatePackInput {
  templatePack?: JsonObject | string;
  templatePackPath?: string;
  templateId: string;
  outputPath: string;
  colorScheme?: string;
  data?: JsonObject;
  contextPacket?: JsonObject | string;
  contextPacketPath?: string;
  title?: string;
  prompt?: string;
  stylePack?: string;
}

export interface ValidateOutputInput {
  path: string;
  expectedPages?: number;
}

export interface PageCountCheckInput {
  path: string;
  expectedPages: number;
}

export interface RenderCheckInput {
  path: string;
  pages?: string;
}

export interface MetadataPageInfoInput {
  inputPath: string;
  pages?: string;
}

export interface SecurityRemoveMetadataInput {
  inputPath: string;
  outputPath: string;
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
