import React from 'react';
import ImageAttachment from './ImageAttachment';
import DocumentAttachment from './DocumentAttachment';

export default function AttachmentPreview({ attachments = [], onRemove, onRetry }) {
  if (!attachments || attachments.length === 0) return null;

  return (
    <div style={{
      width: '100%',
      maxHeight: '120px',
      overflowX: 'auto',
      overflowY: 'hidden',
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      paddingBottom: '12px',
      marginBottom: '8px',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)'
    }}>
      {attachments.map((att) => {
        if (att.type === 'image') {
          return (
            <ImageAttachment
              key={att.id}
              attachment={att}
              onRemove={onRemove}
              onRetry={onRetry}
            />
          );
        }
        return (
          <DocumentAttachment
            key={att.id}
            attachment={att}
            onRemove={onRemove}
            onRetry={onRetry}
          />
        );
      })}
    </div>
  );
}
