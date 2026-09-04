import React, { useEffect, useRef } from 'react';
import { Bot, User, Loader2, Cpu } from 'lucide-react';
import MarkdownMessage from './MarkdownMessage';

export default function ChatMessageList({ messages = [], loading = false }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div style={{
      flex: 1,
      width: '100%',
      maxWidth: '900px',
      margin: '0 auto',
      overflowY: 'auto',
      padding: '24px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px'
    }}>
      {messages.map((msg, index) => {
        const isUser = msg.role === 'user';
        const isSystem = msg.role === 'system';

        if (isSystem) {
          return (
            <div key={msg.id || index} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '8px 0'
            }}>
              <div style={{
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '20px',
                padding: '6px 16px',
                fontSize: '12.5px',
                color: '#94a3b8',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Cpu size={14} style={{ color: '#f97316' }} />
                <span>{msg.content}</span>
              </div>
            </div>
          );
        }

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
              backgroundColor: isUser ? '#1e293b' : '#0f172a',
              border: `1px solid ${isUser ? '#334155' : 'rgba(249, 115, 22, 0.3)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isUser ? '#f8fafc' : '#f97316',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
              flexShrink: 0
            }}>
              {isUser ? <User size={17} /> : <Bot size={17} />}
            </div>

            {/* Bubble */}
            <div style={{
              maxWidth: '82%',
              backgroundColor: isUser ? '#1e293b' : '#141722',
              border: `1px solid ${isUser ? '#334155' : '#232736'}`,
              borderRadius: '16px',
              borderTopRightRadius: isUser ? '4px' : '16px',
              borderTopLeftRadius: isUser ? '16px' : '4px',
              padding: '16px 20px',
              color: '#e2e8f0',
              boxShadow: '0 4px 14px rgba(0, 0, 0, 0.25)'
            }}>
              {isUser ? (
                <div style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontSize: '14.5px',
                  lineHeight: '1.6',
                  color: '#f8fafc'
                }}>
                  {msg.content}
                </div>
              ) : (
                <MarkdownMessage content={msg.content} />
              )}
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
            backgroundColor: '#0f172a',
            border: '1px solid rgba(249, 115, 22, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#f97316',
            flexShrink: 0
          }}>
            <Bot size={17} />
          </div>
          <div style={{
            backgroundColor: '#141722',
            border: '1px solid #232736',
            borderRadius: '16px',
            borderTopLeftRadius: '4px',
            padding: '14px 20px',
            color: '#94a3b8',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: '0 4px 14px rgba(0, 0, 0, 0.25)'
          }}>
            <Loader2 size={16} style={{ animation: 'spin 1s linear infinite', color: '#f97316' }} />
            <span>Shield AI is thinking...</span>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
