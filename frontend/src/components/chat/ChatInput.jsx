import React from 'react';
import { Plus, ChevronDown, Mic, ArrowUp } from 'lucide-react';

export default function ChatInput({ 
  inputValue, 
  setInputValue, 
  activeTab, 
  setActiveTab 
}) {
  return (
    <div style={{ 
      width: '100%', 
      maxWidth: '800px', 
      backgroundColor: 'var(--bg-input)',
      border: '1px solid var(--border-color)',
      borderRadius: '16px',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px'
    }}>
      <textarea 
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Task Hivemind swarm or query defense systems..."
        style={{
          width: '100%',
          minHeight: '60px',
          resize: 'none',
          fontSize: '16px',
          lineHeight: '1.5',
          color: '#fff',
          backgroundColor: 'transparent',
          border: 'none',
          outline: 'none'
        }}
      />

      {/* Input Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button style={{ 
            width: '32px', height: '32px', 
            borderRadius: '8px', 
            backgroundColor: 'var(--bg-button)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-primary)',
            border: 'none',
            cursor: 'pointer'
          }}>
            <Plus size={16} />
          </button>
          
          <div style={{ 
            display: 'flex', 
            backgroundColor: 'var(--bg-button)', 
            padding: '4px', 
            borderRadius: '20px'
          }}>
            {['Chat', 'Coding'].map(tab => (
              <button 
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{ 
                  padding: '4px 12px', 
                  borderRadius: '16px',
                  fontSize: '13px',
                  fontWeight: '500',
                  color: activeTab === tab ? '#fff' : 'var(--text-muted)',
                  backgroundColor: activeTab === tab ? '#333640' : 'transparent',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {activeTab === tab && <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--accent-orange)' }} />}
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button style={{ 
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px',
            borderRadius: '20px',
            backgroundColor: 'transparent',
            color: 'var(--text-muted)',
            fontSize: '13px',
            border: 'none',
            cursor: 'pointer'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: '#fff', fontSize: '13px', fontWeight: '500' }}>Hivemind</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', border: '1px solid #333', padding: '2px 4px', borderRadius: '4px' }}>v4.2</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              Max <ChevronDown size={14} />
            </div>
          </button>
          <button style={{ color: 'var(--text-muted)', backgroundColor: 'transparent', border: 'none', cursor: 'pointer' }}>
            <Mic size={20} />
          </button>
          <button style={{ 
            width: '32px', height: '32px', 
            borderRadius: '8px', 
            backgroundColor: 'var(--bg-button)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--text-primary)',
            border: 'none',
            cursor: 'pointer'
          }}>
            <ArrowUp size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
