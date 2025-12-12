/**
 * useFTUXAnalytics Hook Tests
 *
 * TDD: RED phase - Write tests first
 * First-Time User Experience analytics tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useFTUXAnalytics } from './useFTUXAnalytics';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('useFTUXAnalytics Hook', () => {
  beforeEach(() => {
    localStorage.clear();
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({ ok: true });
  });

  afterEach(() => {
    localStorage.clear();
  });

  // ==============================================================================
  // Session Tracking Tests
  // ==============================================================================

  describe('Session Tracking', () => {
    it('detects first-time user', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      expect(result.current.isFirstTimeUser).toBe(true);
    });

    it('marks returning user after first visit', () => {
      localStorage.setItem('ftux_first_visit', 'true');

      const { result } = renderHook(() => useFTUXAnalytics());

      expect(result.current.isFirstTimeUser).toBe(false);
    });

    it('tracks session start', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      expect(result.current.sessionStartTime).toBeDefined();
      expect(typeof result.current.sessionStartTime).toBe('number');
    });

    it('calculates session duration', async () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      // Wait a bit
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(result.current.getSessionDuration()).toBeGreaterThanOrEqual(0);
    });
  });

  // ==============================================================================
  // Onboarding Tracking Tests
  // ==============================================================================

  describe('Onboarding Tracking', () => {
    it('tracks onboarding start', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackOnboardingStart();
      });

      expect(result.current.onboardingStarted).toBe(true);
    });

    it('tracks onboarding step completion', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackOnboardingStep('step1', 'Create Agent');
      });

      expect(result.current.completedSteps).toContain('step1');
    });

    it('tracks onboarding completion', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackOnboardingComplete();
      });

      expect(result.current.onboardingCompleted).toBe(true);
    });

    it('tracks onboarding skip', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackOnboardingSkip('step2');
      });

      expect(result.current.onboardingSkipped).toBe(true);
      expect(result.current.skipStep).toBe('step2');
    });

    it('calculates onboarding progress', () => {
      const { result } = renderHook(() => useFTUXAnalytics({ totalOnboardingSteps: 5 }));

      act(() => {
        result.current.trackOnboardingStep('step1', 'Step 1');
        result.current.trackOnboardingStep('step2', 'Step 2');
      });

      expect(result.current.onboardingProgress).toBe(40); // 2/5 * 100
    });
  });

  // ==============================================================================
  // Feature Discovery Tracking Tests
  // ==============================================================================

  describe('Feature Discovery Tracking', () => {
    it('tracks feature discovery', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackFeatureDiscovered('dark_mode');
      });

      expect(result.current.discoveredFeatures).toContain('dark_mode');
    });

    it('tracks hint shown', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackHintShown('feature_hint_1');
      });

      expect(result.current.hintsShown).toContain('feature_hint_1');
    });

    it('tracks hint dismissed', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackHintDismissed('feature_hint_1');
      });

      expect(result.current.hintsDismissed).toContain('feature_hint_1');
    });

    it('tracks hint action taken', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackHintActionTaken('feature_hint_1', 'try_it');
      });

      expect(result.current.hintActions).toContainEqual({
        hintId: 'feature_hint_1',
        action: 'try_it',
      });
    });
  });

  // ==============================================================================
  // Tour Tracking Tests
  // ==============================================================================

  describe('Tour Tracking', () => {
    it('tracks tour start', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackTourStart('welcome_tour');
      });

      expect(result.current.toursStarted).toContain('welcome_tour');
    });

    it('tracks tour completion', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackTourComplete('welcome_tour');
      });

      expect(result.current.toursCompleted).toContain('welcome_tour');
    });

    it('tracks tour skip', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackTourSkip('welcome_tour', 2);
      });

      expect(result.current.toursSkipped).toContainEqual({
        tourId: 'welcome_tour',
        atStep: 2,
      });
    });
  });

  // ==============================================================================
  // Metrics Summary Tests
  // ==============================================================================

  describe('Metrics Summary', () => {
    it('generates complete metrics summary', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackOnboardingStart();
        result.current.trackOnboardingStep('step1', 'Step 1');
        result.current.trackFeatureDiscovered('dark_mode');
        result.current.trackTourStart('welcome');
      });

      const summary = result.current.getMetricsSummary();

      expect(summary).toHaveProperty('isFirstTimeUser');
      expect(summary).toHaveProperty('sessionDuration');
      expect(summary).toHaveProperty('onboarding');
      expect(summary).toHaveProperty('features');
      expect(summary).toHaveProperty('tours');
    });

    it('returns metrics in correct format', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      const summary = result.current.getMetricsSummary();

      expect(typeof summary.isFirstTimeUser).toBe('boolean');
      expect(typeof summary.sessionDuration).toBe('number');
      expect(typeof summary.onboarding.started).toBe('boolean');
      expect(Array.isArray(summary.features.discovered)).toBe(true);
    });
  });

  // ==============================================================================
  // Persistence Tests
  // ==============================================================================

  describe('Persistence', () => {
    it('persists first visit flag', () => {
      renderHook(() => useFTUXAnalytics());

      expect(localStorage.getItem('ftux_first_visit')).toBe('true');
    });

    it('persists onboarding progress', () => {
      const { result } = renderHook(() => useFTUXAnalytics());

      act(() => {
        result.current.trackOnboardingStep('step1', 'Step 1');
      });

      const stored = JSON.parse(localStorage.getItem('ftux_onboarding') || '{}');
      expect(stored.completedSteps).toContain('step1');
    });

    it('loads persisted state on mount', () => {
      localStorage.setItem('ftux_onboarding', JSON.stringify({
        completedSteps: ['step1', 'step2'],
        started: true,
      }));

      const { result } = renderHook(() => useFTUXAnalytics());

      expect(result.current.completedSteps).toContain('step1');
      expect(result.current.completedSteps).toContain('step2');
    });
  });
});
