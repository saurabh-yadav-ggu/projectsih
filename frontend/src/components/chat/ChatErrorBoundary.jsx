import React from 'react';
import { AlertCircle, RotateCw } from 'lucide-react';

export class ChatErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ChatErrorBoundary caught error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '30px',
          color: '#f8fafc',
          textAlign: 'center'
        }}>
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '16px',
            padding: '24px 32px',
            maxWidth: '500px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '14px'
          }}>
            <AlertCircle size={32} style={{ color: '#ef4444' }} />
            <h3 style={{ fontSize: '17px', fontWeight: 600 }}>Chat Interface Encountered an Error</h3>
            <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: '1.5' }}>
              {this.state.error?.message || 'An unexpected rendering error occurred while displaying messages.'}
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '8px',
                padding: '8px 18px',
                borderRadius: '8px',
                backgroundColor: '#f97316',
                border: 'none',
                color: '#0f1117',
                fontWeight: 600,
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              <RotateCw size={14} />
              <span>Reload Chat View</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChatErrorBoundary;
