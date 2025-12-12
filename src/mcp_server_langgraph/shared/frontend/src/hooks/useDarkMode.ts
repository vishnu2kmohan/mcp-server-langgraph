/**
 * Unified useDarkMode Hook
 *
 * Manages dark mode preference with:
 * - localStorage persistence
 * - System preference detection
 * - Keyboard shortcut support (Ctrl+Shift+T)
 * - Reduced motion preference detection
 * - Backward-compatible API for both Builder and Playground
 *
 * @module @mcp-server-langgraph/shared-frontend/hooks
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

const STORAGE_KEY = 'theme';
const DARK_CLASS = 'dark';

// =============================================================================
// Types
// =============================================================================

export interface UseDarkModeOptions {
  /**
   * Enable Ctrl+Shift+T keyboard shortcut to toggle dark mode
   * @default false
   */
  enableKeyboardShortcut?: boolean;
}

export interface UseDarkModeResult {
  /**
   * Current dark mode state (primary API)
   */
  isDark: boolean;

  /**
   * Alias for isDark (Builder compatibility)
   */
  isDarkMode: boolean;

  /**
   * Toggle dark mode on/off
   */
  toggle: () => void;

  /**
   * Set dark mode to a specific value (primary API)
   */
  setDark: (value: boolean) => void;

  /**
   * Alias for setDark (Builder compatibility)
   */
  setDarkMode: (value: boolean) => void;

  /**
   * Whether user prefers reduced motion
   */
  prefersReducedMotion: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get initial theme from localStorage or system preference
 */
function getInitialTheme(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  // Check localStorage first
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'dark') return true;
  if (stored === 'light') return false;

  // Fall back to system preference
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return true;
  }

  return false;
}

/**
 * Get reduced motion preference
 */
function getReducedMotionPreference(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

/**
 * Apply theme to document
 */
function applyTheme(isDark: boolean): void {
  if (typeof document === 'undefined') {
    return;
  }

  if (isDark) {
    document.documentElement.classList.add(DARK_CLASS);
  } else {
    document.documentElement.classList.remove(DARK_CLASS);
  }
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDarkMode(options: UseDarkModeOptions = {}): UseDarkModeResult {
  const { enableKeyboardShortcut = false } = options;

  // State
  const [isDark, setIsDark] = useState<boolean>(getInitialTheme);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState<boolean>(
    getReducedMotionPreference
  );

  // Apply theme on mount and when it changes
  useEffect(() => {
    applyTheme(isDark);
    localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');
  }, [isDark]);

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia?.('(prefers-color-scheme: dark)');
    if (!mediaQuery) return;

    const handleChange = (e: MediaQueryListEvent) => {
      // Only update if no explicit preference is stored
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        setIsDark(e.matches);
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Listen for reduced motion preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!mediaQuery) return;

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Toggle function
  const toggle = useCallback(() => {
    setIsDark((prev) => !prev);
  }, []);

  // Set dark mode explicitly
  const setDark = useCallback((value: boolean) => {
    setIsDark(value);
  }, []);

  // Keyboard shortcut: Ctrl+Shift+T to toggle
  useEffect(() => {
    if (!enableKeyboardShortcut) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 't') {
        // Don't trigger when typing in inputs
        const target = event.target as HTMLElement;
        const isInput =
          target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable;

        if (!isInput) {
          event.preventDefault();
          setIsDark((prev) => !prev);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enableKeyboardShortcut]);

  // Memoize the result object for stable reference
  const result = useMemo<UseDarkModeResult>(
    () => ({
      isDark,
      isDarkMode: isDark, // Alias for Builder compatibility
      toggle,
      setDark,
      setDarkMode: setDark, // Alias for Builder compatibility
      prefersReducedMotion,
    }),
    [isDark, toggle, setDark, prefersReducedMotion]
  );

  return result;
}

export default useDarkMode;
