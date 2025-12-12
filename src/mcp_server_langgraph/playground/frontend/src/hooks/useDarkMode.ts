/**
 * useDarkMode Hook
 *
 * Manages dark mode preference with localStorage persistence,
 * system preference detection, and keyboard shortcut support.
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'theme';
const DARK_CLASS = 'dark';

export interface UseDarkModeOptions {
  enableKeyboardShortcut?: boolean;
}

export interface UseDarkModeResult {
  isDark: boolean;
  toggle: () => void;
  setDark: (value: boolean) => void;
}

function getInitialTheme(): boolean {
  // Check localStorage first
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark') return true;
    if (stored === 'light') return false;

    // Fall back to system preference
    if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
      return true;
    }
  }
  return false;
}

function applyTheme(isDark: boolean): void {
  if (typeof document !== 'undefined') {
    if (isDark) {
      document.documentElement.classList.add(DARK_CLASS);
    } else {
      document.documentElement.classList.remove(DARK_CLASS);
    }
  }
}

export function useDarkMode(options: UseDarkModeOptions = {}): UseDarkModeResult {
  const { enableKeyboardShortcut = false } = options;
  const [isDark, setIsDark] = useState<boolean>(getInitialTheme);

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

  const toggle = useCallback(() => {
    setIsDark((prev) => !prev);
  }, []);

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

  return {
    isDark,
    toggle,
    setDark,
  };
}
