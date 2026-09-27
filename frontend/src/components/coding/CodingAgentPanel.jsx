import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Sparkles,
  Send,
  Square,
  ChevronDown,
  ChevronRight,
  Terminal,
  FileText,
  Search,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Layers,
  Bot,
  User,
  ShieldAlert,
  Play,
  Users,
  Brain,
  ListChecks,
  DownloadCloud,
  Info,
  X,
  Shield,
  Cpu,
  Plus,
  History,
  Trash2,
  MessageSquarePlus,
} from 'lucide-react';

function getToolIcon(tool) {
  switch (tool) {
    case 'code_interpreter':
      return <Play size={13} color="#ec4899" />;
    case 'verify_task':
      return <CheckCircle2 size={13} color="#22c55e" />;
    case 'create_plan':
    case 'update_plan':
      return <ListChecks size={13} color="#06b6d4" />;
    case 'update_memory':
      return <Brain size={13} color="#f59e0b" />;
    case 'offload_context':
      return <DownloadCloud size={13} color="#10b981" />;
    case 'task':
      return <Users size={13} color="#a855f7" />;
    case 'execute':
      return <Terminal size={13} color="#10b981" />;
    case 'grep':
    case 'glob':
      return <Search size={13} color="#818cf8" />;
    case 'read_file':
    case 'write_file':
    case 'edit_file':
      return <FileText size={13} color="#60a5fa" />;
    default:
      return <Terminal size={13} color="#fbbf24" />;
  }
}

function getToolBadge(toolName, args = {}) {
  switch (toolName) {
    case 'code_interpreter':
      return { label: 'Python Sandbox', color: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)' };
    case 'verify_task':
      return {
        label: `Sandbox Verify: ${args.goal_or_step ? String(args.goal_or_step).slice(0, 24) : 'Task'}`,
        color: '#22c55e',
        bg: 'rgba(34, 197, 94, 0.15)',
      };
    case 'task':
      return {
        label: `Subagent: ${args.name || args.subagent || 'Worker'}`,
        color: '#c084fc',
        bg: 'rgba(192, 132, 252, 0.15)',
      };
    case 'create_plan':
    case 'update_plan':
      return { label: 'Plan Tracking', color: '#22d3ee', bg: 'rgba(34, 211, 238, 0.15)' };
    case 'update_memory':
      return { label: 'Agent Memory', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)' };
    case 'offload_context':
      return { label: 'Context Offload', color: '#34d399', bg: 'rgba(52, 211, 153, 0.15)' };
    default:
      return null;
  }
}

