import React, { useRef, useState } from 'react';
import { useAutoResizeTextarea } from '../../hooks/useAutoResizeTextarea';
import AttachmentPreview from './AttachmentPreview';
import ComposerToolbar from './ComposerToolbar';
import { UploadCloud } from 'lucide-react';

export default function ChatComposer({
  inputValue,
  setInputValue,
  activeTab,
  setActiveTab,
  attachments = [],
  onAddFiles,
  onRemoveAttachment,
  onRetryAttachment,
  onSendMessage,
  onStop,
  loading
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [pickerAccept, setPickerAccept] = useState('image/*,.pdf,.doc,.docx,.txt,.md,.csv,.json');
  const [isDragging, setIsDragging] = useState(false);

  useAutoResizeTextarea(textareaRef, inputValue);

  const handleOpenPicker = (type) => {
    if (type === 'image') {
      setPickerAccept('image/*');
    } else if (type === 'document') {
      setPickerAccept('.pdf,.doc,.docx,.txt,.md,.csv,.json');
    } else {
      setPickerAccept('image/*,.pdf,.doc,.docx,.txt,.md,.csv,.json');
    }
    setTimeout(() => {
      fileInputRef.current?.click();
    }, 50);
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    try {
      onAddFiles(files);
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape' && loading && onStop) {
      e.preventDefault();
      onStop();
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const canSend = (inputValue.trim().length > 0 || attachments.length > 0) && !loading;
      if (canSend) {
        onSendMessage();
      }
    }
  };

  const handlePaste = (e) => {
    if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
      const pastedFiles = Array.from(e.clipboardData.files);
      const supportedFiles = pastedFiles.filter(f => 
        f.type.startsWith('image/') || /\.(pdf|txt|md|csv|json|doc|docx)$/i.test(f.name)
      );
      if (supportedFiles.length > 0) {
        e.preventDefault();
        onAddFiles(supportedFiles);
      }
    }
  };

  // Drag & Drop Handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onAddFiles(Array.from(e.dataTransfer.files));
    }
  };

  const canSend = (inputValue.trim().length > 0 || attachments.length > 0) && !loading;

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        width: 'calc(100% - 32px)',
        maxWidth: '850px',
        margin: '0 auto 20px auto',
        backgroundColor: '#212121',
        border: `1px solid ${isDragging ? '#f97316' : '#383838'}`,
        borderRadius: '20px',
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        boxShadow: isDragging ? '0 0 20px rgba(249, 115, 22, 0.35)' : '0 8px 32px rgba(0, 0, 0, 0.6)',
        transition: 'border 0.2s ease, box-shadow 0.2s ease',
        flexShrink: 0
      }}
    >
      {/* Drag & Drop Visual Overlay */}
      {isDragging && (
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(249, 115, 22, 0.12)',
          borderRadius: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '10px',
          color: '#f97316',
          fontSize: '14px',
          fontWeight: 600,
          zIndex: 40,
          backdropFilter: 'blur(2px)'
        }}>
          <UploadCloud size={24} />
          <span>Drop files to attach to Shield AI</span>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={pickerAccept}
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {/* Attachments Section (ABOVE Textarea) */}
      <AttachmentPreview
        attachments={attachments}
        onRemove={onRemoveAttachment}
        onRetry={onRetryAttachment}
      />

      {/* Textarea Area */}
      <textarea
        ref={textareaRef}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        placeholder={loading ? "Shield AI is generating... (Esc to stop)" : "Ask Shield AI anything..."}
        rows={1}
        style={{
          width: '100%',
          backgroundColor: 'transparent',
          color: '#ffffff',
          fontSize: '15px',
          lineHeight: '1.6',
          border: 'none',
          outline: 'none',
          resize: 'none',
          padding: '2px 0',
          fontFamily: 'inherit'
        }}
      />

      {/* Toolbar Area */}
      <ComposerToolbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenPicker={handleOpenPicker}
        onSend={() => canSend && onSendMessage()}
        onStop={onStop}
        canSend={canSend}
        loading={loading}
        attachmentCount={attachments.length}
      />
    </div>
  );
}
