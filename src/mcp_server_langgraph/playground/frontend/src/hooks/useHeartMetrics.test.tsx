/**
 * useHeartMetrics Hook Tests
 *
 * HEART framework: Happiness, Engagement, Adoption, Retention, Task Success
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useHeartMetrics, HeartMetricsProvider } from './useHeartMetrics';
import type { ReactNode } from 'react';

// Wrapper component for context
const wrapper = ({ children }: { children: ReactNode }) => (
  <HeartMetricsProvider>{children}</HeartMetricsProvider>
);

describe('useHeartMetrics', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('task tracking', () => {
    it('should_track_task_start', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('send_message');
      });

      expect(result.current.metrics.taskSuccess.tasksStarted).toBe(1);
    });

    it('should_track_task_completion', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('send_message');
        vi.advanceTimersByTime(1000);
        result.current.trackTaskComplete('send_message');
      });

      expect(result.current.metrics.taskSuccess.tasksCompleted).toBe(1);
    });

    it('should_calculate_success_rate', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('task1');
        result.current.trackTaskComplete('task1');
        result.current.trackTaskStart('task2');
        result.current.trackTaskComplete('task2');
        result.current.trackTaskStart('task3');
        result.current.trackTaskError('task3', 'error');
      });

      expect(result.current.metrics.taskSuccess.successRate).toBeCloseTo(0.67, 1);
    });

    it('should_track_task_error', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('send_message');
        result.current.trackTaskError('send_message', 'Network error');
      });

      expect(result.current.metrics.taskSuccess.errors).toBe(1);
    });
  });

  describe('engagement tracking', () => {
    it('should_track_feature_usage', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackFeatureUsed('dark_mode_toggle');
        result.current.trackFeatureUsed('dark_mode_toggle');
        result.current.trackFeatureUsed('observability_traces');
      });

      expect(result.current.metrics.engagement.featureUsage.dark_mode_toggle).toBe(2);
      expect(result.current.metrics.engagement.featureUsage.observability_traces).toBe(1);
    });

    it('should_track_session_duration', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        vi.advanceTimersByTime(60000); // 1 minute
        result.current.updateSessionDuration();
      });

      expect(result.current.metrics.engagement.sessionDurationMs).toBeGreaterThanOrEqual(60000);
    });

    it('should_track_interactions', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackInteraction('click', 'send_button');
        result.current.trackInteraction('keypress', 'enter');
      });

      expect(result.current.metrics.engagement.interactions).toBe(2);
    });
  });

  describe('happiness tracking', () => {
    it('should_record_nps_score', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.recordNPSScore(9);
      });

      expect(result.current.metrics.happiness.npsScore).toBe(9);
    });

    it('should_validate_nps_score_range', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      // Valid scores should be recorded
      act(() => {
        result.current.recordNPSScore(10);
      });
      expect(result.current.metrics.happiness.npsScore).toBe(10);

      // Invalid scores should be clamped
      act(() => {
        result.current.recordNPSScore(11);
      });
      expect(result.current.metrics.happiness.npsScore).toBe(10);
    });

    it('should_track_satisfaction_rating', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.recordSatisfaction(4);
      });

      expect(result.current.metrics.happiness.satisfactionRating).toBe(4);
    });
  });

  describe('adoption tracking', () => {
    it('should_mark_first_use', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      expect(result.current.metrics.adoption.isNewUser).toBe(true);

      act(() => {
        result.current.markReturningUser();
      });

      expect(result.current.metrics.adoption.isNewUser).toBe(false);
    });

    it('should_track_onboarding_steps', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackOnboardingStep('create_session');
        result.current.trackOnboardingStep('send_first_message');
      });

      expect(result.current.metrics.adoption.onboardingStepsCompleted).toContain('create_session');
      expect(result.current.metrics.adoption.onboardingStepsCompleted).toContain('send_first_message');
    });
  });

  describe('retention tracking', () => {
    it('should_track_return_visits', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackReturnVisit();
        result.current.trackReturnVisit();
      });

      expect(result.current.metrics.retention.returnVisits).toBe(2);
    });

    it('should_track_days_active', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackActiveDay();
      });

      expect(result.current.metrics.retention.daysActive).toBe(1);
    });
  });

  describe('persistence', () => {
    it('should_export_metrics', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('task1');
        result.current.trackTaskComplete('task1');
      });

      const exported = result.current.exportMetrics();
      expect(exported).toBeDefined();
      expect(exported.taskSuccess.tasksCompleted).toBe(1);
    });

    it('should_reset_metrics', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('task1');
        result.current.resetMetrics();
      });

      expect(result.current.metrics.taskSuccess.tasksStarted).toBe(0);
    });
  });
});
