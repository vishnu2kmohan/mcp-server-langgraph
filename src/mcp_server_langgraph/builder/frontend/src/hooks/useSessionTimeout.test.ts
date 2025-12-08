/**
 * Tests for Session Timeout Warning Hook
 *
 * TDD: Tests written FIRST before implementation
 *
 * This hook provides:
 * - Session countdown timer
 * - Warning threshold alerts
 * - Session refresh capability
 * - Auto-logout functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSessionTimeout } from './useSessionTimeout';

describe('useSessionTimeout Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ==============================================================================
  // Return Type Tests
  // ==============================================================================

  describe('Return Type', () => {
    it('returns expected properties and methods', () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 60000 })
      );

      expect(result.current).toHaveProperty('remainingTime');
      expect(result.current).toHaveProperty('isWarning');
      expect(result.current).toHaveProperty('isExpired');
      expect(result.current).toHaveProperty('refreshSession');
      expect(result.current).toHaveProperty('formattedTime');
      expect(typeof result.current.remainingTime).toBe('number');
      expect(typeof result.current.isWarning).toBe('boolean');
      expect(typeof result.current.isExpired).toBe('boolean');
      expect(typeof result.current.refreshSession).toBe('function');
      expect(typeof result.current.formattedTime).toBe('string');
    });
  });

  // ==============================================================================
  // Countdown Tests
  // ==============================================================================

  describe('Countdown', () => {
    it('starts with full session duration', () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 60000 }) // 60 seconds
      );

      expect(result.current.remainingTime).toBe(60000);
    });

    it('counts down over time', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 60000 })
      );

      // Advance 10 seconds
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      expect(result.current.remainingTime).toBe(50000);
    });

    it('stops at zero', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 5000 })
      );

      // Advance past session duration
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      expect(result.current.remainingTime).toBe(0);
    });

    it('formats time correctly', () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 125000 }) // 2:05
      );

      expect(result.current.formattedTime).toBe('2:05');
    });

    it('formats time with leading zeros', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 65000 }) // 1:05
      );

      expect(result.current.formattedTime).toBe('1:05');

      await act(async () => {
        vi.advanceTimersByTime(60000); // Now at 5 seconds
      });

      expect(result.current.formattedTime).toBe('0:05');
    });
  });

  // ==============================================================================
  // Warning State Tests
  // ==============================================================================

  describe('Warning State', () => {
    it('isWarning is false when above threshold', () => {
      const { result } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          warningThreshold: 30000, // Warn at 30 seconds
        })
      );

      expect(result.current.isWarning).toBe(false);
    });

    it('isWarning is true when below threshold', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          warningThreshold: 30000,
        })
      );

      // Advance to 25 seconds remaining (below 30s threshold)
      await act(async () => {
        vi.advanceTimersByTime(35000);
      });

      expect(result.current.isWarning).toBe(true);
    });

    it('calls onWarning callback when entering warning state', async () => {
      const onWarning = vi.fn();
      renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          warningThreshold: 30000,
          onWarning,
        })
      );

      // Advance to just past the warning threshold
      await act(async () => {
        vi.advanceTimersByTime(31000);
      });

      expect(onWarning).toHaveBeenCalledTimes(1);
    });

    it('does not call onWarning multiple times', async () => {
      const onWarning = vi.fn();
      renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          warningThreshold: 30000,
          onWarning,
        })
      );

      // Advance past warning threshold
      await act(async () => {
        vi.advanceTimersByTime(35000);
      });

      // Advance more time
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      // Should still only be called once
      expect(onWarning).toHaveBeenCalledTimes(1);
    });
  });

  // ==============================================================================
  // Expiration Tests
  // ==============================================================================

  describe('Expiration', () => {
    it('isExpired is false when time remains', () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 60000 })
      );

      expect(result.current.isExpired).toBe(false);
    });

    it('isExpired is true when time reaches zero', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 5000 })
      );

      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      expect(result.current.isExpired).toBe(true);
    });

    it('calls onExpire callback when session expires', async () => {
      const onExpire = vi.fn();
      renderHook(() =>
        useSessionTimeout({
          sessionDuration: 5000,
          onExpire,
        })
      );

      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      expect(onExpire).toHaveBeenCalledTimes(1);
    });
  });

  // ==============================================================================
  // Session Refresh Tests
  // ==============================================================================

  describe('Session Refresh', () => {
    it('refreshSession resets the countdown', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 60000 })
      );

      // Advance 30 seconds
      await act(async () => {
        vi.advanceTimersByTime(30000);
      });

      expect(result.current.remainingTime).toBe(30000);

      // Refresh session
      act(() => {
        result.current.refreshSession();
      });

      expect(result.current.remainingTime).toBe(60000);
    });

    it('refreshSession resets warning state', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          warningThreshold: 30000,
        })
      );

      // Advance to warning state
      await act(async () => {
        vi.advanceTimersByTime(35000);
      });

      expect(result.current.isWarning).toBe(true);

      // Refresh session
      act(() => {
        result.current.refreshSession();
      });

      expect(result.current.isWarning).toBe(false);
    });

    it('refreshSession allows onWarning to be called again', async () => {
      const onWarning = vi.fn();
      const { result } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          warningThreshold: 30000,
          onWarning,
        })
      );

      // Advance to warning
      await act(async () => {
        vi.advanceTimersByTime(35000);
      });
      expect(onWarning).toHaveBeenCalledTimes(1);

      // Refresh session
      act(() => {
        result.current.refreshSession();
      });

      // Advance to warning again
      await act(async () => {
        vi.advanceTimersByTime(35000);
      });

      expect(onWarning).toHaveBeenCalledTimes(2);
    });
  });

  // ==============================================================================
  // User Activity Detection Tests
  // ==============================================================================

  describe('User Activity Detection', () => {
    it('refreshes session on user activity when autoRefresh is enabled', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          autoRefreshOnActivity: true,
        })
      );

      // Advance 30 seconds
      await act(async () => {
        vi.advanceTimersByTime(30000);
      });

      expect(result.current.remainingTime).toBe(30000);

      // Simulate user activity (mouse move)
      await act(async () => {
        window.dispatchEvent(new MouseEvent('mousemove'));
      });

      expect(result.current.remainingTime).toBe(60000);
    });

    it('does not refresh on activity when autoRefresh is disabled', async () => {
      const { result } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          autoRefreshOnActivity: false,
        })
      );

      // Advance 30 seconds
      await act(async () => {
        vi.advanceTimersByTime(30000);
      });

      expect(result.current.remainingTime).toBe(30000);

      // Simulate user activity
      await act(async () => {
        window.dispatchEvent(new MouseEvent('mousemove'));
      });

      // Should NOT have refreshed
      expect(result.current.remainingTime).toBe(30000);
    });
  });

  // ==============================================================================
  // Cleanup Tests
  // ==============================================================================

  describe('Cleanup', () => {
    it('clears timer on unmount', async () => {
      const { unmount } = renderHook(() =>
        useSessionTimeout({ sessionDuration: 60000 })
      );

      unmount();

      // Should not throw or cause issues after unmount
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });
    });

    it('removes event listeners on unmount', async () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      const { unmount } = renderHook(() =>
        useSessionTimeout({
          sessionDuration: 60000,
          autoRefreshOnActivity: true,
        })
      );

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalled();
      removeEventListenerSpy.mockRestore();
    });
  });
});
