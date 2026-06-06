import React, { Component } from 'react';
import { Button, Typography } from '@arco-design/web-react';
import type { ErrorInfo, ReactNode } from 'react';

const { Title, Paragraph } = Typography;

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className="flex-col items-center justify-center"
          style={{
            padding: 32,
            gap: 16,
            textAlign: 'center',
            minHeight: 200,
          }}
        >
          <Title heading={5} style={{ color: 'var(--ok-danger)' }}>
            Something went wrong
          </Title>
          <Paragraph
            className="text-sm"
            style={{
              color: 'var(--ok-text-secondary)',
              maxWidth: 400,
              wordBreak: 'break-word',
            }}
          >
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </Paragraph>
          <Button type="primary" onClick={this.handleRetry}>
            Try Again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
