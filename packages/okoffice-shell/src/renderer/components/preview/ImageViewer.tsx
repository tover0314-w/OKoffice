import React from 'react';

interface ImageViewerProps {
  filePath: string;
}

const ImageViewer: React.FC<ImageViewerProps> = ({ filePath }) => {
  const src = `file:///${filePath.replace(/\\/g, '/')}`;

  return (
    <div
      className="flex items-center justify-center"
      style={{
        height: '100%',
        overflow: 'auto',
        background: 'var(--ok-bg-tertiary)',
        padding: 8,
      }}
    >
      <img
        src={src}
        alt={filePath.split(/[/\\]/).pop() ?? 'Image'}
        style={{
          maxWidth: '100%',
          maxHeight: '100%',
          objectFit: 'contain',
          borderRadius: 'var(--ok-radius-sm)',
        }}
      />
    </div>
  );
};

export default ImageViewer;
