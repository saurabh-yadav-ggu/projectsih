import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  Download,
  Trash2,
  FolderDown,
  FileText,
  FileSpreadsheet,
  Search,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileCheck,
  File
} from 'lucide-react';
import { fetchGeneratedDocuments, deleteGeneratedDocument, getDocumentDownloadUrl, downloadDocumentFile } from '../../api/documents';

export default function GeneratedFilesModal({
  token,
  isOpen,
  onClose
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('ALL');
  const [deletingId, setDeletingId] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);

  const loadDocuments = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGeneratedDocuments(token);
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err.message || 'Failed to load generated documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadDocuments();
      setSearchQuery('');
      setSelectedFormat('ALL');
      setError(null);
      setSuccessMsg(null);
    }
  }, [isOpen, token]);

  const handleDelete = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }
    setDeletingId(filename);
    setError(null);
    try {
      await deleteGeneratedDocument(token, filename);
      setDocuments(prev => prev.filter(d => d.filename !== filename));
      setSuccessMsg(`Document "${filename}" deleted successfully.`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err.message || 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = async (doc) => {
    setDownloadingId(doc.filename);
    setError(null);
    try {
      await downloadDocumentFile(token, doc.path, doc.filename);
    } catch (err) {
      console.warn('downloadDocumentFile error, falling back to direct URL:', err);
      const url = getDocumentDownloadUrl(doc.path, token);
      const link = document.createElement('a');
      link.href = url;
      link.download = doc.filename;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      setDownloadingId(null);
    }
  };

  const formats = ['ALL', 'DOCX', 'PDF', 'XLSX', 'PPTX', 'CSV'];

  const filteredDocs = useMemo(() => {
    return documents.filter(doc => {
      const matchesSearch = !searchQuery ||
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesFormat = selectedFormat === 'ALL' ||
        doc.format.toUpperCase() === selectedFormat;
      return matchesSearch && matchesFormat;
    });
  }, [documents, searchQuery, selectedFormat]);

  if (!isOpen) return null;

  const getFormatBadgeStyle = (fmt) => {
    const f = fmt.toUpperCase();
    if (f === 'DOCX') return { bg: 'rgba(59, 130, 246, 0.15)', text: '#93c5fd', border: 'rgba(59, 130, 246, 0.3)' };
    if (f === 'PDF') return { bg: 'rgba(239, 68, 68, 0.15)', text: '#fca5a5', border: 'rgba(239, 68, 68, 0.3)' };
    if (f === 'XLSX') return { bg: 'rgba(34, 197, 94, 0.15)', text: '#86efac', border: 'rgba(34, 197, 94, 0.3)' };
    if (f === 'PPTX') return { bg: 'rgba(249, 115, 22, 0.15)', text: '#fdba74', border: 'rgba(249, 115, 22, 0.3)' };
    if (f === 'CSV') return { bg: 'rgba(6, 182, 212, 0.15)', text: '#67e8f9', border: 'rgba(6, 182, 212, 0.3)' };
    return { bg: 'rgba(148, 163, 184, 0.15)', text: '#cbd5e1', border: 'rgba(148, 163, 184, 0.3)' };
  };

  const getFileIcon = (fmt) => {
    const f = fmt.toUpperCase();
    if (f === 'DOCX') return <FileText size={18} color="#60a5fa" />;
    if (f === 'PDF') return <FileCheck size={18} color="#f87171" />;
    if (f === 'XLSX' || f === 'CSV') return <FileSpreadsheet size={18} color="#4ade80" />;
    return <File size={18} color="#fb923c" />;
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '850px',
        maxHeight: '88vh',
        backgroundColor: '#08080b',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 40px rgba(29, 78, 216, 0.15)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(15, 23, 42, 0.85)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: 'rgba(29, 78, 216, 0.15)',
              border: '1px solid rgba(29, 78, 216, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <FolderDown size={20} color="var(--accent-orange, #1d4ed8)" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
                  Generated Documents
                </h2>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  color: '#94a3b8'
                }}>
                  {documents.length} {documents.length === 1 ? 'file' : 'files'}
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: '#64748b' }}>
                Manage, download, and delete deliverables generated by Shield AI subagents.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={loadDocuments}
              disabled={loading}
              title="Refresh document list"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: '#cbd5e1',
                padding: '8px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease'
              }}
            >
              <RefreshCw size={15} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                color: '#cbd5e1',
                padding: '8px',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Toolbar: Search & Format Filter Tabs */}
        <div style={{
          padding: '12px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          backgroundColor: 'rgba(0, 0, 0, 0.2)'
        }}>
          {/* Format Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto' }}>
            {formats.map(fmt => {
              const isSelected = selectedFormat === fmt;
              return (
                <button
                  key={fmt}
                  onClick={() => setSelectedFormat(fmt)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    border: isSelected ? '1px solid #1d4ed8' : '1px solid transparent',
                    backgroundColor: isSelected ? 'rgba(29, 78, 216, 0.2)' : 'transparent',
                    color: isSelected ? '#93c5fd' : '#94a3b8',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {fmt}
                </button>
              );
            })}
          </div>

          {/* Search Input */}
          <div style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            width: '260px'
          }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', color: '#64748b' }} />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '6px 12px 6px 32px',
                fontSize: '12px',
                color: '#f8fafc',
                outline: 'none'
              }}
            />
          </div>
        </div>

        {/* Feedback Messages */}
        {error && (
          <div style={{
            margin: '12px 24px 0 24px',
            padding: '8px 12px',
            borderRadius: '8px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            color: '#fca5a5',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            margin: '12px 24px 0 24px',
            padding: '8px 12px',
            borderRadius: '8px',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.25)',
            color: '#86efac',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <CheckCircle2 size={14} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Document List */}
        <div style={{
          padding: '16px 24px',
          overflowY: 'auto',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          {filteredDocs.length === 0 ? (
            <div style={{
              padding: '48px 20px',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#64748b'
            }}>
              <FolderDown size={36} style={{ marginBottom: '12px', opacity: 0.4 }} />
              <div style={{ fontSize: '14px', fontWeight: 500, color: '#94a3b8' }}>
                {searchQuery || selectedFormat !== 'ALL'
                  ? 'No documents match the filter criteria'
                  : 'No generated documents yet'}
              </div>
              <div style={{ fontSize: '12px', marginTop: '4px', maxWidth: '340px' }}>
                Ask Shield AI to create a Word document (.docx), PDF report (.pdf), or Excel spreadsheet (.xlsx) to see files here.
              </div>
            </div>
          ) : (
            filteredDocs.map((doc) => {
              const badgeStyle = getFormatBadgeStyle(doc.format);
              const isDeleting = deletingId === doc.filename;

              return (
                <div
                  key={doc.id || doc.filename}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    transition: 'all 0.15s ease'
                  }}
                  className="generated-doc-item"
                >
                  {/* Left: Icon & Info */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: 0 }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(0, 0, 0, 0.35)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      {getFileIcon(doc.format)}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{
                        fontSize: '13px',
                        fontWeight: 500,
                        color: '#f8fafc',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: '460px'
                      }}>
                        {doc.filename}
                      </div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '11px',
                        color: '#64748b',
                        marginTop: '3px'
                      }}>
                        <span style={{
                          padding: '1px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 600,
                          backgroundColor: badgeStyle.bg,
                          color: badgeStyle.text,
                          border: `1px solid ${badgeStyle.border}`
                        }}>
                          {doc.format.toUpperCase()}
                        </span>
                        <span>•</span>
                        <span>{doc.size_formatted}</span>
                        <span>•</span>
                        <span>{doc.created_at_formatted}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                    <button
                      onClick={() => handleDownload(doc)}
                      title={`Download ${doc.filename}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '6px 12px',
                        borderRadius: '6px',
                        backgroundColor: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#e2e8f0',
                        fontSize: '12px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <Download size={13} />
                      <span>Download</span>
                    </button>

                    <button
                      onClick={() => handleDelete(doc.filename)}
                      disabled={isDeleting}
                      title={`Delete ${doc.filename}`}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        backgroundColor: 'rgba(239, 68, 68, 0.08)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                        color: '#f87171',
                        cursor: isDeleting ? 'not-allowed' : 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
