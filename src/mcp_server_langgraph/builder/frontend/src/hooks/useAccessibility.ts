/**
 * Accessibility Utilities Hooks
 *
 * Re-exports from shared frontend library with backward-compatible API.
 * See: src/mcp_server_langgraph/shared/frontend/src/hooks/useAccessibility.ts
 *
 * WCAG 2.1 AA Compliance utilities:
 * - useAnnounce: Screen reader announcements via live regions
 * - useFocusTrap: Focus management for modals
 * - useSkipToContent: Skip-to-content navigation
 * - useAccessibility: Combined utilities
 *
 * @deprecated Import from '@mcp-server-langgraph/shared-frontend' instead
 */

import React, { useMemo, useEffect } from 'react';

// Re-export from shared library (note: useFocusTrap is overridden below)
export {
  useAnnounce,
  useSkipLink,
  type UseFocusTrapResult,
  type UseAnnounceResult,
  type UseSkipLinkResult,
} from '../../../../shared/frontend/src/hooks/useAccessibility';

// Import for wrapping
import {
  useFocusTrap as useSharedFocusTrap,
  useAnnounce as useSharedAnnounce,
  useAccessibility as useSharedAccessibility,
} from '../../../../shared/frontend/src/hooks/useAccessibility';

// Re-export the object-based useFocusTrap for tests that need it
// (the simple useFocusTrap(ref, enabled) below is for component use)
export { useFocusTrap as useFocusTrapObject } from '../../../../shared/frontend/src/hooks/useAccessibility';

// ==============================================================================
// Backward-compatible Type Aliases
// ==============================================================================

export interface AnnounceResult {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
  announcePolite: (message: string) => void;
  announceAssertive: (message: string) => void;
}

export interface FocusTrapResult {
  containerRef: React.RefObject<HTMLElement>;
  isActive: boolean;
  activate: () => void;
  deactivate: () => void;
}

export interface SkipToContentResult {
  skipLinkProps: {
    href: string;
    onClick: (event: React.MouseEvent) => void;
    className: string;
  };
}

export interface AccessibilityResult {
  announce: AnnounceResult;
  focusTrap: FocusTrapResult;
  prefersReducedMotion: boolean;
  prefersHighContrast: boolean;
}

// ==============================================================================
// useFocusTrap - Simple focus trap for modals (backward-compatible API)
// ==============================================================================

/**
 * Focus trap hook for modal dialogs
 * Traps focus within a container element when enabled.
 *
 * @param containerRef - Ref to the container element
 * @param enabled - Whether the focus trap is active
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
// useSkipToContent - Skip Navigation Link (backward-compatible alias)
// ==============================================================================

export function useSkipToContent(targetId: string): SkipToContentResult {
  const shared = useSharedAccessibility({ skipLinkTargetId: targetId });

  return useMemo(
    () => ({
      skipLinkProps: {
        href: shared.skipLinkProps.href,
        onClick: shared.skipLinkProps.onClick,
        className:
          'sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-white focus:text-blue-600 focus:underline',
      },
    }),
    [shared.skipLinkProps]
  );
}

// ==============================================================================
// useAccessibility - Combined Utilities (backward-compatible wrapper)
// ==============================================================================

export function useAccessibility(): AccessibilityResult {
  const focusTrapHook = useSharedFocusTrap();
  const announceHook = useSharedAnnounce();
  const shared = useSharedAccessibility();

  return useMemo(
    () => ({
      announce: {
        announce: announceHook.announce,
        announcePolite: announceHook.announcePolite,
        announceAssertive: announceHook.announceAssertive,
      },
      focusTrap: {
        containerRef: focusTrapHook.focusTrapRef,
        isActive: focusTrapHook.isActive,
        activate: focusTrapHook.activate,
        deactivate: focusTrapHook.deactivate,
      },
      prefersReducedMotion: shared.prefersReducedMotion,
      prefersHighContrast: shared.prefersHighContrast,
    }),
    [focusTrapHook, announceHook, shared]
  );
}

export default useAccessibility;
