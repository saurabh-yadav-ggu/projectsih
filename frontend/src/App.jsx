import React, { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';
import './index.css';

import { loginUser, registerUser, fetchCurrentUser } from './api/auth';
import AuthModal from './components/auth/AuthModal';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import Footer from './components/layout/Footer';
import ChatInput from './components/chat/ChatInput';
import QuickTasks from './components/chat/QuickTasks';

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
      />

      {/* MAIN CONTENT AREA */}
      <div className="main-content">
        <TopBar />

        {/* Center Prompt & Task Area */}
        <div style={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          padding: '0 24px',
          paddingBottom: '10vh'
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
          />

          {/* Quick Task Shortcuts */}
          <QuickTasks onSelectTask={(task) => setInputValue(task)} />
        </div>

        <Footer />
      </div>
    </div>
  );
}
