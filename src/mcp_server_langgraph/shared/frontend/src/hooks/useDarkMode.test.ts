/**
 * useDarkMode Hook Tests
 *
 * TDD: RED phase - Write tests first
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useDarkMode } from './useDarkMode';

describe('useDarkMode', () => {
  const originalLocalStorage = global.localStorage;
  const originalMatchMedia = global.matchMedia;

  beforeEach(() => {
    // Mock localStorage
    const store: Record<string, string> = {};
    global.localStorage = {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete store[key];
      }),
      clear: vi.fn(() => {
        Object.keys(store).forEach((key) => delete store[key]);
      }),
      length: 0,
      key: vi.fn(),
    };

    // Mock matchMedia
    global.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    // Mock document.documentElement
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    global.localStorage = originalLocalStorage;
    global.matchMedia = originalMatchMedia;
  });

  describe('initial state', () => {
    it('returns isDark as false by default', () => {
      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(false);
    });

    it('returns isDarkMode alias for backward compatibility', () => {
      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDarkMode).toBe(result.current.isDark);
    });

    it('reads from localStorage when theme is stored', () => {
      localStorage.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(true);
    });

    it('respects system preference when no localStorage value', () => {
      global.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }));

      const { result } = renderHook(() => useDarkMode());
      expect(result.current.isDark).toBe(true);
    });
  });

  describe('toggle', () => {
    it('toggles from light to dark mode', () => {
      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDark).toBe(false);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isDark).toBe(true);
    });

    it('toggles from dark to light mode', () => {
      localStorage.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDark).toBe(true);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isDark).toBe(false);
    });

    it('persists toggle to localStorage', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.toggle();
      });

      expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark');
    });

    it('adds dark class to document.documentElement when dark', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.toggle();
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('setDark', () => {
    it('sets dark mode to true', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDark(true);
      });

      expect(result.current.isDark).toBe(true);
    });

    it('sets dark mode to false', () => {
      localStorage.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDark(false);
      });

      expect(result.current.isDark).toBe(false);
    });
  });

  describe('setDarkMode alias', () => {
    it('works identically to setDark', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDarkMode(true);
      });

      expect(result.current.isDark).toBe(true);
      expect(result.current.isDarkMode).toBe(true);
    });
  });

  describe('keyboard shortcut', () => {
    it('toggles on Ctrl+Shift+T when enabled', () => {
      const { result } = renderHook(() =>
        useDarkMode({ enableKeyboardShortcut: true })
      );

      expect(result.current.isDark).toBe(false);

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 't',
          ctrlKey: true,
          shiftKey: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isDark).toBe(true);
    });

    it('does not toggle when keyboard shortcut is disabled', () => {
      const { result } = renderHook(() =>
        useDarkMode({ enableKeyboardShortcut: false })
      );

      expect(result.current.isDark).toBe(false);

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 't',
          ctrlKey: true,
          shiftKey: true,
        });
        document.dispatchEvent(event);
      });

      expect(result.current.isDark).toBe(false);
    });

    it('does not toggle when typing in input', () => {
      const { result } = renderHook(() =>
        useDarkMode({ enableKeyboardShortcut: true })
      );

      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      expect(result.current.isDark).toBe(false);

      act(() => {
        const event = new KeyboardEvent('keydown', {
          key: 't',
          ctrlKey: true,
          shiftKey: true,
          bubbles: true,
        });
        Object.defineProperty(event, 'target', { value: input });
        document.dispatchEvent(event);
      });

      // Should still be false because we're in an input
      expect(result.current.isDark).toBe(false);

      document.body.removeChild(input);
    });
  });

  describe('system preference changes', () => {
    it('updates when system preference changes and no stored preference', () => {
      let mediaQueryCallback: ((e: MediaQueryListEvent) => void) | null = null;

      global.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn((event: string, callback: (e: MediaQueryListEvent) => void) => {
          if (event === 'change') {
            mediaQueryCallback = callback;
          }
        }),
        removeEventListener: vi.fn(),
      }));

      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDark).toBe(false);

      // Simulate system preference change
      if (mediaQueryCallback) {
        act(() => {
          mediaQueryCallback!({ matches: true } as MediaQueryListEvent);
        });

        expect(result.current.isDark).toBe(true);
      }
    });
  });

  describe('reduced motion preference', () => {
    it('exposes prefersReducedMotion', () => {
      global.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }));

      const { result } = renderHook(() => useDarkMode());
      expect(result.current.prefersReducedMotion).toBe(true);
    });
  });
});
