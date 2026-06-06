import React from 'react';
import { Typography, Spin } from '@arco-design/web-react';
import {
  IconCheckCircle,
  IconCloseCircle,
  IconExclamationCircle,
} from '@arco-design/web-react/icon';
import type { ToolCall } from '@shared/types';

const { Text } = Typography;

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function extractLabel(name: string): string {
  const parts = name.split('__');
  const raw = parts.length > 1 ? parts[parts.length - 1] : name;
  return raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_DOT: Record<ToolCall['status'], { color: string; icon: React.ReactNode }> = {
  pending: { color: 'var(--ok-text-tertiary)', icon: <IconExclamationCircle style={{ fontSize: 14 }} /> },
  running: { color: 'var(--ok-primary)', icon: <Spin size={14} /> },
  completed: { color: 'var(--ok-success)', icon: <IconCheckCircle style={{ fontSize: 14, color: 'var(--ok-success)' }} /> },
  error: { color: 'var(--ok-danger)', icon: <IconCloseCircle style={{ fontSize: 14, color: 'var(--ok-danger)' }} /> },
};

interface ToolCallTimelineProps {
  toolCalls: ToolCall[];
}

const ToolCallTimeline: React.FC<ToolCallTimelineProps> = ({ toolCalls }) => {
  if (toolCalls.length === 0) return null;

  return (
    <div style={{ padding: '4px 0' }}>
      {toolCalls.map((tc, index) => {
        const dot = STATUS_DOT[tc.status];
        const isLast = index === toolCalls.length - 1;

        return (
          <div key={tc.id} className="flex" style={{ minHeight: 28 }}>
            {/* Timeline line + dot */}
            <div
              className="flex-col items-center"
              style={{ width: 24, flexShrink: 0, paddingTop: 2 }}
            >
              {dot.icon}
              {!isLast && (
                <div
                  style={{
                    width: 1,
                    flex: 1,
                    background: 'var(--ok-border-light)',
                    marginTop: 4,
                  }}
                />
              )}
            </div>

            {/* Content */}
            <div
              className="flex items-center gap-2"
              style={{ paddingBottom: isLast ? 0 : 8, flex: 1 }}
            >
              <Text className="text-xs" bold>
                {extractLabel(tc.name)}
              </Text>
              {tc.durationMs != null && (
                <Text className="text-xs text-tertiary">
                  {formatDuration(tc.durationMs)}
                </Text>
              )}
              {tc.status === 'running' && (
                <Text className="text-xs" style={{ color: 'var(--ok-primary)' }}>
                  running...
                </Text>
              )}
              {tc.status === 'error' && tc.result?.error && (
                <Text
                  className="text-xs"
                  style={{ color: 'var(--ok-danger)' }}
                  ellipsis
                >
                  {tc.result.error.message}
                </Text>
              )}
              {tc.status === 'completed' && tc.result?.artifacts.length
                ? tc.result.artifacts.length
                : null}
              {tc.status === 'completed' && tc.result?.artifacts.length ? (
                <Text className="text-xs text-tertiary">
                  {tc.result.artifacts.length} artifact{tc.result.artifacts.length > 1 ? 's' : ''}
                </Text>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ToolCallTimeline;
