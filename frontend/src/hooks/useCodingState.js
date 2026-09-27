import { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchWorkspaceTree,
  readWorkspaceFile,
  writeWorkspaceFile,
  deleteWorkspaceFile,
  renameWorkspaceFile,
  fetchWorkspaceGit,
  fetchWorkspaceActive,
  fetchSuggestedWorkspaces,
  selectActiveWorkspace,
  executeTerminalCommand,
  fetchTerminalInfo,
  submitApprovalDecision,
  fetchCodingSessionMessages,
  createCodingSession,
  listCodingSessions,
  deleteCodingSession,
} from '../api/coding';
import { codingSocket } from '../services/codingSocket';

function getLanguageFromPath(filePath) {
  const ext = filePath.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'js':
    case 'jsx':
    case 'mjs':
      return 'javascript';
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'py':
      return 'python';
    case 'json':
      return 'json';
    case 'html':
      return 'html';
    case 'css':
      return 'css';
    case 'md':
      return 'markdown';
    case 'sql':
      return 'sql';
    case 'sh':
    case 'bash':
      return 'shell';
    case 'yml':
    case 'yaml':
      return 'yaml';
    default:
      return 'plaintext';
  }
}

export function useCodingState({ token, user }) {
  const [sessionId, setSessionId] = useState('default');
  const [sessions, setSessions] = useState([]);
  const [workspaceTree, setWorkspaceTree] = useState([]);
  const [workspaceRoot, setWorkspaceRoot] = useState('');
  const [gitStatus, setGitStatus] = useState({ is_git: false, branch: '', status: '', diff: '' });
  const [openTabs, setOpenTabs] = useState([]);
  const [activeTabPath, setActiveTabPath] = useState(null);
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [isTreeLoading, setIsTreeLoading] = useState(false);
  const [availableWorkspaces, setAvailableWorkspaces] = useState([]);
  const [isSwitchingWorkspace, setIsSwitchingWorkspace] = useState(false);

  // Terminal State
  const [terminalLines, setLines] = useState([
    {
      id: 'init-1',
      type: 'system',
      content: 'Shield AI Autonomous Shell Terminal [Connected to Local Workspace]',
    },
    {
      id: 'init-2',
      type: 'system',
      content: 'Commands execute directly inside your sandboxed workspace. Try ls, python, pip, git status.',
    },
  ]);
  const [terminalCwd, setTerminalCwd] = useState('');
  const [isTerminalRunning, setIsTerminalRunning] = useState(false);

  // Agent State
  const [agentMessages, setAgentMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "👋 **Shield AI Coding Assistant Ready**\n\nI can inspect code, create & edit files, run shell commands, and build entire features autonomously. How can I help with your project?",
      tools: [],
      timestamp: new Date().toISOString(),
    },
  ]);
  const [agentStatus, setAgentStatus] = useState('idle'); // idle, thinking, executing_tool, waiting_approval, error
  const [currentTool, setCurrentTool] = useState(null);
  const [approvalRequest, setApprovalRequest] = useState(null);
  const [hitlMode, setHitlModeState] = useState('safe'); // 'safe' | 'strict' | 'auto'
  const [selectedModel, setSelectedModel] = useState('default');
  const [isConnected, setIsConnected] = useState(false);

  // Connect socket on token mount
  useEffect(() => {
    if (token) {
      codingSocket.setToken(token);
      codingSocket.setSessionId(sessionId);
      codingSocket.connect(token);
    }

    const unsubConnected = codingSocket.on('connected', (connected) => {
      setIsConnected(connected);
    });

    const unsubStatus = codingSocket.on('agent_status', (msg) => {
      setAgentStatus(msg.status || 'idle');
      if (msg.tool) {
        setCurrentTool(msg.tool);
      } else if (msg.status === 'idle') {
        setCurrentTool(null);
      }
    });

    const unsubChunk = codingSocket.on('agent_chunk', (msg) => {
      setAgentMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMsg,
              content: lastMsg.content + msg.content,
            },
          ];
        } else {
          return [
            ...prev,
            {
              id: `agent-chunk-${Date.now()}`,
              role: 'assistant',
              content: msg.content,
              tools: [],
              isStreaming: true,
              timestamp: new Date().toISOString(),
            },
          ];
        }
      });
    });

    const unsubToolStarted = codingSocket.on('tool_started', (msg) => {
      setAgentMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        const newTool = {
          id: msg.tool_id || `tool-${Date.now()}`,
          name: msg.tool,
          args: msg.args,
          status: 'running',
          startTime: Date.now(),
        };

        if (lastMsg && lastMsg.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            {
              ...lastMsg,
              tools: [...(lastMsg.tools || []), newTool],
            },
          ];
        } else {
          return [
            ...prev,
            {
              id: `tool-msg-${Date.now()}`,
              role: 'assistant',
              content: '',
              tools: [newTool],
              isStreaming: true,
              timestamp: new Date().toISOString(),
            },
          ];
        }
      });
    });

    const unsubToolFinished = codingSocket.on('tool_finished', (msg) => {
      setAgentMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.tools) {
          const updatedTools = lastMsg.tools.map((t) => {
            if (t.id === msg.tool_id || t.name === msg.tool) {
              return {
                ...t,
                status: 'completed',
                output: msg.output,
                durationMs: msg.duration_ms,
              };
            }
            return t;
          });
          return [
            ...prev.slice(0, -1),
            { ...lastMsg, tools: updatedTools },
          ];
        }
        return prev;
      });
    });

    const unsubFileChanged = codingSocket.on('file_changed', (msg) => {
      refreshTree();
      refreshGit();

      // If active tab was modified by the agent, auto-reload its content
      if (msg.path) {
        const cleanPath = msg.path.replace(/^\/+/, '');
        setOpenTabs((prevTabs) => {
          const matchingTab = prevTabs.find((t) => t.path === cleanPath || t.path.endsWith(cleanPath));
          if (matchingTab && !matchingTab.isDirty) {
            readWorkspaceFile(token, matchingTab.path, sessionId)
              .then((data) => {
                setOpenTabs((currentTabs) =>
                  currentTabs.map((t) => (t.path === matchingTab.path ? { ...t, content: data.content } : t))
                );
              })
              .catch((err) => console.warn('Could not auto-refresh file content:', err));
          }
          return prevTabs;
        });
      }
    });

    const unsubApproval = codingSocket.on('approval_required', (msg) => {
      setApprovalRequest({
        requestId: msg.request_id,
        action: msg.action,
        command: msg.command,
        riskLevel: msg.risk_level || 'medium',
      });
      setAgentStatus('waiting_approval');
    });

    const unsubCompleted = codingSocket.on('agent_completed', () => {
      setAgentMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.isStreaming) {
          return [
            ...prev.slice(0, -1),
            { ...lastMsg, isStreaming: false },
          ];
        }
        return prev;
      });
      setAgentStatus('idle');
      setCurrentTool(null);
    });

    const unsubWorkspaceSelected = codingSocket.on('workspace_selected', (msg) => {
      if (msg.workspace) {
        setWorkspaceRoot(msg.workspace);
        setTerminalCwd(msg.workspace);
      }
      if (msg.tree) {
        setWorkspaceTree(msg.tree);
      }
      // Reset open tabs since we switched roots
      setOpenTabs([]);
      setActiveTabPath(null);
      refreshGit();
    });

    const unsubError = codingSocket.on('error', (msg) => {
      setAgentMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Error:** ${msg.message || 'Unknown error occurred'}`,
          tools: [],
          isError: true,
          timestamp: new Date().toISOString(),
        },
      ]);
      setAgentStatus('error');
    });

    return () => {
      unsubConnected();
      unsubStatus();
      unsubChunk();
      unsubToolStarted();
      unsubToolFinished();
      unsubFileChanged();
      unsubApproval();
      unsubCompleted();
      unsubWorkspaceSelected();
      unsubError();
    };
  }, [token, sessionId]);

  // Load coding sessions for user
  const loadSessions = useCallback(async () => {
    if (!token) return;
    try {
      const list = await listCodingSessions(token);
      setSessions(list || []);
    } catch (err) {
      console.warn('Could not load coding sessions:', err);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadSessions();
    }
  }, [token, loadSessions]);

  // Load session conversation history from database
  const loadSessionMessages = useCallback(async (sid) => {
    const targetSessionId = sid || sessionId;
    if (!token || !targetSessionId) return;
    try {
      const msgs = await fetchCodingSessionMessages(token, targetSessionId);
      if (msgs && msgs.length > 0) {
        setAgentMessages(msgs);
      } else {
        setAgentMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content: "👋 **Shield AI Coding Assistant Ready**\n\nI can inspect code, create & edit files, run shell commands, and build entire features autonomously. How can I help with your project?",
            tools: [],
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    } catch (err) {
      console.warn('Could not load session messages from DB:', err);
    }
  }, [token, sessionId]);

  useEffect(() => {
    if (token && sessionId) {
      loadSessionMessages(sessionId);
    }
  }, [token, sessionId, loadSessionMessages]);

  // Load tree and git
  const refreshTree = useCallback(async () => {
    if (!token) return;
    setIsTreeLoading(true);
    try {
      const data = await fetchWorkspaceTree(token, sessionId);
      setWorkspaceTree(data.tree || []);
      setWorkspaceRoot(data.root || '');
    } catch (err) {
      console.error('Failed to load file tree:', err);
    } finally {
      setIsTreeLoading(false);
    }
  }, [token, sessionId]);

  const loadSuggestedWorkspaces = useCallback(async () => {
    if (!token) return;
    try {
      const list = await fetchSuggestedWorkspaces(token);
      setAvailableWorkspaces(list || []);
    } catch (err) {
      console.warn('Could not load suggested workspaces:', err);
    }
  }, [token]);

  const refreshGit = useCallback(async () => {
    if (!token) return;
    try {
      const data = await fetchWorkspaceGit(token, sessionId);
      setGitStatus(data);
    } catch (err) {
      console.warn('Could not load git status:', err);
    }
  }, [token, sessionId]);

  const refreshTerminalInfo = useCallback(async () => {
    if (!token) return;
    try {
      const data = await fetchTerminalInfo(token, sessionId);
      setTerminalCwd(data.cwd || '');
    } catch (err) {
      console.warn('Could not fetch terminal info:', err);
    }
  }, [token, sessionId]);

  useEffect(() => {
    if (token) {
      refreshTree();
      refreshGit();
      refreshTerminalInfo();
      loadSuggestedWorkspaces();
    }
  }, [token, refreshTree, refreshGit, refreshTerminalInfo, loadSuggestedWorkspaces]);

  // Switch workspace
  const switchWorkspace = async (targetPath, createIfMissing = true) => {
    if (!token) return;
    setIsSwitchingWorkspace(true);
    try {
      codingSocket.selectWorkspace(targetPath, sessionId);
      const res = await selectActiveWorkspace(token, targetPath, sessionId, createIfMissing);
      if (res && res.workspace) {
        setWorkspaceRoot(res.workspace);
        setTerminalCwd(res.workspace);
        if (res.tree) {
          setWorkspaceTree(res.tree);
        }
        setOpenTabs([]);
        setActiveTabPath(null);
      }
      await refreshGit();
      await loadSuggestedWorkspaces();
      return res;
    } catch (err) {
      console.error('Failed to switch workspace:', err);
      throw err;
    } finally {
      setIsSwitchingWorkspace(false);
    }
  };

  // Open file in editor
  const openFile = async (filePath) => {
    const existing = openTabs.find((t) => t.path === filePath);
    if (existing) {
      setActiveTabPath(filePath);
      return;
    }

    setIsLoadingFile(true);
    try {
      const data = await readWorkspaceFile(token, filePath, sessionId);
      const newTab = {
        path: filePath,
        name: filePath.split('/').pop() || filePath,
        content: data.content,
        language: getLanguageFromPath(filePath),
        isDirty: false,
      };
      setOpenTabs((prev) => [...prev, newTab]);
      setActiveTabPath(filePath);
    } catch (err) {
      console.error('Failed to open file:', err);
    } finally {
      setIsLoadingFile(false);
    }
  };

  const closeTab = (filePath) => {
    setOpenTabs((prev) => {
      const filtered = prev.filter((t) => t.path !== filePath);
      if (activeTabPath === filePath) {
        const nextActive = filtered.length > 0 ? filtered[filtered.length - 1].path : null;
        setActiveTabPath(nextActive);
      }
      return filtered;
    });
  };

  const updateTabContent = (filePath, newContent) => {
    setOpenTabs((prev) =>
      prev.map((t) => (t.path === filePath ? { ...t, content: newContent, isDirty: true } : t))
    );
  };

  const saveActiveFile = async () => {
    const active = openTabs.find((t) => t.path === activeTabPath);
    if (!active || !token) return;

    try {
      await writeWorkspaceFile(token, active.path, active.content, sessionId);
      setOpenTabs((prev) =>
        prev.map((t) => (t.path === activeTabPath ? { ...t, isDirty: false } : t))
      );
      refreshTree();
    } catch (err) {
      console.error('Failed to save file:', err);
    }
  };

  const createFile = async (filePath, initialContent = '') => {
    if (!token) return;
    try {
      await writeWorkspaceFile(token, filePath, initialContent, sessionId);
      await refreshTree();
      await openFile(filePath);
    } catch (err) {
      console.error('Failed to create file:', err);
    }
  };

  const deleteFile = async (filePath) => {
    if (!token) return;
    try {
      await deleteWorkspaceFile(token, filePath, sessionId);
      closeTab(filePath);
      await refreshTree();
    } catch (err) {
      console.error('Failed to delete file:', err);
    }
  };

  const renameFile = async (oldPath, newPath) => {
    if (!token) return;
    try {
      await renameWorkspaceFile(token, oldPath, newPath, sessionId);
      setOpenTabs((prev) =>
        prev.map((t) => (t.path === oldPath ? { ...t, path: newPath, name: newPath.split('/').pop() } : t))
      );
      if (activeTabPath === oldPath) setActiveTabPath(newPath);
      await refreshTree();
    } catch (err) {
      console.error('Failed to rename file:', err);
    }
  };

  // Run terminal command
  const runTerminalCommand = async (commandStr) => {
    if (!commandStr.trim() || !token) return;
    const cmdId = `cmd-${Date.now()}`;
    const cleanCmd = commandStr.trim();

    setLines((prev) => [
      ...prev,
      {
        id: cmdId,
        type: 'command',
        content: cleanCmd,
        cwd: terminalCwd,
      },
    ]);
    setIsTerminalRunning(true);

    try {
      const res = await executeTerminalCommand(token, cleanCmd, terminalCwd, sessionId);
      if (res.cwd) setTerminalCwd(res.cwd);

      if (res.stdout) {
        setLines((prev) => [
          ...prev,
          {
            id: `out-${Date.now()}`,
            type: 'stdout',
            content: res.stdout,
          },
        ]);
      }

      if (res.stderr) {
        setLines((prev) => [
          ...prev,
          {
            id: `err-${Date.now()}`,
            type: 'stderr',
            content: res.stderr,
            exitCode: res.exit_code,
          },
        ]);
      }

      // If command might have modified files, refresh tree
      refreshTree();
      refreshGit();
    } catch (err) {
      setLines((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          type: 'stderr',
          content: err.message || 'Execution error',
          exitCode: 1,
        },
      ]);
    } finally {
      setIsTerminalRunning(false);
    }
  };

  // Agent Prompts & Approvals
  const setHitlMode = (mode) => {
    setHitlModeState(mode);
    codingSocket.setHitlMode(mode, sessionId);
  };

  const sendAgentPrompt = (text) => {
    if (!text.trim() || !token) return;

    // Add user message to UI
    setAgentMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      },
    ]);

    setAgentStatus('thinking');
    codingSocket.sendPrompt(text, selectedModel, workspaceRoot, sessionId, hitlMode);
  };

  const respondApproval = async (decision) => {
    if (!approvalRequest || !token) return;
    const req = approvalRequest;
    const reqId = req.requestId;
    setApprovalRequest(null);

    // Add visual system message noting decision
    setAgentMessages((prev) => [
      ...prev,
      {
        id: `approval-${Date.now()}`,
        role: 'assistant',
        content: decision === 'approve'
          ? `🛡️ **User Approved Action:** \`${req.action}\`\n\`\`\`bash\n${req.command}\n\`\`\`\nResuming autonomous execution...`
          : `🛑 **User Rejected Action:** \`${req.action}\`\n\`\`\`bash\n${req.command}\n\`\`\`\nCancelled action per user instruction.`,
        tools: [],
        timestamp: new Date().toISOString(),
      },
    ]);

    setAgentStatus('thinking');

    try {
      await submitApprovalDecision(token, sessionId, reqId, decision);
    } catch (err) {
      console.warn('Could not record approval to DB:', err);
    }

    codingSocket.sendApproval(reqId, decision, sessionId);
  };

  const stopAgent = () => {
    codingSocket.stop(sessionId);
    setAgentStatus('idle');
  };

  const resetAgent = () => {
    codingSocket.reset(sessionId);
    setAgentMessages([
      {
        id: 'reset',
        role: 'assistant',
        content: '🔄 Session reset. Clean context ready for your next task.',
        tools: [],
        timestamp: new Date().toISOString(),
      },
    ]);
    setAgentStatus('idle');
  };

  const createNewConversation = useCallback(async (title = 'Coding Session') => {
    // 1. If agent is currently executing, stop it
    if (agentStatus === 'thinking' || agentStatus === 'executing_tool') {
      codingSocket.stop(sessionId);
    }

    setApprovalRequest(null);
    setCurrentTool(null);
    setAgentStatus('idle');

    // 2. Create new session in backend or fallback locally
    let newSid = `session-${Date.now()}`;
    if (token) {
      try {
        const newSession = await createCodingSession(token, workspaceRoot, title, selectedModel);
        if (newSession && newSession.id) {
          newSid = newSession.id;
        }
      } catch (err) {
        console.warn('Backend createCodingSession failed, using generated ID:', err);
      }
    }

    // 3. Update websocket and active state
    codingSocket.setSessionId(newSid);
    codingSocket.reset(newSid);
    setSessionId(newSid);

    setAgentMessages([
      {
        id: `welcome-${Date.now()}`,
        role: 'assistant',
        content: "👋 **New Coding Conversation Started**\n\nI'm ready for a new task. You can ask me to write code, debug issues, generate tests, or execute terminal commands in this workspace.",
        tools: [],
        timestamp: new Date().toISOString(),
      },
    ]);

    await loadSessions();
    return newSid;
  }, [token, workspaceRoot, selectedModel, agentStatus, sessionId, loadSessions]);

  const switchSession = useCallback(async (targetSessionId) => {
    if (!targetSessionId || targetSessionId === sessionId) return;

    if (agentStatus === 'thinking' || agentStatus === 'executing_tool') {
      codingSocket.stop(sessionId);
    }

    setApprovalRequest(null);
    setCurrentTool(null);
    setAgentStatus('idle');

    codingSocket.setSessionId(targetSessionId);
    setSessionId(targetSessionId);
    await loadSessionMessages(targetSessionId);
  }, [sessionId, agentStatus, loadSessionMessages]);

  const deleteSession = useCallback(async (targetSessionId) => {
    if (!token || !targetSessionId) return;
    try {
      await deleteCodingSession(token, targetSessionId);
      if (targetSessionId === sessionId) {
        await createNewConversation();
      } else {
        await loadSessions();
      }
    } catch (err) {
      console.error('Failed to delete coding session:', err);
    }
  }, [token, sessionId, createNewConversation, loadSessions]);

  return {
    sessionId,
    setSessionId,
    sessions,
    workspaceTree,
    workspaceRoot,
    gitStatus,
    openTabs,
    activeTabPath,
    setActiveTabPath,
    isLoadingFile,
    isTreeLoading,
    terminalLines,
    terminalCwd,
    isTerminalRunning,
    agentMessages,
    agentStatus,
    currentTool,
    approvalRequest,
    hitlMode,
    setHitlMode,
    selectedModel,
    setSelectedModel,
    isConnected,
    availableWorkspaces,
    isSwitchingWorkspace,
    switchWorkspace,
    loadSuggestedWorkspaces,
    openFile,
    closeTab,
    updateTabContent,
    saveActiveFile,
    createFile,
    deleteFile,
    renameFile,
    refreshTree,
    refreshGit,
    runTerminalCommand,
    sendAgentPrompt,
    respondApproval,
    stopAgent,
    resetAgent,
    createNewConversation,
    switchSession,
    deleteSession,
    loadSessions,
    loadSessionMessages,
  };
}
