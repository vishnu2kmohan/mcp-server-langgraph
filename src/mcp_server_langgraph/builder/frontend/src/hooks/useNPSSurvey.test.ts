/**
 * Tests for useNPSSurvey Hook
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useNPSSurvey } from './useNPSSurvey';

describe('useNPSSurvey Hook', () => {
  // Create a storage object to simulate localStorage persistence
  let storage: Record<string, string> = {};

  const localStorageMock = {
    getItem: vi.fn((key: string) => storage[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      storage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete storage[key];
    }),
    clear: vi.fn(() => {
      storage = {};
    }),
  };

  beforeEach(() => {
    storage = {};
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // ==============================================================================
  // Return Type Tests
  // ==============================================================================

  describe('Return Type', () => {
    it('returns expected properties and methods', () => {
      const { result } = renderHook(() => useNPSSurvey());

      expect(result.current).toHaveProperty('shouldShowNPS');
      expect(result.current).toHaveProperty('recordCodeExport');
      expect(result.current).toHaveProperty('recordWorkflowSave');
      expect(result.current).toHaveProperty('dismissNPS');
      expect(result.current).toHaveProperty('submitNPS');
    });
  });

  // ==============================================================================
  // Code Export Trigger Tests
  // ==============================================================================

  describe('Code Export Trigger', () => {
    it('shows NPS after first code export', () => {
      const { result } = renderHook(() => useNPSSurvey());

      expect(result.current.shouldShowNPS).toBe(false);

      act(() => {
        result.current.recordCodeExport();
      });

      expect(result.current.shouldShowNPS).toBe(true);
    });

    it('does not show NPS on second code export if already shown', () => {
      storage['nps_code_export_shown'] = 'true';

      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordCodeExport();
      });

      expect(result.current.shouldShowNPS).toBe(false);
    });
  });

  // ==============================================================================
  // Workflow Save Trigger Tests
  // ==============================================================================

  describe('Workflow Save Trigger', () => {
    it('shows NPS after 5th workflow save', () => {
      const { result } = renderHook(() => useNPSSurvey());

      // Save 4 times - should not show
      for (let i = 0; i < 4; i++) {
        act(() => {
          result.current.recordWorkflowSave();
        });
        expect(result.current.shouldShowNPS).toBe(false);
      }

      // 5th save should trigger NPS
      act(() => {
        result.current.recordWorkflowSave();
      });

      expect(result.current.shouldShowNPS).toBe(true);
    });

    it('persists save count in localStorage', () => {
      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordWorkflowSave();
      });

      expect(localStorageMock.setItem).toHaveBeenCalledWith('nps_workflow_save_count', '1');
    });

    it('resumes count from localStorage', () => {
      storage['nps_workflow_save_count'] = '4';

      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordWorkflowSave();
      });

      expect(result.current.shouldShowNPS).toBe(true);
    });
  });

  // ==============================================================================
  // Dismiss and Submit Tests
  // ==============================================================================

  describe('Dismiss and Submit', () => {
    it('dismissNPS hides the survey', () => {
      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordCodeExport();
      });

      expect(result.current.shouldShowNPS).toBe(true);

      act(() => {
        result.current.dismissNPS();
      });

      expect(result.current.shouldShowNPS).toBe(false);
    });

    it('submitNPS hides the survey and records timestamp', () => {
      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordCodeExport();
      });

      expect(result.current.shouldShowNPS).toBe(true);

      act(() => {
        result.current.submitNPS(9);
      });

      expect(result.current.shouldShowNPS).toBe(false);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'nps_last_submitted',
        expect.any(String)
      );
    });
  });

  // ==============================================================================
  // Monthly Trigger Tests
  // ==============================================================================

  describe('Monthly Trigger', () => {
    it('does not show NPS if submitted within last 30 days', () => {
      storage['nps_last_submitted'] = new Date().toISOString();

      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordCodeExport();
      });

      expect(result.current.shouldShowNPS).toBe(false);
    });

    it('allows NPS if more than 30 days since last submission', () => {
      storage['nps_last_submitted'] = new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString();

      const { result } = renderHook(() => useNPSSurvey());

      act(() => {
        result.current.recordCodeExport();
      });

      expect(result.current.shouldShowNPS).toBe(true);
    });
  });
});