function ToolCard({ tool }) {
  const [isOpen, setIsOpen] = useState(false);
  const badge = getToolBadge(tool.name, tool.args);

  const argSummary = Object.entries(tool.args || {})
    .filter(([k]) => k !== 'code' && k !== 'test_code')
    .map(([k, v]) => `${k}="${String(v).slice(0, 32)}"`)
    .join(' ');

  return (
    <div
      style={{
        margin: '6px 0',
        borderRadius: '6px',
        border: '1px solid #1a1a20',
        backgroundColor: '#0a0a0d',
        fontSize: '11.5px',
        overflow: 'hidden',
      }}
    >
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          cursor: 'pointer',
          backgroundColor: isOpen ? '#111216' : 'transparent',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          {isOpen ? <ChevronDown size={13} color="#64748b" /> : <ChevronRight size={13} color="#64748b" />}
          {getToolIcon(tool.name)}
          <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 600, color: '#f8fafc' }}>
            {tool.name}
          </span>
          {badge && (
            <span
              style={{
                fontSize: '10px',
                fontWeight: 600,
                color: badge.color,
                backgroundColor: badge.bg,
                padding: '1px 6px',
                borderRadius: '4px',
                whiteSpace: 'nowrap',
              }}
            >
              {badge.label}
            </span>
          )}
          <span style={{ color: '#64748b', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {argSummary}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          {tool.durationMs !== undefined && (
            <span style={{ fontSize: '10px', color: '#64748b', fontFamily: 'var(--font-mono, monospace)' }}>
              {tool.durationMs}ms
            </span>
          )}
          {tool.status === 'running' && (
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#fbbf24' }} className="animate-pulse" />
          )}
          {tool.status === 'completed' && <CheckCircle2 size={13} color="#22c55e" />}
        </div>
      </div>

      {isOpen && (
        <div
          style={{
            padding: '8px 10px',
            borderTop: '1px solid #1a1a20',
            backgroundColor: '#000000',
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '11px',
            maxHeight: '220px',
            overflowY: 'auto',
          }}
        >
          {tool.args && tool.args.goal_or_step && (
            <div style={{ marginBottom: '6px', color: '#22c55e', fontSize: '11px', fontWeight: 600 }}>
              GOAL/TARGET: {tool.args.goal_or_step}
            </div>
          )}
          {tool.args && (tool.args.code || tool.args.test_code) && (
            <div style={{ marginBottom: '6px', paddingBottom: '6px', borderBottom: '1px solid #1a1a20' }}>
              <div style={{ color: tool.name === 'verify_task' ? '#22c55e' : '#ec4899', fontSize: '10px', marginBottom: '3px' }}>
                {tool.name === 'verify_task' ? 'VERIFICATION SCRIPT (SANDBOX):' : 'INPUT CODE:'}
              </div>
              <pre style={{ margin: 0, color: tool.name === 'verify_task' ? '#86efac' : '#f472b6', whiteSpace: 'pre-wrap' }}>
                {tool.args.test_code || tool.args.code}
              </pre>
            </div>
          )}
          {tool.output ? (
            <div>
              <div style={{ color: '#64748b', fontSize: '10px', marginBottom: '3px' }}>OUTPUT:</div>
              <pre style={{ margin: 0, color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>{tool.output}</pre>
            </div>
          ) : (
            <span style={{ color: '#64748b', fontStyle: 'italic' }}>Running or no output...</span>
          )}
        </div>
      )}
    </div>
  );
}

function ThoughtAccordion({ thoughts, isStreaming = false }) {
  const [isOpen, setIsOpen] = useState(isStreaming);
  const text = Array.isArray(thoughts) ? thoughts.join('\n\n') : String(thoughts || '');

  if (!text.trim()) return null;

  const lineCount = text.split('\n').filter((l) => l.trim()).length;

  return (
    <div
      style={{
        margin: '6px 0 10px 0',
        borderRadius: '8px',
        border: '1px solid rgba(168, 85, 247, 0.25)',
        backgroundColor: '#07060b',
        overflow: 'hidden',
        transition: 'all 0.18s ease',
      }}
    >
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 10px',
          cursor: 'pointer',
          backgroundColor: isOpen ? 'rgba(168, 85, 247, 0.08)' : 'rgba(255, 255, 255, 0.02)',
          userSelect: 'none',
          borderBottom: isOpen ? '1px solid rgba(168, 85, 247, 0.15)' : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Brain size={13} color="#c084fc" className={isStreaming ? 'animate-pulse' : ''} />
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#e9d5ff', letterSpacing: '-0.01em' }}>
            Thinking Process
          </span>
          <span
            style={{
              fontSize: '9.5px',
              padding: '1px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(192, 132, 252, 0.15)',
              color: '#d8b4fe',
              fontWeight: 500,
            }}
          >
            {isStreaming ? 'Reasoning...' : `${lineCount} steps`}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#a855f7', fontSize: '10px' }}>
          <span>{isOpen ? 'Collapse' : 'Expand'}</span>
          {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </div>
      </div>

      {isOpen && (
        <div
          style={{
            padding: '10px 12px',
            fontSize: '11.5px',
            lineHeight: 1.6,
            color: '#a1a1aa',
            backgroundColor: '#050408',
            maxHeight: '360px',
            overflowY: 'auto',
          }}
          className="prose prose-invert max-w-none text-xs"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {text}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

function PlanAccordion({ planText }) {
  const [isOpen, setIsOpen] = useState(true);

  if (!planText || !planText.trim()) return null;

  let title = 'Execution Plan';
  let goal = '';
  let steps = [];

  try {
    const titleMatch = planText.match(/title\s*=\s*["']([^"']+)["']/i) || planText.match(/# (?:User Profile|Implementation Plan:?)?\s*([^\n]+)/i);
    if (titleMatch) title = titleMatch[1].trim();

    const goalMatch = planText.match(/goal\s*=\s*["']([^"']+)["']/i) || planText.match(/## Goal\s*\n+([^\n]+)/i) || planText.match(/Goal:\s*([^\n]+)/i);
    if (goalMatch) goal = goalMatch[1].trim();

    const stepRegex = /(?:### Step (\d+):?\s*([^\n]+)|{\s*"step_index":\s*(\d+)[\s\S]*?"description":\s*"([^"]+)")/g;
    let sMatch;
    while ((sMatch = stepRegex.exec(planText)) !== null) {
      const idx = sMatch[1] || sMatch[3];
      const desc = sMatch[2] || sMatch[4];
      if (idx && desc) {
        steps.push({ index: parseInt(idx, 10), description: desc.trim() });
      }
    }

    if (steps.length === 0) {
      const fallbackRegex = /(?:^|\n)(?:Step\s+(\d+):?|(\d+)\.)\s+([^\n]+)/gi;
      let fbMatch;
      while ((fbMatch = fallbackRegex.exec(planText)) !== null) {
        const idx = fbMatch[1] || fbMatch[2];
        const desc = fbMatch[3];
        if (idx && desc && !desc.toLowerCase().startsWith('formulate goal')) {
          steps.push({ index: parseInt(idx, 10), description: desc.trim() });
        }
      }
    }
  } catch (err) {
    // fallback
  }

  return (
    <div
      style={{
        margin: '8px 0 12px 0',
        borderRadius: '8px',
        border: '1px solid rgba(6, 182, 212, 0.3)',
        backgroundColor: '#04070a',
        overflow: 'hidden',
        boxShadow: '0 2px 10px rgba(6, 182, 212, 0.08)',
      }}
    >
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '7px 10px',
          cursor: 'pointer',
          backgroundColor: isOpen ? 'rgba(6, 182, 212, 0.08)' : 'rgba(255, 255, 255, 0.02)',
          userSelect: 'none',
          borderBottom: isOpen ? '1px solid rgba(6, 182, 212, 0.15)' : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          <ListChecks size={14} color="#06b6d4" />
          <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#cffafe', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {title}
          </span>
          <span
            style={{
              fontSize: '9.5px',
              padding: '1px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              color: '#67e8f9',
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}
          >
            {steps.length > 0 ? `${steps.length} Milestones` : 'Goal Plan'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#06b6d4', fontSize: '10px' }}>
          <span>{isOpen ? 'Collapse' : 'View Plan'}</span>
          {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </div>
      </div>

      {isOpen && (
        <div style={{ padding: '10px 12px', backgroundColor: '#020508' }}>
          {goal && (
            <div style={{ marginBottom: '8px', padding: '6px 8px', borderRadius: '4px', backgroundColor: 'rgba(6, 182, 212, 0.05)', border: '1px solid rgba(6, 182, 212, 0.15)', fontSize: '11px', color: '#a5f3fc' }}>
              <span style={{ fontWeight: 600, color: '#22d3ee' }}>Goal: </span>
              {goal}
            </div>
          )}

          {steps.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
              {steps.map((st) => (
                <div
                  key={st.index}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '4px 6px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    fontSize: '11.5px',
                  }}
                >
                  <span
                    style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      backgroundColor: 'rgba(6, 182, 212, 0.15)',
                      color: '#22d3ee',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '9.5px',
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    {st.index}
                  </span>
                  <span style={{ color: '#e2e8f0', flex: 1 }}>{st.description}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="prose prose-invert max-w-none text-xs" style={{ color: '#94a3b8' }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {planText}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function parseMessageContent(rawContent) {
  if (!rawContent || typeof rawContent !== 'string') {
    return { thoughts: [], plan: null, mainContent: '' };
  }

  let content = rawContent;
  const thoughts = [];
  let plan = null;

  // 1. Explicit <thought>...</thought> or <thinking>...</thinking>
  const thoughtRegex = /<(?:thought|thinking)>([\s\S]*?)<\/(?:thought|thinking)>/gi;
  let match;
  while ((match = thoughtRegex.exec(content)) !== null) {
    if (match[1].trim()) thoughts.push(match[1].trim());
  }
  content = content.replace(thoughtRegex, '').trim();

  // 1b. Streaming unclosed <thought> / <thinking>
  const unclosedRegex = /<(?:thought|thinking)>([\s\S]*)$/i;
  const unclosedMatch = unclosedRegex.exec(content);
  if (unclosedMatch) {
    if (unclosedMatch[1].trim()) thoughts.push(unclosedMatch[1].trim());
    content = content.replace(unclosedRegex, '').trim();
  }

  // 2. Extract create_plan tool call text or explicit plan python scripts
  const createPlanRegex = /(?:create_plan\s*\(\s*title=[\s\S]*?\)\s*|```(?:python)?\s*import os\s+plan_path =[\s\S]*?```)/gi;
  let pMatch = createPlanRegex.exec(content);
  if (pMatch) {
    plan = pMatch[0].trim();
    content = content.replace(pMatch[0], '').trim();
  }

  // 3. Extract "Step 1: Formulate Goal & Plan" or "Plan: ..." blocks
  const formulateRegex = /(?:(?:Step 1: Formulate Goal & Plan|I'll follow the autonomous goal-driven feedback loop)[\s\S]*?(?:Let's (?:create the plan file|move on to setting up)|$))/gi;
  let fMatch = formulateRegex.exec(content);
  if (fMatch) {
    thoughts.push(fMatch[0].trim());
    content = content.replace(fMatch[0], '').trim();
  }

  // 4. Extract "# User Profile Management CRUD Operations Plan" or "## Goal ... ## Milestones" markdown blocks
  const planMdRegex = /(?:# [^\n]*Plan\s*\n\s*## Goal[\s\S]*?(?=\n\n[A-Z]|\n[a-z]|I have created the plan file|$))/gi;
  let mdMatch = planMdRegex.exec(content);
  if (mdMatch) {
    if (!plan) plan = mdMatch[0].trim();
    content = content.replace(mdMatch[0], '').trim();
  }

  // Clean trailing helper phrases
  content = content.replace(/I will now create the plan file in the workspace\.?/gi, '');
  content = content.replace(/I have created the plan file\.?/gi, '');
  content = content.trim();

  return {
    thoughts,
    plan,
    mainContent: content,
  };
}

export default function CodingAgentPanel({
  sessionId = 'default',
  sessions = [],
  messages = [],
  status = 'idle',
  currentTool = null,
  approvalRequest = null,
  selectedModel = 'default',
  onChangeModel,
  onSendMessage,
  onStop,
  onReset,
  onNewConversation,
  onSwitchSession,
  onDeleteSession,
  onRespondApproval,
}) {
  const [inputVal, setInputVal] = useState('');
  const [showArchInfo, setShowArchInfo] = useState(false);
  const [showSessionsMenu, setShowSessionsMenu] = useState(false);
  const sessionsMenuRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  // Close sessions dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (sessionsMenuRef.current && !sessionsMenuRef.current.contains(e.target)) {
        setShowSessionsMenu(false);
      }
    };
    if (showSessionsMenu) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [showSessionsMenu]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const clean = inputVal.trim();
    if (!clean || status === 'thinking' || status === 'executing_tool') return;
    onSendMessage(clean);
    setInputVal('');
  };

  const isBusy = status === 'thinking' || status === 'executing_tool';

  return (
    <div
      style={{
        width: '360px',
        minWidth: '300px',
        maxWidth: '440px',
        height: '100%',
        backgroundColor: '#050507',
        borderLeft: '1px solid #1a1a20',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Panel Header */}
      <div
        style={{
          height: '38px',
          borderBottom: '1px solid #1a1a20',
          padding: '0 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#000000',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sparkles size={14} color="#3b82f6" />
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>
            Coding Agent
          </span>
          {isBusy && (
            <span
              style={{
                fontSize: '10.5px',
                padding: '1px 6px',
                borderRadius: '10px',
                backgroundColor: 'rgba(37, 99, 235, 0.2)',
                color: '#60a5fa',
                fontWeight: 500,
              }}
            >
              {status === 'executing_tool' ? `Running ${currentTool || 'tool'}...` : 'Thinking...'}
            </span>
          )}
          {status === 'waiting_approval' && (
            <span
              style={{
                fontSize: '10.5px',
                padding: '1px 7px',
                borderRadius: '10px',
                backgroundColor: 'rgba(245, 158, 11, 0.2)',
                color: '#fde047',
                fontWeight: 600,
                border: '1px solid rgba(245, 158, 11, 0.4)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
              Awaiting Approval
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          {/* New Conversation Button */}
          <button
            onClick={() => {
              if (!isBusy && onNewConversation) {
                onNewConversation();
                setShowSessionsMenu(false);
              }
            }}
            disabled={isBusy}
            title="Start a new coding conversation"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '5px',
              backgroundColor: 'rgba(37, 99, 235, 0.2)',
              border: '1px solid rgba(59, 130, 246, 0.45)',
              color: '#93c5fd',
              fontSize: '11px',
              fontWeight: 600,
              cursor: isBusy ? 'not-allowed' : 'pointer',
              opacity: isBusy ? 0.6 : 1,
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!isBusy) {
                e.currentTarget.style.backgroundColor = '#2563eb';
                e.currentTarget.style.borderColor = '#3b82f6';
                e.currentTarget.style.color = '#ffffff';
                e.currentTarget.style.boxShadow = '0 0 10px rgba(37, 99, 235, 0.4)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isBusy) {
                e.currentTarget.style.backgroundColor = 'rgba(37, 99, 235, 0.2)';
                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.45)';
                e.currentTarget.style.color = '#93c5fd';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
          >
            <Plus size={12} strokeWidth={2.5} />
            <span>New Chat</span>
          </button>

          {/* Conversations History Dropdown Toggle */}
          <button
            onClick={() => {
              setShowSessionsMenu(!showSessionsMenu);
              if (showArchInfo) setShowArchInfo(false);
            }}
            title="Conversation History"
            style={{
              padding: '4px',
              borderRadius: '4px',
              color: showSessionsMenu ? '#3b82f6' : '#94a3b8',
              backgroundColor: showSessionsMenu ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              position: 'relative',
            }}
            onMouseEnter={(e) => {
              if (!showSessionsMenu) e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              if (!showSessionsMenu) e.currentTarget.style.color = '#94a3b8';
            }}
          >
            <History size={13} />
            {sessions && sessions.length > 1 && (
              <span
                style={{
                  position: 'absolute',
                  top: '1px',
                  right: '1px',
                  width: '5px',
                  height: '5px',
                  borderRadius: '50%',
                  backgroundColor: '#3b82f6',
                }}
              />
            )}
          </button>

          <button
            onClick={() => {
              setShowArchInfo(!showArchInfo);
              if (showSessionsMenu) setShowSessionsMenu(false);
            }}
            title="View 4-Pillar Architecture Capabilities"
            style={{
              padding: '4px',
              borderRadius: '4px',
              color: showArchInfo ? '#3b82f6' : '#94a3b8',
              backgroundColor: showArchInfo ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Info size={13} />
          </button>

          <button
            onClick={onReset}
            title="Reset Context"
            style={{
              padding: '4px',
              borderRadius: '4px',
              color: '#94a3b8',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <RotateCcw size={13} />
          </button>
        </div>
      </div>

      {/* Conversations History Popover */}
      {showSessionsMenu && (
        <div
          ref={sessionsMenuRef}
          style={{
            position: 'absolute',
            top: '42px',
            right: '10px',
            width: '280px',
            zIndex: 40,
            backgroundColor: '#0a0b12',
            border: '1px solid #1a1a20',
            borderRadius: '8px',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.8)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 12px',
              borderBottom: '1px solid #1a1a20',
              backgroundColor: '#06070a',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <History size={13} color="#3b82f6" />
              <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#f8fafc' }}>
                Coding Conversations
              </span>
            </div>
            <button
              onClick={() => setShowSessionsMenu(false)}
              style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: 0 }}
            >
              <X size={13} />
            </button>
          </div>

          <div style={{ padding: '8px' }}>
            <button
              onClick={() => {
                if (onNewConversation) onNewConversation();
                setShowSessionsMenu(false);
              }}
              disabled={isBusy}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                padding: '7px 10px',
                borderRadius: '6px',
                backgroundColor: '#1d4ed8',
                color: '#ffffff',
                border: 'none',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: isBusy ? 'not-allowed' : 'pointer',
                marginBottom: '8px',
                transition: 'background-color 0.15s ease',
              }}
              onMouseEnter={(e) => {
                if (!isBusy) e.currentTarget.style.backgroundColor = '#2563eb';
              }}
              onMouseLeave={(e) => {
                if (!isBusy) e.currentTarget.style.backgroundColor = '#1d4ed8';
              }}
            >
              <Plus size={13} strokeWidth={2.5} />
              <span>Start New Conversation</span>
            </button>

            <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {(!sessions || sessions.length === 0) ? (
                <div style={{ padding: '12px 8px', textAlign: 'center', color: '#64748b', fontSize: '11px' }}>
                  Current session active.
                </div>
              ) : (
                sessions.map((s) => {
                  const isActive = s.id === sessionId;
                  return (
                    <div
                      key={s.id}
                      onClick={() => {
                        if (onSwitchSession) onSwitchSession(s.id);
                        setShowSessionsMenu(false);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 8px',
                        borderRadius: '6px',
                        backgroundColor: isActive ? 'rgba(37, 99, 235, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                        border: `1px solid ${isActive ? 'rgba(59, 130, 246, 0.4)' : '#1a1a20'}`,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', gap: '2px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: isActive ? 600 : 500,
                              color: isActive ? '#93c5fd' : '#cbd5e1',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: '180px',
                            }}
                          >
                            {s.title || 'Coding Session'}
                          </span>
                          {isActive && (
                            <span
                              style={{
                                fontSize: '9px',
                                padding: '1px 4px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(59, 130, 246, 0.25)',
                                color: '#60a5fa',
                                fontWeight: 600,
                              }}
                            >
                              Active
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: '9.5px', color: '#64748b' }}>
                          {s.created_at ? new Date(s.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                      </div>

                      {onDeleteSession && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(s.id);
                          }}
                          title="Delete Session"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: '#64748b',
                            cursor: 'pointer',
                            padding: '3px',
                            borderRadius: '4px',
                            display: 'flex',
                            alignItems: 'center',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.color = '#ef4444';
                            e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.color = '#64748b';
                            e.currentTarget.style.backgroundColor = 'transparent';
                          }}
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}


      {/* Architecture Capabilities Info Popover */}
      {showArchInfo && (
        <div
          style={{
            position: 'absolute',
            top: '74px',
            left: '10px',
            right: '10px',
            zIndex: 30,
            backgroundColor: '#0a0b12',
            border: '1px solid #2563eb',
            borderRadius: '8px',
            padding: '12px',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.8)',
            fontSize: '11px',
            color: '#cbd5e1',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontWeight: 600, color: '#93c5fd', fontSize: '11.5px' }}>
              Shield AI Architecture Capabilities
            </span>
            <button
              onClick={() => setShowArchInfo(false)}
              style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: 0 }}
            >
              <X size={13} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div>
              <strong style={{ color: '#60a5fa' }}>1. Execution Environment:</strong>
              <div style={{ color: '#94a3b8', fontSize: '10.5px' }}>
                • <code>code_interpreter</code>: Isolated Python sandbox execution with AST checks.<br />
                • <code>Sandbox</code>: Guarded subprocess with timeout & resource limits.<br />
                • <code>Filesystem</code>: Direct workspace mount at <code>/</code>.
              </div>
            </div>

            <div>
              <strong style={{ color: '#c084fc' }}>2. Delegation:</strong>
              <div style={{ color: '#94a3b8', fontSize: '10.5px' }}>
                • <code>Planning</code>: Structured milestones saved in <code>/.shield/PLAN.md</code>.<br />
                • <code>Subagents</code>: <code>code-reviewer</code>, <code>code-researcher</code>, <code>test-runner</code>.
              </div>
            </div>

            <div>
              <strong style={{ color: '#f59e0b' }}>3. Steering:</strong>
              <div style={{ color: '#94a3b8', fontSize: '10.5px' }}>
                • <code>Human-in-the-loop</code>: Intercepts shell & sandbox runs for user approval.
              </div>
            </div>

            <div>
              <strong style={{ color: '#34d399' }}>4. Context Management:</strong>
              <div style={{ color: '#94a3b8', fontSize: '10.5px' }}>
                • <code>Skills</code>: Domain cheatsheets loaded from <code>/.skills/</code>.<br />
                • <code>Memory</code>: Persistent rules in <code>/.agents/AGENTS.md</code>.<br />
                • <code>Context offloading</code>: Oversized logs offloaded to <code>/.shield/scratch/</code>.<br />
                • <code>Summarization & Prompt caching</code>: Token conservation middleware.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {messages.map((msg) => (
          <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {msg.role === 'user' ? (
              <div
                style={{
                  alignSelf: 'flex-end',
                  maxWidth: '90%',
                  padding: '8px 12px',
                  borderRadius: '12px',
                  borderBottomRightRadius: '2px',
                  backgroundColor: '#172554',
                  border: '1px solid #1d4ed8',
                  color: '#ffffff',
                  fontSize: '12.5px',
                  lineHeight: 1.45,
                }}
              >
                {msg.content}
              </div>
            ) : (
              <div
                style={{
                  alignSelf: 'flex-start',
                  maxWidth: '100%',
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#0a0a0d',
                  border: '1px solid #1a1a20',
                  color: '#cbd5e1',
                  fontSize: '12.5px',
                  lineHeight: 1.5,
                }}
              >
                {/* Render any associated tool events */}
                {msg.tools && msg.tools.length > 0 && (
                  <div style={{ marginBottom: '8px' }}>
                    {msg.tools.map((t) => (
                      <ToolCard key={t.id} tool={t} />
                    ))}
                  </div>
                )}

                {/* Assistant text with Antigravity / Codex style Thinking & Plan Dropdowns */}
                {msg.content && (() => {
                  const { thoughts, plan, mainContent } = parseMessageContent(msg.content);
                  return (
                    <div>
                      {/* Thinking Process Accordion Dropdown */}
                      {thoughts && thoughts.length > 0 && (
                        <ThoughtAccordion thoughts={thoughts} isStreaming={msg.isStreaming} />
                      )}

                      {/* Execution Plan Accordion Dropdown */}
                      {plan && (
                        <PlanAccordion planText={plan} />
                      )}

                      {/* Clean User-Facing Text */}
                      {mainContent && (
                        <div className="prose prose-invert max-w-none text-xs">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {mainContent}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        ))}

        {/* Human-in-the-Loop (HITL) Safety Approval Card */}
        {approvalRequest && (
          <div
            style={{
              padding: '14px',
              borderRadius: '10px',
              backgroundColor: '#0a0908',
              border: `1px solid ${approvalRequest.riskLevel === 'high' ? '#ef4444' : '#f59e0b'}`,
              boxShadow: approvalRequest.riskLevel === 'high' 
                ? '0 0 20px rgba(239, 68, 68, 0.25)' 
                : '0 0 20px rgba(245, 158, 11, 0.2)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            {/* Header with Risk Badge */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                <ShieldAlert size={16} color={approvalRequest.riskLevel === 'high' ? '#ef4444' : '#f59e0b'} />
                <span style={{ 
                  color: approvalRequest.riskLevel === 'high' ? '#fca5a5' : '#fde047', 
                  fontWeight: 600, 
                  fontSize: '12px',
                  letterSpacing: '-0.01em'
                }}>
                  Human-in-the-Loop Approval
                </span>
              </div>

              <span
                style={{
                  fontSize: '9.5px',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  padding: '2px 7px',
                  borderRadius: '10px',
                  backgroundColor: approvalRequest.riskLevel === 'high' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                  color: approvalRequest.riskLevel === 'high' ? '#ef4444' : '#f59e0b',
                  border: `1px solid ${approvalRequest.riskLevel === 'high' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
                  textTransform: 'uppercase',
                }}
              >
                {approvalRequest.riskLevel || 'medium'} Risk
              </span>
            </div>

            {/* Explanatory Callout */}
            <p style={{ fontSize: '11.5px', color: '#cbd5e1', margin: 0, lineHeight: 1.4 }}>
              The autonomous coding agent is requesting your authorization before running:
            </p>

            {/* Target Action / Command Terminal Window */}
            <div
              style={{
                backgroundColor: '#000000',
                border: '1px solid #1a1a20',
                borderRadius: '6px',
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#64748b', fontSize: '10.5px' }}>
                <Terminal size={11} color="#3b82f6" />
                <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 600, color: '#93c5fd' }}>
                  {approvalRequest.action}
                </span>
              </div>
              <pre
                style={{
                  color: '#4ade80',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono, monospace)',
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >
                $ {approvalRequest.command || approvalRequest.action}
              </pre>
            </div>

            {/* Decision Buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <button
                onClick={() => onRespondApproval('approve')}
                style={{
                  flex: 1,
                  padding: '7px 12px',
                  borderRadius: '6px',
                  backgroundColor: '#16a34a',
                  color: '#ffffff',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(22, 163, 74, 0.3)',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#15803d')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#16a34a')}
              >
                <CheckCircle2 size={13} />
                <span>Approve & Run</span>
              </button>

              <button
                onClick={() => onRespondApproval('reject')}
                style={{
                  flex: 1,
                  padding: '7px 12px',
                  borderRadius: '6px',
                  backgroundColor: '#1c1917',
                  border: '1px solid #ef4444',
                  color: '#f87171',
                  fontSize: '11.5px',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                  e.currentTarget.style.color = '#fca5a5';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#1c1917';
                  e.currentTarget.style.color = '#f87171';
                }}
              >
                <AlertTriangle size={13} />
                <span>Reject Action</span>
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick 4-Pillar Task Prompts */}
      <div style={{ padding: '0 10px', display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '6px' }}>
        {[
          { label: '🔄 Run Goal Loop', prompt: 'Formulate an implementation plan with goals, execute the tasks, run the code in sandbox, verify each step in the loop until verified, and report results.' },
          { label: '📋 Create Plan', prompt: 'Create a milestone implementation plan in .shield/PLAN.md with verification criteria.' },
          { label: '🧪 Sandbox Verify', prompt: 'Use verify_task to run test assertions in sandbox and verify if the goal has been successfully implemented.' },
          { label: '⚡ Run Sandbox Code', prompt: 'Use code_interpreter to write and execute a Python snippet verifying the algorithm logic.' },
          { label: '🤖 Code Review', prompt: 'Delegate to code-reviewer subagent to inspect the codebase for security and quality.' },
          { label: '🧠 Save Guideline', prompt: 'Use update_memory to save rule: Always write type annotations and docstrings for functions.' },
        ].map((item) => (
          <button
            key={item.label}
            onClick={() => onSendMessage(item.prompt)}
            disabled={isBusy}
            title={item.prompt}
            style={{
              padding: '3px 8px',
              borderRadius: '12px',
              backgroundColor: '#111216',
              border: '1px solid #1a1a20',
              color: '#cbd5e1',
              fontSize: '10.5px',
              whiteSpace: 'nowrap',
              flexShrink: 0,
              cursor: isBusy ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!isBusy) {
                e.currentTarget.style.color = '#ffffff';
                e.currentTarget.style.borderColor = '#2563eb';
                e.currentTarget.style.backgroundColor = '#1e293b';
              }
            }}
            onMouseLeave={(e) => {
              if (!isBusy) {
                e.currentTarget.style.color = '#cbd5e1';
                e.currentTarget.style.borderColor = '#1a1a20';
                e.currentTarget.style.backgroundColor = '#111216';
              }
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Composer Input Area */}
      <div style={{ padding: '10px', backgroundColor: '#000000', borderTop: '1px solid #1a1a20' }}>
        <form
          onSubmit={handleSubmit}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#0a0a0d',
            border: '1px solid #1a1a20',
            borderRadius: '8px',
            padding: '6px 10px',
          }}
        >
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder={
              approvalRequest
                ? '🛡️ Action paused: Awaiting your decision above...'
                : isBusy
                ? 'Agent is working...'
                : 'Ask the agent to code, fix, or build...'
            }
            disabled={isBusy || Boolean(approvalRequest)}
            style={{
              flex: 1,
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: '12px',
              color: '#f8fafc',
              outline: 'none',
            }}
          />

          {isBusy ? (
            <button
              type="button"
              onClick={onStop}
              title="Stop Agent"
              style={{
                padding: '6px',
                borderRadius: '6px',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Square size={13} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!inputVal.trim()}
              title="Send Prompt"
              style={{
                padding: '6px',
                borderRadius: '6px',
                backgroundColor: inputVal.trim() ? '#2563eb' : '#1e293b',
                color: inputVal.trim() ? '#ffffff' : '#64748b',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Send size={13} />
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
