/**
 * Dark Mode Hook
 *
 * Manages dark mode state with:
 * - localStorage persistence
 * - System preference detection
 * - DOM class management (for Tailwind CSS)
 */

import { useState, useEffect, useCallback } from 'react';

// ==============================================================================
// Types
// ==============================================================================

interface DarkModeResult {
  isDarkMode: boolean;
  toggle: () => void;
  setDarkMode: (value: boolean) => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const STORAGE_KEY = 'theme';
const DARK_CLASS = 'dark';

// ==============================================================================
// Hook Implementation
// ==============================================================================

export function useDarkMode(): DarkModeResult {
  // Initialize from localStorage or system preference
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    // Check localStorage first
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'dark') return true;
      if (stored === 'light') return false;

      // Fall back to system preference
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return true;
      }
    }
    return false;
  });

  // Update DOM and localStorage when dark mode changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (isDarkMode) {
        document.documentElement.classList.add(DARK_CLASS);
        localStorage.setItem(STORAGE_KEY, 'dark');
      } else {
        document.documentElement.classList.remove(DARK_CLASS);
        localStorage.setItem(STORAGE_KEY, 'light');
      }
    }
  }, [isDarkMode]);

  // Toggle dark mode
  const toggle = useCallback(() => {
    setIsDarkMode((prev) => !prev);
  }, []);

  // Set dark mode explicitly
  const setDarkMode = useCallback((value: boolean) => {
    setIsDarkMode(value);
  }, []);

  return {
    isDarkMode,
    toggle,
    setDarkMode,
  };
}

export default useDarkMode;
