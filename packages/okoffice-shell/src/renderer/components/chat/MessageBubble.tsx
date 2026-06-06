import React from 'react';
import { Typography, Spin } from '@arco-design/web-react';
import type { Message, ArtifactRef } from '@shared/types';
import ToolCallCard from './ToolCallCard';
import ToolCallTimeline from './ToolCallTimeline';
import ArtifactCard from './ArtifactCard';

const { Paragraph } = Typography;

interface MessageBubbleProps {
  message: Message;
  streaming?: boolean;
  onArtifactClick?: (artifact: ArtifactRef) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  streaming = false,
  onArtifactClick,
}) => {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;
  const hasArtifacts = message.artifacts.length > 0;
  const isEmpty = !message.content && !hasToolCalls && !hasArtifacts;

  return (
    <div
      className="flex gap-3"
      style={{
        marginBottom: 16,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      <div style={{ maxWidth: '80%', minWidth: 200 }}>
        {/* Text content */}
        {message.content && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--ok-radius-md)',
              background: isUser
                ? 'var(--ok-primary)'
                : 'var(--ok-bg-secondary)',
              color: isUser ? 'var(--ok-primary-text)' : 'var(--ok-text)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: 14,
              lineHeight: 1.6,
            }}
          >
            <Paragraph style={{ margin: 0, color: 'inherit' }}>
              {message.content}
            </Paragraph>
          </div>
        )}

        {/* Streaming indicator */}
        {isAssistant && streaming && isEmpty && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--ok-radius-md)',
              background: 'var(--ok-bg-secondary)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <Spin size={14} />
            <span className="text-xs text-tertiary">Thinking...</span>
          </div>
        )}

        {/* Tool calls timeline (compact) */}
        {hasToolCalls && (
          <div style={{ marginTop: message.content ? 8 : 0 }}>
            <ToolCallTimeline toolCalls={message.toolCalls!} />
          </div>
        )}

        {/* Tool call detail cards (expandable) */}
        {hasToolCalls &&
          message.toolCalls!.map((tc) => (
            <ToolCallCard
              key={tc.id}
              toolCall={tc}
              onArtifactClick={onArtifactClick}
            />
          ))}

        {/* Artifact cards */}
        {hasArtifacts && (
          <div
            className="flex flex-wrap gap-2"
            style={{ marginTop: 8 }}
          >
            {message.artifacts.map((a, i) => (
              <ArtifactCard
                key={`${a.path}-${i}`}
                artifact={a}
                onClick={onArtifactClick}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
