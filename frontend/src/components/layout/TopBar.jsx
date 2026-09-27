import React from 'react';

export default function TopBar({ activeTab = 'Chat', setActiveTab }) {
  return (
    <div style={{ 
      padding: '24px 32px', 
      display: 'flex', 
      justifyContent: 'space-between',
      alignItems: 'center'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-orange)' }} />
        <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          SECURE AND OFFLINE
        </span>
      </div>

      <div style={{ 
        display: 'flex', 
        alignItems: 'center',
        gap: '4px',
        backgroundColor: '#0a0a0d',
        padding: '3px', 
        borderRadius: '20px',
        border: '1px solid #1a1a20'
      }}>
        <button
          onClick={() => setActiveTab && setActiveTab('Chat')}
          style={{
            fontSize: '12.5px',
            fontWeight: 500,
            color: activeTab === 'Chat' ? '#ffffff' : '#94a3b8',
            backgroundColor: activeTab === 'Chat' ? '#172554' : 'transparent',
            padding: '4px 14px',
            borderRadius: '16px',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          Chat
        </button>
        <button
          onClick={() => setActiveTab && setActiveTab('Coding')}
          style={{
            fontSize: '12.5px',
            fontWeight: 500,
            color: activeTab === 'Coding' ? '#ffffff' : '#94a3b8',
            backgroundColor: activeTab === 'Coding' ? '#172554' : 'transparent',
            padding: '4px 14px',
            borderRadius: '16px',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          Coding
        </button>
      </div>
    </div>
  );
}
