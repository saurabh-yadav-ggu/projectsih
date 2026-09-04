import React, { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';
import './index.css';

import { loginUser, registerUser, fetchCurrentUser } from './api/auth';
import { createThread, fetchThreads, fetchThreadMessages, deleteThread, sendMessageStream, uploadDocument } from './api/chat';

import AuthModal from './components/auth/AuthModal';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import Footer from './components/layout/Footer';
import ChatComposer from './components/composer/ChatComposer';
import QuickTasks from './components/chat/QuickTasks';
import ChatMessageList from './components/chat/ChatMessageList';
import { useAttachments } from './hooks/useAttachments';

export default function App() {
  const [activeTab, setActiveTab] = useState('Chat');
  const [inputValue, setInputValue] = useState('');

  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState('login');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [organisation, setOrganisation] = useState('');
  const [designation, setDesignation] = useState('');
  const [error, setError] = useState('');
  const [showAccountMenu, setShowAccountMenu] = useState(false);

  // Threads, Chat & Upload State
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  // Attachment Management Hook
  const { 
    attachments, 
    addFiles, 
    removeAttachment, 
    clearAttachments, 
    updateAttachment 
  } = useAttachments();

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token)
        .then(data => setUser(data))
        .catch(() => {
          setToken(null);
          localStorage.removeItem('token');
          setUser(null);
        });
    }
  }, [token]);

  // Load threads when authenticated
  useEffect(() => {
    if (token && user) {
      loadThreads();
    }
  }, [token, user]);

  const loadThreads = async () => {
    try {
      const data = await fetchThreads(token);
      setThreads(data);
      if (data.length > 0 && !activeThreadId) {
        setActiveThreadId(data[0].id);
        loadThreadMessages(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load threads:', err);
    }
  };

  const loadThreadMessages = async (threadId) => {
    try {
      const msgs = await fetchThreadMessages(token, threadId);
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };

  const handleSelectThread = (threadId) => {
    setActiveThreadId(threadId);
    loadThreadMessages(threadId);
  };

  const handleNewThread = async () => {
    try {
      const newT = await createThread(token, 'New conversation');
      setThreads(prev => [newT, ...prev]);
      setActiveThreadId(newT.id);
      setMessages([]);
      clearAttachments();
    } catch (err) {
      console.error('Failed to create thread:', err);
    }
  };

  const handleDeleteThread = async (threadId) => {
    try {
      await deleteThread(token, threadId);
      const updated = threads.filter(t => t.id !== threadId);
      setThreads(updated);
      if (activeThreadId === threadId) {
        if (updated.length > 0) {
          setActiveThreadId(updated[0].id);
          loadThreadMessages(updated[0].id);
        } else {
          setActiveThreadId(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete thread:', err);
    }
  };

  // Direct upload for Sidebar file button or single drop
  const handleUploadDocumentDirect = async (file) => {
    if (!file) return;
    addFiles([file]);
  };

  const handleRetryAttachment = async (id) => {
    const att = attachments.find(a => a.id === id);
    if (!att) return;
    updateAttachment(id, { status: 'ready', errorMessage: null });
  };

  const handleSendMessage = async (textToSubmit) => {
    const text = textToSubmit !== undefined ? textToSubmit : inputValue;
    if ((!text.trim() && attachments.length === 0) || chatLoading) return;

    let currentTId = activeThreadId;

    // Create thread if none active
    if (!currentTId) {
      try {
        const newT = await createThread(token, 'New conversation');
        currentTId = newT.id;
        setActiveThreadId(newT.id);
        setThreads(prev => [newT, ...prev]);
      } catch (err) {
        console.error('Failed to auto-create thread:', err);
        return;
      }
    }

    setChatLoading(true);

    // Copy attachments for sending
    const currentAttachments = [...attachments];
    let uploadFailed = false;

    // 1. Process and upload attachments if present
    if (currentAttachments.length > 0) {
      for (const att of currentAttachments) {
        try {
          updateAttachment(att.id, { status: 'uploading', progress: 50 });
          await uploadDocument(token, att.file, currentTId);
          updateAttachment(att.id, { status: 'ready', progress: 100 });
        } catch (err) {
          console.error(`Failed to upload file ${att.name}:`, err);
          updateAttachment(att.id, { status: 'error', errorMessage: 'Upload failed' });
          uploadFailed = true;
        }
      }
    }

    if (uploadFailed) {
      setChatLoading(false);
      setUploadStatus('Some attachments failed to upload. Please retry or remove them.');
      setTimeout(() => setUploadStatus(null), 5000);
      return; // Do NOT clear message text or attachments on failure!
    }

    // 2. Optimistic UI update
    const promptMessageText = text.trim() || (currentAttachments.length > 0 ? "Explain the attached files." : "");
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: promptMessageText,
      attachments: currentAttachments,
      created_at: new Date().toISOString()
    };

    const assistantMsgId = `asst-${Date.now()}`;
    const initialAssistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      streaming: true,
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, tempUserMsg, initialAssistantMsg]);
    setInputValue('');
    clearAttachments();

    // 3. Initiate Real-Time Streaming via SSE
    await sendMessageStream(token, currentTId, promptMessageText, {
      onInit: (data) => {
        if (data.thread_id && !activeThreadId) {
          setActiveThreadId(data.thread_id);
        }
      },
      onToken: (tokenChunk) => {
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMsgId) {
            return {
              ...msg,
              content: msg.content + tokenChunk
            };
          }
          return msg;
        }));
      },
      onDone: (doneData) => {
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMsgId) {
            return {
              ...msg,
              content: doneData.message || msg.content,
              streaming: false
            };
          }
          return msg;
        }));
        setChatLoading(false);
        loadThreads();
      },
      onError: (err) => {
        console.error('Streaming error:', err);
        setMessages(prev => prev.map(msg => {
          if (msg.id === assistantMsgId) {
            return {
              ...msg,
              content: msg.content ? `${msg.content}\n\n*[Stream interrupted: ${err.message}]*` : `Error: ${err.message}`,
              streaming: false
            };
          }
          return msg;
        }));
        setChatLoading(false);
      }
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const data = await loginUser(email, password);
      setToken(data.access_token);
      localStorage.setItem('token', data.access_token);
      setUser(data.user);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await registerUser({ name, email, organisation, designation, password });
      setAuthMode('login');
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem('token');
    setUser(null);
    setShowAccountMenu(false);
    setThreads([]);
    setActiveThreadId(null);
    setMessages([]);
    clearAttachments();
  };

  if (!token || (token && !user)) {
    if (token && !user) {
      return <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>;
    }
    return (
      <AuthModal
        authMode={authMode}
        setAuthMode={setAuthMode}
        email={email}
        setEmail={setEmail}
        password={password}
        setPassword={setPassword}
        name={name}
        setName={setName}
        organisation={organisation}
        setOrganisation={setOrganisation}
        designation={designation}
        setDesignation={setDesignation}
        error={error}
        setError={setError}
        handleLogin={handleLogin}
        handleRegister={handleRegister}
      />
    );
  }

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <Sidebar 
        user={user} 
        onLogout={handleLogout} 
        showAccountMenu={showAccountMenu} 
        setShowAccountMenu={setShowAccountMenu} 
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        onUploadDocument={handleUploadDocumentDirect}
      />

      {/* MAIN CONTENT AREA */}
      <div className="main-content">
        <TopBar />

        {uploadStatus && (
          <div style={{
            position: 'absolute',
            top: '70px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: '#181b26',
            border: '1px solid #f97316',
            color: '#fff',
            padding: '8px 16px',
            borderRadius: '20px',
            fontSize: '13px',
            zIndex: 100,
            boxShadow: '0 4px 16px rgba(0,0,0,0.5)'
          }}>
            {uploadStatus}
          </div>
        )}

        {/* Chat / Welcome Area */}
        <div style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: messages.length === 0 ? 'center' : 'flex-end',
          padding: '0 24px 10px',
          overflow: 'hidden'
        }}>
          {messages.length === 0 ? (
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              width: '100%',
              maxWidth: '850px',
              marginBottom: '20px'
            }}>
              {/* Logo & Heading */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
                <ShieldCheck size={36} color="#f97316" strokeWidth={2} />
                <h1 style={{ 
                  fontFamily: 'var(--font-serif)', 
                  fontSize: '40px', 
                  fontWeight: '500', 
                  color: '#fff',
                  letterSpacing: '-0.01em'
                }}>
                  What you want, we coordinate?
                </h1>
              </div>

              {/* Central ChatGPT-style Composer */}
              <ChatComposer 
                inputValue={inputValue} 
                setInputValue={setInputValue} 
                activeTab={activeTab} 
                setActiveTab={setActiveTab} 
                attachments={attachments}
                onAddFiles={addFiles}
                onRemoveAttachment={removeAttachment}
                onRetryAttachment={handleRetryAttachment}
                onSendMessage={handleSendMessage}
                loading={chatLoading}
              />

              {/* Quick Task Shortcuts */}
              <QuickTasks onSelectTask={(task) => {
                setInputValue(task);
                handleSendMessage(task);
              }} />
            </div>
          ) : (
            <div style={{
              flex: 1,
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              overflow: 'hidden'
            }}>
              <ChatMessageList messages={messages} loading={chatLoading} />
              
              <div style={{ width: '100%', display: 'flex', justifyContent: 'center', paddingTop: '10px' }}>
                <ChatComposer 
                  inputValue={inputValue} 
                  setInputValue={setInputValue} 
                  activeTab={activeTab} 
                  setActiveTab={setActiveTab} 
                  attachments={attachments}
                  onAddFiles={addFiles}
                  onRemoveAttachment={removeAttachment}
                  onRetryAttachment={handleRetryAttachment}
                  onSendMessage={handleSendMessage}
                  loading={chatLoading}
                />
              </div>
            </div>
          )}
        </div>

        <Footer />
      </div>
    </div>
  );
}
