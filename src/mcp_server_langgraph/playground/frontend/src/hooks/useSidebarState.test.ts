/**
 * useSidebarState Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSidebarState } from './useSidebarState';

describe('useSidebarState', () => {
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
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should_default_to_expanded', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useSidebarState());

    expect(result.current.isCollapsed).toBe(false);
  });

  it('should_respect_stored_collapsed_state', () => {
    localStorageMock.getItem.mockReturnValue('true');
    const { result } = renderHook(() => useSidebarState());

    expect(result.current.isCollapsed).toBe(true);
  });

  it('should_respect_stored_expanded_state', () => {
    localStorageMock.getItem.mockReturnValue('false');
    const { result } = renderHook(() => useSidebarState());

    expect(result.current.isCollapsed).toBe(false);
  });

  it('should_toggle_collapsed_state', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useSidebarState());

    expect(result.current.isCollapsed).toBe(false);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('sidebar-collapsed', 'true');
  });

  it('should_toggle_back_to_expanded', () => {
    localStorageMock.getItem.mockReturnValue('true');
    const { result } = renderHook(() => useSidebarState());

    expect(result.current.isCollapsed).toBe(true);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('sidebar-collapsed', 'false');
  });

  it('should_set_collapsed_explicitly', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useSidebarState());

    act(() => {
      result.current.setCollapsed(true);
    });

    expect(result.current.isCollapsed).toBe(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('sidebar-collapsed', 'true');
  });

  it('should_set_expanded_explicitly', () => {
    localStorageMock.getItem.mockReturnValue('true');
    const { result } = renderHook(() => useSidebarState());

    act(() => {
      result.current.setCollapsed(false);
    });

    expect(result.current.isCollapsed).toBe(false);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('sidebar-collapsed', 'false');
  });

  it('should_use_custom_storage_key', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useSidebarState('custom-key'));

    act(() => {
      result.current.toggle();
    });

    expect(localStorageMock.setItem).toHaveBeenCalledWith('custom-key', 'true');
  });

  it('should_persist_section_collapsed_states', () => {
    localStorageMock.getItem.mockReturnValue(JSON.stringify({ servers: true, sessions: false }));
    const { result } = renderHook(() => useSidebarState());

    expect(result.current.sections.servers).toBe(true);
    expect(result.current.sections.sessions).toBe(false);
  });

  it('should_toggle_section_state', () => {
    localStorageMock.getItem.mockReturnValue(null);
    const { result } = renderHook(() => useSidebarState());

    act(() => {
      result.current.toggleSection('servers');
    });

    expect(result.current.sections.servers).toBe(true);
  });

  it('should_toggle_section_back', () => {
    localStorageMock.getItem.mockReturnValue(JSON.stringify({ servers: true }));
    const { result } = renderHook(() => useSidebarState());

    act(() => {
      result.current.toggleSection('servers');
    });

    expect(result.current.sections.servers).toBe(false);
  });
});
