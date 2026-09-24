import React, { useState, useEffect, memo } from 'react';
import {
  Bot,
  User,
  Loader2,
  Cpu,
  FileText,
  Download,
  Check,
  AlertCircle,
  ArrowDown
} from 'lucide-react';
import MarkdownMessage from './MarkdownMessage';
import ToolExecution from './ToolExecution';
import MessageActions from './MessageActions';
import { downloadDocument } from '../../api/chat';
import { useAutoScroll } from '../../hooks/useAutoScroll';

const DOCUMENT_EXTENSIONS = /\.(docx|xlsx|pptx|pdf|md|txt|csv)$/i;

function findDocumentPaths(content = '') {
  if (!content) return [];
  const matches = [];

  // 1. Matches labeled patterns: FilePath: ..., **FilePath:** ..., file_path = "..."
  const labeledPattern = /(?:\*{0,2}(?:FilePath|filePath|file_path|path|File Path)\*{0,2})\s*["']?\s*[:=]\s*[`"']?([^\r\n`"'()[\]]+\.(?:docx|xlsx|pptx|pdf|md|txt|csv))[`"']?/gi;
  for (const match of content.matchAll(labeledPattern)) {
    if (match[1]) {
      matches.push(match[1].trim().replaceAll('\\\\', '\\'));
    }
  }

  // 2. Matches markdown code spans or link targets: `path/to/doc.docx` or [Link](path/to/doc.docx)
  const markdownPathPattern = /[`(]([^\r\n`"()[\]]+\.(?:docx|xlsx|pptx|pdf|md|txt|csv))[`)]/gi;
  for (const match of content.matchAll(markdownPathPattern)) {
    if (match[1]) {
      matches.push(match[1].trim().replaceAll('\\\\', '\\'));
    }
  }

  // 3. Matches plain absolute or relative paths with common roots or drive letters
  const plainPathPattern = /(?:[A-Za-z]:[\\/]|(?:\.{1,2}[\\/])|\/(?:sih|data|app|project|documents)[\\/])[^\s<>"'`()[\]]+\.(?:docx|xlsx|pptx|pdf|md|txt|csv)/gi;
  for (const match of content.matchAll(plainPathPattern)) {
    matches.push(match[0].replace(/[),.;:]+$/, '').trim().replaceAll('\\\\', '\\'));
  }

  return [...new Set(matches)].filter((path) => DOCUMENT_EXTENSIONS.test(path));
}

