import React from 'react';
import { Typography, Button } from '@arco-design/web-react';
import { IconExperiment } from '@arco-design/web-react/icon';

const { Title, Paragraph } = Typography;

const WorkflowPage: React.FC = () => {
  return (
    <div
      className="flex-col items-center justify-center"
      style={{ height: '100%', gap: 16, padding: 48 }}
    >
      <IconExperiment
        style={{ fontSize: 48, color: 'var(--ok-text-tertiary)' }}
      />
      <Title heading={5} style={{ color: 'var(--ok-text-secondary)' }}>
        Workflows
      </Title>
      <Paragraph
        style={{
          color: 'var(--ok-text-tertiary)',
          maxWidth: 360,
          textAlign: 'center',
        }}
      >
        The visual workflow editor is coming soon. Build multi-step document
        processing pipelines by connecting tools together.
      </Paragraph>
      <Button type="primary" disabled>
        Coming Soon
      </Button>
    </div>
  );
};

export default WorkflowPage;
