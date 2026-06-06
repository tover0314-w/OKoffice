import OpenAI from 'openai';
import type { ChatMessage, LLMChunk } from '@shared/types';
import type { LLMProvider, ToolDefinition } from './provider';

export class OpenAIProvider implements LLMProvider {
  protected client: OpenAI;
  protected model: string;

  constructor(apiKey: string, model: string, baseUrl?: string) {
    this.model = model;
    this.client = new OpenAI({
      apiKey,
      ...(baseUrl ? { baseURL: baseUrl } : {}),
    });
  }

  async *chatStream(
    messages: ChatMessage[],
    tools: ToolDefinition[],
  ): AsyncGenerator<LLMChunk> {
    const openaiMessages = this.toOpenAIMessages(messages);
    const openaiTools = this.toOpenAITools(tools);

    const params: OpenAI.Chat.Completions.ChatCompletionCreateParamsStreaming = {
      model: this.model,
      messages: openaiMessages,
      stream: true,
    };

    if (openaiTools.length > 0) {
      params.tools = openaiTools;
    }

    const stream = await this.client.chat.completions.create(params);

    const toolCallAccumulators = new Map<
      number,
      { id: string; name: string; args: string }
    >();

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (!delta) {
        continue;
      }

      if (delta.content) {
        yield { type: 'text', content: delta.content };
      }

      if (delta.tool_calls) {
        for (const tc of delta.tool_calls) {
          const idx = tc.index;
          if (!toolCallAccumulators.has(idx)) {
            toolCallAccumulators.set(idx, {
              id: tc.id ?? '',
              name: tc.function?.name ?? '',
              args: '',
            });
          }

          const acc = toolCallAccumulators.get(idx)!;
          if (tc.id) {
            acc.id = tc.id;
          }
          if (tc.function?.name) {
            acc.name = tc.function.name;
          }
          if (tc.function?.arguments) {
            acc.args += tc.function.arguments;
          }
        }
      }

      const finishReason = chunk.choices[0]?.finish_reason;
      if (finishReason) {
        for (const [, acc] of toolCallAccumulators) {
          let parsedArgs: Record<string, unknown> = {};
          try {
            parsedArgs = JSON.parse(acc.args || '{}');
          } catch {
            parsedArgs = {};
          }
          yield {
            type: 'tool_call',
            id: acc.id,
            name: acc.name,
            args: parsedArgs,
          };
        }

        yield { type: 'done', finishReason };
      }
    }
  }

  protected toOpenAIMessages(
    messages: ChatMessage[],
  ): OpenAI.Chat.Completions.ChatCompletionMessageParam[] {
    const result: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [];

    for (const msg of messages) {
      if (msg.role === 'system') {
        result.push({ role: 'system', content: msg.content });
      } else if (msg.role === 'user') {
        result.push({ role: 'user', content: msg.content });
      } else if (msg.role === 'assistant') {
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          result.push({
            role: 'assistant',
            content: msg.content || null,
            tool_calls: msg.toolCalls.map((tc) => ({
              id: tc.id,
              type: 'function' as const,
              function: {
                name: tc.name,
                arguments: JSON.stringify(tc.args),
              },
            })),
          });
        } else {
          result.push({ role: 'assistant', content: msg.content });
        }
      } else if (msg.role === 'tool') {
        if (msg.toolResults) {
          for (const tr of msg.toolResults) {
            result.push({
              role: 'tool',
              tool_call_id: tr.toolCallId,
              content: tr.content,
            });
          }
        }
      }
    }

    return result;
  }

  protected toOpenAITools(
    tools: ToolDefinition[],
  ): OpenAI.Chat.Completions.ChatCompletionTool[] {
    return tools.map((t) => ({
      type: 'function' as const,
      function: {
        name: t.name,
        description: t.description,
        parameters: t.inputSchema,
      },
    }));
  }
}