function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function saveDocument(token, filePath, setDownloadStatus) {
  const filename = filePath.split(/[\\/]/).pop()?.replace(/^["'`]+|["'`]+$/g, '') || 'document';
  setDownloadStatus(prev => ({ ...prev, [filePath]: 'downloading' }));

  try {
    const response = await downloadDocument(token, filePath);
    const blob = await response.blob();

    if (window.isSecureContext && 'showSaveFilePicker' in window) {
      try {
        const handle = await window.showSaveFilePicker({ suggestedName: filename });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        setDownloadStatus(prev => ({ ...prev, [filePath]: 'done' }));
        setTimeout(() => setDownloadStatus(prev => { const n = { ...prev }; delete n[filePath]; return n; }), 3000);
        return;
      } catch (pickerErr) {
        if (pickerErr.name === 'AbortError') {
          setDownloadStatus(prev => { const n = { ...prev }; delete n[filePath]; return n; });
          return;
        }
        console.warn('showSaveFilePicker error, falling back to browser download:', pickerErr);
      }
    }

    triggerBrowserDownload(blob, filename);
    setDownloadStatus(prev => ({ ...prev, [filePath]: 'done' }));
    setTimeout(() => setDownloadStatus(prev => { const n = { ...prev }; delete n[filePath]; return n; }), 3000);
  } catch (error) {
    console.error('Failed to download document:', error);
    setDownloadStatus(prev => ({ ...prev, [filePath]: 'error' }));
    alert(`Download failed: ${error.message || 'Unable to retrieve document'}`);
    setTimeout(() => setDownloadStatus(prev => { const n = { ...prev }; delete n[filePath]; return n; }), 5000);
  }
}

// Memoized Message Item to prevent unnecessary re-renders of older conversation history
const MessageItem = memo(function MessageItem({
  msg,
  isLast,
  token,
  downloadStatus,
  onSaveDocument,
  onRegenerate,
  onEditUserMessage,
  onRetry
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(msg.content);

  const isUser = msg.role === 'user';
  const isSystem = msg.role === 'system';
  const isStreaming = msg.status === 'STREAMING';
  const isStopped = msg.status === 'STOPPED';
  const isError = msg.status === 'ERROR';

  if (isSystem) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '8px 0'
      }}>
        <div style={{
          backgroundColor: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '20px',
          padding: '6px 16px',
          fontSize: '12.5px',
          color: '#94a3b8',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Cpu size={14} style={{ color: '#3b82f6' }} />
          <span>{msg.content}</span>
        </div>
      </div>
    );
  }

  const attachments = msg.attachments || [];
  const explicitArtifacts = (msg.artifacts || []).map(a => a.path).filter(Boolean);
  const parsedPaths = !isUser && !isStreaming ? findDocumentPaths(msg.content) : [];
  const documentPaths = [...new Set([...parsedPaths, ...explicitArtifacts])];

  const handleSaveEdit = () => {
    if (editText.trim() && editText !== msg.content) {
      onEditUserMessage(msg.id, editText);
    }
    setIsEditing(false);
  };

  if (isUser) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-end',
        width: '100%'
      }}>
        {/* User Attachments */}
        {attachments.length > 0 && (
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
            marginBottom: '6px',
            justifyContent: 'flex-end'
          }}>
            {attachments.map((att, i) => {
              if (att.type === 'image' && att.previewUrl) {
                return (
                  <div key={i} style={{
                    width: '120px',
                    height: '120px',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    backgroundColor: '#000'
                  }}>
                    <img
                      src={att.previewUrl}
                      alt={att.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>
                );
              }
              return (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: 'rgba(29, 78, 216, 0.25)',
                  border: '1px solid rgba(29, 78, 216, 0.5)',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  fontSize: '12.5px',
                  color: '#f8fafc'
                }}>
                  <FileText size={16} style={{ color: '#93c5fd' }} />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: 600 }}>{att.name}</span>
                    <span style={{ fontSize: '10.5px', color: '#cbd5e1' }}>
                      {att.formattedSize || 'Document'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* User Message: Editable or Blue Bubble */}
        {isEditing ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%', maxWidth: '920px' }}>
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={3}
              style={{
                width: '100%',
                backgroundColor: '#0a0a0d',
                border: '1px solid #1d4ed8',
                borderRadius: '10px',
                padding: '12px',
                color: '#f8fafc',
                fontSize: '15px',
                fontFamily: 'inherit',
                resize: 'vertical'
              }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => { setEditText(msg.content); setIsEditing(false); }}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  backgroundColor: 'transparent',
                  border: '1px solid #475569',
                  color: '#94a3b8',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  backgroundColor: '#1d4ed8',
                  border: 'none',
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Save & Submit
              </button>
            </div>
          </div>
        ) : (
          <>
            <div style={{
              maxWidth: '82%',
              backgroundColor: '#1d4ed8',
              color: '#ffffff',
              padding: '12px 18px',
              borderRadius: '20px',
              borderBottomRightRadius: '4px',
              fontSize: '15px',
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              boxShadow: '0 2px 10px rgba(0, 0, 0, 0.4)'
            }}>
              {msg.content}
            </div>

            {/* User subtle action icons aligned to the right below bubble */}
            <MessageActions
              role="user"
              content={msg.content}
              status={msg.status}
              isLast={isLast}
              onEdit={() => setIsEditing(true)}
            />
          </>
        )}
      </div>
    );
  }

  // Assistant Message: Plain text directly on the black background (NO surrounding card, box, or bubble)
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start',
      width: '100%'
    }}>
      {/* Tool Execution and Deep Agent Pipeline Accordion (CRITICAL: PRESERVED) */}
      {(msg.toolCalls?.length > 0 || msg.pipelineSteps?.length > 0 || msg.plan || msg.verification) && (
        <div style={{ width: '100%', marginBottom: '10px' }}>
          <ToolExecution
            toolCalls={msg.toolCalls}
            pipelineSteps={msg.pipelineSteps}
            plan={msg.plan}
            verification={msg.verification}
            isStreaming={isStreaming}
          />
        </div>
      )}

      {/* Assistant Message Plain Text Directly on Background */}
      <div style={{
        color: '#ffffff',
        fontSize: '15.5px',
        lineHeight: '1.7',
        width: '100%',
        padding: '0',
        backgroundColor: 'transparent',
        border: 'none',
        boxShadow: 'none'
      }}>
        {msg.content ? (
          <div className={isStreaming ? "streaming-message" : ""}>
            <MarkdownMessage content={msg.content} />
          </div>
        ) : isStreaming ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#94a3b8', fontSize: '14.5px', padding: '6px 0' }}>
            <div className="streaming-dots">
              <span className="dot dot-1" />
              <span className="dot dot-2" />
              <span className="dot dot-3" />
            </div>
            <span className="thinking-shimmer">Shield AI is thinking...</span>
          </div>
        ) : null}

        {/* Smooth Glowing Streaming Cursor */}
        {isStreaming && msg.content && (
          <span
            className="streaming-cursor"
            style={{
              display: 'inline-block',
              width: '6px',
              height: '18px',
              backgroundColor: '#38bdf8',
              marginLeft: '4px',
              borderRadius: '2px',
              verticalAlign: 'text-bottom',
              animation: 'smoothStreamPulse 0.9s cubic-bezier(0.4, 0, 0.6, 1) infinite'
            }}
          />
        )}

        {/* Status Badges */}
        {isStopped && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            marginTop: '8px',
            fontSize: '11px',
            color: '#94a3b8',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            padding: '2px 6px',
            backgroundColor: 'rgba(255, 255, 255, 0.04)'
          }}>
            <span>Stopped</span>
          </div>
        )}

        {/* Document Download Cards */}
        {token && documentPaths.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
            {documentPaths.map((filePath) => {
              const filename = filePath.split(/[\\/]/).pop()?.replace(/^["'`]+|["'`]+$/g, '') || 'document';
              const status = downloadStatus[filePath];
              const isDownloading = status === 'downloading';
              const isDone = status === 'done';
              const isErr = status === 'error';

              return (
                <button
                  key={filePath}
                  type="button"
                  disabled={isDownloading}
                  onClick={() => onSaveDocument(filePath)}
                  title={`Download ${filename}`}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '7px',
                    border: isErr
                      ? '1px solid rgba(239, 68, 68, 0.45)'
                      : isDone
                      ? '1px solid rgba(34, 197, 94, 0.45)'
                      : '1px solid rgba(29, 78, 216, 0.55)',
                    borderRadius: '7px',
                    padding: '8px 11px',
                    color: isErr ? '#fca5a5' : isDone ? '#86efac' : '#93c5fd',
                    background: isErr
                      ? 'rgba(239, 68, 68, 0.12)'
                      : isDone
                      ? 'rgba(34, 197, 94, 0.12)'
                      : 'rgba(29, 78, 216, 0.18)',
                    cursor: isDownloading ? 'wait' : 'pointer',
                    fontSize: '12px',
                    transition: 'all 0.2s ease'
                  }}
                >
                  {isDownloading ? (
                    <>
                      <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                      Saving {filename}...
                    </>
                  ) : isDone ? (
                    <>
                      <Check size={14} />
                      Saved {filename}
                    </>
                  ) : isErr ? (
                    <>
                      <AlertCircle size={14} />
                      Retry {filename}
                    </>
                  ) : (
                    <>
                      <Download size={14} />
                      Save {filename}
                    </>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Assistant subtle action icons below text */}
      {!isEditing && (
        <MessageActions
          role={msg.role}
          content={msg.content}
          status={msg.status}
          isLast={isLast}
          onRegenerate={() => onRegenerate(msg.id)}
          onRetry={onRetry}
        />
      )}
    </div>
  );
});

export default function ChatMessageList({
  messages = [],
  loading = false,
  token,
  onRegenerate,
  onEditUserMessage,
  onRetry
}) {
  const {
    containerRef,
    bottomRef,
    showJumpToLatest,
    handleScroll,
    jumpToLatest,
    scrollToBottom
  } = useAutoScroll({ threshold: 120 });

  const [downloadStatus, setDownloadStatus] = useState({});

  useEffect(() => {
    scrollToBottom({ smooth: false });
  }, [messages, loading, scrollToBottom]);

  const handleSaveDoc = (filePath) => {
    saveDocument(token, filePath, setDownloadStatus);
  };

  return (
    <div style={{ position: 'relative', flex: 1, width: '100%', overflow: 'hidden' }}>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        style={{
          height: '100%',
          width: '100%',
          maxWidth: '1080px',
          margin: '0 auto',
          overflowY: 'auto',
          padding: '28px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '28px'
        }}
      >
        {messages.map((msg, index) => (
          <MessageItem
            key={msg.id || index}
            msg={msg}
            isLast={index === messages.length - 1}
            token={token}
            downloadStatus={downloadStatus}
            onSaveDocument={handleSaveDoc}
            onRegenerate={onRegenerate}
            onEditUserMessage={onEditUserMessage}
            onRetry={onRetry}
          />
        ))}

        {loading && !messages.some(m => m.status === 'STREAMING') && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#94a3b8', fontSize: '14.5px', padding: '6px 0' }}>
            <div className="streaming-dots">
              <span className="dot dot-1" />
              <span className="dot dot-2" />
              <span className="dot dot-3" />
            </div>
            <span className="thinking-shimmer">Shield AI is thinking...</span>
          </div>
        )}

        <div ref={bottomRef} style={{ height: '1px' }} />
      </div>

      {/* Floating "Jump to Latest" Button */}
      {showJumpToLatest && (
        <div style={{
          position: 'absolute',
          bottom: '16px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 30
        }}>
          <button
            type="button"
            onClick={jumpToLatest}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#0a0a0d',
              border: `1px solid ${loading ? '#1d4ed8' : '#222225'}`,
              color: '#ffffff',
              padding: '8px 18px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: 500,
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.7), 0 0 12px rgba(29, 78, 216, 0.3)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {loading ? (
              <>
                <span style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: '#1d4ed8',
                  animation: 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                }} />
                <span>Generating... Click to view latest</span>
                <ArrowDown size={14} style={{ color: '#3b82f6' }} />
              </>
            ) : (
              <>
                <ArrowDown size={14} style={{ color: '#3b82f6' }} />
                <span>Jump to latest</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
