import { randomUUID } from 'node:crypto';
import type {
  ChatMessage,
  LLMChunk,
  Message,
  ToolCall,
  ToolResultDisplay,
  ToolResultRef,
  ArtifactRef,
} from '@shared/types';
import { DEFAULTS } from '@shared/constants';
import type { LLMProvider } from './provider';
import { ConversationStore } from '../db/conversation-store';
import type { MessageFormatter } from './message-formatter';

export interface ToolRunner {
  getToolDefinitions(): Promise<Array<import('./provider').ToolDefinition>>;
  executeTool(name: string, args: Record<string, unknown>): Promise<ToolResultDisplay>;
}

export interface WSBroadcaster {
  broadcast(event: string, data: unknown): void;
}

export class ToolCallLoop {
  private llmProvider: LLMProvider;
  private toolRunner: ToolRunner;
  private conversationStore: ConversationStore;
  private wsServer: WSBroadcaster;
  private messageFormatter: MessageFormatter;
  private aborted: boolean;

  constructor(
    llmProvider: LLMProvider,
    toolRunner: ToolRunner,
    conversationStore: ConversationStore,
    wsServer: WSBroadcaster,
    messageFormatter: MessageFormatter,
  ) {
    this.llmProvider = llmProvider;
    this.toolRunner = toolRunner;
    this.conversationStore = conversationStore;
    this.wsServer = wsServer;
    this.messageFormatter = messageFormatter;
    this.aborted = false;
  }

  stop(): void {
    this.aborted = true;
  }

  async run(conversationId: string): Promise<void> {
    this.aborted = false;

    const conversation = this.conversationStore.getById(conversationId);
    if (!conversation) {
      throw new Error(`Conversation not found: ${conversationId}`);
    }

    const toolDefs = await this.toolRunner.getToolDefinitions();

    const maxIterations = DEFAULTS.MAX_TOOL_LOOP_ITERATIONS;

    for (let iteration = 0; iteration < maxIterations; iteration++) {
      if (this.aborted) {
        this.broadcastEvent('llm:stream_done', { conversationId });
        return;
      }

      const chatMessages = this.messageFormatter.fromMessages(conversation.messages);
      this.prependSystemPrompt(chatMessages, conversation.systemPrompt);

      let assistantContent = '';
      const pendingToolCalls: Array<{
        id: string;
        name: string;
        args: Record<string, unknown>;
      }> = [];

      let hadToolCalls = false;

      const stream = this.llmProvider.chatStream(chatMessages, toolDefs);

      for await (const chunk of stream) {
        if (this.aborted) {
          this.broadcastEvent('llm:stream_done', { conversationId });
          return;
        }

        if (chunk.type === 'text') {
          assistantContent += chunk.content;
          this.broadcastEvent('llm:chunk', {
            conversationId,
            content: chunk.content,
          });
        } else if (chunk.type === 'tool_call') {
          hadToolCalls = true;
          pendingToolCalls.push({
            id: chunk.id,
            name: chunk.name,
            args: chunk.args,
          });
        }
        // 'done' chunk signals end of this stream iteration
      }

      // Build assistant message with tool calls
      const assistantMessage = this.buildAssistantMessage(
        conversationId,
        assistantContent,
        pendingToolCalls,
      );
      this.conversationStore.addMessage(conversationId, assistantMessage);
      conversation.messages.push(assistantMessage);

      if (!hadToolCalls || pendingToolCalls.length === 0) {
        this.broadcastEvent('llm:stream_done', { conversationId });
        return;
      }

      // Execute each tool call
      for (const tc of pendingToolCalls) {
        const toolCallRecord: ToolCall = {
          id: tc.id,
          name: tc.name,
          args: tc.args,
          status: 'running',
          startedAt: new Date().toISOString(),
        };

        this.broadcastEvent('llm:tool_call_started', {
          conversationId,
          toolCall: toolCallRecord,
        });

        let result: ToolResultDisplay;
        const startTime = Date.now();

        try {
          result = await this.toolRunner.executeTool(tc.name, tc.args);
        } catch (err) {
          result = {
            jobId: randomUUID(),
            status: 'failed',
            artifacts: [],
            warnings: [],
            error: {
              code: 'TOOL_EXECUTION_ERROR',
              message: err instanceof Error ? err.message : String(err),
            },
          };
        }

        const durationMs = Date.now() - startTime;
        result.data = { ...result.data, durationMs };

        this.broadcastEvent('llm:tool_call_completed', {
          conversationId,
          toolCallId: tc.id,
          result,
        });

        // Append tool result message
        const toolResultMessage = this.buildToolResultMessage(
          conversationId,
          tc.id,
          tc.name,
          result,
        );
        this.conversationStore.addMessage(conversationId, toolResultMessage);
        conversation.messages.push(toolResultMessage);
      }

      // Loop back to LLM with the new tool results appended
    }

    // Exhausted max iterations
    this.broadcastEvent('llm:stream_done', { conversationId });
  }

  private broadcastEvent(event: string, data: unknown): void {
    this.wsServer.broadcast(event, data);
  }

  private prependSystemPrompt(
    chatMessages: ChatMessage[],
    systemPrompt: string | null,
  ): void {
    const prompt =
      systemPrompt ??
      'You are an OKoffice assistant. Help users create, inspect, and transform PDF and Office documents using the available tools.';

    chatMessages.unshift({ role: 'system', content: prompt });
  }

  private buildAssistantMessage(
    conversationId: string,
    content: string,
    toolCalls: Array<{ id: string; name: string; args: Record<string, unknown> }>,
  ): Message {
    return {
      id: randomUUID(),
      conversationId,
      role: 'assistant',
      content,
      toolCalls: toolCalls.map((tc) => ({
        id: tc.id,
        name: tc.name,
        args: tc.args,
        status: 'pending' as const,
        startedAt: new Date().toISOString(),
      })),
      artifacts: [],
      createdAt: new Date().toISOString(),
    };
  }

  private buildToolResultMessage(
    conversationId: string,
    toolCallId: string,
    toolName: string,
    result: ToolResultDisplay,
  ): Message {
    const toolResultRef: ToolResultRef = {
      toolCallId,
      toolName,
      result,
    };

    return {
      id: randomUUID(),
      conversationId,
      role: 'tool',
      content: JSON.stringify(result),
      toolResults: [toolResultRef],
      artifacts: result.artifacts ?? [],
      createdAt: new Date().toISOString(),
    };
  }
}
