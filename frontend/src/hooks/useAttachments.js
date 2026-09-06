import { useState, useEffect, useCallback, useRef } from 'react';

export function formatBytes(bytes, decimals = 1) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function detectAttachmentType(file) {
  const mime = file.type || '';
  const name = file.name.toLowerCase();
  
  if (mime.startsWith('image/') || /\.(png|jpg|jpeg|webp|gif|svg)$/i.test(name)) {
    return 'image';
  }
  if (mime === 'application/pdf' || name.endsWith('.pdf')) {
    return 'pdf';
  }
  return 'document';
}

export function useAttachments() {
  const [attachments, setAttachments] = useState([]);
  const attachmentsRef = useRef(attachments);

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  // Revoke object URLs on component unmount
  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach(att => {
        if (att.previewUrl) {
          URL.revokeObjectURL(att.previewUrl);
        }
      });
    };
  }, []);

  const addFiles = useCallback((files) => {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    const newAttachments = fileArray.map(file => {
      const type = detectAttachmentType(file);
      const id = typeof crypto !== 'undefined' && crypto.randomUUID 
        ? crypto.randomUUID() 
        : `att-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      let previewUrl = null;
      if (type === 'image') {
        try {
          previewUrl = URL.createObjectURL(file);
        } catch (e) {
          console.error('Failed to create object URL:', e);
        }
      }

      return {
        id,
        file,
        name: file.name,
        size: file.size,
        formattedSize: formatBytes(file.size),
        type,
        previewUrl,
        status: 'ready', // 'pending' | 'uploading' | 'processing' | 'ready' | 'error'
        progress: 100,
        errorMessage: null
      };
    });

    setAttachments(prev => {
      // Filter out exact duplicate file instances if needed
      const existingNames = new Set(prev.map(a => `${a.name}-${a.size}`));
      const uniqueNew = newAttachments.filter(a => !existingNames.has(`${a.name}-${a.size}`));
      return [...prev, ...uniqueNew];
    });
  }, []);

  const removeAttachment = useCallback((id) => {
    setAttachments(prev => {
      const target = prev.find(a => a.id === id);
      if (target && target.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter(a => a.id !== id);
    });
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments(prev => {
      prev.forEach(att => {
        if (att.previewUrl) {
          URL.revokeObjectURL(att.previewUrl);
        }
      });
      return [];
    });
  }, []);

  const updateAttachment = useCallback((id, updates) => {
    setAttachments(prev => prev.map(att => att.id === id ? { ...att, ...updates } : att));
  }, []);

  return {
    attachments,
    setAttachments,
    addFiles,
    removeAttachment,
    clearAttachments,
    updateAttachment
  };
}
