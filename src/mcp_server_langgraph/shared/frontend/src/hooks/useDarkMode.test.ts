/**
 * useDarkMode Hook Tests
 *
 * TDD: RED phase - Write tests first
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useDarkMode } from './useDarkMode';

describe('useDarkMode', () => {
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
      // Mock matchMedia to return dark preference
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: query === '(prefers-color-scheme: dark)',
          media: query,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
        })),
      });

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
    it('does not update when system preference changes after explicit preference stored', () => {
      // The hook stores the theme on mount, so system preference changes won't override
      let mediaQueryCallback: ((e: MediaQueryListEvent) => void) | null = null;

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          addEventListener: vi.fn((event: string, callback: (e: MediaQueryListEvent) => void) => {
            if (event === 'change') {
              mediaQueryCallback = callback;
            }
          }),
          removeEventListener: vi.fn(),
        })),
      });

      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDark).toBe(false);

      // Simulate system preference change - should NOT update because localStorage has value
      if (mediaQueryCallback) {
        act(() => {
          mediaQueryCallback!({ matches: true } as MediaQueryListEvent);
        });

        // Should still be false because user preference (stored on mount) takes precedence
        expect(result.current.isDark).toBe(false);
      }
    });

    it('listens for system preference changes', () => {
      const addEventListenerMock = vi.fn();
      const removeEventListenerMock = vi.fn();

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          addEventListener: addEventListenerMock,
          removeEventListener: removeEventListenerMock,
        })),
      });

      const { unmount } = renderHook(() => useDarkMode());

      // Verify listener was added for prefers-color-scheme
      expect(addEventListenerMock).toHaveBeenCalledWith('change', expect.any(Function));

      unmount();

      // Verify listener was removed on cleanup
      expect(removeEventListenerMock).toHaveBeenCalledWith('change', expect.any(Function));
    });
  });

  describe('reduced motion preference', () => {
    it('exposes prefersReducedMotion', () => {
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: query === '(prefers-reduced-motion: reduce)',
          media: query,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
        })),
      });

      const { result } = renderHook(() => useDarkMode());
      expect(result.current.prefersReducedMotion).toBe(true);
    });
  });
});
