/**
 * useAccessibility Hook
 *
 * Re-exports from shared frontend library with backward-compatible API.
 * See: src/mcp_server_langgraph/shared/frontend/src/hooks/useAccessibility.ts
 *
 * Provides accessibility utilities including focus trapping,
 * screen reader announcements, and keyboard navigation.
 *
 * @deprecated Import from '@mcp-server-langgraph/shared-frontend' instead
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';

// Re-export base types from shared library
export {
  useSkipLink,
  type UseSkipLinkResult,
  type UseAccessibilityOptions,
} from '../../../../shared/frontend/src/hooks/useAccessibility';

// Import shared implementations
import {
  useAnnounce as useSharedAnnounce,
  useFocusTrap as useSharedFocusTrap,
  useAccessibility as useSharedAccessibility,
} from '../../../../shared/frontend/src/hooks/useAccessibility';

// ==============================================================================
// useFocusTrap - Backward-compatible wrapper
// ==============================================================================

/**
 * Focus trap hook for modal dialogs
 * @deprecated Use useFocusTrap from shared instead with different API
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
        if (document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable?.focus();
        }
      } else {
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

// ==============================================================================
// useAnnounce - Backward-compatible wrapper
// ==============================================================================

/**
 * Screen reader announcement hook
 */
export function useAnnounce(
  politeness: 'polite' | 'assertive' = 'polite'
): { announce: (message: string) => void } {
  const shared = useSharedAnnounce();

  const announce = useCallback(
    (message: string) => {
      shared.announce(message, politeness);
    },
    [shared, politeness]
  );

  return { announce };
}

// ==============================================================================
// useAccessibility - Combined utilities (backward-compatible wrapper)
// ==============================================================================

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
  const shared = useSharedAnnounce();

  useFocusTrap(focusTrapRef, isFocusTrapEnabled);

  const enableFocusTrap = useCallback(() => {
    setIsFocusTrapEnabled(true);
  }, []);

  const disableFocusTrap = useCallback(() => {
    setIsFocusTrapEnabled(false);
  }, []);

  const announce = useCallback(
    (message: string) => {
      shared.announce(message, 'polite');
    },
    [shared]
  );

  return {
    announce,
    focusTrapRef,
    isFocusTrapEnabled,
    enableFocusTrap,
    disableFocusTrap,
  };
}

// ==============================================================================
// useKeyboardNavigation - Playground-specific (not in shared)
// ==============================================================================

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
