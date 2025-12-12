/**
 * useServiceWorker Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useServiceWorker } from './useServiceWorker';

describe('useServiceWorker', () => {
  const originalNavigator = global.navigator;
  const originalWindow = global.window;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should_detect_service_worker_support', () => {
    const { result } = renderHook(() => useServiceWorker());

    // In test environment, serviceWorker is typically not available
    expect(typeof result.current.isSupported).toBe('boolean');
  });

  it('should_track_offline_status', () => {
    const { result } = renderHook(() => useServiceWorker());

    expect(typeof result.current.isOffline).toBe('boolean');
  });

  it('should_provide_update_function', () => {
    const { result } = renderHook(() => useServiceWorker());

    expect(typeof result.current.updateServiceWorker).toBe('function');
  });

  it('should_respond_to_online_event', () => {
    const { result } = renderHook(() => useServiceWorker());

    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    expect(result.current.isOffline).toBe(false);
  });

  it('should_respond_to_offline_event', () => {
    const { result } = renderHook(() => useServiceWorker());

    // First set to online
    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    // Then set to offline
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });

    expect(result.current.isOffline).toBe(true);
  });

  it('should_have_default_registered_state', () => {
    const { result } = renderHook(() => useServiceWorker());

    // In dev mode, service worker won't be registered
    expect(result.current.isRegistered).toBe(false);
  });

  it('should_have_default_update_state', () => {
    const { result } = renderHook(() => useServiceWorker());

    expect(result.current.hasUpdate).toBe(false);
  });
});
