import Anthropic from '@anthropic-ai/sdk';
import type { ChatMessage, LLMChunk } from '@shared/types';
import type { LLMProvider, ToolDefinition } from './provider';

export class AnthropicProvider implements LLMProvider {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string, baseUrl?: string) {
    this.model = model;
    this.client = new Anthropic({
      apiKey,
      ...(baseUrl ? { baseURL: baseUrl } : {}),
    });
  }

  async *chatStream(
    messages: ChatMessage[],
    tools: ToolDefinition[],
  ): AsyncGenerator<LLMChunk> {
    const { systemPrompt, anthropicMessages } = this.toAnthropicMessages(messages);
    const anthropicTools = this.toAnthropicTools(tools);

    const params: Anthropic.MessageCreateParamsStreaming = {
      model: this.model,
      max_tokens: 4096,
      messages: anthropicMessages,
    };

    if (systemPrompt) {
      params.system = systemPrompt;
    }

    if (anthropicTools.length > 0) {
      params.tools = anthropicTools;
    }

    const stream = this.client.messages.stream(params);

    let currentToolCallId = '';
    let currentToolCallName = '';
    let currentToolCallArgs = '';

    for await (const event of stream) {
      if (event.type === 'content_block_start') {
        if (event.content_block.type === 'text') {
          // Text block starting; content will arrive in delta events.
        } else if (event.content_block.type === 'tool_use') {
          currentToolCallId = event.content_block.id;
          currentToolCallName = event.content_block.name;
          currentToolCallArgs = '';
        }
      }

      if (event.type === 'content_block_delta') {
        if (event.delta.type === 'text_delta') {
          yield { type: 'text', content: event.delta.text };
        } else if (event.delta.type === 'input_json_delta') {
          currentToolCallArgs += event.delta.partial_json;
        }
      }

      if (event.type === 'content_block_stop') {
        if (currentToolCallId) {
          let parsedArgs: Record<string, unknown> = {};
          try {
            parsedArgs = JSON.parse(currentToolCallArgs || '{}');
          } catch {
            parsedArgs = {};
          }

          yield {
            type: 'tool_call',
            id: currentToolCallId,
            name: currentToolCallName,
            args: parsedArgs,
          };

          currentToolCallId = '';
          currentToolCallName = '';
          currentToolCallArgs = '';
        }
      }

      if (event.type === 'message_stop') {
        yield { type: 'done', finishReason: 'stop' };
      }
    }
  }

  private toAnthropicMessages(messages: ChatMessage[]): {
    systemPrompt: string;
    anthropicMessages: Anthropic.MessageParam[];
  } {
    let systemPrompt = '';
    const anthropicMessages: Anthropic.MessageParam[] = [];

    for (const msg of messages) {
      if (msg.role === 'system') {
        systemPrompt += (systemPrompt ? '\n' : '') + msg.content;
        continue;
      }

      if (msg.role === 'user') {
        anthropicMessages.push({
          role: 'user',
          content: msg.content,
        });
      } else if (msg.role === 'assistant') {
        const content: Anthropic.ContentBlockParam[] = [];

        if (msg.content) {
          content.push({ type: 'text', text: msg.content });
        }

        if (msg.toolCalls) {
          for (const tc of msg.toolCalls) {
            content.push({
              type: 'tool_use',
              id: tc.id,
              name: tc.name,
              input: tc.args,
            });
          }
        }

        anthropicMessages.push({
          role: 'assistant',
          content: content.length === 1 && content[0].type === 'text'
            ? content[0].text
            : content,
        });
      } else if (msg.role === 'tool') {
        if (msg.toolResults) {
          const toolContent: Anthropic.ToolResultBlockParam[] = msg.toolResults.map(
            (tr) => ({
              type: 'tool_result',
              tool_use_id: tr.toolCallId,
              content: tr.content,
            }),
          );

          anthropicMessages.push({
            role: 'user',
            content: toolContent,
          });
        }
      }
    }

    return { systemPrompt, anthropicMessages };
  }

  private toAnthropicTools(tools: ToolDefinition[]): Anthropic.Tool[] {
    return tools.map((t) => ({
      name: t.name,
      description: t.description,
      input_schema: t.inputSchema as Anthropic.Tool.InputSchema,
    }));
  }
}
