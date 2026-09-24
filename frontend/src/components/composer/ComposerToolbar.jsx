import React, { useState } from 'react';
import { Plus, Mic, ArrowUp, Square, Paperclip } from 'lucide-react';
import ModeSelector from './ModeSelector';
import AttachmentMenu from './AttachmentMenu';

export default function ComposerToolbar({
  activeTab,
  setActiveTab,
  onOpenPicker,
  onSend,
  onStop,
  canSend,
  loading,
  attachmentCount
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [recording, setRecording] = useState(false);

  const handleMicClick = () => {
    setRecording(!recording);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingTop: '8px',
      position: 'relative'
    }}>
      {/* Left Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', position: 'relative' }}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Attach files"
          title="Attach image or document (.pdf, .doc, .txt, .md)"
          style={{
            width: '34px',
            height: '34px',
            borderRadius: '10px',
            backgroundColor: attachmentCount > 0 ? 'rgba(29, 78, 216, 0.2)' : '#121215',
            border: `1px solid ${attachmentCount > 0 ? 'rgba(29, 78, 216, 0.5)' : '#23242a'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: attachmentCount > 0 ? '#3b82f6' : '#94a3b8',
            cursor: 'pointer',
            position: 'relative',
            transition: 'all 0.15s ease'
          }}
        >
          {attachmentCount > 0 ? <Paperclip size={16} /> : <Plus size={18} />}
          {attachmentCount > 0 && (
            <span style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              backgroundColor: '#1d4ed8',
              color: '#ffffff',
              fontSize: '10px',
              fontWeight: '700',
              borderRadius: '50%',
              width: '15px',
              height: '15px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {attachmentCount}
            </span>
          )}
        </button>

        <AttachmentMenu
          isOpen={menuOpen}
          onClose={() => setMenuOpen(false)}
          onSelectType={(type) => {
            onOpenPicker(type);
          }}
        />

        <ModeSelector activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>

      {/* Right Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Voice Button */}
        <button
          onClick={handleMicClick}
          aria-label="Record voice input"
          title={recording ? 'Stop voice recording' : 'Voice input'}
          style={{
            width: '34px',
            height: '34px',
            borderRadius: '10px',
            backgroundColor: recording ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
            border: recording ? '1px solid #ef4444' : 'none',
            color: recording ? '#ef4444' : '#94a3b8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <Mic size={18} className={recording ? 'animate-pulse' : ''} />
        </button>

        {/* Send or Stop Button */}
        {loading ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generation"
            title="Stop generation (Esc)"
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              backgroundColor: '#121215',
              border: '1px solid #1d4ed8',
              color: '#3b82f6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              boxShadow: '0 0 14px rgba(29, 78, 216, 0.4)'
            }}
          >
            <Square size={13} fill="#1d4ed8" />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSend}
            disabled={!canSend}
            aria-label="Send message"
            title={canSend ? 'Send message' : 'Type a message or attach a file'}
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              backgroundColor: canSend ? '#1d4ed8' : '#141418',
              color: canSend ? '#ffffff' : '#64748b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: 'none',
              cursor: canSend ? 'pointer' : 'not-allowed',
              transition: 'all 0.15s ease',
              boxShadow: canSend ? '0 2px 10px rgba(29, 78, 216, 0.4)' : 'none'
            }}
          >
            <ArrowUp size={18} strokeWidth={2.5} />
          </button>
        )}
      </div>
    </div>
  );
}
