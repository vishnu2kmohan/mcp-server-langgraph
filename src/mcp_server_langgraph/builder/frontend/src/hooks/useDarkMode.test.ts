/**
 * Tests for Dark Mode Hook
 *
 * TDD: Tests written FIRST before implementation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDarkMode } from './useDarkMode';

describe('useDarkMode Hook', () => {
  // Mock localStorage
  const localStorageMock = (() => {
    let store: Record<string, string> = {};
    return {
      getItem: vi.fn((key: string) => store[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        store[key] = value;
      }),
      clear: () => {
        store = {};
      },
    };
  })();

  // Mock matchMedia
  const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

  beforeEach(() => {
    // Reset matchMedia to return light mode by default
    matchMediaMock.mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    vi.stubGlobal('localStorage', localStorageMock);
    vi.stubGlobal('matchMedia', matchMediaMock);
    localStorageMock.clear();
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // ==============================================================================
  // Return Type Tests
  // ==============================================================================

  describe('Return Type', () => {
    it('returns isDarkMode boolean and toggle function', () => {
      const { result } = renderHook(() => useDarkMode());

      expect(result.current).toHaveProperty('isDarkMode');
      expect(result.current).toHaveProperty('toggle');
      expect(result.current).toHaveProperty('setDarkMode');
      expect(typeof result.current.isDarkMode).toBe('boolean');
      expect(typeof result.current.toggle).toBe('function');
    });
  });

  // ==============================================================================
  // Initial State Tests
  // ==============================================================================

  describe('Initial State', () => {
    it('defaults to light mode', () => {
      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDarkMode).toBe(false);
    });

    it('respects localStorage preference', () => {
      localStorageMock.setItem('theme', 'dark');

      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDarkMode).toBe(true);
    });

    it('respects system preference when no localStorage', () => {
      matchMediaMock.mockImplementation((query: string) => ({
        matches: query.includes('dark'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDarkMode).toBe(true);
    });
  });

  // ==============================================================================
  // Toggle Tests
  // ==============================================================================

  describe('Toggle', () => {
    it('toggles dark mode on', () => {
      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDarkMode).toBe(false);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isDarkMode).toBe(true);
    });

    it('toggles dark mode off', () => {
      localStorageMock.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());

      expect(result.current.isDarkMode).toBe(true);

      act(() => {
        result.current.toggle();
      });

      expect(result.current.isDarkMode).toBe(false);
    });

    it('persists preference to localStorage', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.toggle();
      });

      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
    });
  });

  // ==============================================================================
  // Set Dark Mode Tests
  // ==============================================================================

  describe('setDarkMode', () => {
    it('sets dark mode explicitly', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDarkMode(true);
      });

      expect(result.current.isDarkMode).toBe(true);
    });

    it('sets light mode explicitly', () => {
      localStorageMock.setItem('theme', 'dark');
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDarkMode(false);
      });

      expect(result.current.isDarkMode).toBe(false);
    });
  });

  // ==============================================================================
  // DOM Class Tests
  // ==============================================================================

  describe('DOM Class', () => {
    it('adds dark class to document element when enabled', () => {
      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDarkMode(true);
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('removes dark class from document element when disabled', () => {
      document.documentElement.classList.add('dark');
      localStorageMock.setItem('theme', 'dark');

      const { result } = renderHook(() => useDarkMode());

      act(() => {
        result.current.setDarkMode(false);
      });

      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });
});
