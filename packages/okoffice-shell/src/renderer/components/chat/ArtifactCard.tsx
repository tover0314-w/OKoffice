import React, { useCallback } from 'react';
import { Typography, Tag } from '@arco-design/web-react';
import {
  IconFile,
  IconFilePdf,
  IconFileImage,
} from '@arco-design/web-react/icon';
import type { ArtifactRef, FileType } from '@shared/types';

const { Text } = Typography;

function getFileType(mimeType: string): FileType {
  if (mimeType.includes('pdf')) return 'pdf';
  if (mimeType.includes('word') || mimeType.includes('docx')) return 'docx';
  if (mimeType.includes('sheet') || mimeType.includes('xlsx')) return 'xlsx';
  if (mimeType.includes('presentation') || mimeType.includes('pptx')) return 'pptx';
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.includes('json')) return 'json';
  if (mimeType.includes('markdown')) return 'markdown';
  if (mimeType.startsWith('text/')) return 'text';
  return 'other';
}

function getFileIcon(type: FileType): React.ReactNode {
  switch (type) {
    case 'pdf':
      return <IconFilePdf style={{ color: '#ef4444' }} />;
    case 'image':
      return <IconFileImage style={{ color: '#8b5cf6' }} />;
    default:
      return <IconFile style={{ color: 'var(--ok-text-tertiary)' }} />;
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileName(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] ?? path;
}

interface ArtifactCardProps {
  artifact: ArtifactRef;
  onClick?: (artifact: ArtifactRef) => void;
}

const ArtifactCard: React.FC<ArtifactCardProps> = ({ artifact, onClick }) => {
  const fileType = getFileType(artifact.mimeType);
  const icon = getFileIcon(fileType);
  const fileName = getFileName(artifact.path);

  const handleClick = useCallback(() => {
    onClick?.(artifact);
  }, [artifact, onClick]);

  return (
    <div
      onClick={handleClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        background: 'var(--ok-bg-secondary)',
        borderRadius: 'var(--ok-radius-md)',
        border: '1px solid var(--ok-border-light)',
        cursor: 'pointer',
        transition: 'border-color 0.15s',
        maxWidth: 280,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--ok-primary)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--ok-border-light)';
      }}
    >
      {icon}
      <div style={{ flex: 1, minWidth: 0 }}>
        <Text className="text-xs" bold ellipsis style={{ display: 'block' }}>
          {fileName}
        </Text>
        <div className="flex items-center gap-2">
          {artifact.sizeBytes != null && (
            <Text className="text-xs text-tertiary">{formatSize(artifact.sizeBytes)}</Text>
          )}
          {artifact.pageCount != null && (
            <Text className="text-xs text-tertiary">
              {artifact.pageCount} pg
            </Text>
          )}
          <Tag size="small" style={{ fontSize: 10, lineHeight: '16px' }}>
            {fileType}
          </Tag>
        </div>
      </div>
    </div>
  );
};

export default ArtifactCard;
