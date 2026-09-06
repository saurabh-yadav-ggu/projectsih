import React from 'react';
import { FileText, FileCode, File, X, CheckCircle2, Loader2, AlertCircle, RefreshCw } from 'lucide-react';

export default function DocumentAttachment({ attachment, onRemove, onRetry }) {
  const isPdf = attachment.name.toLowerCase().endsWith('.pdf');
  const isCodeOrTxt = /\.(txt|md|csv|json|py|js|jsx|ts|tsx|html|css)$/i.test(attachment.name);

  const getStatusBadge = () => {
    switch (attachment.status) {
      case 'uploading':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#f97316', fontSize: '11px' }}>
            <Loader2 size={12} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
            Uploading {attachment.progress ? `${attachment.progress}%` : ''}
          </span>
        );
      case 'processing':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#38bdf8', fontSize: '11px' }}>
            <Loader2 size={12} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
            Indexing RAG...
          </span>
        );
      case 'error':
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#ef4444', fontSize: '11px' }}>
            <AlertCircle size={12} />
            {attachment.errorMessage || 'Failed'}
          </span>
        );
      case 'ready':
      default:
        return (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#22c55e', fontSize: '11px', fontWeight: 500 }}>
            <CheckCircle2 size={12} />
            Ready
          </span>
        );
    }
  };

  const getIcon = () => {
    if (isPdf) return <FileText size={18} style={{ color: '#ef4444' }} />;
    if (isCodeOrTxt) return <FileCode size={18} style={{ color: '#38bdf8' }} />;
    return <File size={18} style={{ color: '#f97316' }} />;
  };

  const fileTypeLabel = isPdf ? 'PDF' : (attachment.name.split('.').pop() || 'DOC').toUpperCase();

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      backgroundColor: '#161922',
      border: `1px solid ${attachment.status === 'error' ? 'rgba(239, 68, 68, 0.4)' : '#262a3a'}`,
      borderRadius: '10px',
      padding: '8px 12px',
      minWidth: '200px',
      maxWidth: '260px',
      height: '60px',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
      flexShrink: 0,
      position: 'relative'
    }} title={attachment.name}>
      {/* Document Icon Box */}
      <div style={{
        width: '36px',
        height: '36px',
        borderRadius: '8px',
        backgroundColor: '#0f1117',
        border: '1px solid #232736',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        {getIcon()}
      </div>

      {/* File Info */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        flex: 1,
        overflow: 'hidden'
      }}>
        <div style={{
          fontSize: '13px',
          fontWeight: 600,
          color: '#f8fafc',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}>
          {attachment.name}
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '11px',
          color: '#94a3b8'
        }}>
          <span>{fileTypeLabel} • {attachment.formattedSize}</span>
          {getStatusBadge()}
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
        {attachment.status === 'error' && onRetry && (
          <button
            onClick={() => onRetry(attachment.id)}
            aria-label="Retry upload"
            style={{
              padding: '4px',
              borderRadius: '6px',
              color: '#f97316',
              cursor: 'pointer'
            }}
            title="Retry upload"
          >
            <RefreshCw size={13} />
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove(attachment.id);
          }}
          aria-label="Remove attachment"
          style={{
            padding: '4px',
            borderRadius: '6px',
            color: '#94a3b8',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          title={`Remove ${attachment.name}`}
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
