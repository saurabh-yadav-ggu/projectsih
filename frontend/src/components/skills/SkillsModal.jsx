import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  Plus,
  Search,
  Sparkles,
  FileText,
  Code,
  Terminal,
  Cpu,
  Trash2,
  Edit3,
  Play,
  Check,
  AlertCircle,
  FolderGit2,
  BookOpen,
  ArrowRight
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  fetchSkills,
  fetchSkill,
  createSkill,
  updateSkill,
  deleteSkill
} from '../../api/skills';

const SAMPLE_STARTER_TEMPLATE = `---
name: custom_document_skill
title: Custom Document Blueprint
description: Instructions and Python code pattern for generating structured corporate deliverables.
category: document
format: pdf
---

# Document Design Guidelines

When generating this document:
1. Include an executive title, subtitle, and metadata block (Author, Date, Version).
2. Utilize consistent padding, margins, and crisp color palettes.
3. For tables, format headers with distinct contrasting backgrounds.

### Python Code Pattern (ReportLab / Sandbox):
\`\`\`python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

doc = SimpleDocTemplate(target_path, pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Header
title_style = ParagraphStyle(
    'TitleStyle',
    parent=styles['Heading1'],
    fontSize=20,
    textColor=colors.HexColor('#1E293B')
)
story.append(Paragraph("Enterprise Executive Summary", title_style))
story.append(Spacer(1, 14))

# Content
story.append(Paragraph("This document was generated automatically by Shield AI sandbox.", styles['Normal']))

doc.build(story)
\`\`\`
`;

