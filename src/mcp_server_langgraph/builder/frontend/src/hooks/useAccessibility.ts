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

import { useMemo } from 'react';

// Re-export from shared library
export {
  useFocusTrap,
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
