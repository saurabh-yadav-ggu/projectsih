import React from 'react';

export default function TopBar() {
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
        gap: '8px',
        backgroundColor: 'transparent',
        padding: '6px 16px', 
        borderRadius: '20px',
        border: '1px solid #333'
      }}>
        <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-muted)' }}>Chat</span>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>•</span>
        <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--accent-orange)' }}>Coding</span>
      </div>
    </div>
  );
}
