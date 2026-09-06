import React, { useState, useEffect } from 'react';
import { ShieldCheck, WifiOff } from 'lucide-react';
import './index.css';

import { loginUser, registerUser, fetchCurrentUser } from './api/auth';
import AuthModal from './components/auth/AuthModal';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import ChatComposer from './components/composer/ChatComposer';
import QuickTasks from './components/chat/QuickTasks';
import ChatMessageList from './components/chat/ChatMessageList';
import ChatErrorBoundary from './components/chat/ChatErrorBoundary';
import { useAttachments } from './hooks/useAttachments';
import { useChatState } from './hooks/useChatState';

function AppContent() {
  const [activeTab, setActiveTab] = useState('Chat');
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
  const [uploadStatus, setUploadStatus] = useState(null);
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);

  // Monitor network connectivity
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Attachment Management Hook
  const {
    attachments,
    addFiles,
    removeAttachment,
    clearAttachments,
    updateAttachment
  } = useAttachments();

  // Central Chat & Thread State Hook
  const {
    threads,
    activeThreadId,
    messages,
    isGenerating,
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
  } = useChatState({
    token,
    user,
    onUploadError: (errText) => {
      setUploadStatus(errText);
      setTimeout(() => setUploadStatus(null), 5000);
    }
  });

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

  // Load threads when user is authenticated
  useEffect(() => {
    if (token && user) {
      loadThreads();
    }
  }, [token, user, loadThreads]);

  // Direct upload for Sidebar file button
  const handleUploadDocumentDirect = (file) => {
    if (!file) return;
    addFiles([file]);
  };

  const handleRetryAttachment = (id) => {
    updateAttachment(id, { status: 'ready', errorMessage: null });
  };

  const handleSend = (textToSubmit) => {
    sendMessage({
      textToSubmit,
      attachments,
      clearAttachmentsCallback: clearAttachments
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const data = await loginUser(email, password);
      setToken(data.access_token);
      localStorage.setItem('token', data.access_token);
      window.dispatchEvent(new Event('shield-auth-changed'));
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
    stopGeneration();
    setToken(null);
    localStorage.removeItem('token');
    window.dispatchEvent(new Event('shield-auth-changed'));
    setUser(null);
    setShowAccountMenu(false);
    clearAttachments();
  };

  if (!token || (token && !user)) {
    if (token && !user) {
      return (
        <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
          Initializing Shield AI...
        </div>
      );
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
        onSelectThread={selectThread}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        onUploadDocument={handleUploadDocumentDirect}
      />

      {/* MAIN CONTENT AREA */}
      <div className="main-content">
        <TopBar />

        {/* Network Connection Warning */}
        {!isOnline && (
          <div style={{
            position: 'absolute',
            top: '64px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: '#181b26',
            border: '1px solid #ef4444',
            color: '#fca5a5',
            padding: '6px 14px',
            borderRadius: '20px',
            fontSize: '12px',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.5)'
          }}>
            <WifiOff size={14} />
            <span>Connection lost. Waiting for network...</span>
          </div>
        )}

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
                  fontFamily: 'var(--font-serif, serif)',
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
                onSendMessage={handleSend}
                onStop={stopGeneration}
                loading={isGenerating}
              />

              {/* Quick Task Shortcuts */}
              <QuickTasks onSelectTask={(task) => {
                setInputValue(task);
                handleSend(task);
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
              <ChatErrorBoundary>
                <ChatMessageList
                  messages={messages}
                  loading={isGenerating}
                  token={token}
                  onRegenerate={regenerateResponse}
                  onEditUserMessage={editUserMessage}
                  onRetry={retryLastMessage}
                />
              </ChatErrorBoundary>

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
                  onSendMessage={handleSend}
                  onStop={stopGeneration}
                  loading={isGenerating}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return <AppContent />;
}
