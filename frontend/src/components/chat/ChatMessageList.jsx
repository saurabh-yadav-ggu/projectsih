import React, { useEffect, useRef } from 'react';
import { Bot, User, Loader2 } from 'lucide-react';

export default function ChatMessageList({ messages = [], loading = false }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div style={{
      flex: 1,
      width: '100%',
      maxWidth: '850px',
      margin: '0 auto',
      overflowY: 'auto',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px'
    }}>
      {messages.map((msg, index) => {
        const isUser = msg.role === 'user';
        return (
          <div key={msg.id || index} style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '14px',
            flexDirection: isUser ? 'row-reverse' : 'row'
          }}>
            {/* Avatar */}
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              backgroundColor: isUser ? 'var(--bg-button)' : '#1e2029',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isUser ? 'var(--accent-orange)' : 'var(--accent-green)',
              flexShrink: 0
            }}>
              {isUser ? <User size={18} /> : <Bot size={18} />}
            </div>

            {/* Bubble */}
            <div style={{
              maxWidth: '75%',
              backgroundColor: isUser ? '#1e2029' : 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              borderRadius: '16px',
              borderTopRightRadius: isUser ? '4px' : '16px',
              borderTopLeftRadius: isUser ? '16px' : '4px',
              padding: '14px 18px',
              color: '#e2e8f0',
              fontSize: '15px',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
            }}>
              {msg.content}
            </div>
          </div>
        );
      })}

      {loading && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
          <div style={{
            width: '34px',
            height: '34px',
            borderRadius: '10px',
            backgroundColor: '#1e2029',
            border: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-green)',
            flexShrink: 0
          }}>
            <Bot size={18} />
          </div>
          <div style={{
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            borderTopLeftRadius: '4px',
            padding: '14px 18px',
            color: 'var(--text-secondary)',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <Loader2 size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
            <span>Shield AI is thinking...</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
