/**
 * useMobileOptimizations Hook
 *
 * Provides mobile optimization utilities and device detection.
 * Features:
 * - Device type detection (mobile/tablet/desktop)
 * - Touch support detection
 * - Viewport dimensions and orientation
 * - Responsive breakpoint detection
 * - Safe area insets
 * - Virtual keyboard detection
 * - Reduced motion preference
 * - PWA standalone mode detection
 */

import { useState, useEffect, useMemo, useCallback } from "react";

// ==============================================================================
// Types
// ==============================================================================

export interface SafeAreaInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export type Breakpoint = "sm" | "md" | "lg" | "xl" | "2xl";

export interface MobileOptimizationsState {
  /** Is the device a mobile phone */
  isMobile: boolean;
  /** Is the device a tablet */
  isTablet: boolean;
  /** Is the device a desktop */
  isDesktop: boolean;
  /** Does the device support touch */
  hasTouch: boolean;
  /** Current responsive breakpoint */
  breakpoint: Breakpoint;
  /** Viewport width in pixels */
  viewportWidth: number;
  /** Viewport height in pixels */
  viewportHeight: number;
  /** Is device in portrait orientation */
  isPortrait: boolean;
  /** Is device in landscape orientation */
  isLandscape: boolean;
  /** Safe area insets for notched devices */
  safeAreaInsets: SafeAreaInsets;
  /** Recommended touch target size in pixels */
  touchTargetSize: number;
  /** Is virtual keyboard visible */
  isKeyboardVisible: boolean;
  /** Is app running in PWA standalone mode */
  isStandalone: boolean;
  /** Does user prefer reduced motion */
  prefersReducedMotion: boolean;
}

// ==============================================================================
// Constants
// ==============================================================================

const MOBILE_REGEX =
  /Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i;
const TABLET_REGEX = /iPad|Android(?!.*Mobile)|Tablet/i;

const BREAKPOINTS = {
  sm: 0,
  md: 640,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
};

// WCAG minimum touch target size
const MIN_TOUCH_TARGET = 44;
const DESKTOP_TARGET = 32;

// ==============================================================================
// Helper Functions
// ==============================================================================

function detectMobile(userAgent: string): boolean {
  return MOBILE_REGEX.test(userAgent);
}

function detectTablet(userAgent: string): boolean {
  return TABLET_REGEX.test(userAgent);
}

function detectTouch(): boolean {
  if (typeof navigator === "undefined") return false;
  return navigator.maxTouchPoints > 0;
}

function getBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINTS["2xl"]) return "2xl";
  if (width >= BREAKPOINTS.xl) return "xl";
  if (width >= BREAKPOINTS.lg) return "lg";
  if (width >= BREAKPOINTS.md) return "md";
  return "sm";
}

function getSafeAreaInsets(): SafeAreaInsets {
  if (
    typeof window === "undefined" ||
    typeof getComputedStyle === "undefined"
  ) {
    return { top: 0, right: 0, bottom: 0, left: 0 };
  }

  const root = document.documentElement;
  const style = getComputedStyle(root);

  return {
    top: parseInt(style.getPropertyValue("--sat") || "0", 10) || 0,
    right: parseInt(style.getPropertyValue("--sar") || "0", 10) || 0,
    bottom: parseInt(style.getPropertyValue("--sab") || "0", 10) || 0,
    left: parseInt(style.getPropertyValue("--sal") || "0", 10) || 0,
  };
}

function checkReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function checkStandalone(): boolean {
  if (typeof window === "undefined") return false;

  // Check for iOS standalone mode
  const nav = navigator as Navigator & { standalone?: boolean };
  if (nav.standalone === true) return true;

  // Check for display-mode: standalone
  return window.matchMedia("(display-mode: standalone)").matches;
}

// ==============================================================================
// Hook
// ==============================================================================

export function useMobileOptimizations(): MobileOptimizationsState {
  // Get initial values
  const userAgent = typeof navigator !== "undefined" ? navigator.userAgent : "";

  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth : 1024,
  );
  const [viewportHeight, setViewportHeight] = useState(() =>
    typeof window !== "undefined" ? window.innerHeight : 768,
  );
  const [isKeyboardVisible, setIsKeyboardVisible] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() =>
    checkReducedMotion(),
  );
  const [isStandalone, setIsStandalone] = useState(() => checkStandalone());

  // Detect device type
  const isMobile = useMemo(() => detectMobile(userAgent), [userAgent]);
  const isTablet = useMemo(() => detectTablet(userAgent), [userAgent]);
  const isDesktop = useMemo(() => !isMobile && !isTablet, [isMobile, isTablet]);

  // Detect touch support
  const hasTouch = useMemo(() => detectTouch(), []);

  // Calculate breakpoint
  const breakpoint = useMemo(
    () => getBreakpoint(viewportWidth),
    [viewportWidth],
  );

  // Calculate orientation
  const isPortrait = useMemo(
    () => viewportHeight > viewportWidth,
    [viewportWidth, viewportHeight],
  );
  const isLandscape = useMemo(
    () => viewportWidth > viewportHeight,
    [viewportWidth, viewportHeight],
  );

  // Get safe area insets
  const safeAreaInsets = useMemo(() => getSafeAreaInsets(), []);

  // Calculate touch target size
  const touchTargetSize = useMemo(() => {
    if (isMobile || isTablet || hasTouch) {
      return MIN_TOUCH_TARGET;
    }
    return DESKTOP_TARGET;
  }, [isMobile, isTablet, hasTouch]);

  // Handle resize events
  const handleResize = useCallback(() => {
    if (typeof window !== "undefined") {
      setViewportWidth(window.innerWidth);
      setViewportHeight(window.innerHeight);
    }
  }, []);

  // Handle visual viewport changes (keyboard visibility)
  const handleVisualViewportChange = useCallback(() => {
    if (typeof window !== "undefined" && window.visualViewport) {
      const viewportHeightDiff =
        window.innerHeight - window.visualViewport.height;
      // If viewport height reduced by more than 150px, keyboard is likely visible
      setIsKeyboardVisible(viewportHeightDiff > 150);
    }
  }, []);

  // Setup event listeners
  useEffect(() => {
    if (typeof window === "undefined") return;

    window.addEventListener("resize", handleResize);

    // Listen for visual viewport changes (keyboard)
    if (window.visualViewport) {
      window.visualViewport.addEventListener(
        "resize",
        handleVisualViewportChange,
      );
    }

    // Listen for reduced motion preference changes
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleMotionChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };
    motionQuery.addEventListener("change", handleMotionChange);

    // Listen for standalone mode changes
    const standaloneQuery = window.matchMedia("(display-mode: standalone)");
    const handleStandaloneChange = (e: MediaQueryListEvent) => {
      setIsStandalone(e.matches);
    };
    standaloneQuery.addEventListener("change", handleStandaloneChange);

    return () => {
      window.removeEventListener("resize", handleResize);

      if (window.visualViewport) {
        window.visualViewport.removeEventListener(
          "resize",
          handleVisualViewportChange,
        );
      }

      motionQuery.removeEventListener("change", handleMotionChange);
      standaloneQuery.removeEventListener("change", handleStandaloneChange);
    };
  }, [handleResize, handleVisualViewportChange]);

  return {
    isMobile,
    isTablet,
    isDesktop,
    hasTouch,
    breakpoint,
    viewportWidth,
    viewportHeight,
    isPortrait,
    isLandscape,
    safeAreaInsets,
    touchTargetSize,
    isKeyboardVisible,
    isStandalone,
    prefersReducedMotion,
  };
}

export default useMobileOptimizations;
