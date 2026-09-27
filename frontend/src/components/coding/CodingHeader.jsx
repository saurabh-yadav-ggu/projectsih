import React from 'react';
import {
  Code,
  MessageSquare,
  ShieldCheck,
  ShieldAlert,
  Shield,
  Folder,
  Circle,
  ChevronDown,
} from 'lucide-react';

export default function CodingHeader({
  activeTab = 'Coding',
  setActiveTab,
  workspaceRoot = '',
  isConnected = false,
  selectedModel = 'default',
  onChangeModel,
  hitlMode = 'safe',
  onChangeHitlMode,
  user = null,
  onOpenWorkspaceModal,
}) {
  const folderName = workspaceRoot ? workspaceRoot.split(/[\/\\]/).pop() || 'workspace' : 'workspace';

  return (
    <div
      style={{
        height: '46px',
        backgroundColor: '#000000',
        borderBottom: '1px solid #1a1a20',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      {/* Left: Brand & Mode Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={20} color="#1d4ed8" strokeWidth={2.2} />
          <span style={{ fontSize: '13.5px', fontWeight: 600, color: '#ffffff', letterSpacing: '-0.01em' }}>
            Shield AI
          </span>
          <span
            style={{
              fontSize: '11px',
              padding: '1px 6px',
              borderRadius: '4px',
              backgroundColor: '#172554',
              color: '#93c5fd',
              fontWeight: 500,
            }}
          >
            Studio
          </span>
        </div>

        {/* Mode Selector Pill */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: '#0a0a0d',
            padding: '3px',
            borderRadius: '20px',
            border: '1px solid #1a1a20',
          }}
        >
          <button
            onClick={() => setActiveTab('Chat')}
            style={{
              padding: '3px 10px',
              borderRadius: '16px',
              fontSize: '11.5px',
              fontWeight: 500,
              color: activeTab === 'Chat' ? '#ffffff' : '#94a3b8',
              backgroundColor: activeTab === 'Chat' ? '#172554' : 'transparent',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <MessageSquare size={12} color={activeTab === 'Chat' ? '#3b82f6' : '#94a3b8'} />
            <span>Chat</span>
          </button>

          <button
            onClick={() => setActiveTab('Coding')}
            style={{
              padding: '3px 10px',
              borderRadius: '16px',
              fontSize: '11.5px',
              fontWeight: 500,
              color: activeTab === 'Coding' ? '#ffffff' : '#94a3b8',
              backgroundColor: activeTab === 'Coding' ? '#172554' : 'transparent',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {activeTab === 'Coding' && (
              <div style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: '#3b82f6' }} />
            )}
            <Code size={12} color={activeTab === 'Coding' ? '#3b82f6' : '#94a3b8'} />
            <span>Coding</span>
          </button>
        </div>
      </div>

      {/* Center: Active Workspace Selector Button */}
      <button
        onClick={onOpenWorkspaceModal}
        title="Click to select or switch workspace directory (where the agent writes code)"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 10px',
          borderRadius: '6px',
          backgroundColor: '#0a0b10',
          border: '1px solid #1e2230',
          fontSize: '11.5px',
          color: '#cbd5e1',
          maxWidth: '340px',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#131726';
          e.currentTarget.style.borderColor = '#2563eb';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = '#0a0b10';
          e.currentTarget.style.borderColor = '#1e2230';
        }}
      >
        <Folder size={13} color="#3b82f6" style={{ flexShrink: 0 }} />
        <span style={{ color: '#64748b' }}>Workspace:</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 600, color: '#93c5fd' }}>
          {folderName}
        </span>
        <ChevronDown size={12} color="#64748b" style={{ flexShrink: 0, marginLeft: '2px' }} />
      </button>

      {/* Right: HITL Mode, Model Selector & Connection Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Human-in-the-Loop (HITL) Mode Selector */}
        <div
          title={
            hitlMode === 'safe'
              ? 'HITL Safe: Shell commands require human approval before execution'
              : hitlMode === 'strict'
              ? 'HITL Strict: All shell commands and file modifications require human approval'
              : 'Full Auto: Agent executes commands without pausing for approval'
          }
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#0a0a0d',
            border: `1px solid ${hitlMode === 'strict' ? '#ef4444' : hitlMode === 'safe' ? '#2563eb' : '#f59e0b'}`,
            borderRadius: '6px',
            padding: '3px 8px',
          }}
        >
          <ShieldAlert size={12} color={hitlMode === 'strict' ? '#ef4444' : hitlMode === 'safe' ? '#60a5fa' : '#f59e0b'} />
          <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 500 }}>HITL:</span>
          <select
            value={hitlMode}
            onChange={(e) => onChangeHitlMode && onChangeHitlMode(e.target.value)}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: '11.5px',
              fontWeight: 600,
              color: hitlMode === 'strict' ? '#f87171' : hitlMode === 'safe' ? '#93c5fd' : '#fcd34d',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="safe" style={{ backgroundColor: '#0a0a0d', color: '#fff' }}>Safe (Shell Approval)</option>
            <option value="strict" style={{ backgroundColor: '#0a0a0d', color: '#fff' }}>Strict (All Actions)</option>
            <option value="auto" style={{ backgroundColor: '#0a0a0d', color: '#fff' }}>Full Auto (Unattended)</option>
          </select>
        </div>

        {/* Live Status Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '11px',
            color: isConnected ? '#22c55e' : '#f59e0b',
            padding: '2px 8px',
            borderRadius: '12px',
            backgroundColor: isConnected ? 'rgba(34, 197, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            border: isConnected ? '1px solid rgba(34, 197, 94, 0.2)' : '1px solid rgba(245, 158, 11, 0.2)',
          }}
        >
          <Circle size={6} fill={isConnected ? '#22c55e' : '#f59e0b'} strokeWidth={0} />
          <span>{isConnected ? 'Agent Live' : 'Connecting...'}</span>
        </div>
      </div>
    </div>
  );
}
