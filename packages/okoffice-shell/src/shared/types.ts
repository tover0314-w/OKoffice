// === LLM ===

export type LLMProviderType = 'openai' | 'anthropic' | 'ollama';

export interface LLMConfig {
  provider: LLMProviderType;
  apiKey: string;
  model: string;
  baseUrl?: string;
  temperature: number;
  maxTokens: number;
  systemPrompt: string;
}

// === Conversation ===

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  model: string;
  provider: LLMProviderType;
  systemPrompt: string | null;
  messages: Message[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  model: string;
  lastMessagePreview: string;
}

// === Messages ===

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface Message {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResultRef[];
  artifacts: ArtifactRef[];
  createdAt: string;
}

// === Tool Calls ===

export type ToolCallStatus = 'pending' | 'running' | 'completed' | 'error';

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: ToolCallStatus;
  result?: ToolResultDisplay;
  startedAt: string;
  completedAt?: string;
  durationMs?: number;
}

export interface ToolResultDisplay {
  jobId: string;
  status: 'succeeded' | 'failed';
  artifacts: ArtifactRef[];
  warnings: string[];
  data?: Record<string, unknown>;
  error?: { code: string; message: string };
}

export interface ToolResultRef {
  toolCallId: string;
  toolName: string;
  result: ToolResultDisplay;
}

// === Artifacts ===

export interface ArtifactRef {
  path: string;
  mimeType: string;
  sizeBytes?: number;
  pageCount?: number;
}

// === Tool Metadata ===

export interface ToolCategory {
  name: string;
  label: string;
  icon: string;
  tools: ToolSpec[];
}

export interface ToolSpec {
  name: string;
  status: 'stable' | 'beta' | 'experimental' | 'planned';
  description: string;
  category: string | null;
  interfaces: string[];
  inputSchema: Record<string, unknown> | null;
  outputSchema: Record<string, unknown> | null;
  implemented: boolean;
}

// === File System ===

export type FileType =
  | 'pdf'
  | 'docx'
  | 'xlsx'
  | 'pptx'
  | 'image'
  | 'text'
  | 'markdown'
  | 'code'
  | 'json'
  | 'other';

export interface FileEntry {
  name: string;
  path: string;
  isDirectory: boolean;
  size: number;
  modifiedAt: string;
  fileType: FileType;
  children?: FileEntry[];
}

export interface FileInfo {
  path: string;
  mimeType: string;
  size: number;
  pageCount?: number;
}

export interface PdfPageInfo {
  pageCount: number;
  pages: Array<{
    width: number;
    height: number;
    rotation: number;
    hasText: boolean;
  }>;
}

export interface PreviewData {
  type: 'pdf' | 'text' | 'html' | 'table' | 'slides' | 'image';
  content: string;
  pageCount?: number;
  sheets?: string[];
}

// === Workflow ===

export interface Workflow {
  id: string;
  name: string;
  description: string;
  definition: WorkflowDefinition;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  updatedAt: string;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  config: WorkflowConfig;
}

export interface WorkflowNode {
  id: string;
  type: 'tool' | 'input' | 'output' | 'condition' | 'parallel';
  position: { x: number; y: number };
  data: WorkflowNodeData;
}

export interface WorkflowNodeData {
  label: string;
  toolName?: string;
  parameters?: Record<string, unknown>;
  description?: string;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface WorkflowConfig {
  inputPath?: string;
  outputPath?: string;
  onError: 'stop' | 'skip' | 'continue';
  maxRetries: number;
}

export interface WorkflowRunResult {
  workflowId: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  steps: WorkflowStepResult[];
  artifacts: ArtifactRef[];
  startedAt: string;
  completedAt?: string;
}

export interface WorkflowStepResult {
  nodeId: string;
  toolName: string;
  status: ToolCallStatus;
  result?: ToolResultDisplay;
  durationMs?: number;
}

// === MCP ===

export interface MCPStatus {
  connected: boolean;
  toolCount: number;
  serverPid?: number;
  uptime?: number;
  lastError?: string;
}

// === Stream Events ===

export type StreamEvent =
  | { type: 'llm:chunk'; conversationId: string; content: string }
  | { type: 'llm:tool_call_started'; conversationId: string; toolCall: ToolCall }
  | {
      type: 'llm:tool_call_completed';
      conversationId: string;
      toolCallId: string;
      result: ToolResultDisplay;
    }
  | { type: 'llm:stream_done'; conversationId: string }
  | { type: 'file:changed'; path: string; kind: 'add' | 'change' | 'unlink' }
  | {
      type: 'workflow:step_progress';
      workflowId: string;
      nodeId: string;
      status: ToolCallStatus;
    };

// === LLM Chunks (internal to main process) ===

export type LLMChunk =
  | { type: 'text'; content: string }
  | {
      type: 'tool_call';
      id: string;
      name: string;
      args: Record<string, unknown>;
    }
  | { type: 'done'; finishReason: string };

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: Array<{
    id: string;
    name: string;
    args: Record<string, unknown>;
  }>;
  toolResults?: Array<{
    toolCallId: string;
    content: string;
  }>;
}
