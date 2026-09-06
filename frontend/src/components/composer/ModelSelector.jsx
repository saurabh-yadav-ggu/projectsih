import React, { useState, useRef, useEffect } from 'react';
import { Cpu, ChevronDown, Check } from 'lucide-react';

export default function ModelSelector() {
  const [open, setOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('Hivemind v4.2 Max');
  const dropdownRef = useRef(null);

  const models = [
    { name: 'Hivemind v4.2 Max', tag: 'Offline / Local', desc: 'Ministral 3:3b + Gemma Embeddings' },
    { name: 'Shield Vision 3B', tag: 'Multi-Modal', desc: 'Local Image Analysis Engine' },
    { name: 'RAG Knowledge Core', tag: 'Thread Scoped', desc: 'ChromaDB Vector Store Retrieval' }
  ];

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [open]);

  return (
    <div ref={dropdownRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(!open)}
        aria-label="Select AI Model"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 10px',
          borderRadius: '16px',
          backgroundColor: 'transparent',
          color: '#94a3b8',
          fontSize: '12.5px',
          border: 'none',
          cursor: 'pointer'
        }}
        title="Model configuration"
      >
        <Cpu size={14} style={{ color: '#f97316' }} />
        <span style={{ color: '#f8fafc', fontWeight: 500 }}>{selectedModel}</span>
        <ChevronDown size={13} style={{ color: '#64748b' }} />
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          right: '0',
          marginBottom: '8px',
          backgroundColor: '#181b26',
          border: '1px solid #282c3f',
          borderRadius: '12px',
          padding: '6px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
          zIndex: 50,
          minWidth: '240px'
        }}>
          {models.map(m => (
            <button
              key={m.name}
              onClick={() => {
                setSelectedModel(m.name);
                setOpen(false);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                borderRadius: '8px',
                backgroundColor: selectedModel === m.name ? '#232738' : 'transparent',
                cursor: 'pointer',
                textAlign: 'left',
                border: 'none'
              }}
              className="nav-item"
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ fontSize: '13px', fontWeight: 500, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>{m.name}</span>
                  <span style={{ fontSize: '10px', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)', borderRadius: '4px', padding: '1px 4px' }}>
                    {m.tag}
                  </span>
                </div>
                <span style={{ fontSize: '11px', color: '#64748b' }}>{m.desc}</span>
              </div>
              {selectedModel === m.name && <Check size={14} style={{ color: '#4ade80' }} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
