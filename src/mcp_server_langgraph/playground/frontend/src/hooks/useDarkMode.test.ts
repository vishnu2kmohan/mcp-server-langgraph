/**
 * useDarkMode Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDarkMode } from './useDarkMode';

describe('useDarkMode', () => {
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    document.documentElement.classList.remove('dark');
  });

  it('should_default_to_light_mode', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(false);
  });

  it('should_respect_stored_preference', () => {
    localStorageMock.getItem.mockReturnValue('dark');
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(true);
  });

  it('should_toggle_dark_mode', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useDarkMode());

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isDark).toBe(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  it('should_set_dark_mode_explicitly', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useDarkMode());

    act(() => {
      result.current.setDark(true);
    });

    expect(result.current.isDark).toBe(true);
  });

  it('should_apply_dark_class_to_html_element', () => {
    localStorageMock.getItem.mockReturnValue('dark');
    renderHook(() => useDarkMode());
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('should_remove_dark_class_when_light_mode', () => {
    document.documentElement.classList.add('dark');
    localStorageMock.getItem.mockReturnValue('light');
    renderHook(() => useDarkMode());
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });
});
