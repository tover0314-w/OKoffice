import React, { useCallback } from 'react';
import { Typography, Button } from '@arco-design/web-react';
import { IconClose } from '@arco-design/web-react/icon';
import type { FileEntry, FileType } from '@shared/types';
import PdfPreview from './PdfPreview';
import TextViewer from './TextViewer';
import ImageViewer from './ImageViewer';

const { Text } = Typography;

function getPreviewType(entry: FileEntry): 'pdf' | 'text' | 'image' | 'unsupported' {
  switch (entry.fileType) {
    case 'pdf':
      return 'pdf';
    case 'text':
    case 'code':
    case 'markdown':
    case 'json':
      return 'text';
    case 'image':
      return 'image';
    case 'docx':
    case 'xlsx':
    case 'pptx':
      return 'text'; // will extract text via MCP
    default:
      return 'unsupported';
  }
}

interface PreviewPanelProps {
  file: FileEntry | null;
  onClose: () => void;
}

const PreviewPanel: React.FC<PreviewPanelProps> = ({ file, onClose }) => {
  if (!file) {
    return (
      <div
        className="flex items-center justify-center"
        style={{
          height: '100%',
          background: 'var(--ok-bg)',
          color: 'var(--ok-text-tertiary)',
        }}
      >
        <Text className="text-xs text-tertiary">
          Select a file to preview
        </Text>
      </div>
    );
  }

  const previewType = getPreviewType(file);

  return (
    <div
      className="flex-col"
      style={{
        height: '100%',
        background: 'var(--ok-bg)',
        borderLeft: '1px solid var(--ok-border-light)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between"
        style={{
          padding: '4px 8px',
          borderBottom: '1px solid var(--ok-border-light)',
          flexShrink: 0,
        }}
      >
        <Text className="text-xs" bold ellipsis style={{ flex: 1 }}>
          {file.name}
        </Text>
        <Button
          size="mini"
          type="text"
          icon={<IconClose />}
          onClick={onClose}
        />
      </div>

      {/* Preview content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {previewType === 'pdf' && <PdfPreview filePath={file.path} />}
        {previewType === 'text' && <TextViewer filePath={file.path} />}
        {previewType === 'image' && <ImageViewer filePath={file.path} />}
        {previewType === 'unsupported' && (
          <div
            className="flex items-center justify-center"
            style={{ height: '100%' }}
          >
            <Text className="text-xs text-tertiary">
              Preview not available for this file type
            </Text>
          </div>
        )}
      </div>
    </div>
  );
};

export default PreviewPanel;
