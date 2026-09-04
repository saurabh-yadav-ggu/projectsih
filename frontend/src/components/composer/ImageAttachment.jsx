import React from 'react';
import { X, Loader2, AlertCircle } from 'lucide-react';

export default function ImageAttachment({ attachment, onRemove, onRetry }) {
  const isUploading = attachment.status === 'uploading' || attachment.status === 'processing';
  const isError = attachment.status === 'error';

  return (
    <div style={{
      position: 'relative',
      width: '90px',
      height: '90px',
      borderRadius: '10px',
      overflow: 'hidden',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      backgroundColor: '#181a24',
      flexShrink: 0,
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)'
    }}>
      {attachment.previewUrl ? (
        <img
          src={attachment.previewUrl}
          alt={attachment.name}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block'
          }}
        />
      ) : (
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#94a3b8',
          fontSize: '11px'
        }}>
          Image
        </div>
      )}

      {/* Loading Overlay */}
      {isUploading && (
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.65)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '4px',
          color: '#f97316'
        }}>
          <Loader2 size={18} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '10px', fontWeight: 600, color: '#f8fafc' }}>
            {attachment.status === 'processing' ? 'Indexing' : 'Uploading'}
          </span>
        </div>
      )}

      {/* Error Overlay */}
      {isError && (
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(239, 68, 68, 0.85)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '2px',
          color: '#fff',
          padding: '4px',
          textAlign: 'center'
        }}>
          <AlertCircle size={16} />
          <span style={{ fontSize: '9px', fontWeight: 600 }}>Failed</span>
          {onRetry && (
            <button
              onClick={() => onRetry(attachment.id)}
              style={{
                fontSize: '9px',
                background: 'rgba(0,0,0,0.4)',
                border: 'none',
                borderRadius: '4px',
                padding: '2px 6px',
                color: '#fff',
                cursor: 'pointer',
                marginTop: '2px'
              }}
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Remove Button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(attachment.id);
        }}
        aria-label="Remove attachment"
        style={{
          position: 'absolute',
          top: '4px',
          right: '4px',
          width: '20px',
          height: '20px',
          borderRadius: '50%',
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          color: '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
          zIndex: 5
        }}
        title={`Remove ${attachment.name}`}
      >
        <X size={12} />
      </button>
    </div>
  );
}
