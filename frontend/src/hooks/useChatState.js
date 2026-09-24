import { useState, useRef, useCallback, useEffect } from 'react';
import {
  createThread,
  fetchThreads,
  fetchThreadMessages,
  deleteThread as apiDeleteThread,
  uploadDocument
} from '../api/chat';
import { streamingController } from '../services/streamingController';

function generateId(prefix = 'msg') {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useChatState({ token, onUploadError }) {
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStatus, setActiveStatus] = useState('IDLE'); // 'IDLE' | 'STREAMING' | 'STOPPED' | 'ERROR'
  const [inputValue, setInputValue] = useState('');
  const draftsRef = useRef({}); // threadId -> draft string
  const activeThreadIdRef = useRef(activeThreadId);

  useEffect(() => {
    activeThreadIdRef.current = activeThreadId;
  }, [activeThreadId]);

  const loadThreadMessages = useCallback(async (threadId) => {
    if (!token || !threadId) return;
    try {
      const msgs = await fetchThreadMessages(token, threadId);
      // Map API messages into structured message schema
      const formatted = msgs.map(m => ({
        id: m.id || generateId('msg'),
        threadId,
        role: m.role,
        content: m.content || '',
        status: 'COMPLETED',
        createdAt: m.created_at || new Date().toISOString(),
        attachments: m.attachments || [],
        toolCalls: m.tool_calls || []
      }));
      setMessages(formatted);
    } catch (err) {
      console.error('Failed to load messages for thread:', threadId, err);
    }
  }, [token]);

  // Load threads on login
  const loadThreads = useCallback(async () => {
    if (!token) return;
    try {
      const data = await fetchThreads(token);
      setThreads(data);
      if (data.length > 0 && !activeThreadIdRef.current) {
        const firstId = data[0].id;
        setActiveThreadId(firstId);
        loadThreadMessages(firstId);
      }
    } catch (err) {
      console.error('Failed to load threads:', err);
    }
  }, [token, loadThreadMessages]);

  // Handle switching threads with draft preservation
  const selectThread = useCallback((newThreadId) => {
    if (newThreadId === activeThreadIdRef.current) return;

    // Save current draft
    if (activeThreadIdRef.current) {
      draftsRef.current[activeThreadIdRef.current] = inputValue;
    }

    setActiveThreadId(newThreadId);
    setMessages([]);
    loadThreadMessages(newThreadId);

    // Restore draft for new thread if present
    setInputValue(draftsRef.current[newThreadId] || '');
  }, [inputValue, loadThreadMessages]);

  // Handle starting a brand new thread
  const handleNewThread = useCallback(async () => {
    if (!token) return null;
    try {
      const newT = await createThread(token, 'New conversation');
      setThreads(prev => [newT, ...prev]);
      if (activeThreadIdRef.current) {
        draftsRef.current[activeThreadIdRef.current] = inputValue;
      }
      setActiveThreadId(newT.id);
      setMessages([]);
      setInputValue('');
      return newT.id;
    } catch (err) {
      console.error('Failed to create new thread:', err);
      return null;
    }
  }, [token, inputValue]);

  // Handle deleting a thread
  const handleDeleteThread = useCallback(async (threadId) => {
    if (!token) return;
    try {
      // Abort active stream if deleting currently streaming thread
      if (streamingController.isStreaming(threadId)) {
        streamingController.abortStream(threadId);
      }

      await apiDeleteThread(token, threadId);
      const updated = threads.filter(t => t.id !== threadId);
      setThreads(updated);
      delete draftsRef.current[threadId];

      if (activeThreadIdRef.current === threadId) {
        if (updated.length > 0) {
          const nextId = updated[0].id;
          setActiveThreadId(nextId);
          loadThreadMessages(nextId);
          setInputValue(draftsRef.current[nextId] || '');
        } else {
          setActiveThreadId(null);
          setMessages([]);
          setInputValue('');
        }
      }
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
  }, [token, threads, loadThreadMessages]);

  // Stop active generation
  const stopGeneration = useCallback(() => {
    const threadId = activeThreadIdRef.current;
    if (!threadId) return;

    const stopped = streamingController.abortStream(threadId);
    if (stopped) {
      setIsGenerating(false);
      setActiveStatus('STOPPED');
      setMessages(prev => prev.map(m => {
        if (m.status === 'STREAMING') {
          return {
            ...m,
            status: 'STOPPED',
            content: m.content ? `${m.content}\n\n*[Generation stopped by user]*` : '*[Generation stopped by user]*'
          };
        }
        return m;
      }));
    }
  }, []);

  // Send message stream
  const sendMessage = useCallback(async ({
    textToSubmit,
    attachments = [],
    clearAttachmentsCallback
  }) => {
    const text = textToSubmit !== undefined ? textToSubmit : inputValue;
    const hasContent = text.trim().length > 0 || attachments.length > 0;

    // Guard against empty submissions or active duplicate generation
    if (!hasContent || isGenerating) return;

    let currentTId = activeThreadIdRef.current;

    // Create thread if none active
    if (!currentTId) {
      currentTId = await handleNewThread();
      if (!currentTId) return;
    }

    setIsGenerating(true);
    setActiveStatus('STREAMING');

    // 1. Upload attachments if present
    const currentAttachments = [...attachments];
    let uploadFailed = false;
    let detectedImagePath = null;

    if (currentAttachments.length > 0) {
      for (const att of currentAttachments) {
        try {
          const uploadRes = await uploadDocument(token, att.file, currentTId);
          if (uploadRes && (uploadRes.is_image || (att.file && att.file.type && att.file.type.startsWith('image/')))) {
            detectedImagePath = uploadRes.file_path;
          }
        } catch (err) {
          console.error(`Failed to upload ${att.name}:`, err);
          uploadFailed = true;
        }
      }
    }

    if (uploadFailed) {
      setIsGenerating(false);
      setActiveStatus('ERROR');
      if (onUploadError) {
        onUploadError('Some attachments failed to upload. Please retry or remove them.');
      }
      return;
    }

    // 2. Prepare Optimistic UI Messages
    const promptMessageText = text.trim() || (currentAttachments.length > 0 ? 'Explain the attached files.' : '');
    const userMsgId = generateId('user');
    const assistantMsgId = generateId('asst');

    const userMessage = {
      id: userMsgId,
      threadId: currentTId,
      role: 'user',
      content: promptMessageText,
      status: 'COMPLETED',
      attachments: currentAttachments,
      createdAt: new Date().toISOString()
    };

    const assistantPlaceholder = {
      id: assistantMsgId,
      threadId: currentTId,
      role: 'assistant',
      content: '',
      status: 'STREAMING',
      createdAt: new Date().toISOString(),
      toolCalls: []
    };

    setMessages(prev => [...prev, userMessage, assistantPlaceholder]);
    setInputValue('');
    if (clearAttachmentsCallback) clearAttachmentsCallback();
    delete draftsRef.current[currentTId];

    // 3. Start Streaming via StreamingController with RAF token batching
    let pendingTokenBuffer = '';
    let flushRafId = null;

    const flushTokens = () => {
      if (!pendingTokenBuffer) return;
      const toAdd = pendingTokenBuffer;
      pendingTokenBuffer = '';
      setMessages(prev => prev.map(m => {
        if (m.id === assistantMsgId) {
          return {
            ...m,
            content: m.content + toAdd
          };
        }
        return m;
      }));
    };

    const scheduleFlush = () => {
      if (flushRafId) return;
      flushRafId = requestAnimationFrame(() => {
        flushRafId = null;
        flushTokens();
      });
    };

    await streamingController.startStream({
      token,
      threadId: currentTId,
      message: promptMessageText,
      imagePath: detectedImagePath,
      onInit: (data) => {
        if (data.thread_id && !activeThreadIdRef.current) {
          setActiveThreadId(data.thread_id);
        }
      },
      onToken: (chunk) => {
        pendingTokenBuffer += chunk;
        scheduleFlush();
      },
      onPlan: (planData) => {
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            return { ...m, plan: planData };
          }
          return m;
        }));
      },
      onSubagentStart: (subagentData) => {
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            const steps = m.pipelineSteps || [];
            return {
              ...m,
              pipelineSteps: [...steps, {
                id: generateId('step'),
                agent: subagentData.agent,
                status: 'running',
                timestamp: Date.now()
              }]
            };
          }
          return m;
        }));
      },
      onSubagentResult: (subagentData) => {
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            const steps = (m.pipelineSteps || []).map(s => {
              if (s.agent === subagentData.agent && s.status === 'running') {
                return { ...s, status: 'completed' };
              }
              return s;
            });
            return { ...m, pipelineSteps: steps };
          }
          return m;
        }));
      },
      onArtifactCreated: (artData) => {
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            const artifacts = m.artifacts || [];
            const exists = artifacts.some(a => a.path === artData.path);
            return {
              ...m,
              artifacts: exists ? artifacts : [...artifacts, artData]
            };
          }
          return m;
        }));
      },
      onVerification: (verData) => {
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            return {
              ...m,
              verification: verData
            };
          }
          return m;
        }));
      },
      onToolStart: (toolData) => {
        if (flushRafId) {
          cancelAnimationFrame(flushRafId);
          flushRafId = null;
        }
        flushTokens();
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            return {
              ...m,
              toolCalls: [...(m.toolCalls || []), {
                id: generateId('tool'),
                tool: toolData.tool || 'Tool',
                status: 'running',
                input: toolData.input
              }]
            };
          }
          return m;
        }));
      },
      onToolEnd: (toolData) => {
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            const calls = (m.toolCalls || []).map(tc => {
              if (tc.tool === toolData.tool && tc.status === 'running') {
                return { ...tc, status: 'completed', output: toolData.output };
              }
              return tc;
            });
            return { ...m, toolCalls: calls };
          }
          return m;
        }));
      },
      onDone: (doneData) => {
        if (flushRafId) {
          cancelAnimationFrame(flushRafId);
          flushRafId = null;
        }
        const finalMsg = doneData.message || (pendingTokenBuffer ? undefined : null);
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            const updatedTools = (m.toolCalls || []).map(tc =>
              tc.status === 'running' ? { ...tc, status: 'completed' } : tc
            );
            const updatedSteps = (m.pipelineSteps || []).map(ps =>
              ps.status === 'running' ? { ...ps, status: 'completed' } : ps
            );
            return {
              ...m,
              content: finalMsg !== undefined && finalMsg !== null ? finalMsg : (m.content + pendingTokenBuffer),
              toolCalls: updatedTools,
              pipelineSteps: updatedSteps,
              status: 'COMPLETED'
            };
          }
          return m;
        }));
        pendingTokenBuffer = '';
        setIsGenerating(false);
        setActiveStatus('IDLE');
        loadThreads();
      },
      onError: (err, accumulatedText) => {
        if (flushRafId) {
          cancelAnimationFrame(flushRafId);
          flushRafId = null;
        }
        pendingTokenBuffer = '';
        console.error('Stream error:', err);
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            const updatedTools = (m.toolCalls || []).map(tc =>
              tc.status === 'running' ? { ...tc, status: 'error' } : tc
            );
            const updatedSteps = (m.pipelineSteps || []).map(ps =>
              ps.status === 'running' ? { ...ps, status: 'error' } : ps
            );
            return {
              ...m,
              content: accumulatedText
                ? `${accumulatedText}\n\n*[Stream interrupted: ${err.message}]*`
                : `Error: ${err.message}`,
              toolCalls: updatedTools,
              pipelineSteps: updatedSteps,
              status: 'ERROR',
              error: err.message
            };
          }
          return m;
        }));
        setIsGenerating(false);
        setActiveStatus('ERROR');
      },
      onAbort: (accumulatedText) => {
        if (flushRafId) {
          cancelAnimationFrame(flushRafId);
          flushRafId = null;
        }
        pendingTokenBuffer = '';
        setMessages(prev => prev.map(m => {
          if (m.id === assistantMsgId) {
            return {
              ...m,
              content: accumulatedText
                ? `${accumulatedText}\n\n*[Generation stopped]*`
                : '*[Generation stopped]*',
              status: 'STOPPED'
            };
          }
          return m;
        }));
        setIsGenerating(false);
        setActiveStatus('STOPPED');
      }
    });
  }, [inputValue, isGenerating, token, handleNewThread, loadThreads, onUploadError]);

  // Regenerate response from previous user prompt
  const regenerateResponse = useCallback(async (targetAssistantMsgId) => {
    if (isGenerating) return;

    const targetIdx = messages.findIndex(m => m.id === targetAssistantMsgId);
    if (targetIdx <= 0) return;

    // Find preceding user message
    let precedingUserMsg = null;
    for (let i = targetIdx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        precedingUserMsg = messages[i];
        break;
      }
    }

    if (!precedingUserMsg) return;

    // Remove the assistant message (and any subsequent messages)
    setMessages(prev => prev.slice(0, targetIdx));

    // Re-trigger send with previous user message content
    await sendMessage({ textToSubmit: precedingUserMsg.content });
  }, [messages, isGenerating, sendMessage]);

  // Edit user prompt: removes following messages and sends updated text
  const editUserMessage = useCallback(async (userMsgId, newText) => {
    if (isGenerating || !newText.trim()) return;

    const userIdx = messages.findIndex(m => m.id === userMsgId);
    if (userIdx === -1) return;

    // Keep messages before this user message
    setMessages(prev => prev.slice(0, userIdx));

    // Send edited prompt
    await sendMessage({ textToSubmit: newText.trim() });
  }, [messages, isGenerating, sendMessage]);

  // Retry last generation
  const retryLastMessage = useCallback(async () => {
    if (isGenerating || messages.length === 0) return;

    const lastMsg = messages[messages.length - 1];
    if (lastMsg.role === 'assistant') {
      await regenerateResponse(lastMsg.id);
    }
  }, [isGenerating, messages, regenerateResponse]);

  return {
    threads,
    activeThreadId,
    messages,
    isGenerating,
    activeStatus,
    inputValue,
    setInputValue,
    loadThreads,
    selectThread,
    handleNewThread,
    handleDeleteThread,
    sendMessage,
    stopGeneration,
    regenerateResponse,
    editUserMessage,
    retryLastMessage
  };
}

export default useChatState;
