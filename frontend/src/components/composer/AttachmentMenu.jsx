import React, { useEffect, useRef } from 'react';
import { Image, FileText } from 'lucide-react';

export default function AttachmentMenu({ isOpen, onClose, onSelectType }) {
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div ref={menuRef} style={{
      position: 'absolute',
      bottom: '100%',
      left: '0',
      marginBottom: '8px',
      backgroundColor: '#0a0a0d',
      border: '1px solid #1a1a20',
      borderRadius: '12px',
      padding: '6px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
      zIndex: 50,
      minWidth: '160px'
    }}>
      <button
        onClick={() => {
          onSelectType('image');
          onClose();
        }}
        aria-label="Attach image"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '8px 12px',
          fontSize: '13px',
          color: '#f8fafc',
          borderRadius: '8px',
          backgroundColor: 'transparent',
          cursor: 'pointer',
          textAlign: 'left'
        }}
        className="nav-item"
      >
        <Image size={16} style={{ color: '#38bdf8' }} />
        <span>Attach Image</span>
      </button>

      <button
        onClick={() => {
          onSelectType('document');
          onClose();
        }}
        aria-label="Attach document"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '8px 12px',
          fontSize: '13px',
          color: '#f8fafc',
          borderRadius: '8px',
          backgroundColor: 'transparent',
          cursor: 'pointer',
          textAlign: 'left'
        }}
        className="nav-item"
      >
        <FileText size={16} style={{ color: '#3b82f6' }} />
        <span>Attach Document</span>
      </button>
    </div>
  );
}
