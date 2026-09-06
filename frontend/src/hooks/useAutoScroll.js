import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * useAutoScroll Hook
 * ChatGPT-grade smart scrolling behavior:
 * - Automatically scrolls to bottom during streaming ONLY when user is already near bottom.
 * - Pauses auto-scroll immediately if user scrolls upward.
 * - Displays a "Jump to latest" indicator when scrolled away from bottom.
 * - Uses requestAnimationFrame to throttle scroll updates and avoid layout thrashing.
 * - Handles dynamic element expansion (code blocks, markdown, images).
 */
export function useAutoScroll({ threshold = 180 } = {}) {
  const containerRef = useRef(null);
  const bottomRef = useRef(null);
  const autoScrollEnabledRef = useRef(true);
  const rafIdRef = useRef(null);
  const lastScrollTopRef = useRef(0);
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);

  // Check if scroll position is within threshold from the bottom
  const isNearBottom = useCallback((margin = threshold) => {
    const el = containerRef.current;
    if (!el) return true;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    return distanceToBottom <= margin;
  }, [threshold]);

  // Perform throttled scroll to bottom
  const scrollToBottom = useCallback(({ smooth = false, force = false } = {}) => {
    if (!force && !autoScrollEnabledRef.current) return;

    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }

    rafIdRef.current = requestAnimationFrame(() => {
      const el = containerRef.current;
      if (!el) return;

      if (smooth) {
        el.scrollTo({
          top: el.scrollHeight,
          behavior: 'smooth'
        });
      } else {
        el.scrollTop = el.scrollHeight;
      }
    });
  }, []);

  // Handle user scroll interactions
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;

    const currentScrollTop = el.scrollTop;
    const isScrollingDown = currentScrollTop > lastScrollTopRef.current;
    lastScrollTopRef.current = currentScrollTop;

    const near = isNearBottom();
    if (near || (isScrollingDown && isNearBottom(threshold * 1.5))) {
      autoScrollEnabledRef.current = true;
      setShowJumpToLatest(false);
    } else {
      autoScrollEnabledRef.current = false;
      setShowJumpToLatest(true);
    }
  }, [isNearBottom, threshold]);

  // Floating button click to jump back to newest message
  const jumpToLatest = useCallback(() => {
    autoScrollEnabledRef.current = true;
    setShowJumpToLatest(false);
    scrollToBottom({ smooth: true, force: true });
  }, [scrollToBottom]);

  // Clean up animation frames on unmount
  useEffect(() => {
    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  return {
    containerRef,
    bottomRef,
    showJumpToLatest,
    isNearBottom,
    scrollToBottom,
    handleScroll,
    jumpToLatest,
    autoScrollEnabledRef
  };
}

export default useAutoScroll;
