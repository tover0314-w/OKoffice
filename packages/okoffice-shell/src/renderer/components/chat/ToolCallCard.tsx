import React, { useState, useCallback } from 'react';
import {
  Card,
  Typography,
  Tag,
  Spin,
  Collapse,
  Descriptions,
  Button,
} from '@arco-design/web-react';
import {
  IconCheckCircle,
  IconCloseCircle,
  IconLoading,
  IconFile,
  IconCode,
} from '@arco-design/web-react/icon';
import type { ToolCall, ToolResultDisplay, ArtifactRef } from '@shared/types';

const { Text, Paragraph } = Typography;

const STATUS_CONFIG: Record<
  ToolCall['status'],
  { color: string; icon: React.ReactNode; label: string }
> = {
  pending: { color: 'gray', icon: <IconCode />, label: 'Pending' },
  running: { color: 'blue', icon: <Spin size={14} />, label: 'Running' },
  completed: { color: 'green', icon: <IconCheckCircle />, label: 'Completed' },
  error: { color: 'red', icon: <IconCloseCircle />, label: 'Error' },
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatArgs(args: Record<string, unknown>): string {
  return JSON.stringify(args, null, 2);
}

function extractToolLabel(name: string): string {
  const parts = name.split('__');
  const raw = parts.length > 1 ? parts[parts.length - 1] : name;
  return raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function extractCategory(name: string): string {
  const prefix = name.split('__')[0] ?? name;
  return prefix.replace(/_/g, ' ').toUpperCase();
}

const ArtifactList: React.FC<{ artifacts: ArtifactRef[] }> = ({ artifacts }) => {
  if (artifacts.length === 0) return null;

  return (
    <div style={{ marginTop: 8 }}>
      <Text className="text-xs text-tertiary" style={{ marginBottom: 4, display: 'block' }}>
        Artifacts
      </Text>
      {artifacts.map((a, i) => (
        <div
          key={i}
          className="flex items-center gap-2"
          style={{
            padding: '4px 8px',
            background: 'var(--ok-bg-tertiary)',
            borderRadius: 'var(--ok-radius-sm)',
            marginBottom: 4,
            fontSize: 12,
          }}
        >
          <IconFile style={{ fontSize: 14, color: 'var(--ok-text-tertiary)' }} />
          <Text className="text-xs" ellipsis style={{ flex: 1 }}>
            {a.path}
          </Text>
          {a.pageCount != null && (
            <Text className="text-xs text-tertiary">{a.pageCount} pages</Text>
          )}
        </div>
      ))}
    </div>
  );
};

const ResultDataView: React.FC<{ data: Record<string, unknown> }> = ({ data }) => {
  const entries = Object.entries(data).slice(0, 8);
  if (entries.length === 0) return null;

  return (
    <Descriptions
      size="mini"
      column={1}
      style={{ marginTop: 8 }}
      data={entries.map(([key, val]) => ({
        label: key,
        value: typeof val === 'object' ? JSON.stringify(val) : String(val),
      }))}
    />
  );
};

interface ToolCallCardProps {
  toolCall: ToolCall;
  onArtifactClick?: (artifact: ArtifactRef) => void;
}

const ToolCallCard: React.FC<ToolCallCardProps> = ({ toolCall, onArtifactClick }) => {
  const [expanded, setExpanded] = useState(toolCall.status === 'running');
  const config = STATUS_CONFIG[toolCall.status];
  const label = extractToolLabel(toolCall.name);
  const category = extractCategory(toolCall.name);

  const handleArtifactClick = useCallback(
    (artifact: ArtifactRef) => {
      onArtifactClick?.(artifact);
    },
    [onArtifactClick],
  );

  return (
    <Card
      size="small"
      style={{
        marginBottom: 8,
        borderLeft: `3px solid ${toolCall.status === 'error' ? 'var(--ok-danger)' : toolCall.status === 'running' ? 'var(--ok-primary)' : 'var(--ok-success)'}`,
      }}
      bodyStyle={{ padding: '8px 12px' }}
    >
      <div
        className="flex items-center justify-between"
        onClick={() => setExpanded(!expanded)}
        style={{ cursor: 'pointer' }}
      >
        <div className="flex items-center gap-2">
          {config.icon}
          <Text bold style={{ fontSize: 13 }}>
            {label}
          </Text>
          <Tag size="small" color={config.color}>
            {category}
          </Tag>
        </div>
        <div className="flex items-center gap-2">
          {toolCall.durationMs != null && (
            <Text className="text-xs text-tertiary">
              {formatDuration(toolCall.durationMs)}
            </Text>
          )}
          <Tag
            size="small"
            color={config.color}
            icon={config.icon}
          >
            {config.label}
          </Tag>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 8 }}>
          <Collapse
            defaultActiveKey={[]}
            bordered={false}
            style={{ background: 'transparent' }}
          >
            <Collapse.Item header="Input" name="input" style={{ fontSize: 12 }}>
              <pre
                style={{
                  margin: 0,
                  padding: 8,
                  background: 'var(--ok-bg-tertiary)',
                  borderRadius: 'var(--ok-radius-sm)',
                  fontSize: 11,
                  overflow: 'auto',
                  maxHeight: 200,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                {formatArgs(toolCall.args)}
              </pre>
            </Collapse.Item>

            {toolCall.result && (
              <Collapse.Item header="Output" name="output" style={{ fontSize: 12 }}>
                {toolCall.result.status === 'failed' && toolCall.result.error && (
                  <Paragraph
                    style={{
                      color: 'var(--ok-danger)',
                      background: 'var(--ok-bg-tertiary)',
                      padding: 8,
                      borderRadius: 'var(--ok-radius-sm)',
                      marginBottom: 8,
                      fontSize: 12,
                    }}
                  >
                    {toolCall.result.error.code}: {toolCall.result.error.message}
                  </Paragraph>
                )}
                {toolCall.result.warnings.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    {toolCall.result.warnings.map((w, i) => (
                      <Text key={i} className="text-xs" style={{ color: 'var(--ok-warning)', display: 'block' }}>
                        {w}
                      </Text>
                    ))}
                  </div>
                )}
                {toolCall.result.data && (
                  <ResultDataView data={toolCall.result.data} />
                )}
                {toolCall.result.artifacts.length > 0 && (
                  <ArtifactList artifacts={toolCall.result.artifacts} />
                )}
              </Collapse.Item>
            )}
          </Collapse>
        </div>
      )}
    </Card>
  );
};

export default ToolCallCard;
