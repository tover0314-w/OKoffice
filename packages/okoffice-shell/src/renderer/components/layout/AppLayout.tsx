import React, { useState, useCallback } from 'react';
import { Layout } from '@arco-design/web-react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import PreviewPanel from '../preview/PreviewPanel';
import FileBrowserPanel from '../file/FileBrowserPanel';
import { usePreview } from '../../contexts/PreviewContext';
import type { FileEntry } from '@shared/types';

const { Sider, Content, Header } = Layout;

const COLLAPSE_BREAKPOINT = 768;

const AppLayout: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [fileBrowserVisible, setFileBrowserVisible] = useState(false);
  const { previewFile, setPreviewFile } = usePreview();

  const handleResize = useCallback(() => {
    if (window.innerWidth < COLLAPSE_BREAKPOINT && !sidebarCollapsed) {
      setSidebarCollapsed(true);
    }
  }, [sidebarCollapsed]);

  React.useEffect(() => {
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, [handleResize]);

  const handleFileSelect = useCallback(
    (entry: FileEntry) => {
      if (!entry.isDirectory) {
        setPreviewFile(entry);
        setPreviewVisible(true);
      }
    },
    [setPreviewFile],
  );

  const handleClosePreview = useCallback(() => {
    setPreviewVisible(false);
    setPreviewFile(null);
  }, [setPreviewFile]);

  return (
    <Layout
      style={{
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
      }}
    >
      <Sider
        collapsed={sidebarCollapsed}
        collapsible
        width={240}
        collapsedWidth={0}
        onCollapse={(collapsed: boolean) => setSidebarCollapsed(collapsed)}
        style={{
          background: 'var(--ok-bg-secondary)',
          borderRight: '1px solid var(--ok-border)',
          overflow: 'hidden',
          transition: 'width var(--ok-transition-normal)',
        }}
        trigger={null}
      >
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((prev) => !prev)}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            height: 48,
            padding: '0 16px',
            background: 'var(--ok-bg)',
            borderBottom: '1px solid var(--ok-border)',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <TopBar
            sidebarCollapsed={sidebarCollapsed}
            onToggleSidebar={() => setSidebarCollapsed((prev) => !prev)}
            previewVisible={previewVisible}
            onTogglePreview={() => setPreviewVisible((prev) => !prev)}
          />
        </Header>

        <Content
          style={{
            flex: 1,
            overflow: 'hidden',
            display: 'flex',
          }}
        >
          {/* File browser (optional left panel) */}
          {fileBrowserVisible && (
            <div style={{ width: 220, flexShrink: 0 }}>
              <FileBrowserPanel
                onFileSelect={handleFileSelect}
              />
            </div>
          )}

          {/* Main content */}
          <div
            style={{
              flex: 1,
              overflow: 'auto',
              position: 'relative',
            }}
          >
            <Outlet />
          </div>

          {/* Preview panel */}
          {previewVisible && (
            <div style={{ width: 420, flexShrink: 0 }}>
              <PreviewPanel
                file={previewFile}
                onClose={handleClosePreview}
              />
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
