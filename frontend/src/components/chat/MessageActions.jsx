import React, { useState } from 'react';
import { Copy, Check, RotateCw, Pencil, AlertCircle } from 'lucide-react';

export default function MessageActions({
  role = 'assistant',
  content = '',
  status = 'COMPLETED',
  onRegenerate,
  onEdit,
  onRetry,
  isLast = false
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = role === 'user';
  const isStreaming = status === 'STREAMING';
  const isError = status === 'ERROR';

  if (isStreaming) return null;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      marginTop: '6px',
      fontSize: '12px',
      color: '#64748b'
    }}>
      {/* Copy Action */}
      <button
        type="button"
        onClick={handleCopy}
        title={copied ? 'Copied to clipboard' : 'Copy message'}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '3px 7px',
          borderRadius: '5px',
          backgroundColor: copied ? 'rgba(34, 197, 94, 0.12)' : 'rgba(255, 255, 255, 0.04)',
          border: `1px solid ${copied ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255, 255, 255, 0.07)'}`,
          color: copied ? '#4ade80' : '#94a3b8',
          cursor: 'pointer',
          transition: 'all 0.15s ease'
        }}
      >
        {copied ? <Check size={12} /> : <Copy size={12} />}
        <span>{copied ? 'Copied' : 'Copy'}</span>
      </button>

      {/* User Edit Action */}
      {isUser && onEdit && (
        <button
          type="button"
          onClick={onEdit}
          title="Edit prompt"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 7px',
            borderRadius: '5px',
            backgroundColor: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.07)',
            color: '#94a3b8',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <Pencil size={12} />
          <span>Edit</span>
        </button>
      )}

      {/* Assistant Regenerate Action (shown on last assistant message or completed) */}
      {!isUser && !isError && onRegenerate && isLast && (
        <button
          type="button"
          onClick={onRegenerate}
          title="Regenerate response"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 7px',
            borderRadius: '5px',
            backgroundColor: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.07)',
            color: '#94a3b8',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <RotateCw size={12} />
          <span>Regenerate</span>
        </button>
      )}

      {/* Assistant Retry Action (shown on error) */}
      {!isUser && isError && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          title="Retry response"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 7px',
            borderRadius: '5px',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <AlertCircle size={12} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}
