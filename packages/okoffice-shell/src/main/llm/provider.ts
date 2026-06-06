export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface LLMProvider {
  chatStream(
    messages: Array<import('@shared/types').ChatMessage>,
    tools: ToolDefinition[],
  ): AsyncGenerator<import('@shared/types').LLMChunk>;
}
