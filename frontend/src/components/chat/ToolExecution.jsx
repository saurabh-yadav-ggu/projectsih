import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Wrench,
  CheckCircle2,
  Loader2,
  AlertCircle,
  FileCheck,
  Cpu,
  Brain,
  Layers,
  Code
} from 'lucide-react';

function formatAgentName(name = '') {
  return name
    .replace(/_agent/gi, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase()) + ' Agent';
}

function formatToolName(name = '') {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

export default function ToolExecution({
  toolCalls = [],
  pipelineSteps = [],
  plan = null,
  verification = null,
  isStreaming = false
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasTools = toolCalls && toolCalls.length > 0;
  const hasSteps = pipelineSteps && pipelineSteps.length > 0;
  const hasPlan = Boolean(plan);
  const hasVerification = Boolean(verification);

  if (!hasTools && !hasSteps && !hasPlan && !hasVerification) return null;

  const runningTools = toolCalls.filter(tc => tc.status === 'running').length;
  const runningSteps = pipelineSteps.filter(s => s.status === 'running').length;
  const isActive = Boolean(isStreaming && (runningTools > 0 || runningSteps > 0 || isStreaming));

  const isVerifiedPass = verification?.status === 'PASS';
  const isVerifiedFail = verification?.status === 'FAIL';

  // Overall label summary
  let summaryLabel = 'Deep Agent Process';
  if (hasSteps) {
    const latestStep = pipelineSteps[pipelineSteps.length - 1];
    summaryLabel = isActive
      ? `Processing: ${formatAgentName(latestStep.agent)}...`
      : `Completed: ${formatAgentName(latestStep.agent)}`;
  } else if (hasTools) {
    summaryLabel = isActive
      ? `Executing tools (${toolCalls.filter(tc => tc.status === 'completed').length}/${toolCalls.length})...`
      : `Executed ${toolCalls.length} ${toolCalls.length === 1 ? 'tool' : 'tools'}`;
  }

  return (
    <div style={{
      marginBottom: '12px',
      borderRadius: '10px',
      border: isVerifiedPass
        ? '1px solid rgba(34, 197, 94, 0.25)'
        : isVerifiedFail
        ? '1px solid rgba(239, 68, 68, 0.25)'
        : '1px solid rgba(255, 255, 255, 0.08)',
      backgroundColor: 'rgba(0, 0, 0, 0.3)',
      overflow: 'hidden',
      fontSize: '13px',
      transition: 'all 0.2s ease'
    }}>
      {/* Header bar */}
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
            <Loader2 size={14} style={{ color: '#3b82f6', animation: 'spin 1s linear infinite' }} />
          ) : isVerifiedFail ? (
            <AlertCircle size={14} style={{ color: '#ef4444' }} />
          ) : (
            <CheckCircle2 size={14} style={{ color: '#22c55e' }} />
          )}

          <span style={{ fontWeight: 500, color: '#cbd5e1' }}>
            {summaryLabel}
          </span>

          {/* Verification Status Pill */}
          {hasVerification && (
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '10px',
              fontWeight: 600,
              padding: '2px 7px',
              borderRadius: '12px',
              backgroundColor: isVerifiedPass ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: isVerifiedPass ? '#86efac' : '#fca5a5',
              border: isVerifiedPass ? '1px solid rgba(34, 197, 94, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
              marginLeft: '6px'
            }}>
              <FileCheck size={11} />
              {isVerifiedPass ? 'Verified' : 'Verification Issue'}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: '#64748b' }}>
          <span>{isExpanded ? 'Hide Details' : 'Details'}</span>
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {/* Expanded Pipeline Details */}
      {isExpanded && (
        <div style={{
          padding: '12px 14px',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          {/* Plan Section if available */}
          {hasPlan && plan.steps && (
            <div style={{
              padding: '8px 10px',
              borderRadius: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              fontSize: '12px',
              color: '#94a3b8'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>
                <Brain size={13} style={{ color: '#3b82f6' }} />
                <span>Execution Plan ({plan.intent})</span>
              </div>
              <ul style={{ margin: '4px 0 0 16px', padding: 0, lineHeight: 1.5 }}>
                {plan.steps.map((st, i) => (
                  <li key={i}>{st}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Subagent Steps */}
          {hasSteps && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {pipelineSteps.map((step, idx) => {
                const isRunning = step.status === 'running';
                return (
                  <div key={step.id || idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                    {isRunning ? (
                      <Loader2 size={13} style={{ color: '#3b82f6', animation: 'spin 1s linear infinite' }} />
                    ) : (
                      <CheckCircle2 size={13} style={{ color: '#22c55e' }} />
                    )}
                    <span style={{ fontWeight: 500, color: '#e2e8f0' }}>
                      {formatAgentName(step.agent)}
                    </span>
                    <span style={{
                      fontSize: '10px',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      backgroundColor: isRunning ? 'rgba(29, 78, 216, 0.2)' : 'rgba(34, 197, 94, 0.15)',
                      color: isRunning ? '#93c5fd' : '#86efac'
                    }}>
                      {step.status}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Tool Calls */}
          {hasTools && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {toolCalls.map((tc, index) => {
                const isRunning = tc.status === 'running';
                const isDone = tc.status === 'completed';
                const isErr = tc.status === 'error';

                return (
                  <div key={tc.id || index} style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {isRunning ? (
                        <Loader2 size={13} style={{ color: '#3b82f6', animation: 'spin 1s linear infinite' }} />
                      ) : isDone ? (
                        <CheckCircle2 size={13} style={{ color: '#22c55e' }} />
                      ) : isErr ? (
                        <AlertCircle size={13} style={{ color: '#ef4444' }} />
                      ) : (
                        <Wrench size={13} style={{ color: '#64748b' }} />
                      )}
                      <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                        {formatToolName(tc.tool)}
                      </span>
                      <span style={{
                        fontSize: '10px',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        backgroundColor: isRunning ? 'rgba(29, 78, 216, 0.2)' : 'rgba(34, 197, 94, 0.15)',
                        color: isRunning ? '#93c5fd' : '#86efac'
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
                        marginLeft: '21px',
                        maxHeight: '100px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {typeof tc.output === 'object' ? JSON.stringify(tc.output, null, 2) : String(tc.output)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Verification Details */}
          {hasVerification && verification.checks && (
            <div style={{
              marginTop: '4px',
              padding: '6px 10px',
              borderRadius: '6px',
              backgroundColor: isVerifiedPass ? 'rgba(34, 197, 94, 0.05)' : 'rgba(239, 68, 68, 0.05)',
              border: isVerifiedPass ? '1px solid rgba(34, 197, 94, 0.15)' : '1px solid rgba(239, 68, 68, 0.15)',
              fontSize: '11px',
              color: '#94a3b8'
            }}>
              <div style={{ fontWeight: 600, color: isVerifiedPass ? '#86efac' : '#fca5a5', marginBottom: '2px' }}>
                Artifact Verification: {verification.status}
              </div>
              <ul style={{ margin: '2px 0 0 16px', padding: 0 }}>
                {verification.checks.map((chk, i) => (
                  <li key={i}>{chk}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
