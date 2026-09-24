import React, { useState } from 'react';
import { Copy, Check, RotateCw, Pencil, AlertCircle, ThumbsDown, Upload, MoreHorizontal } from 'lucide-react';

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
  const [disliked, setDisliked] = useState(false);
  const [shared, setShared] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const isUser = role === 'user';
  const isStreaming = status === 'STREAMING';
  const isError = status === 'ERROR';

  if (isStreaming) return null;

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({ title: 'Shield AI Message', text: content }).catch(() => {});
    } else {
      navigator.clipboard.writeText(content);
      setShared(true);
      setTimeout(() => setShared(false), 2000);
    }
  };

  const iconBtnStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#71717a',
    cursor: 'pointer',
    transition: 'color 0.15s ease, background-color 0.15s ease'
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      marginTop: '6px',
      color: '#71717a',
      position: 'relative'
    }}>
      {isUser ? (
        /* User actions: Copy, Share, Edit */
        <>
          <button
            type="button"
            onClick={handleCopy}
            title={copied ? 'Copied' : 'Copy'}
            style={iconBtnStyle}
            onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            {copied ? <Check size={14} style={{ color: '#4ade80' }} /> : <Copy size={14} />}
          </button>

          <button
            type="button"
            onClick={handleShare}
            title={shared ? 'Link copied' : 'Share'}
            style={iconBtnStyle}
            onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            {shared ? <Check size={14} style={{ color: '#4ade80' }} /> : <Upload size={14} />}
          </button>

          {onEdit && (
            <button
              type="button"
              onClick={onEdit}
              title="Edit message"
              style={iconBtnStyle}
              onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <Pencil size={14} />
            </button>
          )}
        </>
      ) : (
        /* Assistant actions: Copy, ThumbsDown, Share, Regenerate, More */
        <>
          <button
            type="button"
            onClick={handleCopy}
            title={copied ? 'Copied' : 'Copy'}
            style={iconBtnStyle}
            onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            {copied ? <Check size={14} style={{ color: '#4ade80' }} /> : <Copy size={14} />}
          </button>

          <button
            type="button"
            onClick={() => setDisliked(!disliked)}
            title={disliked ? 'Feedback sent' : 'Bad response'}
            style={{
              ...iconBtnStyle,
              color: disliked ? '#f87171' : '#71717a'
            }}
            onMouseEnter={e => { if (!disliked) { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; } }}
            onMouseLeave={e => { if (!disliked) { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; } }}
          >
            <ThumbsDown size={14} />
          </button>

          <button
            type="button"
            onClick={handleShare}
            title={shared ? 'Link copied' : 'Share'}
            style={iconBtnStyle}
            onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            {shared ? <Check size={14} style={{ color: '#4ade80' }} /> : <Upload size={14} />}
          </button>

          {onRegenerate && (
            <button
              type="button"
              onClick={onRegenerate}
              title="Regenerate response"
              style={iconBtnStyle}
              onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <RotateCw size={14} />
            </button>
          )}

          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => setShowMenu(!showMenu)}
              title="More options"
              style={iconBtnStyle}
              onMouseEnter={e => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#71717a'; e.currentTarget.style.backgroundColor = 'transparent'; }}
            >
              <MoreHorizontal size={14} />
            </button>
            {showMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: '0',
                marginTop: '4px',
                backgroundColor: '#121215',
                border: '1px solid #232328',
                borderRadius: '8px',
                padding: '4px',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                zIndex: 40,
                minWidth: '130px',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)'
              }}>
                <button
                  type="button"
                  onClick={() => { handleCopy(); setShowMenu(false); }}
                  style={{
                    padding: '6px 10px',
                    fontSize: '12px',
                    color: '#f8fafc',
                    backgroundColor: 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    borderRadius: '5px',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = '#1e1e24'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  Copy Text
                </button>
              </div>
            )}
          </div>

          {isError && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              title="Retry response"
              style={{
                ...iconBtnStyle,
                color: '#fca5a5'
              }}
            >
              <AlertCircle size={14} />
            </button>
          )}
        </>
      )}
    </div>
  );
}
