/**
 * Unified Accessibility Hooks
 *
 * WCAG 2.1 AA compliance utilities including:
 * - Focus trap for modals/dialogs
 * - Screen reader announcements (aria-live)
 * - Skip-to-content link
 * - Motion and contrast preference detection
 *
 * @module @mcp-server-langgraph/shared-frontend/hooks
 */

import { useRef, useState, useCallback, useEffect, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface UseFocusTrapResult {
  /**
   * Ref to attach to the container element
   */
  focusTrapRef: React.RefObject<HTMLElement>;

  /**
   * Activate the focus trap
   */
  activate: () => void;

  /**
   * Deactivate the focus trap
   */
  deactivate: () => void;

  /**
   * Whether the focus trap is currently active
   */
  isActive: boolean;
}

export interface UseAnnounceResult {
  /**
   * Announce a message to screen readers (polite by default)
   */
  announce: (message: string, politeness?: 'polite' | 'assertive') => void;

  /**
   * Announce with polite politeness
   */
  announcePolite: (message: string) => void;

  /**
   * Announce with assertive politeness (for urgent messages)
   */
  announceAssertive: (message: string) => void;
}

export interface UseSkipLinkResult {
  /**
   * Props to spread on the skip link element
   */
  skipLinkProps: {
    href: string;
    onClick: (e: React.MouseEvent) => void;
  };

  /**
   * Props to spread on the target element
   */
  targetProps: {
    id: string;
    tabIndex: number;
  };
}

export interface UseAccessibilityOptions {
  /**
   * ID for skip-to-content target
   */
  skipLinkTargetId?: string;
}

export interface UseAccessibilityResult {
  // Focus trap
  focusTrapRef: React.RefObject<HTMLElement>;
  activateFocusTrap: () => void;
  deactivateFocusTrap: () => void;
  isFocusTrapActive: boolean;

  // Announcements
  announce: (message: string, politeness?: 'polite' | 'assertive') => void;
  announcePolite: (message: string) => void;
  announceAssertive: (message: string) => void;

  // Skip link
  skipLinkProps: UseSkipLinkResult['skipLinkProps'];
  skipLinkTargetProps: UseSkipLinkResult['targetProps'];

  // Preferences
  prefersReducedMotion: boolean;
  prefersHighContrast: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

const ANNOUNCEMENT_TIMEOUT = 1000;

// =============================================================================
// useFocusTrap Hook
// =============================================================================

export function useFocusTrap(): UseFocusTrapResult {
  const focusTrapRef = useRef<HTMLElement>(null);
  const [isActive, setIsActive] = useState(false);
  const previousActiveElement = useRef<Element | null>(null);

  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!focusTrapRef.current) return [];
    return Array.from(
      focusTrapRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    );
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key !== 'Tab' || !isActive) return;

      const focusableElements = getFocusableElements();
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey) {
        // Shift+Tab: if on first element, go to last
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: if on last element, go to first
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    },
    [isActive, getFocusableElements]
  );

  const activate = useCallback(() => {
    previousActiveElement.current = document.activeElement;
    setIsActive(true);

    // Focus first focusable element
    const focusableElements = getFocusableElements();
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }
  }, [getFocusableElements]);

  const deactivate = useCallback(() => {
    setIsActive(false);

    // Restore focus to previous element
    if (previousActiveElement.current instanceof HTMLElement) {
      previousActiveElement.current.focus();
    }
  }, []);

  useEffect(() => {
    if (!isActive) return;

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isActive, handleKeyDown]);

  return {
    focusTrapRef,
    activate,
    deactivate,
    isActive,
  };
}

// =============================================================================
// useAnnounce Hook
// =============================================================================

export function useAnnounce(): UseAnnounceResult {
  const liveRegionRef = useRef<HTMLDivElement | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Create or get live region
  const getOrCreateLiveRegion = useCallback(
    (politeness: 'polite' | 'assertive'): HTMLDivElement => {
      // Check for existing region with same politeness
      let region = document.querySelector<HTMLDivElement>(
        `[data-announce-region="${politeness}"]`
      );

      if (!region) {
        region = document.createElement('div');
        region.setAttribute('aria-live', politeness);
        region.setAttribute('aria-atomic', 'true');
        region.setAttribute('data-announce-region', politeness);
        region.style.cssText = `
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
        document.body.appendChild(region);
      }

      return region;
    },
    []
  );

  const announce = useCallback(
    (message: string, politeness: 'polite' | 'assertive' = 'polite') => {
      const region = getOrCreateLiveRegion(politeness);
      liveRegionRef.current = region;

      // Clear previous timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Set the message
      region.textContent = message;

      // Clear after timeout
      timeoutRef.current = setTimeout(() => {
        region.textContent = '';
      }, ANNOUNCEMENT_TIMEOUT);
    },
    [getOrCreateLiveRegion]
  );

  const announcePolite = useCallback(
    (message: string) => {
      announce(message, 'polite');
    },
    [announce]
  );

  const announceAssertive = useCallback(
    (message: string) => {
      announce(message, 'assertive');
    },
    [announce]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    announce,
    announcePolite,
    announceAssertive,
  };
}

// =============================================================================
// useSkipLink Hook
// =============================================================================

export function useSkipLink(targetId: string): UseSkipLinkResult {
  const onClick = useCallback(
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
      onClick,
    },
    targetProps: {
      id: targetId,
      tabIndex: -1,
    },
  };
}

// =============================================================================
// useAccessibility Combined Hook
// =============================================================================

export function useAccessibility(
  options: UseAccessibilityOptions = {}
): UseAccessibilityResult {
  const { skipLinkTargetId = 'main-content' } = options;

  // Focus trap
  const {
    focusTrapRef,
    activate: activateFocusTrap,
    deactivate: deactivateFocusTrap,
    isActive: isFocusTrapActive,
  } = useFocusTrap();

  // Announcements
  const { announce, announcePolite, announceAssertive } = useAnnounce();

  // Skip link
  const { skipLinkProps, targetProps: skipLinkTargetProps } =
    useSkipLink(skipLinkTargetId);

  // Preference detection
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  });

  const [prefersHighContrast, setPrefersHighContrast] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-contrast: more)').matches ?? false;
  });

  // Listen for preference changes
  useEffect(() => {
    const motionQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const contrastQuery = window.matchMedia?.('(prefers-contrast: more)');

    const handleMotionChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    const handleContrastChange = (e: MediaQueryListEvent) => {
      setPrefersHighContrast(e.matches);
    };

    motionQuery?.addEventListener('change', handleMotionChange);
    contrastQuery?.addEventListener('change', handleContrastChange);

    return () => {
      motionQuery?.removeEventListener('change', handleMotionChange);
      contrastQuery?.removeEventListener('change', handleContrastChange);
    };
  }, []);

  return useMemo(
    () => ({
      // Focus trap
      focusTrapRef,
      activateFocusTrap,
      deactivateFocusTrap,
      isFocusTrapActive,

      // Announcements
      announce,
      announcePolite,
      announceAssertive,

      // Skip link
      skipLinkProps,
      skipLinkTargetProps,

      // Preferences
      prefersReducedMotion,
      prefersHighContrast,
    }),
    [
      focusTrapRef,
      activateFocusTrap,
      deactivateFocusTrap,
      isFocusTrapActive,
      announce,
      announcePolite,
      announceAssertive,
      skipLinkProps,
      skipLinkTargetProps,
      prefersReducedMotion,
      prefersHighContrast,
    ]
  );
}

export default useAccessibility;
