import React from 'react';
import { ShieldCheck } from 'lucide-react';

export default function AuthModal({
  authMode,
  setAuthMode,
  email,
  setEmail,
  password,
  setPassword,
  name,
  setName,
  organisation,
  setOrganisation,
  designation,
  setDesignation,
  error,
  setError,
  handleLogin,
  handleRegister
}) {
  return (
    <div className="app-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ 
        width: '400px', backgroundColor: 'var(--bg-sidebar)', padding: '32px', 
        borderRadius: '16px', border: '1px solid var(--border-color)',
        display: 'flex', flexDirection: 'column', gap: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'center' }}>
          <ShieldCheck size={32} color="var(--accent-orange)" strokeWidth={2} />
          <span style={{ fontSize: '24px', fontWeight: '600', letterSpacing: '-0.02em', color: '#fff' }}>Shield AI</span>
        </div>
        <h2 style={{ textAlign: 'center', color: '#fff', fontSize: '18px', fontWeight: '500' }}>
          {authMode === 'login' ? 'Sign In to your account' : 'Create an account'}
        </h2>
        {error && <div style={{ color: '#ef4444', fontSize: '13px', textAlign: 'center' }}>{error}</div>}
        <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {authMode === 'register' && (
            <>
              <input required type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff' }} />
              <input required type="text" placeholder="Organisation" value={organisation} onChange={e => setOrganisation(e.target.value)} style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff' }} />
              <input required type="text" placeholder="Designation" value={designation} onChange={e => setDesignation(e.target.value)} style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff' }} />
            </>
          )}
          <input required type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff' }} />
          <input required type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', color: '#fff' }} />
          <button type="submit" style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'var(--accent-orange)', color: '#000', fontWeight: '600', marginTop: '8px', cursor: 'pointer' }}>
            {authMode === 'login' ? 'Sign In' : 'Sign Up'}
          </button>
        </form>
        <div style={{ textAlign: 'center', fontSize: '13px', color: 'var(--text-muted)' }}>
          {authMode === 'login' ? "Don't have an account? " : "Already have an account? "}
          <span style={{ color: 'var(--accent-orange)', cursor: 'pointer' }} onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(''); }}>
            {authMode === 'login' ? 'Register here' : 'Sign In'}
          </span>
        </div>
      </div>
    </div>
  );
}
