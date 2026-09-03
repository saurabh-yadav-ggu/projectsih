import React from 'react';
import { 
  ShieldCheck, Plus, Filter, Download, LayoutTemplate, Settings, Command 
} from 'lucide-react';

export default function Sidebar({ user, onLogout, showAccountMenu, setShowAccountMenu }) {
  const userInitials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
    : 'U';

  const recentTasks = [
    { text: 'V-BAT Swarm Border Reconnaissance', color: 'var(--accent-green)' },
    { text: 'GPS-Denied Waypoint Nav Protocol', color: 'var(--accent-orange)' },
    { text: 'Counter-sUAS Interceptor Mesh Test', color: 'var(--text-muted)' },
    { text: 'Tactical Edge Vision Model v8.4 Eval', color: 'var(--text-muted)' },
    { text: 'Autonomous EW Detection Envelope', color: 'var(--text-muted)' },
    { text: 'Fighter-Jet Co-Pilot Swarm Logic', color: 'var(--text-muted)' },
    { text: 'Low-Altitude LIDAR Obstacle Avoidance', color: 'var(--text-muted)' }
  ];

  return (
    <div className="sidebar">
      {/* Sidebar Header */}
      <div style={{ padding: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheck size={24} color="var(--accent-orange)" strokeWidth={2} />
          <span style={{ fontSize: '18px', fontWeight: '600', letterSpacing: '-0.02em', color: '#fff' }}>Shield AI</span>
        </div>
        <div style={{ 
          fontSize: '9px', 
          fontWeight: '700', 
          color: 'var(--accent-orange)', 
          border: '1px solid var(--accent-orange)',
          borderRadius: '4px',
          padding: '2px 6px',
          letterSpacing: '0.05em',
          whiteSpace: 'nowrap'
        }}>
          SECURE
        </div>
      </div>

      {/* New Button */}
      <div style={{ padding: '0 24px', marginBottom: '24px' }}>
        <button style={{ 
          width: '100%', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          backgroundColor: 'var(--bg-button)',
          padding: '10px 14px',
          borderRadius: '8px',
          color: '#fff',
          fontSize: '14px',
          fontWeight: '500',
          cursor: 'pointer'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Plus size={16} />
            <span>New</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '2px', color: 'var(--text-muted)' }}>
            <Command size={12} />
            <span style={{ fontSize: '12px' }}>N</span>
          </div>
        </button>
      </div>

      {/* Navigation Links */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '0 16px' }}>
        {['Documents', 'Projects'].map(item => (
          <div key={item} style={{ padding: '8px 12px', fontSize: '14px', color: '#d1d5db', cursor: 'pointer', borderRadius: '6px' }} className="nav-item">
            {item}
          </div>
        ))}
        <div style={{ padding: '8px 12px', fontSize: '14px', color: '#d1d5db', cursor: 'pointer', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }} className="nav-item">
          <span>Skills</span>
          <span style={{ fontSize: '10px', fontWeight: '600', color: 'var(--accent-green)', border: '1px solid var(--accent-green)', padding: '2px 6px', borderRadius: '4px' }}>LIVE v4.2</span>
        </div>
        {['Coding', 'Customize'].map(item => (
          <div key={item} style={{ padding: '8px 12px', fontSize: '14px', color: '#d1d5db', cursor: 'pointer', borderRadius: '6px' }} className="nav-item">
            {item}
          </div>
        ))}
      </div>

      {/* Recent Section */}
      <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        <div style={{ 
          padding: '0 24px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '16px'
        }}>
          <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>RECENT CHATS AND TASKS</span>
          <Filter size={14} color="var(--text-muted)" style={{ cursor: 'pointer' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', padding: '0 16px', overflowY: 'auto', flex: 1 }}>
          {recentTasks.map((task, i) => (
            <div key={i} style={{ 
              padding: '8px 12px', 
              fontSize: '13px', 
              color: 'var(--text-secondary)', 
              cursor: 'pointer', 
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              flexShrink: 0
            }} className="nav-item">
              <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: task.color, flexShrink: 0 }} />
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{task.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom Profile Area */}
      <div style={{ display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {showAccountMenu && (
          <div style={{
            position: 'absolute',
            bottom: '100%',
            left: '24px',
            width: 'calc(100% - 48px)',
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '8px',
            marginBottom: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            zIndex: 10
          }}>
            <div style={{ padding: '8px', borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#fff' }}>{user?.name}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{user?.email}</div>
            </div>
            <button onClick={onLogout} style={{
              padding: '8px',
              textAlign: 'left',
              fontSize: '13px',
              color: '#ef4444',
              borderRadius: '4px',
              cursor: 'pointer',
              width: '100%',
              backgroundColor: 'transparent',
              border: 'none'
            }} className="nav-item">
              Logout
            </button>
          </div>
        )}
        <div style={{ padding: '0 24px 12px' }}>
          <div style={{ 
            width: '32px', height: '32px', 
            borderRadius: '6px', 
            backgroundColor: 'var(--bg-button)', 
            display: 'flex', alignItems: 'center', justifyContent: 'center' 
          }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-green)' }} />
          </div>
        </div>
        <div style={{ 
          padding: '16px 24px', 
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer'
        }} onClick={() => setShowAccountMenu(!showAccountMenu)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              width: '32px', 
              height: '32px', 
              borderRadius: '8px', 
              backgroundColor: '#3b2f21', 
              color: 'var(--accent-orange)',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: '600'
            }}>
              {userInitials}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '13px', fontWeight: '500', color: '#fff' }}>{user?.name}</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{user?.designation || 'Account'}</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-muted)' }} onClick={e => e.stopPropagation()}>
            <Download size={16} style={{ cursor: 'pointer' }} />
            <LayoutTemplate size={16} style={{ cursor: 'pointer' }} />
            <Settings size={16} style={{ cursor: 'pointer' }} />
          </div>
        </div>
      </div>
    </div>
  );
}