export default function SkillsModal({
  token,
  isOpen,
  onClose,
  onUseSkillInChat
}) {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activeSkillId, setActiveSkillId] = useState(null);
  const [activeSkillDetail, setActiveSkillDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Editor Modal State
  const [isEditing, setIsEditing] = useState(false);
  const [editingSkillId, setEditingSkillId] = useState(null);
  const [formName, setFormName] = useState('');
  const [formTitle, setFormTitle] = useState('');
  const [formCategory, setFormCategory] = useState('document');
  const [formFormat, setFormFormat] = useState('pdf');
  const [formDescription, setFormDescription] = useState('');
  const [formContent, setFormContent] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  // Load skills list
  const loadSkills = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSkills(token);
      setSkills(data);
      if (data.length > 0 && !activeSkillId) {
        setActiveSkillId(data[0].id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load skills');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadSkills();
    }
  }, [isOpen, token]);

  // Load active skill detail
  useEffect(() => {
    if (!isOpen || !activeSkillId || !token) return;
    let isCurrent = true;
    setDetailLoading(true);
    fetchSkill(token, activeSkillId)
      .then(detail => {
        if (isCurrent) setActiveSkillDetail(detail);
      })
      .catch(err => {
        if (isCurrent) console.warn('Failed to load skill detail:', err);
      })
      .finally(() => {
        if (isCurrent) setDetailLoading(false);
      });
    return () => { isCurrent = false; };
  }, [activeSkillId, isOpen, token]);

  // Filter skills
  const filteredSkills = useMemo(() => {
    return skills.filter(skill => {
      const matchesSearch =
        skill.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (skill.description && skill.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
        skill.format.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (selectedCategory === 'all') return true;
      if (selectedCategory === 'custom') return !skill.is_system;
      if (selectedCategory === 'document') return skill.category === 'document';
      if (selectedCategory === 'coding') return skill.category === 'coding';
      if (selectedCategory === 'ai-system') return skill.category === 'ai-system' || skill.category === 'ai-research';
      return skill.category === selectedCategory;
    });
  }, [skills, searchQuery, selectedCategory]);

  const categoryCounts = useMemo(() => {
    const counts = { all: skills.length, document: 0, coding: 0, 'ai-system': 0, custom: 0 };
    skills.forEach(s => {
      if (!s.is_system) counts.custom++;
      if (s.category === 'document') counts.document++;
      if (s.category === 'coding') counts.coding++;
      if (s.category === 'ai-system' || s.category === 'ai-research') counts['ai-system']++;
    });
    return counts;
  }, [skills]);

  // Open Create Dialog
  const handleOpenCreate = () => {
    setIsEditing(true);
    setEditingSkillId(null);
    setFormName('');
    setFormTitle('');
    setFormCategory('document');
    setFormFormat('pdf');
    setFormDescription('');
    setFormContent(SAMPLE_STARTER_TEMPLATE);
    setFormError(null);
  };

  // Open Edit Dialog
  const handleOpenEdit = (skill) => {
    setIsEditing(true);
    setEditingSkillId(skill.id);
    setFormName(skill.name);
    setFormTitle(skill.title);
    setFormCategory(skill.category);
    setFormFormat(skill.format);
    setFormDescription(skill.description);
    setFormContent(activeSkillDetail?.content || skill.description || '');
    setFormError(null);
  };

  // Handle Save
  const handleSaveSkill = async (e) => {
    e.preventDefault();
    if (!formName.trim() || !formTitle.trim() || !formContent.trim()) {
      setFormError('Please fill in name, title, and content.');
      return;
    }
    setFormSubmitting(true);
    setFormError(null);
    try {
      if (editingSkillId) {
        const updated = await updateSkill(token, editingSkillId, {
          title: formTitle,
          description: formDescription,
          category: formCategory,
          format: formFormat,
          content: formContent
        });
        setIsEditing(false);
        await loadSkills();
        setActiveSkillId(updated.id);
      } else {
        const created = await createSkill(token, {
          name: formName,
          title: formTitle,
          description: formDescription,
          category: formCategory,
          format: formFormat,
          content: formContent
        });
        setIsEditing(false);
        await loadSkills();
        setActiveSkillId(created.id);
      }
    } catch (err) {
      setFormError(err.message || 'Failed to save skill');
    } finally {
      setFormSubmitting(false);
    }
  };

  // Handle Delete
  const handleDeleteSkill = async (skillId) => {
    if (!confirm(`Are you sure you want to delete custom skill "${skillId}"?`)) return;
    try {
      await deleteSkill(token, skillId);
      await loadSkills();
      setActiveSkillId(null);
      setActiveSkillDetail(null);
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  // Trigger skill execution from chat
  const handleUseSkill = (skill) => {
    if (!onUseSkillInChat) return;
    const formatName = skill.format.toUpperCase();
    const promptText = `Generate a ${formatName} document adhering to the "${skill.title}" skill guidelines with realistic content: `;
    onUseSkillInChat(promptText);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: '#11141d',
        border: '1px solid #232838',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '1100px',
        height: '85vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.7)'
      }}>
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid #232838',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#0d1017'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: 'rgba(29, 78, 216, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#3b82f6'
            }}>
              <Sparkles size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#fff', margin: 0 }}>
                  Agent Skill Library & Blueprints
                </h2>
                <span style={{
                  fontSize: '11px',
                  fontWeight: '600',
                  color: '#10b981',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  border: '1px solid rgba(16, 185, 129, 0.25)',
                  padding: '2px 8px',
                  borderRadius: '12px'
                }}>
                  {skills.length} Loaded
                </span>
              </div>
              <p style={{ fontSize: '12px', color: '#8b949e', margin: '2px 0 0 0' }}>
                Specialized document generation rules, sandbox patterns, and official Claude/AI templates.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={handleOpenCreate}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#1d4ed8',
                color: '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <Plus size={16} />
              <span>New Custom Skill</span>
            </button>
            <button
              onClick={onClose}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: '#8b949e',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div style={{
          padding: '12px 24px',
          borderBottom: '1px solid #1f2433',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          backgroundColor: '#10141f'
        }}>
          {/* Category Tabs */}
          <div style={{ display: 'flex', gap: '6px', overflowX: 'auto' }}>
            {[
              { id: 'all', label: `All (${categoryCounts.all})` },
              { id: 'document', label: `Documents (${categoryCounts.document})` },
              { id: 'coding', label: `Coding (${categoryCounts.coding})` },
              { id: 'ai-system', label: `AI System (${categoryCounts['ai-system']})` },
              { id: 'custom', label: `Custom (${categoryCounts.custom})` }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setSelectedCategory(tab.id)}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: selectedCategory === tab.id ? '600' : '400',
                  color: selectedCategory === tab.id ? '#fff' : '#94a3b8',
                  backgroundColor: selectedCategory === tab.id ? '#23293a' : 'transparent',
                  border: selectedCategory === tab.id ? '1px solid #374151' : '1px solid transparent',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div style={{
            position: 'relative',
            width: '260px',
            display: 'flex',
            alignItems: 'center'
          }}>
            <Search size={14} color="#6b7280" style={{ position: 'absolute', left: '10px' }} />
            <input
              type="text"
              placeholder="Search skills, formats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: '#161a26',
                border: '1px solid #282f44',
                borderRadius: '8px',
                padding: '6px 10px 6px 30px',
                fontSize: '12px',
                color: '#fff',
                outline: 'none'
              }}
            />
          </div>
        </div>

        {/* Main Content Area */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Left Column: Skill List */}
          <div style={{
            width: '360px',
            borderRight: '1px solid #1f2433',
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            backgroundColor: '#0c0f17'
          }}>
            {loading ? (
              <div style={{ padding: '30px', textAlign: 'center', color: '#6b7280', fontSize: '13px' }}>
                Loading skills directory...
              </div>
            ) : filteredSkills.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: '#6b7280', fontSize: '13px' }}>
                No matching skills found.
              </div>
            ) : (
              filteredSkills.map(skill => {
                const isSelected = activeSkillId === skill.id;
                const isCustom = !skill.is_system;
                const fmtUpper = (skill.format || 'DOC').toUpperCase();

                let fmtBg = '#1e293b';
                let fmtColor = '#94a3b8';
                if (fmtUpper === 'PDF') { fmtBg = 'rgba(239, 68, 68, 0.15)'; fmtColor = '#ef4444'; }
                else if (fmtUpper === 'DOCX') { fmtBg = 'rgba(59, 130, 246, 0.15)'; fmtColor = '#60a5fa'; }
                else if (fmtUpper === 'XLSX') { fmtBg = 'rgba(16, 185, 129, 0.15)'; fmtColor = '#34d399'; }
                else if (fmtUpper === 'PPTX') { fmtBg = 'rgba(249, 115, 22, 0.15)'; fmtColor = '#fb923c'; }

                return (
                  <div
                    key={skill.id}
                    onClick={() => setActiveSkillId(skill.id)}
                    style={{
                      padding: '12px 14px',
                      borderRadius: '10px',
                      backgroundColor: isSelected ? '#172554' : '#121622',
                      border: isSelected ? '1px solid #1d4ed8' : '1px solid #1e2436',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <span style={{
                        fontSize: '13px',
                        fontWeight: '600',
                        color: isSelected ? '#fff' : '#e2e8f0',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {skill.title}
                      </span>
                      <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                        <span style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          backgroundColor: fmtBg,
                          color: fmtColor,
                          letterSpacing: '0.04em'
                        }}>
                          {fmtUpper}
                        </span>
                        {isCustom ? (
                          <span style={{
                            fontSize: '9px',
                            fontWeight: '600',
                            padding: '1px 5px',
                            borderRadius: '4px',
                            backgroundColor: 'rgba(168, 85, 247, 0.15)',
                            color: '#c084fc'
                          }}>
                            CUSTOM
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <p style={{
                      fontSize: '11px',
                      color: '#8b949e',
                      margin: 0,
                      lineHeight: '1.4',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                    }}>
                      {skill.description || 'Custom agent skill specification.'}
                    </p>
                  </div>
                );
              })
            )}
          </div>

          {/* Right Column: Skill Detail & Markdown Preview */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            backgroundColor: '#11141d'
          }}>
            {activeSkillDetail ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* Detail Header */}
                <div style={{
                  padding: '20px 24px',
                  borderBottom: '1px solid #1f2433',
                  backgroundColor: '#131722',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '16px'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                      <h3 style={{ fontSize: '20px', fontWeight: '600', color: '#fff', margin: 0 }}>
                        {activeSkillDetail.title}
                      </h3>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        backgroundColor: '#1e293b',
                        color: '#94a3b8'
                      }}>
                        {activeSkillDetail.format.toUpperCase()}
                      </span>
                      <span style={{
                        fontSize: '11px',
                        color: '#6b7280'
                      }}>
                        ID: {activeSkillDetail.name}
                      </span>
                    </div>
                    <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0, lineHeight: '1.5' }}>
                      {activeSkillDetail.description}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                    <button
                      onClick={() => handleUseSkill(activeSkillDetail)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        backgroundColor: '#1d4ed8',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '8px',
                        padding: '8px 14px',
                        fontSize: '12px',
                        fontWeight: '600',
                        cursor: 'pointer'
                      }}
                      title="Insert prompt template in Chat"
                    >
                      <Play size={14} fill="#fff" />
                      <span>Use in Chat</span>
                    </button>

                    {!activeSkillDetail.is_system && (
                      <>
                        <button
                          onClick={() => handleOpenEdit(activeSkillDetail)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: '#1f2433',
                            color: '#94a3b8',
                            border: '1px solid #2d354b',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          <Edit3 size={14} />
                          <span>Edit</span>
                        </button>
                        <button
                          onClick={() => handleDeleteSkill(activeSkillDetail.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            color: '#ef4444',
                            border: '1px solid rgba(239, 68, 68, 0.2)',
                            borderRadius: '8px',
                            padding: '8px 12px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Markdown Guidelines View */}
                <div style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '24px',
                  color: '#cbd5e1',
                  fontSize: '13px',
                  lineHeight: '1.7'
                }} className="markdown-body">
                  {detailLoading ? (
                    <div style={{ color: '#6b7280', textAlign: 'center', padding: '40px' }}>
                      Loading skill specification...
                    </div>
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {activeSkillDetail.content || 'No content found.'}
                    </ReactMarkdown>
                  )}
                </div>
              </div>
            ) : (
              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6b7280',
                gap: '12px'
              }}>
                <FileText size={48} strokeWidth={1} />
                <span>Select a skill from the directory to inspect its guidelines.</span>
              </div>
            )}
          </div>
        </div>

        {/* Create / Edit Skill Modal Sub-Dialog */}
        {isEditing && (
          <div style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            padding: '20px'
          }}>
            <div style={{
              backgroundColor: '#131722',
              border: '1px solid #2d354b',
              borderRadius: '14px',
              width: '100%',
              maxWidth: '850px',
              height: '80vh',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              boxShadow: '0 24px 60px rgba(0,0,0,0.8)'
            }}>
              {/* Sub-dialog header */}
              <div style={{
                padding: '16px 20px',
                borderBottom: '1px solid #23293d',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: '#0e111a'
              }}>
                <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#fff', margin: 0 }}>
                  {editingSkillId ? 'Edit Custom Skill' : 'Create Custom Skill'}
                </h3>
                <button
                  onClick={() => setIsEditing(false)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                >
                  <X size={18} />
                </button>
              </div>

              {/* Form Content */}
              <form onSubmit={handleSaveSkill} style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {formError && (
                    <div style={{
                      padding: '10px 14px',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid #ef4444',
                      borderRadius: '8px',
                      color: '#fca5a5',
                      fontSize: '12px'
                    }}>
                      {formError}
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#94a3b8', marginBottom: '4px' }}>
                        Skill Identifier (Name)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. invoice_pdf"
                        value={formName}
                        onChange={(e) => setFormName(e.target.value)}
                        disabled={!!editingSkillId}
                        style={{
                          width: '100%',
                          backgroundColor: '#191f2e',
                          border: '1px solid #2a3349',
                          borderRadius: '8px',
                          padding: '8px 12px',
                          color: '#fff',
                          fontSize: '13px',
                          outline: 'none'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#94a3b8', marginBottom: '4px' }}>
                        Display Title
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Corporate Invoice Generator"
                        value={formTitle}
                        onChange={(e) => setFormTitle(e.target.value)}
                        style={{
                          width: '100%',
                          backgroundColor: '#191f2e',
                          border: '1px solid #2a3349',
                          borderRadius: '8px',
                          padding: '8px 12px',
                          color: '#fff',
                          fontSize: '13px',
                          outline: 'none'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#94a3b8', marginBottom: '4px' }}>
                        Category
                      </label>
                      <select
                        value={formCategory}
                        onChange={(e) => setFormCategory(e.target.value)}
                        style={{
                          width: '100%',
                          backgroundColor: '#191f2e',
                          border: '1px solid #2a3349',
                          borderRadius: '8px',
                          padding: '8px 12px',
                          color: '#fff',
                          fontSize: '13px',
                          outline: 'none'
                        }}
                      >
                        <option value="document">Document Generation</option>
                        <option value="coding">Coding & Scripting</option>
                        <option value="ai-system">AI System / RAG</option>
                        <option value="design">Creative & Design</option>
                        <option value="custom">Custom Workflow</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#94a3b8', marginBottom: '4px' }}>
                        Target Deliverable Format
                      </label>
                      <select
                        value={formFormat}
                        onChange={(e) => setFormFormat(e.target.value)}
                        style={{
                          width: '100%',
                          backgroundColor: '#191f2e',
                          border: '1px solid #2a3349',
                          borderRadius: '8px',
                          padding: '8px 12px',
                          color: '#fff',
                          fontSize: '13px',
                          outline: 'none'
                        }}
                      >
                        <option value="pdf">PDF (.pdf)</option>
                        <option value="docx">Word Document (.docx)</option>
                        <option value="xlsx">Excel Spreadsheet (.xlsx)</option>
                        <option value="pptx">PowerPoint Presentation (.pptx)</option>
                        <option value="html">Web Page / Report (.html)</option>
                        <option value="csv">Tabular Data (.csv)</option>
                        <option value="python">Python Code (.py)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#94a3b8', marginBottom: '4px' }}>
                      Skill Description (Helps the model decide when to load this skill)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Instructions for rendering professional invoices with ReportLab tables."
                      value={formDescription}
                      onChange={(e) => setFormDescription(e.target.value)}
                      style={{
                        width: '100%',
                        backgroundColor: '#191f2e',
                        border: '1px solid #2a3349',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        color: '#fff',
                        fontSize: '13px',
                        outline: 'none'
                      }}
                    />
                  </div>

                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: '#94a3b8', marginBottom: '4px' }}>
                      Skill Guidelines & Code Blueprint (Markdown with Python template)
                    </label>
                    <textarea
                      value={formContent}
                      onChange={(e) => setFormContent(e.target.value)}
                      style={{
                        flex: 1,
                        minHeight: '220px',
                        backgroundColor: '#141824',
                        border: '1px solid #2a3349',
                        borderRadius: '8px',
                        padding: '12px',
                        color: '#e2e8f0',
                        fontSize: '12px',
                        fontFamily: 'monospace',
                        lineHeight: '1.5',
                        resize: 'none',
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>

                {/* Sub-dialog Footer */}
                <div style={{
                  padding: '14px 20px',
                  borderTop: '1px solid #23293d',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  gap: '10px',
                  backgroundColor: '#0e111a'
                }}>
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: 'transparent',
                      border: '1px solid #2d354b',
                      borderRadius: '8px',
                      color: '#94a3b8',
                      fontSize: '13px',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={formSubmitting}
                    style={{
                      padding: '8px 18px',
                      backgroundColor: '#1d4ed8',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '13px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      opacity: formSubmitting ? 0.7 : 1
                    }}
                  >
                    {formSubmitting ? 'Saving...' : 'Save Skill'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
