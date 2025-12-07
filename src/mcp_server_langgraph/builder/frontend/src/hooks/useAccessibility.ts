/**
 * Accessibility Utilities Hooks
 *
 * WCAG 2.1 AA Compliance utilities:
 * - useAnnounce: Screen reader announcements via live regions
 * - useFocusTrap: Focus management for modals
 * - useSkipToContent: Skip-to-content navigation
 * - useAccessibility: Combined utilities
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';

// ==============================================================================
// useAnnounce - Screen Reader Announcements
// ==============================================================================

interface AnnounceResult {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
  announcePolite: (message: string) => void;
  announceAssertive: (message: string) => void;
}

const CLEAR_DELAY = 1000;

export function useAnnounce(): AnnounceResult {
  const politeRef = useRef<HTMLDivElement | null>(null);
  const assertiveRef = useRef<HTMLDivElement | null>(null);
  const clearTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Create live regions on mount
  useEffect(() => {
    // Create polite live region
    const politeRegion = document.createElement('div');
    politeRegion.setAttribute('aria-live', 'polite');
    politeRegion.setAttribute('aria-atomic', 'true');
    politeRegion.setAttribute('data-announcer', 'polite');
    politeRegion.style.cssText = `
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
    document.body.appendChild(politeRegion);
    politeRef.current = politeRegion;

    // Create assertive live region
    const assertiveRegion = document.createElement('div');
    assertiveRegion.setAttribute('aria-live', 'assertive');
    assertiveRegion.setAttribute('aria-atomic', 'true');
    assertiveRegion.setAttribute('data-announcer', 'assertive');
    assertiveRegion.style.cssText = politeRegion.style.cssText;
    document.body.appendChild(assertiveRegion);
    assertiveRef.current = assertiveRegion;

    return () => {
      politeRegion.remove();
      assertiveRegion.remove();
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current);
      }
    };
  }, []);

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const region = priority === 'assertive' ? assertiveRef.current : politeRef.current;

    if (region) {
      // Clear previous timeout
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current);
      }

      // Set the message
      region.textContent = message;

      // Clear after delay
      clearTimeoutRef.current = setTimeout(() => {
        if (region) {
          region.textContent = '';
        }
      }, CLEAR_DELAY);
    }
  }, []);

  const announcePolite = useCallback((message: string) => {
    announce(message, 'polite');
  }, [announce]);

  const announceAssertive = useCallback((message: string) => {
    announce(message, 'assertive');
  }, [announce]);

  return {
    announce,
    announcePolite,
    announceAssertive,
  };
}

// ==============================================================================
// useFocusTrap - Modal Focus Management
// ==============================================================================

interface FocusTrapResult {
  containerRef: React.RefObject<HTMLElement>;
  isActive: boolean;
  activate: () => void;
  deactivate: () => void;
}

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

export function useFocusTrap(): FocusTrapResult {
  const containerRef = useRef<HTMLElement>(null);
  const [isActive, setIsActive] = useState(false);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const getFocusableElements = useCallback(() => {
    if (!containerRef.current) return [];
    return Array.from(containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS));
  }, []);

  const activate = useCallback(() => {
    // Store current focus to restore later
    previousFocusRef.current = document.activeElement as HTMLElement;
    setIsActive(true);

    // Focus first focusable element
    const focusable = getFocusableElements();
    if (focusable.length > 0) {
      focusable[0].focus();
    }
  }, [getFocusableElements]);

  const deactivate = useCallback(() => {
    setIsActive(false);

    // Restore previous focus
    if (previousFocusRef.current) {
      previousFocusRef.current.focus();
    }
  }, []);

  // Handle keyboard navigation
  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;

      const focusable = getFocusableElements();
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey) {
        // Shift+Tab: wrap from first to last
        if (document.activeElement === first) {
          event.preventDefault();
          last.focus();
        }
      } else {
        // Tab: wrap from last to first
        if (document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };

    const container = containerRef.current;
    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [isActive, getFocusableElements]);

  return {
    containerRef,
    isActive,
    activate,
    deactivate,
  };
}

// ==============================================================================
// useSkipToContent - Skip Navigation Link
// ==============================================================================

interface SkipToContentResult {
  skipLinkProps: {
    href: string;
    onClick: (event: React.MouseEvent) => void;
    className: string;
  };
}

export function useSkipToContent(targetId: string): SkipToContentResult {
  const handleClick = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault();
      const target = document.getElementById(targetId);
      if (target) {
        target.focus();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    },
    [targetId]
  );

  const skipLinkProps = useMemo(
    () => ({
      href: `#${targetId}`,
      onClick: handleClick,
      className: 'sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-white focus:text-blue-600 focus:underline',
    }),
    [targetId, handleClick]
  );

  return { skipLinkProps };
}

// ==============================================================================
// useAccessibility - Combined Utilities
// ==============================================================================

interface AccessibilityResult {
  announce: AnnounceResult;
  focusTrap: FocusTrapResult;
  prefersReducedMotion: boolean;
  prefersHighContrast: boolean;
}

export function useAccessibility(): AccessibilityResult {
  const announce = useAnnounce();
  const focusTrap = useFocusTrap();

  // Detect motion preference
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  });

  // Detect high contrast preference
  const [prefersHighContrast, setPrefersHighContrast] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-contrast: more)')?.matches ?? false;
  });

  // Listen for preference changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const motionQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const contrastQuery = window.matchMedia?.('(prefers-contrast: more)');

    const handleMotionChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    const handleContrastChange = (e: MediaQueryListEvent) => {
      setPrefersHighContrast(e.matches);
    };

    motionQuery?.addEventListener?.('change', handleMotionChange);
    contrastQuery?.addEventListener?.('change', handleContrastChange);

    return () => {
      motionQuery?.removeEventListener?.('change', handleMotionChange);
      contrastQuery?.removeEventListener?.('change', handleContrastChange);
    };
  }, []);

  return {
    announce,
    focusTrap,
    prefersReducedMotion,
    prefersHighContrast,
  };
}

export default useAccessibility;
