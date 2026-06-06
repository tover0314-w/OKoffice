import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Typography, Spin, Button, Slider } from '@arco-design/web-react';
import {
  IconLeft,
  IconRight,
  IconZoomIn,
  IconZoomOut,
} from '@arco-design/web-react/icon';
import type { PdfPageInfo } from '@shared/types';
import api from '../../api/bridge';

const { Text } = Typography;

interface PdfPreviewProps {
  filePath: string;
}

const PdfPreview: React.FC<PdfPreviewProps> = ({ filePath }) => {
  const [pageInfo, setPageInfo] = useState<PdfPageInfo | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.5);
  const [imageData, setImageData] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadPageInfo = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const info = await api.preview.getPdfPageInfo(filePath);
      setPageInfo(info);
      setCurrentPage(1);
    } catch (err) {
      setError('Failed to load PDF info');
    } finally {
      setLoading(false);
    }
  }, [filePath]);

  const renderPage = useCallback(async () => {
    if (!pageInfo) return;
    setLoading(true);
    try {
      const base64 = await api.preview.renderPdfPage(filePath, currentPage, scale);
      setImageData(`data:image/png;base64,${base64}`);
    } catch {
      setError('Failed to render page');
      setImageData(null);
    } finally {
      setLoading(false);
    }
  }, [filePath, currentPage, scale, pageInfo]);

  useEffect(() => {
    loadPageInfo();
  }, [loadPageInfo]);

  useEffect(() => {
    renderPage();
  }, [renderPage]);

  const handlePrevPage = useCallback(() => {
    setCurrentPage((p) => Math.max(1, p - 1));
  }, []);

  const handleNextPage = useCallback(() => {
    if (!pageInfo) return;
    setCurrentPage((p) => Math.min(pageInfo.pageCount, p + 1));
  }, [pageInfo]);

  const handleZoomIn = useCallback(() => {
    setScale((s) => Math.min(3, s + 0.25));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale((s) => Math.max(0.5, s - 0.25));
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowLeft') handlePrevPage();
      if (e.key === 'ArrowRight') handleNextPage();
    },
    [handlePrevPage, handleNextPage],
  );

  if (error) {
    return (
      <div className="flex items-center justify-center" style={{ padding: 24 }}>
        <Text style={{ color: 'var(--ok-danger)' }}>{error}</Text>
      </div>
    );
  }

  return (
    <div
      className="flex-col"
      style={{ height: '100%' }}
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Toolbar */}
      <div
        className="flex items-center justify-between"
        style={{
          padding: '4px 8px',
          borderBottom: '1px solid var(--ok-border-light)',
          flexShrink: 0,
        }}
      >
        <div className="flex items-center gap-1">
          <Button
            size="mini"
            icon={<IconLeft />}
            onClick={handlePrevPage}
            disabled={currentPage <= 1}
          />
          <Text className="text-xs">
            {currentPage} / {pageInfo?.pageCount ?? '-'}
          </Text>
          <Button
            size="mini"
            icon={<IconRight />}
            onClick={handleNextPage}
            disabled={!pageInfo || currentPage >= pageInfo.pageCount}
          />
        </div>
        <div className="flex items-center gap-1">
          <Button size="mini" icon={<IconZoomOut />} onClick={handleZoomOut} />
          <Slider
            value={scale}
            min={0.5}
            max={3}
            step={0.25}
            onChange={setScale}
            style={{ width: 80 }}
          />
          <Button size="mini" icon={<IconZoomIn />} onClick={handleZoomIn} />
        </div>
      </div>

      {/* Canvas area */}
      <div
        ref={containerRef}
        style={{ flex: 1, overflow: 'auto', background: 'var(--ok-bg-tertiary)' }}
        className="flex items-start justify-center"
      >
        {loading && !imageData && (
          <div className="flex items-center justify-center" style={{ padding: 48 }}>
            <Spin tip="Rendering..." />
          </div>
        )}
        {imageData && (
          <img
            src={imageData}
            alt={`Page ${currentPage}`}
            style={{
              maxWidth: '100%',
              margin: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            }}
          />
        )}
      </div>
    </div>
  );
};

export default PdfPreview;
