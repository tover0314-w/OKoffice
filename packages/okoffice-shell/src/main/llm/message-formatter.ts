import type { ChatMessage, Message, ToolCall } from '@shared/types';

export class MessageFormatter {
  /**
   * Convert internal Message[] to the transport ChatMessage[] format.
   */
  static fromMessages(messages: Message[]): ChatMessage[] {
    const result: ChatMessage[] = [];

    for (const msg of messages) {
      if (msg.role === 'user' || msg.role === 'system') {
        result.push({
          role: msg.role,
          content: msg.content,
        });
      } else if (msg.role === 'assistant') {
        result.push({
          role: 'assistant',
          content: msg.content,
          toolCalls: msg.toolCalls?.map((tc) => ({
            id: tc.id,
            name: tc.name,
            args: tc.args,
          })),
        });
      } else if (msg.role === 'tool') {
        result.push({
          role: 'tool',
          content: msg.content,
          toolResults: msg.toolResults?.map((tr) => ({
            toolCallId: tr.toolCallId,
            content: JSON.stringify(tr.result),
          })),
        });
      }
    }

    return result;
  }

  /**
   * Convert ChatMessage[] to OpenAI-compatible message format.
   */
  static toOpenAI(
    messages: ChatMessage[],
  ): Array<{
    role: string;
    content: string | null;
    tool_calls?: Array<{
      id: string;
      type: 'function';
      function: { name: string; arguments: string };
    }>;
    tool_call_id?: string;
  }> {
    const result: Array<Record<string, unknown>> = [];

    for (const msg of messages) {
      if (msg.role === 'tool' && msg.toolResults) {
        for (const tr of msg.toolResults) {
          result.push({
            role: 'tool',
            content: tr.content,
            tool_call_id: tr.toolCallId,
          });
        }
        continue;
      }

      const entry: Record<string, unknown> = {
        role: msg.role,
        content: msg.content,
      };

      if (msg.role === 'assistant' && msg.toolCalls && msg.toolCalls.length > 0) {
        entry.tool_calls = msg.toolCalls.map((tc) => ({
          id: tc.id,
          type: 'function' as const,
          function: {
            name: tc.name,
            arguments: JSON.stringify(tc.args),
          },
        }));
      }

      result.push(entry);
    }

    return result as Array<{
      role: string;
      content: string | null;
      tool_calls?: Array<{
        id: string;
        type: 'function';
        function: { name: string; arguments: string };
      }>;
      tool_call_id?: string;
    }>;
  }

  /**
   * Convert ChatMessage[] to Anthropic-compatible message format.
   * Returns the system prompt separately, since Anthropic expects it
   * at the top-level parameter, not in the messages array.
   */
  static toAnthropic(messages: ChatMessage[]): {
    systemPrompt: string;
    messages: Array<{
      role: 'user' | 'assistant';
      content: unknown;
    }>;
  } {
    let systemPrompt = '';
    const result: Array<{ role: 'user' | 'assistant'; content: unknown }> = [];

    for (const msg of messages) {
      if (msg.role === 'system') {
        systemPrompt += (systemPrompt ? '\n' : '') + msg.content;
        continue;
      }

      if (msg.role === 'user') {
        result.push({ role: 'user', content: msg.content });
      } else if (msg.role === 'assistant') {
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          const content: Array<Record<string, unknown>> = [];
          if (msg.content) {
            content.push({ type: 'text', text: msg.content });
          }
          for (const tc of msg.toolCalls) {
            content.push({
              type: 'tool_use',
              id: tc.id,
              name: tc.name,
              input: tc.args,
            });
          }
          result.push({ role: 'assistant', content });
        } else {
          result.push({ role: 'assistant', content: msg.content });
        }
      } else if (msg.role === 'tool' && msg.toolResults) {
        const toolContent = msg.toolResults.map((tr) => ({
          type: 'tool_result',
          tool_use_id: tr.toolCallId,
          content: tr.content,
        }));
        result.push({ role: 'user', content: toolContent });
      }
    }

    return { systemPrompt, messages: result };
  }

  /**
   * Extract tool call information from a raw LLM response chunk.
   * Useful when the provider returns unstructured data that needs parsing.
   */
  static extractToolCalls(
    message: Record<string, unknown>,
  ): Array<{ id: string; name: string; args: Record<string, unknown> }> {
    const toolCalls: Array<{ id: string; name: string; args: Record<string, unknown> }> = [];

    const rawToolCalls = message.tool_calls as
      | Array<Record<string, unknown>>
      | undefined;

    if (!rawToolCalls) {
      return toolCalls;
    }

    for (const raw of rawToolCalls) {
      const fn = raw.function as Record<string, unknown> | undefined;
      if (!fn) {
        continue;
      }

      let args: Record<string, unknown> = {};
      const argsStr = fn.arguments as string | undefined;
      if (argsStr) {
        try {
          args = JSON.parse(argsStr);
        } catch {
          args = {};
        }
      }

      toolCalls.push({
        id: (raw.id as string) ?? '',
        name: (fn.name as string) ?? '',
        args,
      });
    }

    return toolCalls;
  }
}
