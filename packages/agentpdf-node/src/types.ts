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

export interface SetupKiloCodeInput {
  outputPath?: string;
  safeRoot?: string;
  command?: string;
  argsPrefix?: string[];
  serverName?: string;
}

export interface SetupOpenClawInput {
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

export interface InspectHealthInput {
  inputPath: string;
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

export interface AuthoringBrief extends JsonObject {
  topic?: string;
  goal?: string;
  audience?: string;
  page_count?: number;
  deliverable?: string;
}

export interface EvidenceCard extends JsonObject {
  id?: string;
  claim?: string;
  evidence?: string;
  source_title?: string;
  source_url?: string;
  confidence?: "high" | "medium" | "low";
  usable_for?: string[];
}

export interface SourceCard extends JsonObject {
  id?: string;
  title?: string;
  publisher?: string;
  source_date?: string;
  source_url?: string;
  source_type?: string;
  reliability?: string;
  summary?: string;
  key_points?: string[];
  useful_for?: string[];
  fetch_status?: string;
}

export interface ResearchPlanInput {
  brief: AuthoringBrief;
}

export interface ResearchSourceCardsInput {
  brief?: AuthoringBrief;
  sources: JsonObject[];
}

export interface ResearchEvidenceCardsInput {
  sourceCards: SourceCard[];
}

export interface DesignTokensInput {
  theme?: string;
  overrides?: JsonObject;
}

export interface WorkflowResearchDeckInput {
  brief: AuthoringBrief;
  evidenceCards?: EvidenceCard[];
  htmlOutputPath?: string;
  pdfOutputPath?: string;
  artifactDir?: string;
  execute?: boolean;
}

export interface WorkflowResearchDeckRequest extends WorkflowResearchDeckInput {}

export interface AuthoringPlanInput {
  brief: AuthoringBrief;
}

export interface StoryboardPlanInput {
  brief: AuthoringBrief;
  authoringPlan?: JsonObject;
  evidenceCards?: EvidenceCard[];
}

export interface PagesWriteInput {
  brief: AuthoringBrief;
  storyboard: JsonObject;
  evidenceCards?: EvidenceCard[];
  designTokens?: JsonObject;
}

export interface PagesReviseInput {
  pageDocument: JsonObject;
  revisions?: JsonObject[];
  designTokens?: JsonObject;
}

export interface CreateHtmlPackageInput {
  pageDocument?: JsonObject;
  html?: string;
  htmlPath?: string;
  htmlOutputPath: string;
  title?: string;
}

export interface QaVisualReportInput {
  inputPath: string;
  expectedPageCount?: number;
  htmlPackageManifestPath?: string;
  pages?: string;
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

export interface ContextImageAnalyzeInput {
  inputPath: string;
  languages?: string[];
  runOcr?: boolean;
  engine?: string;
  psm?: number;
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
  renderer?: "markdown" | "html" | string;
  htmlOutputPath?: string;
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
  renderer?: string;
  htmlOutputPath?: string;
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

export interface EvidenceCiteClaimsInput {
  claims: JsonObject[];
  composition?: JsonObject;
  compositionPath?: string;
  sourceMap?: JsonObject | JsonObject[];
  sourceMapPath?: string;
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

export interface ArtifactManifestInput {
  artifactPaths: string[];
  outputPath?: string;
  title?: string;
  metadata?: JsonObject;
}

export interface ArtifactGraphInput {
  artifactManifestPath?: string;
  artifactPaths?: string[];
  outputPath?: string;
  title?: string;
}

export interface ArtifactSourceMapInput {
  composition?: JsonObject;
  compositionPath?: string;
  sourceMap?: JsonObject | JsonObject[];
  sourceMapPath?: string;
  contextPacket?: JsonObject;
  contextPacketPath?: string;
  artifactManifestPath?: string;
  artifactPaths?: string[];
  outputPath?: string;
  title?: string;
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

export interface NUpInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
  perSheet?: number;
}

export interface BookletInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
}

export interface OptimizePdfInput {
  inputPath: string;
  outputPath: string;
}

export interface ToPdfaInput extends OptimizePdfInput {
  profile?: string;
}

export interface ValidatePdfaInput {
  inputPath: string;
}

export interface HtmlToPdfInput {
  inputPath: string;
  outputPath: string;
}

export interface RenderHtmlPackageInput {
  packagePath: string;
  outputPath: string;
}

export interface UrlToPdfInput {
  url: string;
  outputPath: string;
  allowPrivateHosts?: boolean;
  allowFileUrls?: boolean;
}

export interface OfficeToPdfInput {
  inputPath: string;
  outputPath: string;
}

export interface PdfToStructuredInput {
  inputPath: string;
  outputPath: string;
  pages?: string;
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

export interface AddShapeInput {
  inputPath: string;
  outputPath: string;
  shape: "rectangle" | "line" | "circle" | "ellipse" | string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  strokeColor?: string;
  fillColor?: string;
  lineWidth?: number;
  opacity?: number;
}

export interface MarkBboxInput {
  inputPath: string;
  outputPath: string;
  page: number;
  bbox: number[];
  color?: string;
  lineWidth?: number;
}

export interface FreehandDrawInput {
  inputPath: string;
  outputPath: string;
  page: number;
  points: number[][];
  strokeColor?: string;
  lineWidth?: number;
  opacity?: number;
}

export interface ResizePagesInput {
  inputPath: string;
  outputPath: string;
  width: number;
  height: number;
  pages?: string;
}

export interface AddMarginInput {
  inputPath: string;
  outputPath: string;
  margin?: number;
  pages?: string;
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
}

export interface UnderlayInput {
  inputPath: string;
  outputPath: string;
  text: string;
  pages?: string;
  fontSize?: number;
  opacity?: number;
  angle?: number;
  color?: string;
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
  renderer?: "markdown" | "html" | string;
  htmlOutputPath?: string;
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

export interface MetadataUpdateOutlineInput {
  inputPath: string;
  outline: JsonObject[];
  outputPath: string;
}

export interface SecurityRemoveMetadataInput {
  inputPath: string;
  outputPath: string;
}

export interface SecuritySanitizeInput {
  inputPath: string;
  outputPath: string;
  removeMetadata?: boolean;
}

export interface SecurityPasswordInput {
  inputPath: string;
  outputPath: string;
  password: string;
  ownerPassword?: string;
}

export interface SecurityAuthorizedPasswordInput {
  inputPath: string;
  outputPath: string;
  password: string;
}

export interface SecuritySignInput {
  inputPath: string;
  outputPath: string;
  secret?: string;
}

export interface SecurityVerifySignatureInput {
  inputPath: string;
  signaturePath: string;
  secret?: string;
}

export interface SecurityMalwareScanInput {
  inputPath: string;
}

export interface RedactionRegion {
  page: number;
  bbox: [number, number, number, number] | number[];
  label?: string;
}

export interface SecurityRedactInput {
  inputPath: string;
  outputPath: string;
  regions: RedactionRegion[];
  fillColor?: string;
  renderScale?: number;
}

export interface SecurityVerifyRedactionInput {
  inputPath: string;
  searchTerms?: string[];
}

export type ValidationRedactionCheckInput = SecurityVerifyRedactionInput;

export interface ExtractImagesInput {
  inputPath: string;
  pages?: string;
  outDir?: string;
}

export interface ExtractFontsInput {
  inputPath: string;
  pages?: string;
}

export interface BlankPageCheckInput {
  path: string;
  pages?: string;
}

export interface ParseLiteInput {
  inputPath: string;
  pages?: string;
}

export interface SemanticDiffInput {
  beforePath: string;
  afterPath: string;
  pages?: string;
}

export interface VisualDiffInput extends SemanticDiffInput {
  maxDifferenceRatio?: number;
  renderScale?: number;
}

export interface VersionReportInput extends SemanticDiffInput {
  outputPath?: string;
}

export interface SemanticParseInput {
  inputPath: string;
  pages?: string;
}

export interface FormsCreateInput {
  outputPath: string;
  fields: JsonObject[];
}

export interface FormsImportDataInput {
  inputPath: string;
  data: JsonObject;
  outputPath: string;
}

export interface FormsValidateInput {
  inputPath: string;
  requiredFields?: string[];
}

export interface OcrScanToPdfInput {
  imagePaths: string[];
  outputPath: string;
}

export interface OcrInput {
  inputPath: string;
  pages?: string;
  languages?: string[];
  dpi?: number;
  engine?: string;
  psm?: number;
}

export interface OcrSearchablePdfInput extends OcrInput {
  outputPath: string;
}

export interface OcrPdfRewriteInput {
  inputPath: string;
  outputPath: string;
}

export interface OcrMultilingualInput extends OcrPdfRewriteInput {
  languages?: string[];
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
