import React from 'react';
import { Spin } from '@arco-design/web-react';

interface LoadingSpinnerProps {
  tip?: string;
  size?: 'small' | 'default' | 'large';
  fullscreen?: boolean;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  tip = 'Loading...',
  size = 'default',
  fullscreen = false,
}) => {
  if (fullscreen) {
    return (
      <div
        className="flex items-center justify-center"
        style={{
          position: 'fixed',
          inset: 0,
          background: 'var(--ok-bg)',
          zIndex: 9999,
        }}
      >
        <Spin tip={tip} size={size} />
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-center"
      style={{ padding: 24, width: '100%' }}
    >
      <Spin tip={tip} size={size} />
    </div>
  );
};

export default LoadingSpinner;
