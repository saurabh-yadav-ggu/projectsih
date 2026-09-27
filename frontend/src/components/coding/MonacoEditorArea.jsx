import React from 'react';
import Editor from '@monaco-editor/react';
import { X, FileCode, Save, Sparkles, Code2, Terminal } from 'lucide-react';

export default function MonacoEditorArea({
  tabs = [],
  activeTabPath = null,
  onSelectTab,
  onCloseTab,
  onChangeContent,
  onSaveFile,
  isLoading = false,
}) {
  const activeTab = tabs.find((t) => t.path === activeTabPath);

  // Keyboard shortcut Ctrl+S / Cmd+S
  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      onSaveFile();
    }
  };

  return (
    <div
      onKeyDown={handleKeyDown}
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#000000',
        overflow: 'hidden',
      }}
    >
      {/* Tabs Header */}
      {tabs.length > 0 && (
        <div
          style={{
            height: '38px',
            backgroundColor: '#050507',
            borderBottom: '1px solid #1a1a20',
            display: 'flex',
            alignItems: 'center',
            overflowX: 'auto',
            userSelect: 'none',
          }}
        >
          {tabs.map((tab) => {
            const isActive = tab.path === activeTabPath;
            return (
              <div
                key={tab.path}
                onClick={() => onSelectTab(tab.path)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '0 12px',
                  height: '100%',
                  fontSize: '12px',
                  cursor: 'pointer',
                  borderRight: '1px solid #1a1a20',
                  backgroundColor: isActive ? '#000000' : 'transparent',
                  color: isActive ? '#60a5fa' : '#94a3b8',
                  borderTop: isActive ? '2px solid #2563eb' : '2px solid transparent',
                  fontWeight: isActive ? 500 : 400,
                  transition: 'background 0.1s ease',
                  flexShrink: 0,
                }}
              >
                <FileCode size={13} color={isActive ? '#3b82f6' : '#64748b'} />
                <span style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {tab.name}
                </span>

                {/* Dirty Indicator Dot */}
                {tab.isDirty && (
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#3b82f6',
                    }}
                    title="Unsaved changes"
                  />
                )}

                {/* Close Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseTab(tab.path);
                  }}
                  style={{
                    padding: '2px',
                    borderRadius: '4px',
                    color: '#64748b',
                    display: 'flex',
                    alignItems: 'center',
                    border: 'none',
                    background: 'none',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
                >
                  <X size={12} />
                </button>
              </div>
            );
          })}

          {/* Save Action Badge */}
          {activeTab && activeTab.isDirty && (
            <button
              onClick={onSaveFile}
              title="Save (Ctrl+S)"
              style={{
                marginLeft: 'auto',
                marginRight: '12px',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                backgroundColor: '#172554',
                color: '#93c5fd',
                border: '1px solid #1d4ed8',
              }}
            >
              <Save size={12} />
              <span>Save</span>
            </button>
          )}
        </div>
      )}

      {/* Editor Surface or Empty State */}
      <div style={{ flex: 1, position: 'relative' }}>
        {activeTab ? (
          <Editor
            height="100%"
            path={activeTab.path}
            language={activeTab.language || 'plaintext'}
            value={activeTab.content}
            theme="vs-dark"
            onChange={(val) => onChangeContent(activeTab.path, val || '')}
            options={{
              fontSize: 13,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              minimap: { enabled: true },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              automaticLayout: true,
              smoothScrolling: true,
              cursorBlinking: 'smooth',
              cursorSmoothCaretAnimation: 'on',
              lineNumbersMinChars: 3,
              padding: { top: 12 },
              renderLineHighlight: 'all',
              bracketPairColorization: { enabled: true },
            }}
          />
        ) : (
          <div
            style={{
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              padding: '24px',
              color: '#64748b',
            }}
          >
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                border: '1px solid rgba(37, 99, 235, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
              }}
            >
              <Code2 size={28} color="#3b82f6" />
            </div>

            <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
              Shield AI Coding Studio
            </h2>
            <p style={{ fontSize: '13px', color: '#94a3b8', maxWidth: '380px', marginBottom: '24px', lineHeight: 1.5 }}>
              Autonomous coding environment with Monaco code editor, shell terminal, and Deep Agents integration.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', maxWidth: '520px', width: '100%' }}>
              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#050507', border: '1px solid #1a1a20', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#60a5fa', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  <FileCode size={13} />
                  <span>Files</span>
                </div>
                <p style={{ fontSize: '11px', color: '#64748b' }}>Select any file from the explorer on the left to edit.</p>
              </div>

              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#050507', border: '1px solid #1a1a20', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#a855f7', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  <Sparkles size={13} />
                  <span>Agent</span>
                </div>
                <p style={{ fontSize: '11px', color: '#64748b' }}>Ask the Agent on the right to build, debug, or refactor code.</p>
              </div>

              <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: '#050507', border: '1px solid #1a1a20', textAlign: 'left' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  <Terminal size={13} />
                  <span>Terminal</span>
                </div>
                <p style={{ fontSize: '11px', color: '#64748b' }}>Run python, npm, git commands in the terminal drawer below.</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
