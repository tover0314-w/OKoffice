import React from 'react';
import { Spin, Typography } from '@arco-design/web-react';

const { Text } = Typography;

interface StreamingIndicatorProps {
  toolCallCount?: number;
}

const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({ toolCallCount = 0 }) => {
  return (
    <div
      className="flex items-center gap-2"
      style={{
        padding: '4px 12px',
        background: 'var(--ok-bg-secondary)',
        borderRadius: 'var(--ok-radius-md)',
        display: 'inline-flex',
        fontSize: 12,
      }}
    >
      <Spin size={14} />
      <Text className="text-xs text-tertiary">
        {toolCallCount > 0
          ? `Running tools... (${toolCallCount} called)`
          : 'Thinking...'}
      </Text>
    </div>
  );
};

export default StreamingIndicator;
