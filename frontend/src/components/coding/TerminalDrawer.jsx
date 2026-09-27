import React, { useState, useRef, useEffect } from 'react';
import {
  Terminal as TerminalIcon,
  GitBranch,
  ChevronUp,
  ChevronDown,
  Trash2,
  Maximize2,
  Minimize2,
  CornerDownLeft,
  CheckCircle2,
  FileCode,
} from 'lucide-react';

export default function TerminalDrawer({
  lines = [],
  cwd = '',
  isRunning = false,
  onRunCommand,
  gitStatus = { is_git: false, branch: '', status: '', diff: '' },
}) {
  const [isOpen, setIsOpen] = useState(true);
  const [isMaximized, setIsMaximized] = useState(false);
  const [activeTab, setActiveTab] = useState('terminal'); // 'terminal' | 'git'
  const [inputVal, setInputVal] = useState('');
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto scroll to bottom
  useEffect(() => {
    if (isOpen && activeTab === 'terminal') {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [lines, isRunning, isOpen, activeTab]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const clean = inputVal.trim();
    if (!clean) return;

    setHistory((prev) => [...prev, clean]);
    setHistoryIndex(-1);
    setInputVal('');
    onRunCommand(clean);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const nextIdx = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
        setHistoryIndex(nextIdx);
        setInputVal(history[nextIdx] || '');
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex !== -1) {
        const nextIdx = historyIndex + 1;
        if (nextIdx >= history.length) {
          setHistoryIndex(-1);
          setInputVal('');
        } else {
          setHistoryIndex(nextIdx);
          setInputVal(history[nextIdx] || '');
        }
      }
    }
  };

  const folderName = cwd ? cwd.split(/[\/\\]/).pop() || 'workspace' : 'workspace';
  const drawerHeight = isMaximized ? '420px' : isOpen ? '220px' : '36px';

  return (
    <div
      style={{
        height: drawerHeight,
        backgroundColor: '#050507',
        borderTop: '1px solid #1a1a20',
        display: 'flex',
        flexDirection: 'column',
        transition: 'height 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Drawer Bar */}
      <div
        style={{
          height: '36px',
          backgroundColor: '#000000',
          borderBottom: isOpen ? '1px solid #1a1a20' : 'none',
          padding: '0 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          userSelect: 'none',
          cursor: 'pointer',
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {/* Left Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(true);
              setActiveTab('terminal');
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 500,
              backgroundColor: activeTab === 'terminal' && isOpen ? '#172554' : 'transparent',
              color: activeTab === 'terminal' && isOpen ? '#93c5fd' : '#94a3b8',
              border: 'none',
            }}
          >
            <TerminalIcon size={13} color={activeTab === 'terminal' ? '#3b82f6' : '#64748b'} />
            <span>Terminal</span>
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(true);
              setActiveTab('git');
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 500,
              backgroundColor: activeTab === 'git' && isOpen ? '#172554' : 'transparent',
              color: activeTab === 'git' && isOpen ? '#93c5fd' : '#94a3b8',
              border: 'none',
            }}
          >
            <GitBranch size={13} color={activeTab === 'git' ? '#3b82f6' : '#64748b'} />
            <span>Git {gitStatus.branch ? `(${gitStatus.branch})` : ''}</span>
          </button>
        </div>

        {/* Right Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
          {isOpen && (
            <button
              onClick={() => setIsMaximized(!isMaximized)}
              title={isMaximized ? 'Restore' : 'Maximize'}
              style={{ padding: '4px', color: '#94a3b8' }}
            >
              {isMaximized ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            </button>
          )}

          <button
            onClick={() => setIsOpen(!isOpen)}
            title={isOpen ? 'Collapse' : 'Expand'}
            style={{ padding: '4px', color: '#94a3b8' }}
          >
            {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      {/* Drawer Content */}
      {isOpen && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {activeTab === 'terminal' ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                padding: '8px 12px',
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: '12px',
                overflowY: 'auto',
                backgroundColor: '#050507',
              }}
              onClick={() => inputRef.current?.focus()}
            >
              {/* Output Lines */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {lines.map((line) => {
                  if (line.type === 'command') {
                    return (
                      <div key={line.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#60a5fa' }}>
                        <span style={{ color: '#22c55e' }}>➜</span>
                        <span style={{ color: '#06b6d4' }}>{folderName}</span>
                        <span style={{ color: '#f8fafc', fontWeight: 500 }}>{line.content}</span>
                      </div>
                    );
                  } else if (line.type === 'stdout') {
                    return (
                      <pre
                        key={line.id}
                        style={{
                          margin: 0,
                          color: '#cbd5e1',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'inherit',
                          lineHeight: 1.45,
                        }}
                      >
                        {line.content}
                      </pre>
                    );
                  } else if (line.type === 'stderr') {
                    return (
                      <pre
                        key={line.id}
                        style={{
                          margin: 0,
                          color: '#f87171',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'inherit',
                          lineHeight: 1.45,
                        }}
                      >
                        {line.content}
                      </pre>
                    );
                  } else {
                    return (
                      <div key={line.id} style={{ color: '#64748b', fontSize: '11px', fontStyle: 'italic' }}>
                        {line.content}
                      </div>
                    );
                  }
                })}

                {isRunning && (
                  <div style={{ color: '#fbbf24', fontSize: '11.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#fbbf24' }} className="animate-pulse" />
                    <span>Running command...</span>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>

              {/* Input Prompt Row */}
              <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                <span style={{ color: '#22c55e', userSelect: 'none' }}>➜</span>
                <span style={{ color: '#06b6d4', userSelect: 'none' }}>{folderName}</span>
                <input
                  ref={inputRef}
                  type="text"
                  value={inputVal}
                  onChange={(e) => setInputVal(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={isRunning ? 'Executing...' : 'Type command here...'}
                  disabled={isRunning}
                  style={{
                    flex: 1,
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: '#f8fafc',
                    fontFamily: 'inherit',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                />
              </form>
            </div>
          ) : (
            /* Git Tab Content */
            <div style={{ flex: 1, padding: '12px', overflowY: 'auto', fontSize: '12px', color: '#cbd5e1' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <GitBranch size={16} color="#3b82f6" />
                <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                  Branch: {gitStatus.branch || 'None / Not a git repository'}
                </span>
              </div>

              {gitStatus.status ? (
                <div>
                  <h4 style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Changed Files
                  </h4>
                  <pre
                    style={{
                      backgroundColor: '#0a0a0d',
                      border: '1px solid #1a1a20',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: '#fbbf24',
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '11.5px',
                      whiteSpace: 'pre-wrap',
                      marginBottom: '12px',
                    }}
                  >
                    {gitStatus.status}
                  </pre>
                </div>
              ) : (
                <p style={{ color: '#64748b', fontSize: '12px', marginBottom: '12px' }}>
                  Working tree clean. No uncommitted changes.
                </p>
              )}

              {gitStatus.diff && (
                <div>
                  <h4 style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Working Diff
                  </h4>
                  <pre
                    style={{
                      backgroundColor: '#0a0a0d',
                      border: '1px solid #1a1a20',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: '#93c5fd',
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '11px',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {gitStatus.diff}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
