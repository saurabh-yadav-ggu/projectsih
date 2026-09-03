import React from 'react';

export default function Footer() {
  return (
    <div style={{ 
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      padding: '24px 32px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      borderTop: '1px solid var(--border-color)'
    }}>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
        Secure . Fast . Offline
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-green)' }} />
        <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          ALL SYSTEMS OPERATIONAL
        </span>
      </div>
    </div>
  );
}
