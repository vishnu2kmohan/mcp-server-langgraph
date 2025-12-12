/**
 * Tests for HEART Metrics Hook
 *
 * TDD: Tests written FIRST before implementation
 *
 * HEART Framework:
 * - Happiness: User satisfaction (NPS, ratings)
 * - Engagement: Session duration, feature usage
 * - Adoption: New user tracking, onboarding
 * - Retention: Return visits, active days
 * - Task Success: Completion rates, error rates
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { HeartMetricsProvider, useHeartMetrics } from './useHeartMetrics';

// Wrapper component for testing
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <HeartMetricsProvider>{children}</HeartMetricsProvider>
);

describe('useHeartMetrics Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ==============================================================================
  // Context & Provider Tests
  // ==============================================================================

  describe('Context & Provider', () => {
    it('throws error when used outside provider', () => {
      // Suppress console error for this test
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useHeartMetrics());
      }).toThrow('useHeartMetrics must be used within a HeartMetricsProvider');

      spy.mockRestore();
    });

    it('provides initial metrics', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      expect(result.current.metrics).toBeDefined();
      expect(result.current.metrics.taskSuccess).toBeDefined();
      expect(result.current.metrics.engagement).toBeDefined();
      expect(result.current.metrics.happiness).toBeDefined();
      expect(result.current.metrics.adoption).toBeDefined();
      expect(result.current.metrics.retention).toBeDefined();
    });
  });

  // ==============================================================================
  // Task Success Tests
  // ==============================================================================

  describe('Task Success', () => {
    it('tracks task start', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('generate_code');
      });

      expect(result.current.metrics.taskSuccess.tasksStarted).toBe(1);
    });

    it('tracks task completion', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('generate_code');
        vi.advanceTimersByTime(1000);
        result.current.trackTaskComplete('generate_code');
      });

      expect(result.current.metrics.taskSuccess.tasksCompleted).toBe(1);
      expect(result.current.metrics.taskSuccess.successRate).toBe(1);
    });

    it('tracks task errors', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('generate_code');
        result.current.trackTaskError('generate_code', 'API failed');
      });

      expect(result.current.metrics.taskSuccess.errors).toBe(1);
      expect(result.current.metrics.taskSuccess.successRate).toBe(0);
    });

    it('calculates average completion time', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('task1');
        vi.advanceTimersByTime(1000);
        result.current.trackTaskComplete('task1');

        result.current.trackTaskStart('task2');
        vi.advanceTimersByTime(2000);
        result.current.trackTaskComplete('task2');
      });

      expect(result.current.metrics.taskSuccess.averageCompletionTimeMs).toBe(1500);
    });
  });

  // ==============================================================================
  // Engagement Tests
  // ==============================================================================

  describe('Engagement', () => {
    it('tracks feature usage', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackFeatureUsed('dark_mode');
        result.current.trackFeatureUsed('dark_mode');
      });

      expect(result.current.metrics.engagement.featureUsage['dark_mode']).toBe(2);
    });

    it('tracks interactions', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackInteraction('click', 'generate_button');
      });

      expect(result.current.metrics.engagement.interactions).toBe(1);
    });

    it('updates session duration', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        vi.advanceTimersByTime(5000);
        result.current.updateSessionDuration();
      });

      expect(result.current.metrics.engagement.sessionDurationMs).toBeGreaterThan(0);
    });
  });

  // ==============================================================================
  // Happiness Tests
  // ==============================================================================

  describe('Happiness', () => {
    it('records NPS score (0-10)', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.recordNPSScore(8);
      });

      expect(result.current.metrics.happiness.npsScore).toBe(8);
    });

    it('clamps NPS score to valid range', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.recordNPSScore(15);
      });

      expect(result.current.metrics.happiness.npsScore).toBe(10);

      act(() => {
        result.current.recordNPSScore(-5);
      });

      expect(result.current.metrics.happiness.npsScore).toBe(0);
    });

    it('records satisfaction rating (1-5)', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.recordSatisfaction(4);
      });

      expect(result.current.metrics.happiness.satisfactionRating).toBe(4);
    });
  });

  // ==============================================================================
  // Adoption Tests
  // ==============================================================================

  describe('Adoption', () => {
    it('starts with isNewUser true', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      expect(result.current.metrics.adoption.isNewUser).toBe(true);
    });

    it('marks returning user', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.markReturningUser();
      });

      expect(result.current.metrics.adoption.isNewUser).toBe(false);
    });

    it('tracks onboarding steps', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackOnboardingStep('welcome');
        result.current.trackOnboardingStep('add_node');
      });

      expect(result.current.metrics.adoption.onboardingStepsCompleted).toContain('welcome');
      expect(result.current.metrics.adoption.onboardingStepsCompleted).toContain('add_node');
    });

    it('does not duplicate onboarding steps', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackOnboardingStep('welcome');
        result.current.trackOnboardingStep('welcome');
      });

      expect(result.current.metrics.adoption.onboardingStepsCompleted.filter((s) => s === 'welcome').length).toBe(1);
    });
  });

  // ==============================================================================
  // Retention Tests
  // ==============================================================================

  describe('Retention', () => {
    it('tracks return visits', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackReturnVisit();
      });

      expect(result.current.metrics.retention.returnVisits).toBe(1);
    });

    it('tracks active days', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackActiveDay();
      });

      expect(result.current.metrics.retention.daysActive).toBe(1);
      expect(result.current.metrics.retention.lastActiveDate).not.toBeNull();
    });

    it('does not increment days active for same day', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackActiveDay();
        result.current.trackActiveDay();
      });

      expect(result.current.metrics.retention.daysActive).toBe(1);
    });
  });

  // ==============================================================================
  // Utility Tests
  // ==============================================================================

  describe('Utilities', () => {
    it('exports metrics', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('test');
      });

      const exported = result.current.exportMetrics();
      expect(exported.taskSuccess.tasksStarted).toBe(1);
    });

    it('resets metrics', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.trackTaskStart('test');
        result.current.trackFeatureUsed('feature');
        result.current.resetMetrics();
      });

      expect(result.current.metrics.taskSuccess.tasksStarted).toBe(0);
      expect(result.current.metrics.engagement.featureUsage).toEqual({});
    });
  });

  // ==============================================================================
  // Privacy Tests
  // ==============================================================================

  describe('Privacy', () => {
    it('respects Do Not Track setting', () => {
      // Mock navigator.doNotTrack
      Object.defineProperty(navigator, 'doNotTrack', {
        value: '1',
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      expect(result.current.isTrackingEnabled).toBe(false);

      // Restore
      Object.defineProperty(navigator, 'doNotTrack', {
        value: null,
        writable: true,
        configurable: true,
      });
    });

    it('allows opting out of tracking', () => {
      const { result } = renderHook(() => useHeartMetrics(), { wrapper });

      act(() => {
        result.current.setTrackingEnabled(false);
      });

      expect(result.current.isTrackingEnabled).toBe(false);
    });
  });
});
