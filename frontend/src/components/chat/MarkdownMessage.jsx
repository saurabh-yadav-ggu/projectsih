import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Terminal } from 'lucide-react';

function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{
      margin: '16px 0',
      borderRadius: '10px',
      overflow: 'hidden',
      border: '1px solid #2d3142',
      backgroundColor: '#0d0f14',
      boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"
    }}>
      {/* IDE Code Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 14px',
        backgroundColor: '#161922',
        borderBottom: '1px solid #232736',
        fontSize: '12px',
        color: '#94a3b8'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
          <Terminal size={14} style={{ color: '#38bdf8' }} />
          <span style={{ textTransform: 'lowercase', color: '#cbd5e1' }}>{language || 'code'}</span>
        </div>
        <button
          onClick={handleCopy}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: copied ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255, 255, 255, 0.06)',
            border: `1px solid ${copied ? 'rgba(34, 197, 94, 0.4)' : 'rgba(255, 255, 255, 0.1)'}`,
            borderRadius: '6px',
            padding: '4px 10px',
            color: copied ? '#4ade80' : '#cbd5e1',
            fontSize: '12px',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
          title="Copy code"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>

      {/* Code Area */}
      <pre style={{
        margin: 0,
        padding: '16px',
        overflowX: 'auto',
        fontSize: '13.5px',
        lineHeight: '1.6',
        color: '#e2e8f0',
        backgroundColor: '#0d0f14',
        tabSize: 4
      }}>
        <code>{value}</code>
      </pre>
    </div>
  );
}

export default function MarkdownMessage({ content = '' }) {
  return (
    <div className="markdown-body" style={{
      fontSize: '14.5px',
      lineHeight: '1.7',
      color: '#e2e8f0'
    }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeText = String(children).replace(/\n$/, '');

            if (!inline && (match || codeText.includes('\n'))) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  value={codeText}
                />
              );
            }

            return (
              <code
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.09)',
                  color: '#38bdf8',
                  padding: '2px 6px',
                  borderRadius: '5px',
                  fontSize: '0.88em',
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  border: '1px solid rgba(255, 255, 255, 0.12)'
                }}
                {...props}
              >
                {children}
              </code>
            );
          },
          h1({ children }) {
            return (
              <h1 style={{
                fontSize: '1.45rem',
                fontWeight: 700,
                marginTop: '20px',
                marginBottom: '12px',
                color: '#f8fafc',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                paddingBottom: '6px'
              }}>
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return (
              <h2 style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                marginTop: '18px',
                marginBottom: '10px',
                color: '#f1f5f9'
              }}>
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return (
              <h3 style={{
                fontSize: '1.08rem',
                fontWeight: 650,
                marginTop: '14px',
                marginBottom: '8px',
                color: '#e2e8f0'
              }}>
                {children}
              </h3>
            );
          },
          p({ children }) {
            return (
              <p style={{
                marginBottom: '12px',
                lineHeight: '1.75',
                color: '#cbd5e1'
              }}>
                {children}
              </p>
            );
          },
          ul({ children }) {
            return (
              <ul style={{
                paddingLeft: '22px',
                marginBottom: '14px',
                listStyleType: 'disc'
              }}>
                {children}
              </ul>
            );
          },
          ol({ children }) {
            return (
              <ol style={{
                paddingLeft: '22px',
                marginBottom: '14px',
                listStyleType: 'decimal'
              }}>
                {children}
              </ol>
            );
          },
          li({ children }) {
            return (
              <li style={{
                marginBottom: '6px',
                lineHeight: '1.65',
                color: '#cbd5e1'
              }}>
                {children}
              </li>
            );
          },
          strong({ children }) {
            return (
              <strong style={{
                fontWeight: 650,
                color: '#ffffff'
              }}>
                {children}
              </strong>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote style={{
                borderLeft: '3px solid #f97316',
                backgroundColor: 'rgba(249, 115, 22, 0.05)',
                padding: '10px 16px',
                borderRadius: '0 8px 8px 0',
                margin: '14px 0',
                color: '#e2e8f0',
                fontStyle: 'italic'
              }}>
                {children}
              </blockquote>
            );
          },
          hr() {
            return (
              <hr style={{
                border: 'none',
                height: '1px',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                margin: '20px 0'
              }} />
            );
          },
          table({ children }) {
            return (
              <div style={{ overflowX: 'auto', margin: '16px 0' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  overflow: 'hidden'
                }}>
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th style={{
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                padding: '10px 14px',
                textAlign: 'left',
                fontWeight: 600,
                color: '#f8fafc',
                borderBottom: '1px solid rgba(255, 255, 255, 0.12)'
              }}>
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td style={{
                padding: '10px 14px',
                borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                color: '#cbd5e1'
              }}>
                {children}
              </td>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  color: '#38bdf8',
                  textDecoration: 'none',
                  borderBottom: '1px dashed #38bdf8'
                }}
              >
                {children}
              </a>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
