import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import { DEFAULTS } from '@shared/constants';
import type { McpClient } from './client';
import type { ToolResultDisplay, ArtifactRef } from '@shared/types';

export interface ToolRunStartedPayload {
  toolName: string;
  toolCallId: string;
  args: Record<string, unknown>;
  timestamp: string;
}

export interface ToolRunCompletedPayload {
  toolName: string;
  toolCallId: string;
  result: ToolResultDisplay;
  durationMs: number;
}

export class ToolRunner extends EventEmitter {
  constructor(private readonly mcpClient: McpClient) {
    super();
  }

  async execute(
    toolName: string,
    args: Record<string, unknown>,
  ): Promise<ToolResultDisplay> {
    const toolCallId = uuidv4();
    const startedAt = Date.now();

    this.emit('started', {
      toolName,
      toolCallId,
      args,
      timestamp: new Date(startedAt).toISOString(),
    } satisfies ToolRunStartedPayload);

    let result: ToolResultDisplay;

    try {
      const raw = await this.mcpClient.callTool(toolName, args);
      result = this.parseResult(raw, toolCallId);
    } catch (err) {
      result = {
        jobId: toolCallId,
        status: 'failed',
        artifacts: [],
        warnings: [],
        error: {
          code: 'TOOL_EXECUTION_ERROR',
          message: err instanceof Error ? err.message : String(err),
        },
      };
    }

    const durationMs = Date.now() - startedAt;
    result = { ...result };

    this.emit('completed', {
      toolName,
      toolCallId,
      result,
      durationMs,
    } satisfies ToolRunCompletedPayload);

    return result;
  }

  private parseResult(raw: unknown, jobId: string): ToolResultDisplay {
    if (typeof raw === 'object' && raw !== null) {
      const obj = raw as Record<string, unknown>;

      if (obj.content && Array.isArray(obj.content)) {
        const textContent = (obj.content as Array<{ type: string; text?: string }>)
          .filter((c) => c.type === 'text' && typeof c.text === 'string')
          .map((c) => c.text!)
          .join('\n');

        if (textContent) {
          try {
            const parsed = JSON.parse(textContent);
            return this.normalizeToolResult(parsed, jobId);
          } catch {
            return this.wrapTextResult(textContent, jobId);
          }
        }
      }

      if (obj.status === 'succeeded' || obj.status === 'failed') {
        return this.normalizeToolResult(obj, jobId);
      }

      return this.normalizeToolResult(obj, jobId);
    }

    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw);
        return this.normalizeToolResult(parsed, jobId);
      } catch {
        return this.wrapTextResult(raw, jobId);
      }
    }

    return {
      jobId,
      status: 'succeeded',
      artifacts: [],
      warnings: [],
      data: { raw: raw as Record<string, unknown> },
    };
  }

  private normalizeToolResult(
    obj: Record<string, unknown>,
    jobId: string,
  ): ToolResultDisplay {
    return {
      jobId: (obj.jobId as string) ?? jobId,
      status: (obj.status as 'succeeded' | 'failed') ?? 'succeeded',
      artifacts: (obj.artifacts as ArtifactRef[]) ?? [],
      warnings: (obj.warnings as string[]) ?? [],
      data: obj.data as Record<string, unknown> | undefined,
      error: obj.error as { code: string; message: string } | undefined,
    };
  }

  private wrapTextResult(text: string, jobId: string): ToolResultDisplay {
    return {
      jobId,
      status: 'succeeded',
      artifacts: [],
      warnings: [],
      data: { text },
    };
  }
}
