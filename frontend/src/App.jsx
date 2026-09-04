import React, { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';
import './index.css';

import { loginUser, registerUser, fetchCurrentUser } from './api/auth';
import { createThread, fetchThreads, fetchThreadMessages, deleteThread, sendMessage, uploadDocument } from './api/chat';

import AuthModal from './components/auth/AuthModal';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import Footer from './components/layout/Footer';
import ChatInput from './components/chat/ChatInput';
import QuickTasks from './components/chat/QuickTasks';
import ChatMessageList from './components/chat/ChatMessageList';

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
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

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

  const handleSendMessage = async (textToSubmit) => {
    const text = textToSubmit || inputValue;
    if (!text.trim() || chatLoading) return;

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

    // Optimistic UI update
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setInputValue('');
    setChatLoading(true);

    try {
      const res = await sendMessage(token, currentTId, text);
      const assistantMsg = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: res.message,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMsg]);

      // Refresh threads list to update auto-generated title
      loadThreads();
    } catch (err) {
      console.error('Failed to send message:', err);
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to get response from server.'}`,
        created_at: new Date().toISOString()
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleUploadDocument = async (file) => {
    if (!file || uploading) return;
    setUploading(true);
    setUploadStatus(`Uploading & Processing ${file.name}...`);
    try {
      const res = await uploadDocument(token, file);
      const isImg = res.is_image;
      const successMsg = isImg
        ? `Successfully uploaded image "${file.name}". Saved at: ${res.file_path}`
        : `Successfully indexed "${file.name}" (${res.chunks_added} chunks) into RAG knowledge base.`;

      setUploadStatus(successMsg);

      // Append systemic assistant message to chat if active thread exists
      setMessages(prev => [...prev, {
        id: `sys-${Date.now()}`,
        role: 'assistant',
        content: isImg 
          ? `🖼️ **Image Uploaded**: "${file.name}"\nPath: \`${res.file_path}\`\n\nThe image description has been indexed into your knowledge base. You can also ask me to analyze, describe, or inspect this image!`
          : `📄 **Document Ingested**: "${file.name}" (${res.chunks_added} chunks)\n\nYou can now ask questions about the contents of this document!`,
        created_at: new Date().toISOString()
      }]);

      setTimeout(() => setUploadStatus(null), 6000);
    } catch (err) {
      console.error('Failed to upload document:', err);
      const errorMsg = `Upload failed: ${err.message}`;
      setUploadStatus(errorMsg);
      setTimeout(() => setUploadStatus(null), 5000);
    } finally {
      setUploading(false);
    }
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
        onUploadDocument={handleUploadDocument}
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
            backgroundColor: 'var(--bg-button)',
            border: '1px solid var(--accent-orange)',
            color: '#fff',
            padding: '8px 16px',
            borderRadius: '20px',
            fontSize: '13px',
            zIndex: 100,
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
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
          padding: '0 24px 24px',
          overflow: 'hidden'
        }}>
          {messages.length === 0 ? (
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              justifyContent: 'center',
              marginBottom: '30px'
            }}>
              {/* Logo & Heading */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '40px' }}>
                <ShieldCheck size={36} color="var(--accent-orange)" strokeWidth={2} />
                <h1 style={{ 
                  fontFamily: 'var(--font-serif)', 
                  fontSize: '42px', 
                  fontWeight: '500', 
                  color: '#fff',
                  letterSpacing: '-0.01em'
                }}>
                  What you want, we coordinate?
                </h1>
              </div>

              {/* Central Textarea & Input Controls */}
              <ChatInput 
                inputValue={inputValue} 
                setInputValue={setInputValue} 
                activeTab={activeTab} 
                setActiveTab={setActiveTab} 
                onSendMessage={handleSendMessage}
                onUploadDocument={handleUploadDocument}
                uploading={uploading}
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
              
              <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '12px' }}>
                <ChatInput 
                  inputValue={inputValue} 
                  setInputValue={setInputValue} 
                  activeTab={activeTab} 
                  setActiveTab={setActiveTab} 
                  onSendMessage={handleSendMessage}
                  onUploadDocument={handleUploadDocument}
                  uploading={uploading}
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
