import { useCallback, useEffect, useRef, useState } from "react";

export interface UseAutoTailOptions {
  containerRef: React.RefObject<HTMLElement>;
  enabled?: boolean;
  onEntriesChange?: () => void;
}

export interface UseAutoTailReturn {
  isAutoTailing: boolean;
  toggle: () => void;
  scrollToBottom: () => void;
}

/**
 * Auto-tail helper that keeps a scrolling container pinned to bottom while the
 * user is at (or near) the bottom. If the user scrolls up, auto-tail pauses
 * until they scroll back to the end or toggle it on again.
 */
export function useAutoTail({
  containerRef,
  enabled = true,
  onEntriesChange,
}: UseAutoTailOptions): UseAutoTailReturn {
  const [isAutoTailing, setIsAutoTailing] = useState(enabled);
  const isAtBottomRef = useRef(true);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    isAtBottomRef.current = true;
  }, [containerRef]);

  // Track manual scrolls to pause auto-tail when user scrolls up
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onScroll = () => {
      const distanceFromBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight;
      const atBottom = distanceFromBottom <= 4; // small threshold
      isAtBottomRef.current = atBottom;
      if (!atBottom && isAutoTailing) {
        setIsAutoTailing(false);
      }
    };

    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [containerRef, isAutoTailing]);

  // Auto-scroll when new entries arrive and auto-tail is active
  useEffect(() => {
    if (!isAutoTailing) return;
    if (onEntriesChange) onEntriesChange();
    scrollToBottom();
  }, [isAutoTailing, onEntriesChange, scrollToBottom]);

  const toggle = useCallback(() => {
    setIsAutoTailing((prev) => {
      const next = !prev;
      if (next) {
        // Immediately jump to bottom when re-enabling
        scrollToBottom();
      }
      return next;
    });
  }, [scrollToBottom]);

  return {
    isAutoTailing,
    toggle,
    scrollToBottom,
  };
}

export default useAutoTail;
