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

const DOCUMENT_EXTENSIONS = /\.(docx|xlsx|pptx|pdf|md|txt)$/i;

function findDocumentPaths(content = '') {
  if (!content) return [];
  const matches = [];

  // 1. Matches labeled patterns: FilePath: ..., **FilePath:** ..., file_path = "..."
  const labeledPattern = /(?:\*{0,2}(?:FilePath|filePath|file_path|path|File Path)\*{0,2})\s*["']?\s*[:=]\s*[`"']?([^\r\n`"'()[\]]+\.(?:docx|xlsx|pptx|pdf|md|txt))[`"']?/gi;
  for (const match of content.matchAll(labeledPattern)) {
    if (match[1]) {
      matches.push(match[1].trim().replaceAll('\\\\', '\\'));
    }
  }

  // 2. Matches markdown code spans or link targets: `path/to/doc.docx` or [Link](path/to/doc.docx)
  const markdownPathPattern = /[`(]([^\r\n`"()[\]]+\.(?:docx|xlsx|pptx|pdf|md|txt))[`)]/gi;
  for (const match of content.matchAll(markdownPathPattern)) {
    if (match[1]) {
      matches.push(match[1].trim().replaceAll('\\\\', '\\'));
    }
  }

  // 3. Matches plain absolute or relative paths with common roots or drive letters
  const plainPathPattern = /(?:[A-Za-z]:[\\/]|(?:\.{1,2}[\\/])|\/(?:sih|data|app|project|documents)[\\/])[^\s<>"'`()[\]]+\.(?:docx|xlsx|pptx|pdf|md|txt)/gi;
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
          <Cpu size={14} style={{ color: '#f97316' }} />
          <span>{msg.content}</span>
        </div>
      </div>
    );
  }

  const attachments = msg.attachments || [];
  const documentPaths = !isUser && !isStreaming ? findDocumentPaths(msg.content) : [];

  const handleSaveEdit = () => {
    if (editText.trim() && editText !== msg.content) {
      onEditUserMessage(msg.id, editText);
    }
    setIsEditing(false);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '14px',
      flexDirection: isUser ? 'row-reverse' : 'row'
    }}>
      {/* Avatar */}
      <div style={{
        width: '34px',
        height: '34px',
        borderRadius: '10px',
        backgroundColor: isUser ? '#1e293b' : '#0f172a',
        border: `1px solid ${isUser ? '#334155' : 'rgba(249, 115, 22, 0.3)'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: isUser ? '#f8fafc' : '#f97316',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
        flexShrink: 0
      }}>
        {isUser ? <User size={17} /> : <Bot size={17} />}
      </div>

      {/* Bubble Container */}
      <div style={{
        maxWidth: '82%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start'
      }}>
        <div style={{
          backgroundColor: isUser ? '#212121' : '#141416',
          border: `1px solid ${isError ? '#ef4444' : isUser ? '#383838' : '#27272a'}`,
          borderRadius: '16px',
          borderTopRightRadius: isUser ? '4px' : '16px',
          borderTopLeftRadius: isUser ? '16px' : '4px',
          padding: '16px 20px',
          color: '#ffffff',
          boxShadow: '0 4px 14px rgba(0, 0, 0, 0.4)',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          position: 'relative',
          width: '100%'
        }}>
          {/* Attachments inside bubble */}
          {attachments.length > 0 && (
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px',
              marginBottom: '4px'
            }}>
              {attachments.map((att, i) => {
                if (att.type === 'image' && att.previewUrl) {
                  return (
                    <div key={i} style={{
                      width: '120px',
                      height: '120px',
                      borderRadius: '10px',
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
                    backgroundColor: 'rgba(0, 0, 0, 0.3)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '12.5px',
                    color: '#f8fafc'
                  }}>
                    <FileText size={16} style={{ color: '#f97316' }} />
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: 600 }}>{att.name}</span>
                      <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>
                        {att.formattedSize || 'Document'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Tool Execution Accordion for Assistant */}
          {!isUser && msg.toolCalls && msg.toolCalls.length > 0 && (
            <ToolExecution toolCalls={msg.toolCalls} isStreaming={isStreaming} />
          )}

          {/* User Message: Editable or Standard View */}
          {isUser ? (
            isEditing ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #f97316',
                    borderRadius: '8px',
                    padding: '10px',
                    color: '#f8fafc',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    resize: 'vertical'
                  }}
                />
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => { setEditText(msg.content); setIsEditing(false); }}
                    style={{
                      padding: '5px 12px',
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
                      padding: '5px 12px',
                      borderRadius: '6px',
                      backgroundColor: '#f97316',
                      border: 'none',
                      color: '#0f1117',
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
              <div style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontSize: '14.5px',
                lineHeight: '1.6',
                color: '#f8fafc'
              }}>
                {msg.content}
              </div>
            )
          ) : (
            /* Assistant Message */
            <div style={{ position: 'relative' }}>
              {msg.content ? (
                <MarkdownMessage content={msg.content} />
              ) : isStreaming ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '14px' }}>
                  <Loader2 size={15} style={{ animation: 'spin 1s linear infinite', color: '#f97316' }} />
                  <span>Shield AI is thinking...</span>
                </div>
              ) : null}

              {/* Pulsing Streaming Cursor */}
              {isStreaming && msg.content && (
                <span style={{
                  display: 'inline-block',
                  width: '8px',
                  height: '16px',
                  backgroundColor: '#f97316',
                  marginLeft: '4px',
                  borderRadius: '2px',
                  verticalAlign: 'middle',
                  animation: 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                }} />
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
                            : '1px solid rgba(249, 115, 22, 0.45)',
                          borderRadius: '7px',
                          padding: '8px 11px',
                          color: isErr ? '#fca5a5' : isDone ? '#86efac' : '#fed7aa',
                          background: isErr
                            ? 'rgba(239, 68, 68, 0.12)'
                            : isDone
                            ? 'rgba(34, 197, 94, 0.12)'
                            : 'rgba(249, 115, 22, 0.12)',
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
          )}
        </div>

        {/* Message Actions (Copy, Regenerate, Edit, Retry) */}
        {!isEditing && (
          <MessageActions
            role={msg.role}
            content={msg.content}
            status={msg.status}
            isLast={isLast}
            onRegenerate={() => onRegenerate(msg.id)}
            onEdit={() => setIsEditing(true)}
            onRetry={onRetry}
          />
        )}
      </div>
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

  // Auto-scroll when messages update, but ONLY when user was already near bottom
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
          maxWidth: '900px',
          margin: '0 auto',
          overflowY: 'auto',
          padding: '24px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px'
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
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              backgroundColor: '#0f172a',
              border: '1px solid rgba(249, 115, 22, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#f97316',
              flexShrink: 0
            }}>
              <Bot size={17} />
            </div>
            <div style={{
              backgroundColor: '#141722',
              border: '1px solid #232736',
              borderRadius: '16px',
              borderTopLeftRadius: '4px',
              padding: '14px 20px',
              color: '#94a3b8',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.25)'
            }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite', color: '#f97316' }} />
              <span>Shield AI is thinking...</span>
            </div>
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
              backgroundColor: '#212121',
              border: `1px solid ${loading ? '#f97316' : '#383838'}`,
              color: '#ffffff',
              padding: '8px 18px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: 500,
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.7), 0 0 12px rgba(249, 115, 22, 0.25)',
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
                  backgroundColor: '#f97316',
                  animation: 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite'
                }} />
                <span>Generating... Click to view latest</span>
                <ArrowDown size={14} style={{ color: '#f97316' }} />
              </>
            ) : (
              <>
                <ArrowDown size={14} style={{ color: '#f97316' }} />
                <span>Jump to latest</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
