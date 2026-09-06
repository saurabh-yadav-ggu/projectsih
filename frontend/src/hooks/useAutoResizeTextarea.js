import { useEffect } from 'react';

export function useAutoResizeTextarea(textareaRef, value) {
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    const scrollHeight = textarea.scrollHeight;
    
    // Max height corresponding to ~8 lines (~180px)
    const maxHeight = 180;
    const minHeight = 44;

    if (scrollHeight > maxHeight) {
      textarea.style.height = `${maxHeight}px`;
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.height = `${Math.max(scrollHeight, minHeight)}px`;
      textarea.style.overflowY = 'hidden';
    }
  }, [textareaRef, value]);
}
