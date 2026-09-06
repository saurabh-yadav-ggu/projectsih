import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Wrench, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';

function formatToolName(name = '') {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

export default function ToolExecution({ toolCalls = [], isStreaming = false }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!toolCalls || toolCalls.length === 0) return null;

  const runningCount = toolCalls.filter(tc => tc.status === 'running').length;
  const completedCount = toolCalls.filter(tc => tc.status === 'completed').length;
  const hasError = toolCalls.some(tc => tc.status === 'error');
  const isActive = runningCount > 0 || isStreaming;

  return (
    <div style={{
      marginBottom: '10px',
      borderRadius: '10px',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      backgroundColor: 'rgba(0, 0, 0, 0.25)',
      overflow: 'hidden',
      fontSize: '13px',
      transition: 'all 0.2s ease'
    }}>
      {/* Header / Toggle bar */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          backgroundColor: isExpanded ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
          color: '#94a3b8',
          cursor: 'pointer',
          border: 'none',
          textAlign: 'left'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isActive ? (
            <Loader2 size={14} style={{ color: '#f97316', animation: 'spin 1s linear infinite' }} />
          ) : hasError ? (
            <AlertCircle size={14} style={{ color: '#ef4444' }} />
          ) : (
            <CheckCircle2 size={14} style={{ color: '#22c55e' }} />
          )}
          <span style={{ fontWeight: 500, color: '#cbd5e1' }}>
            {isActive
              ? `Agent executing tools (${completedCount}/${toolCalls.length})...`
              : `Agent executed ${toolCalls.length} ${toolCalls.length === 1 ? 'tool' : 'tools'}`}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: '#64748b' }}>
          <span>{isExpanded ? 'Hide' : 'View'}</span>
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {/* Expanded Step Details */}
      {isExpanded && (
        <div style={{
          padding: '10px 14px',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          {toolCalls.map((tc, index) => {
            const isRunning = tc.status === 'running';
            const isDone = tc.status === 'completed';
            const isErr = tc.status === 'error';

            return (
              <div
                key={tc.id || index}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  fontSize: '12px',
                  color: '#94a3b8'
                }}
              >
                {isRunning ? (
                  <Loader2 size={13} style={{ color: '#f97316', animation: 'spin 1s linear infinite', marginTop: '2px' }} />
                ) : isDone ? (
                  <CheckCircle2 size={13} style={{ color: '#22c55e', marginTop: '2px' }} />
                ) : isErr ? (
                  <AlertCircle size={13} style={{ color: '#ef4444', marginTop: '2px' }} />
                ) : (
                  <Wrench size={13} style={{ color: '#64748b', marginTop: '2px' }} />
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                      {formatToolName(tc.tool)}
                    </span>
                    <span style={{
                      fontSize: '10px',
                      padding: '1px 5px',
                      borderRadius: '4px',
                      backgroundColor: isRunning
                        ? 'rgba(249, 115, 22, 0.15)'
                        : isDone
                        ? 'rgba(34, 197, 94, 0.15)'
                        : 'rgba(255, 255, 255, 0.08)',
                      color: isRunning ? '#fed7aa' : isDone ? '#86efac' : '#94a3b8'
                    }}>
                      {tc.status}
                    </span>
                  </div>

                  {tc.output && (
                    <div style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.35)',
                      padding: '6px 8px',
                      borderRadius: '6px',
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '11px',
                      color: '#94a3b8',
                      marginTop: '4px',
                      maxHeight: '120px',
                      overflowY: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all'
                    }}>
                      {typeof tc.output === 'object' ? JSON.stringify(tc.output, null, 2) : String(tc.output)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
