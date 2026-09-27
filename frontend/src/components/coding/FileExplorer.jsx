import React, { useState, useMemo } from 'react';
import {
  Folder,
  FolderOpen,
  FilePlus,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  FileCode,
  FileText,
  FileJson,
  File,
  Trash2,
  FolderTree,
  FolderInput,
  CornerLeftUp,
} from 'lucide-react';

function getFileIcon(name) {
  const ext = name.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'js':
    case 'jsx':
    case 'mjs':
      return <FileCode size={14} color="#eab308" />;
    case 'ts':
    case 'tsx':
      return <FileCode size={14} color="#3b82f6" />;
    case 'py':
      return <FileCode size={14} color="#10b981" />;
    case 'json':
      return <FileJson size={14} color="#f59e0b" />;
    case 'md':
      return <FileText size={14} color="#06b6d4" />;
    case 'css':
    case 'scss':
      return <FileCode size={14} color="#ec4899" />;
    case 'html':
      return <FileCode size={14} color="#f97316" />;
    default:
      return <File size={14} color="#94a3b8" />;
  }
}

const IGNORED_SYSTEM_NAMES = new Set([
  '.agents',
  '.shield',
  '.skills',
  '.git',
  '.vscode',
  '.idea',
  'node_modules',
  '__pycache__',
  '.venv',
  'venv',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache',
  'dist',
  'build',
]);

function filterWorkspaceTree(nodes) {
  if (!Array.isArray(nodes)) return [];
  return nodes
    .filter((node) => {
      if (node.name && (node.name.startsWith('.') || IGNORED_SYSTEM_NAMES.has(node.name))) {
        return false;
      }
      return true;
    })
    .map((node) => {
      if (node.children) {
        return {
          ...node,
          children: filterWorkspaceTree(node.children),
        };
      }
      return node;
    });
}

