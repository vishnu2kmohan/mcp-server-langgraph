/**
 * useMediaQuery Hook
 *
 * A responsive design hook for detecting media query changes.
 * Provides:
 * - useMediaQuery: Low-level hook for custom media queries
 * - useBreakpoint: High-level hook with common breakpoint helpers
 *
 * Breakpoints follow Tailwind CSS conventions:
 * - Mobile: < 640px (sm)
 * - Tablet: 640px - 1023px (sm to lg)
 * - Desktop: >= 1024px (lg+)
 */

import { useState, useEffect, useCallback, useMemo } from "react";

// =============================================================================
// Types
// =============================================================================

export type Breakpoint = "mobile" | "tablet" | "desktop";

export interface BreakpointState {
  /** Current breakpoint name */
  breakpoint: Breakpoint;
  /** True when screen width < 640px */
  isMobile: boolean;
  /** True when screen width 640px - 1023px */
  isTablet: boolean;
  /** True when screen width >= 1024px */
  isDesktop: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const BREAKPOINTS = {
  mobile: "(max-width: 639px)",
  tablet: "(min-width: 640px) and (max-width: 1023px)",
  desktop: "(min-width: 1024px)",
} as const;

// =============================================================================
// useMediaQuery Hook
// =============================================================================

/**
 * Low-level hook for matching custom media queries
 *
 * @param query - CSS media query string (e.g., "(min-width: 768px)")
 * @returns boolean indicating if the media query matches
 *
 * @example
 * const isLargeScreen = useMediaQuery("(min-width: 1024px)");
 */
export function useMediaQuery(query: string): boolean {
  // Initialize with server-safe default (false)
  const [matches, setMatches] = useState<boolean>(() => {
    // Check if window is available (client-side)
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia(query).matches;
    }
    return false;
  });

  // Memoized change handler
  const handleChange = useCallback((event: MediaQueryListEvent) => {
    setMatches(event.matches);
  }, []);

  useEffect(() => {
    // Guard for SSR
    if (typeof window === "undefined" || !window.matchMedia) {
      return;
    }

    const mediaQueryList = window.matchMedia(query);

    // Set initial value
    setMatches(mediaQueryList.matches);

    // Add listener for changes
    mediaQueryList.addEventListener("change", handleChange);

    // Cleanup
    return () => {
      mediaQueryList.removeEventListener("change", handleChange);
    };
  }, [query, handleChange]);

  return matches;
}

// =============================================================================
// useBreakpoint Hook
// =============================================================================

/**
 * High-level hook providing common breakpoint helpers
 *
 * @returns BreakpointState with boolean flags and current breakpoint name
 *
 * @example
 * const { isMobile, isDesktop, breakpoint } = useBreakpoint();
 * if (isMobile) {
 *   // Render mobile-specific UI
 * }
 */
export function useBreakpoint(): BreakpointState {
  const isMobile = useMediaQuery(BREAKPOINTS.mobile);
  const isTablet = useMediaQuery(BREAKPOINTS.tablet);
  const isDesktop = useMediaQuery(BREAKPOINTS.desktop);

  // Determine current breakpoint name
  const breakpoint: Breakpoint = useMemo(() => {
    if (isMobile) return "mobile";
    if (isTablet) return "tablet";
    return "desktop";
  }, [isMobile, isTablet]);

  return useMemo(
    () => ({
      breakpoint,
      isMobile,
      isTablet,
      isDesktop,
    }),
    [breakpoint, isMobile, isTablet, isDesktop],
  );
}

// =============================================================================
// Exports
// =============================================================================

export default useMediaQuery;
