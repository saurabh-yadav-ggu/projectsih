import React, { useState, useEffect } from 'react';
import {
  Folder,
  FolderPlus,
  FolderOpen,
  Check,
  X,
  HardDrive,
  Code,
  ArrowRight,
  AlertCircle,
  Loader2,
  ChevronRight,
  CornerLeftUp,
  Compass,
  ListFilter,
  Monitor,
} from 'lucide-react';
import { browseDirectories } from '../../api/coding';

export default function WorkspaceModal({
  isOpen,
  onClose,
  token,
  currentWorkspace = '',
  suggestedWorkspaces = [],
  onSelectWorkspace,
  isSwitching = false,
}) {
  const [activeTab, setActiveTab] = useState('browse'); // 'browse' | 'quick'
  const [customPath, setCustomPath] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Filesystem directory browser state
  const [browsingPath, setBrowsingPath] = useState('');
  const [browseData, setBrowseData] = useState({
    current_path: '',
    parent_path: null,
    drives: [],
    directories: [],
  });
  const [isLoadingBrowse, setIsLoadingBrowse] = useState(false);

  // Initialize browser path when modal opens
  useEffect(() => {
    if (isOpen) {
      setErrorMsg('');
      const initial = currentWorkspace || '';
      setBrowsingPath(initial);
      loadBrowsePath(initial);
    }
  }, [isOpen, currentWorkspace]);

  const loadBrowsePath = async (path) => {
    if (!token) return;
    setIsLoadingBrowse(true);
    setErrorMsg('');
    try {
      const data = await browseDirectories(token, path);
      setBrowseData(data);
      setBrowsingPath(data.current_path || path);
    } catch (err) {
      console.warn('Could not browse directory:', err);
      setErrorMsg(err.message || 'Failed to read directory');
    } finally {
      setIsLoadingBrowse(false);
    }
  };

  if (!isOpen) return null;

  const handleSelect = async (path) => {
    if (!path) return;
    setErrorMsg('');
    try {
      await onSelectWorkspace(path);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to switch workspace');
    }
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (!customPath.trim()) return;
    handleSelect(customPath.trim());
  };

  // Browser native directory picker if supported
  const handleNativePicker = async () => {
    if (typeof window !== 'undefined' && 'showDirectoryPicker' in window) {
      try {
        const handle = await window.showDirectoryPicker();
        if (handle && handle.name) {
          // If native picker returns folder name, try selecting it or browsing to it
          handleSelect(handle.name);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.warn('Native picker error:', err);
        }
      }
    }
  };

  const normalize = (p) => (p || '').replace(/\\/g, '/').toLowerCase();
  const currentNormalized = normalize(currentWorkspace);

  // Generate breadcrumb items
  const cleanBrowsePath = (browseData.current_path || browsingPath || '').replace(/\\/g, '/');
  const pathParts = cleanBrowsePath.split('/').filter(Boolean);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        animation: 'fadeIn 0.15s ease-out',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSwitching) onClose();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '640px',
          backgroundColor: '#090a0f',
          border: '1px solid #1e2230',
          borderRadius: '12px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 0 1px rgba(30, 58, 138, 0.25)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid #161822',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#0c0d14',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: '#172554',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#60a5fa',
              }}
            >
              <FolderOpen size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', margin: 0, letterSpacing: '-0.01em' }}>
                Select Workspace Folder
              </h2>
              <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0 0' }}>
                Choose where the AI agent and filesystem backend will write, edit, and run code
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={isSwitching}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#64748b',
              cursor: isSwitching ? 'not-allowed' : 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#64748b')}
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 20px',
            backgroundColor: '#07080c',
            borderBottom: '1px solid #161822',
          }}
        >
          <button
            onClick={() => setActiveTab('browse')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '11.5px',
              fontWeight: 500,
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'browse' ? '#172554' : 'transparent',
              color: activeTab === 'browse' ? '#93c5fd' : '#64748b',
              transition: 'all 0.15s ease',
            }}
          >
            <Compass size={13} />
            <span>Browse Filesystem</span>
          </button>

          <button
            onClick={() => setActiveTab('quick')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '11.5px',
              fontWeight: 500,
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'quick' ? '#172554' : 'transparent',
              color: activeTab === 'quick' ? '#93c5fd' : '#64748b',
              transition: 'all 0.15s ease',
            }}
          >
            <ListFilter size={13} />
            <span>Suggested & Custom Path</span>
          </button>
        </div>

        {/* Modal Content Body */}
        <div style={{ padding: '16px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
          {errorMsg && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 12px',
                borderRadius: '8px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                fontSize: '12px',
              }}
            >
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* TAB 1: BROWSE FILESYSTEM */}
          {activeTab === 'browse' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Drives & Root Quick Select */}
              {browseData.drives && browseData.drives.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '11px', color: '#64748b', marginRight: '4px' }}>Drives:</span>
                  {browseData.drives.map((drv) => (
                    <button
                      key={drv}
                      onClick={() => loadBrowsePath(drv)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '3px 8px',
                        borderRadius: '5px',
                        fontSize: '11px',
                        fontFamily: 'Consolas, monospace',
                        backgroundColor: '#0f111a',
                        border: '1px solid #1e2436',
                        color: '#93c5fd',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#3b82f6')}
                      onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e2436')}
                    >
                      <HardDrive size={11} />
                      <span>{drv}</span>
                    </button>
                  ))}

                  {/* Native file system picker if supported */}
                  {typeof window !== 'undefined' && 'showDirectoryPicker' in window && (
                    <button
                      onClick={handleNativePicker}
                      title="Open Windows / OS folder picker"
                      style={{
                        marginLeft: 'auto',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '3px 8px',
                        borderRadius: '5px',
                        fontSize: '11px',
                        backgroundColor: '#111827',
                        border: '1px solid #374151',
                        color: '#cbd5e1',
                        cursor: 'pointer',
                      }}
                    >
                      <Monitor size={11} color="#a855f7" />
                      <span>OS Picker...</span>
                    </button>
                  )}
                </div>
              )}

              {/* Breadcrumb Path Bar */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  backgroundColor: '#0c0e17',
                  border: '1px solid #1a1e2d',
                  fontSize: '11.5px',
                  fontFamily: 'Consolas, monospace',
                  overflowX: 'auto',
                  whiteSpace: 'nowrap',
                }}
              >
                <button
                  onClick={() => loadBrowsePath(browseData.drives[0] || '/')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#60a5fa',
                    cursor: 'pointer',
                    padding: 0,
                    fontWeight: 600,
                  }}
                >
                  Root
                </button>

                {pathParts.map((part, idx) => {
                  const partPath = pathParts.slice(0, idx + 1).join('/');
                  const fullPartPath = (browseData.current_path && browseData.current_path.includes(':'))
                    ? (idx === 0 ? `${part}/` : `${pathParts[0]}/${pathParts.slice(1, idx + 1).join('/')}`)
                    : `/${partPath}`;

                  return (
                    <React.Fragment key={idx}>
                      <ChevronRight size={11} color="#475569" style={{ flexShrink: 0 }} />
                      <button
                        onClick={() => loadBrowsePath(fullPartPath)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: idx === pathParts.length - 1 ? '#f8fafc' : '#93c5fd',
                          fontWeight: idx === pathParts.length - 1 ? 600 : 400,
                          cursor: 'pointer',
                          padding: 0,
                        }}
                      >
                        {part}
                      </button>
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Directory Listing Container */}
              <div
                style={{
                  border: '1px solid #1a1e2d',
                  borderRadius: '8px',
                  backgroundColor: '#06070a',
                  maxHeight: '260px',
                  minHeight: '160px',
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                {isLoadingBrowse ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '140px', gap: '8px', color: '#64748b', fontSize: '12px' }}>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Loading folders...</span>
                  </div>
                ) : (
                  <>
                    {/* Up to Parent Row */}
                    {browseData.parent_path && (
                      <div
                        onClick={() => loadBrowsePath(browseData.parent_path)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '7px 12px',
                          borderBottom: '1px solid #141724',
                          cursor: 'pointer',
                          color: '#94a3b8',
                          fontSize: '12px',
                          userSelect: 'none',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#0e111a')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <CornerLeftUp size={14} color="#3b82f6" />
                        <span style={{ fontWeight: 500 }}>.. (Go up one level)</span>
                      </div>
                    )}

                    {/* Subdirectories */}
                    {browseData.directories && browseData.directories.length > 0 ? (
                      browseData.directories.map((dir) => {
                        const isDirCurrent = normalize(dir.path) === currentNormalized;
                        return (
                          <div
                            key={dir.path}
                            onClick={() => loadBrowsePath(dir.path)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '7px 12px',
                              borderBottom: '1px solid #0f121d',
                              cursor: 'pointer',
                              color: isDirCurrent ? '#60a5fa' : '#cbd5e1',
                              fontSize: '12px',
                              userSelect: 'none',
                              backgroundColor: isDirCurrent ? 'rgba(37, 99, 235, 0.1)' : 'transparent',
                            }}
                            onMouseEnter={(e) => {
                              if (!isDirCurrent) e.currentTarget.style.backgroundColor = '#0e111a';
                            }}
                            onMouseLeave={(e) => {
                              if (!isDirCurrent) e.currentTarget.style.backgroundColor = 'transparent';
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                              <Folder size={14} color="#fbbf24" style={{ flexShrink: 0 }} />
                              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {dir.name}
                              </span>
                            </div>

                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelect(dir.path);
                              }}
                              disabled={isSwitching}
                              title="Set as Workspace"
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '3px 8px',
                                borderRadius: '4px',
                                fontSize: '10.5px',
                                fontWeight: 500,
                                backgroundColor: '#172554',
                                color: '#93c5fd',
                                border: '1px solid #1e3a8a',
                                cursor: 'pointer',
                                flexShrink: 0,
                              }}
                              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#1d4ed8')}
                              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#172554')}
                            >
                              <span>Select</span>
                              <ArrowRight size={10} />
                            </button>
                          </div>
                        );
                      })
                    ) : (
                      <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                        No subdirectories in this folder
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Bottom Action for Browsed Directory */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  backgroundColor: '#0c0e17',
                  border: '1px solid #1e2436',
                  gap: '10px',
                }}
              >
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontSize: '10.5px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Current Browsed Folder
                  </div>
                  <div
                    style={{
                      fontSize: '11.5px',
                      fontFamily: 'Consolas, monospace',
                      color: '#93c5fd',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={browseData.current_path || browsingPath}
                  >
                    {browseData.current_path || browsingPath || 'No folder chosen'}
                  </div>
                </div>

                <button
                  onClick={() => handleSelect(browseData.current_path || browsingPath)}
                  disabled={isSwitching || !browseData.current_path}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '7px 14px',
                    borderRadius: '6px',
                    backgroundColor: isSwitching || !browseData.current_path ? '#1e2436' : '#2563eb',
                    color: isSwitching || !browseData.current_path ? '#64748b' : '#ffffff',
                    border: 'none',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: isSwitching || !browseData.current_path ? 'not-allowed' : 'pointer',
                    flexShrink: 0,
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSwitching && browseData.current_path) e.currentTarget.style.backgroundColor = '#1d4ed8';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSwitching && browseData.current_path) e.currentTarget.style.backgroundColor = '#2563eb';
                  }}
                >
                  {isSwitching ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      <span>Switching...</span>
                    </>
                  ) : (
                    <>
                      <FolderPlus size={13} />
                      <span>Select as Workspace</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: SUGGESTED WORKSPACES & MANUAL PATH */}
          {activeTab === 'quick' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Current Active Workspace Card */}
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                  Current Active Workspace
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    backgroundColor: '#0f111a',
                    border: '1px solid #1e2436',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <HardDrive size={15} color="#3b82f6" style={{ flexShrink: 0 }} />
                    <span
                      style={{
                        fontSize: '12px',
                        fontFamily: 'Consolas, monospace',
                        color: '#93c5fd',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={currentWorkspace}
                    >
                      {currentWorkspace || 'Default sandbox'}
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '12px',
                      backgroundColor: '#14532d',
                      color: '#86efac',
                      border: '1px solid #166534',
                      flexShrink: 0,
                    }}
                  >
                    Active
                  </span>
                </div>
              </div>

              {/* Suggested Workspaces */}
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                  Suggested Workspaces
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {suggestedWorkspaces && suggestedWorkspaces.length > 0 ? (
                    suggestedWorkspaces.map((ws, idx) => {
                      const isCurrent = normalize(ws.path) === currentNormalized;
                      return (
                        <button
                          key={ws.path || idx}
                          disabled={isSwitching || isCurrent}
                          onClick={() => handleSelect(ws.path)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '10px 12px',
                            borderRadius: '8px',
                            backgroundColor: isCurrent ? '#111827' : '#0c0e17',
                            border: `1px solid ${isCurrent ? '#2563eb' : '#181b28'}`,
                            cursor: isCurrent || isSwitching ? 'default' : 'pointer',
                            textAlign: 'left',
                            transition: 'all 0.15s ease',
                          }}
                          onMouseEnter={(e) => {
                            if (!isCurrent && !isSwitching) {
                              e.currentTarget.style.backgroundColor = '#131726';
                              e.currentTarget.style.borderColor = '#2d3748';
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!isCurrent && !isSwitching) {
                              e.currentTarget.style.backgroundColor = '#0c0e17';
                              e.currentTarget.style.borderColor = '#181b28';
                            }
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                            <Folder
                              size={16}
                              color={isCurrent ? '#60a5fa' : ws.type === 'project_root' ? '#a855f7' : '#38bdf8'}
                              style={{ flexShrink: 0 }}
                            />
                            <div style={{ overflow: 'hidden' }}>
                              <div style={{ fontSize: '12.5px', fontWeight: 500, color: isCurrent ? '#93c5fd' : '#f1f5f9' }}>
                                {ws.name}
                              </div>
                              <div
                                style={{
                                  fontSize: '11px',
                                  fontFamily: 'Consolas, monospace',
                                  color: '#64748b',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                                title={ws.path}
                              >
                                {ws.path}
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                            {isCurrent ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#60a5fa', fontSize: '11px' }}>
                                <Check size={14} />
                                <span>Current</span>
                              </div>
                            ) : (
                              <div style={{ color: '#475569', display: 'flex', alignItems: 'center' }}>
                                <ArrowRight size={13} />
                              </div>
                            )}
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div style={{ fontSize: '12px', color: '#64748b', padding: '8px' }}>
                      No suggested workspaces found.
                    </div>
                  )}
                </div>
              </div>

              {/* Custom Path Input */}
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                  Manual Path or New Project
                </div>

                <form onSubmit={handleCustomSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <input
                    type="text"
                    value={customPath}
                    onChange={(e) => setCustomPath(e.target.value)}
                    placeholder="Enter directory (e.g. D:/my-project or my-new-app)..."
                    disabled={isSwitching}
                    style={{
                      width: '100%',
                      padding: '9px 12px',
                      borderRadius: '8px',
                      backgroundColor: '#0c0e17',
                      border: '1px solid #1e2436',
                      fontSize: '12px',
                      fontFamily: 'Consolas, monospace',
                      color: '#f8fafc',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                    onFocus={(e) => (e.target.style.borderColor = '#2563eb')}
                    onBlur={(e) => (e.target.style.borderColor = '#1e2436')}
                  />

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>
                      Relative names are created under <span style={{ fontFamily: 'monospace', color: '#94a3b8' }}>projects/</span>
                    </span>
                    <button
                      type="submit"
                      disabled={!customPath.trim() || isSwitching}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 14px',
                        borderRadius: '6px',
                        backgroundColor: !customPath.trim() || isSwitching ? '#1e2436' : '#2563eb',
                        color: !customPath.trim() || isSwitching ? '#64748b' : '#ffffff',
                        border: 'none',
                        fontSize: '12px',
                        fontWeight: 500,
                        cursor: !customPath.trim() || isSwitching ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {isSwitching ? (
                        <>
                          <Loader2 size={13} className="animate-spin" />
                          <span>Switching...</span>
                        </>
                      ) : (
                        <>
                          <FolderPlus size={13} />
                          <span>Open Workspace</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '10px 20px',
            backgroundColor: '#06070a',
            borderTop: '1px solid #141724',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: '#64748b',
          }}
        >
          <span>Deep Agent re-mounts filesystem backend tools to the chosen folder</span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '11px',
              padding: '2px 6px',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
