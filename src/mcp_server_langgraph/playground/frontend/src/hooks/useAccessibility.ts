/**
 * useAccessibility Hook
 *
 * Provides accessibility utilities including focus trapping,
 * screen reader announcements, and keyboard navigation.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Focus trap hook for modal dialogs
 */
export function useFocusTrap(
  containerRef: React.RefObject<HTMLElement | null>,
  enabled: boolean
): void {
  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    // Focus first element on mount
    firstFocusable?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable?.focus();
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [containerRef, enabled]);
}

/**
 * Screen reader announcement hook
 */
export function useAnnounce(
  politeness: 'polite' | 'assertive' = 'polite'
): { announce: (message: string) => void } {
  const liveRegionRef = useRef<HTMLDivElement | null>(null);

  // Create live region on mount
  useEffect(() => {
    const liveRegion = document.createElement('div');
    liveRegion.setAttribute('aria-live', politeness);
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.setAttribute('role', 'status');
    liveRegion.style.cssText = `
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    `;
    document.body.appendChild(liveRegion);
    liveRegionRef.current = liveRegion;

    return () => {
      document.body.removeChild(liveRegion);
    };
  }, [politeness]);

  const announce = useCallback((message: string) => {
    if (liveRegionRef.current) {
      liveRegionRef.current.textContent = message;

      // Clear after delay to allow re-announcement of same message
      setTimeout(() => {
        if (liveRegionRef.current) {
          liveRegionRef.current.textContent = '';
        }
      }, 1000);
    }
  }, []);

  return { announce };
}

/**
 * Combined accessibility hook
 */
export function useAccessibility(): {
  announce: (message: string) => void;
  focusTrapRef: React.RefObject<HTMLElement | null>;
  isFocusTrapEnabled: boolean;
  enableFocusTrap: () => void;
  disableFocusTrap: () => void;
} {
  const focusTrapRef = useRef<HTMLElement | null>(null);
  const [isFocusTrapEnabled, setIsFocusTrapEnabled] = useState(false);
  const { announce } = useAnnounce();

  useFocusTrap(focusTrapRef, isFocusTrapEnabled);

  const enableFocusTrap = useCallback(() => {
    setIsFocusTrapEnabled(true);
  }, []);

  const disableFocusTrap = useCallback(() => {
    setIsFocusTrapEnabled(false);
  }, []);

  return {
    announce,
    focusTrapRef,
    isFocusTrapEnabled,
    enableFocusTrap,
    disableFocusTrap,
  };
}

/**
 * Keyboard navigation hook for lists
 */
export function useKeyboardNavigation<T>(
  items: T[],
  onSelect: (item: T, index: number) => void
): {
  activeIndex: number;
  setActiveIndex: (index: number) => void;
  handleKeyDown: (e: React.KeyboardEvent) => void;
} {
  const [activeIndex, setActiveIndex] = useState(0);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setActiveIndex((prev) => Math.min(prev + 1, items.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setActiveIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Home':
          e.preventDefault();
          setActiveIndex(0);
          break;
        case 'End':
          e.preventDefault();
          setActiveIndex(items.length - 1);
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (items[activeIndex]) {
            onSelect(items[activeIndex], activeIndex);
          }
          break;
      }
    },
    [items, activeIndex, onSelect]
  );

  return {
    activeIndex,
    setActiveIndex,
    handleKeyDown,
  };
}

/**
 * Skip link target hook
 */
export function useSkipLink(targetId: string): {
  skipLinkProps: {
    href: string;
    onClick: (e: React.MouseEvent) => void;
  };
  targetProps: {
    id: string;
    tabIndex: number;
  };
} {
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const target = document.getElementById(targetId);
      if (target) {
        target.focus();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [targetId]
  );

  return {
    skipLinkProps: {
      href: `#${targetId}`,
      onClick: handleClick,
    },
    targetProps: {
      id: targetId,
      tabIndex: -1,
    },
  };
}
