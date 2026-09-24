import React from 'react';
import { MessageSquare, Code } from 'lucide-react';

export default function ModeSelector({ activeTab, setActiveTab }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      backgroundColor: '#0a0a0d',
      padding: '3px',
      borderRadius: '20px',
      border: '1px solid #1a1a20'
    }}>
      {[
        { id: 'Chat', icon: MessageSquare },
        { id: 'Coding', icon: Code }
      ].map(({ id, icon: Icon }) => {
        const isSelected = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            style={{
              padding: '4px 12px',
              borderRadius: '16px',
              fontSize: '12.5px',
              fontWeight: 500,
              color: isSelected ? '#ffffff' : '#94a3b8',
              backgroundColor: isSelected ? '#172554' : 'transparent',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {isSelected && (
              <div style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#1d4ed8' }} />
            )}
            <Icon size={13} style={{ color: isSelected ? '#3b82f6' : '#94a3b8' }} />
            <span>{id}</span>
          </button>
        );
      })}
    </div>
  );
}
