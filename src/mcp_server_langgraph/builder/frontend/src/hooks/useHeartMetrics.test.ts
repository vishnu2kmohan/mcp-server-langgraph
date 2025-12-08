/**
 * Tests for HEART Metrics Hook
 *
 * TDD: Tests written FIRST before implementation
 *
 * HEART Framework:
 * - Happiness: User satisfaction metrics
 * - Engagement: User interaction depth
 * - Adoption: New user acquisition
 * - Retention: Return visits
 * - Task Success: Completion rates
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useHeartMetrics } from './useHeartMetrics';

describe('useHeartMetrics Hook', () => {
  const mockSendBeacon = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    sessionStorage.clear();
    vi.stubGlobal('navigator', { sendBeacon: mockSendBeacon });
    mockSendBeacon.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  // ==============================================================================
  // Return Type Tests
  // ==============================================================================

  describe('Return Type', () => {
    it('returns expected properties and methods', () => {
      const { result } = renderHook(() => useHeartMetrics());

      expect(result.current).toHaveProperty('trackEvent');
      expect(result.current).toHaveProperty('trackTaskStart');
      expect(result.current).toHaveProperty('trackTaskComplete');
      expect(result.current).toHaveProperty('trackTaskFail');
      expect(result.current).toHaveProperty('trackEngagement');
      expect(result.current).toHaveProperty('getSessionMetrics');
      expect(typeof result.current.trackEvent).toBe('function');
    });
  });

  // ==============================================================================
  // Event Tracking Tests
  // ==============================================================================

  describe('Event Tracking', () => {
    it('tracks custom events', () => {
      const { result } = renderHook(() => useHeartMetrics());

      act(() => {
        result.current.trackEvent({
          category: 'engagement',
          action: 'button_click',
          label: 'export_code',
        });
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.events.length).toBe(1);
      expect(metrics.events[0].action).toBe('button_click');
    });

    it('includes timestamp in events', () => {
      const { result } = renderHook(() => useHeartMetrics());

      const now = Date.now();
      vi.setSystemTime(now);

      act(() => {
        result.current.trackEvent({
          category: 'engagement',
          action: 'test_action',
        });
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.events[0].timestamp).toBe(now);
    });

    it('includes session ID in events', () => {
      const { result } = renderHook(() => useHeartMetrics());

      act(() => {
        result.current.trackEvent({
          category: 'engagement',
          action: 'test_action',
        });
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.sessionId).toBeDefined();
      expect(typeof metrics.sessionId).toBe('string');
    });
  });

  // ==============================================================================
  // Task Success Metrics
  // ==============================================================================

  describe('Task Success', () => {
    it('tracks task start time', () => {
      const { result } = renderHook(() => useHeartMetrics());

      const taskId = 'generate_code';

      act(() => {
        result.current.trackTaskStart(taskId);
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.tasks[taskId]).toBeDefined();
      expect(metrics.tasks[taskId].startTime).toBeDefined();
    });

    it('tracks task completion with duration', () => {
      const { result } = renderHook(() => useHeartMetrics());

      const taskId = 'generate_code';

      act(() => {
        result.current.trackTaskStart(taskId);
      });

      // Advance 5 seconds
      vi.advanceTimersByTime(5000);

      act(() => {
        result.current.trackTaskComplete(taskId);
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.tasks[taskId].completed).toBe(true);
      expect(metrics.tasks[taskId].duration).toBeGreaterThanOrEqual(5000);
    });

    it('tracks task failure', () => {
      const { result } = renderHook(() => useHeartMetrics());

      const taskId = 'generate_code';

      act(() => {
        result.current.trackTaskStart(taskId);
        result.current.trackTaskFail(taskId, 'API Error');
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.tasks[taskId].failed).toBe(true);
      expect(metrics.tasks[taskId].error).toBe('API Error');
    });

    it('calculates task success rate', () => {
      const { result } = renderHook(() => useHeartMetrics());

      // Complete 3 tasks, fail 1
      act(() => {
        result.current.trackTaskStart('task1');
        result.current.trackTaskComplete('task1');

        result.current.trackTaskStart('task2');
        result.current.trackTaskComplete('task2');

        result.current.trackTaskStart('task3');
        result.current.trackTaskComplete('task3');

        result.current.trackTaskStart('task4');
        result.current.trackTaskFail('task4', 'Error');
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.taskSuccessRate).toBe(0.75); // 3/4
    });
  });

  // ==============================================================================
  // Engagement Metrics
  // ==============================================================================

  describe('Engagement', () => {
    it('tracks engagement interactions', () => {
      const { result } = renderHook(() => useHeartMetrics());

      act(() => {
        result.current.trackEngagement('node_added');
        result.current.trackEngagement('edge_connected');
        result.current.trackEngagement('code_exported');
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.engagementScore).toBeGreaterThan(0);
    });

    it('tracks time on page', () => {
      const { result } = renderHook(() => useHeartMetrics());

      // Advance 60 seconds
      vi.advanceTimersByTime(60000);

      const metrics = result.current.getSessionMetrics();
      expect(metrics.timeOnPage).toBeGreaterThanOrEqual(60000);
    });

    it('tracks feature usage', () => {
      const { result } = renderHook(() => useHeartMetrics());

      act(() => {
        result.current.trackEngagement('feature:dark_mode');
        result.current.trackEngagement('feature:undo_redo');
        result.current.trackEngagement('feature:export_json');
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.featuresUsed.length).toBe(3);
      expect(metrics.featuresUsed).toContain('dark_mode');
    });
  });

  // ==============================================================================
  // Retention Metrics
  // ==============================================================================

  describe('Retention', () => {
    it('detects new vs returning users', () => {
      const { result } = renderHook(() => useHeartMetrics());

      const metrics = result.current.getSessionMetrics();
      expect(metrics.isNewUser).toBeDefined();
      expect(typeof metrics.isNewUser).toBe('boolean');
    });

    it('tracks returning users via localStorage', () => {
      // First visit
      const { result: firstVisit, unmount } = renderHook(() => useHeartMetrics());

      expect(firstVisit.current.getSessionMetrics().isNewUser).toBe(true);
      unmount();

      // Second visit
      const { result: secondVisit } = renderHook(() => useHeartMetrics());

      expect(secondVisit.current.getSessionMetrics().isNewUser).toBe(false);
    });

    it('tracks visit count', () => {
      // First visit
      const { unmount: unmount1 } = renderHook(() => useHeartMetrics());
      unmount1();

      // Second visit
      const { unmount: unmount2 } = renderHook(() => useHeartMetrics());
      unmount2();

      // Third visit
      const { result } = renderHook(() => useHeartMetrics());

      const metrics = result.current.getSessionMetrics();
      expect(metrics.visitCount).toBe(3);
    });
  });

  // ==============================================================================
  // Data Persistence
  // ==============================================================================

  describe('Data Persistence', () => {
    it('flushes metrics on page unload', () => {
      const { result } = renderHook(() => useHeartMetrics({ endpoint: '/api/metrics' }));

      // Add an event so there's something to flush
      act(() => {
        result.current.trackEvent({ category: 'test', action: 'test' });
      });

      // Simulate page unload
      window.dispatchEvent(new Event('beforeunload'));

      expect(mockSendBeacon).toHaveBeenCalled();
    });

    it('batches events before sending', () => {
      const { result } = renderHook(() =>
        useHeartMetrics({ batchSize: 5, endpoint: '/api/metrics' })
      );

      // Send 4 events (below batch threshold)
      for (let i = 0; i < 4; i++) {
        act(() => {
          result.current.trackEvent({ category: 'test', action: `action_${i}` });
        });
      }

      expect(mockSendBeacon).not.toHaveBeenCalled();

      // Send 5th event (triggers batch)
      act(() => {
        result.current.trackEvent({ category: 'test', action: 'action_5' });
      });

      // Batch should be sent
      expect(mockSendBeacon).toHaveBeenCalled();
    });
  });

  // ==============================================================================
  // Privacy Compliance
  // ==============================================================================

  describe('Privacy', () => {
    it('respects do-not-track setting', () => {
      vi.stubGlobal('navigator', { doNotTrack: '1', sendBeacon: mockSendBeacon });

      const { result } = renderHook(() => useHeartMetrics({ respectDoNotTrack: true }));

      act(() => {
        result.current.trackEvent({ category: 'test', action: 'test' });
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.events.length).toBe(0);
    });

    it('can disable tracking', () => {
      const { result } = renderHook(() => useHeartMetrics({ enabled: false }));

      act(() => {
        result.current.trackEvent({ category: 'test', action: 'test' });
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.events.length).toBe(0);
    });

    it('anonymizes user data by default', () => {
      const { result } = renderHook(() => useHeartMetrics());

      act(() => {
        result.current.trackEvent({ category: 'test', action: 'test' });
      });

      const metrics = result.current.getSessionMetrics();
      expect(metrics.userId).toBeUndefined();
    });
  });
});