function FileTreeNode({
  node,
  level,
  onSelectFile,
  activePath,
  onDeleteFile,
  onSelectWorkspace,
  workspaceRoot,
}) {
  const [isOpen, setIsOpen] = useState(level < 2);
  const isSelected = activePath === node.path;

  const handleClick = (e) => {
    e.stopPropagation();
    if (node.type === 'directory') {
      setIsOpen(!isOpen);
    } else {
      onSelectFile(node.path);
    }
  };

  return (
    <div>
      <div
        onClick={handleClick}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '4px 8px',
          paddingLeft: `${level * 14 + 10}px`,
          fontSize: '12px',
          cursor: 'pointer',
          borderRadius: '4px',
          userSelect: 'none',
          backgroundColor: isSelected ? 'rgba(37, 99, 235, 0.2)' : 'transparent',
          color: isSelected ? '#60a5fa' : '#cbd5e1',
          transition: 'background 0.12s ease',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
          const actions = e.currentTarget.querySelectorAll('.hover-action');
          actions.forEach((a) => (a.style.opacity = '1'));
        }}
        onMouseLeave={(e) => {
          if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
          const actions = e.currentTarget.querySelectorAll('.hover-action');
          actions.forEach((a) => (a.style.opacity = '0'));
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          {node.type === 'directory' ? (
            <>
              {isOpen ? <ChevronDown size={13} color="#64748b" /> : <ChevronRight size={13} color="#64748b" />}
              {isOpen ? <FolderOpen size={14} color="#fbbf24" /> : <Folder size={14} color="#f59e0b" />}
            </>
          ) : (
            <>
              <span style={{ width: '13px' }} />
              {getFileIcon(node.name)}
            </>
          )}
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {node.name}
          </span>
        </div>

        {/* Hover Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
          {/* Select folder as workspace button */}
          {node.type === 'directory' && onSelectWorkspace && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                const cleanRoot = (workspaceRoot || '').replace(/\\/g, '/').replace(/\/+$/, '');
                const target = `${cleanRoot}/${node.path}`;
                onSelectWorkspace(target);
              }}
              title={`Open "${node.name}" as Workspace`}
              style={{
                opacity: 0.6,
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                padding: '2px',
                color: '#60a5fa',
                display: 'flex',
                alignItems: 'center',
                transition: 'opacity 0.1s ease',
              }}
              className="hover-action"
            >
              <FolderInput size={12} />
            </button>
          )}

          {/* Delete Action */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (window.confirm(`Delete ${node.name}?`)) {
                onDeleteFile(node.path);
              }
            }}
            title={`Delete ${node.name}`}
            style={{
              opacity: 0,
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              padding: '2px',
              color: '#ef4444',
              display: 'flex',
              alignItems: 'center',
              transition: 'opacity 0.1s ease',
            }}
            className="hover-action"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {node.type === 'directory' && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              level={level + 1}
              onSelectFile={onSelectFile}
              activePath={activePath}
              onDeleteFile={onDeleteFile}
              onSelectWorkspace={onSelectWorkspace}
              workspaceRoot={workspaceRoot}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileExplorer({
  tree = [],
  workspaceRoot = '',
  activePath = null,
  onSelectFile,
  onCreateFile,
  onDeleteFile,
  onRefresh,
  isLoading = false,
  onOpenWorkspaceModal,
  onSelectWorkspace,
}) {
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    const clean = newFileName.trim();
    if (clean) {
      onCreateFile(clean);
      setNewFileName('');
      setShowNewFileInput(false);
    }
  };

  const folderName = workspaceRoot ? workspaceRoot.split(/[\/\\]/).pop() || 'workspace' : 'workspace';
  const cleanRoot = (workspaceRoot || '').replace(/\\/g, '/');
  const lastSlashIdx = cleanRoot.lastIndexOf('/');
  const parentPath = lastSlashIdx > 2 ? cleanRoot.substring(0, lastSlashIdx) : null;

  const visibleTree = useMemo(() => filterWorkspaceTree(tree), [tree]);

  return (
    <div
      style={{
        width: '240px',
        minWidth: '200px',
        maxWidth: '320px',
        height: '100%',
        backgroundColor: '#050507',
        borderRight: '1px solid #1a1a20',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Explorer Header */}
      <div
        style={{
          height: '38px',
          borderBottom: '1px solid #1a1a20',
          padding: '0 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#000000',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <FolderTree size={14} color="#3b82f6" />
          <span style={{ fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em', color: '#94a3b8', textTransform: 'uppercase' }}>
            Explorer
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {onOpenWorkspaceModal && (
            <button
              onClick={onOpenWorkspaceModal}
              title="Select / Open Workspace Folder..."
              style={{
                padding: '4px',
                borderRadius: '4px',
                color: '#94a3b8',
                display: 'flex',
                alignItems: 'center',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
            >
              <FolderInput size={14} />
            </button>
          )}
          <button
            onClick={() => setShowNewFileInput(!showNewFileInput)}
            title="New File"
            style={{
              padding: '4px',
              borderRadius: '4px',
              color: '#94a3b8',
              display: 'flex',
              alignItems: 'center',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <FilePlus size={14} />
          </button>
          <button
            onClick={onRefresh}
            title="Refresh Files"
            style={{
              padding: '4px',
              borderRadius: '4px',
              color: '#94a3b8',
              display: 'flex',
              alignItems: 'center',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Active Workspace Label & Switch Action */}
      <div
        style={{
          padding: '6px 12px',
          fontSize: '11px',
          fontWeight: 600,
          color: '#64748b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(26, 26, 32, 0.6)',
          backgroundColor: '#07080c',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
          <Folder size={12} color="#3b82f6" style={{ flexShrink: 0 }} />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={workspaceRoot}>
            {folderName.toUpperCase()}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {parentPath && onSelectWorkspace && (
            <button
              onClick={() => onSelectWorkspace(parentPath)}
              title={`Go up to parent: ${parentPath}`}
              style={{
                background: 'none',
                border: 'none',
                color: '#60a5fa',
                cursor: 'pointer',
                fontSize: '10.5px',
                padding: '1px 4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                fontWeight: 500,
                flexShrink: 0,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#93c5fd')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#60a5fa')}
            >
              <CornerLeftUp size={11} />
              <span>Up</span>
            </button>
          )}

          {onOpenWorkspaceModal && (
            <button
              onClick={onOpenWorkspaceModal}
              title="Change workspace folder"
              style={{
                background: 'none',
                border: 'none',
                color: '#3b82f6',
                cursor: 'pointer',
                fontSize: '10.5px',
                padding: '1px 4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                fontWeight: 500,
                flexShrink: 0,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#93c5fd')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#3b82f6')}
            >
              Change
            </button>
          )}
        </div>
      </div>

      {/* New File Inline Input */}
      {showNewFileInput && (
        <form onSubmit={handleCreateSubmit} style={{ padding: '6px 10px', backgroundColor: '#0a0a0d', borderBottom: '1px solid #1a1a20' }}>
          <input
            autoFocus
            type="text"
            placeholder="e.g. app.py, src/index.js"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setShowNewFileInput(false);
            }}
            style={{
              width: '100%',
              backgroundColor: '#111216',
              border: '1px solid #2563eb',
              borderRadius: '4px',
              padding: '4px 8px',
              fontSize: '11.5px',
              color: '#ffffff',
              outline: 'none',
              fontFamily: 'var(--font-mono, monospace)',
            }}
          />
        </form>
      )}

      {/* Tree Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
        {visibleTree.length === 0 ? (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
            {isLoading ? 'Scanning workspace...' : 'Workspace is empty. Create a file or ask the Agent to generate code!'}
          </div>
        ) : (
          visibleTree.map((node) => (
            <FileTreeNode
              key={node.path}
              node={node}
              level={0}
              onSelectFile={onSelectFile}
              activePath={activePath}
              onDeleteFile={onDeleteFile}
              onSelectWorkspace={onSelectWorkspace}
              workspaceRoot={workspaceRoot}
            />
          ))
        )}
      </div>
    </div>
  );
}
