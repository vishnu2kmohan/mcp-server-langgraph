/**
 * Feature Flags Slice Tests
 *
 * TDD tests for the feature flags state slice.
 * Tests cover:
 * - Loading state
 * - Setting flags
 * - Error handling
 * - Reset
 * - Selectors
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import featureFlagsReducer, {
  setFeatureFlagsLoading,
  setFeatureFlags,
  setFeatureFlagsError,
  resetFeatureFlags,
  selectFeatureFlags,
  selectFeatureFlagsLoading,
  selectFeatureFlag,
} from './featureFlagsSlice';

describe('featureFlagsSlice', () => {
  const initialState = {
    flags: {},
    isLoading: false,
    error: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should return initial state when called with undefined', () => {
      const result = featureFlagsReducer(undefined, { type: 'unknown' });
      expect(result).toEqual(initialState);
    });
  });

  describe('setFeatureFlagsLoading', () => {
    it('should set loading to true', () => {
      const result = featureFlagsReducer(initialState, setFeatureFlagsLoading(true));
      expect(result.isLoading).toBe(true);
    });

    it('should set loading to false', () => {
      const state = { ...initialState, isLoading: true };
      const result = featureFlagsReducer(state, setFeatureFlagsLoading(false));
      expect(result.isLoading).toBe(false);
    });
  });

  describe('setFeatureFlags', () => {
    it('should set feature flags', () => {
      const flags = {
        enableWorkflowsFeature: true,
        enableSessionsFeature: true,
      };
      const result = featureFlagsReducer(initialState, setFeatureFlags(flags));

      expect(result.flags).toEqual(flags);
      expect(result.isLoading).toBe(false);
    });

    it('should merge with existing flags', () => {
      const state = {
        ...initialState,
        flags: { enableWorkflowsFeature: true },
      };
      const newFlags = { enableSessionsFeature: true };
      const result = featureFlagsReducer(state, setFeatureFlags(newFlags));

      expect(result.flags).toEqual({
        enableWorkflowsFeature: true,
        enableSessionsFeature: true,
      });
    });

    it('should override existing flag values', () => {
      const state = {
        ...initialState,
        flags: { enableWorkflowsFeature: true },
      };
      const newFlags = { enableWorkflowsFeature: false };
      const result = featureFlagsReducer(state, setFeatureFlags(newFlags));

      expect(result.flags.enableWorkflowsFeature).toBe(false);
    });

    it('should set isLoading to false after setting flags', () => {
      const state = { ...initialState, isLoading: true };
      const result = featureFlagsReducer(state, setFeatureFlags({}));
      expect(result.isLoading).toBe(false);
    });

    it('should handle all feature flag types', () => {
      const allFlags = {
        enableWorkflowsFeature: true,
        enableSessionsFeature: true,
        enableCostDashboard: true,
        enableCostDashboardUsers: false,
        enableObservabilityUI: true,
        enableCodeExport: true,
        enableAISuggestions: true,
        enableMCPWebsocket: false,
      };
      const result = featureFlagsReducer(initialState, setFeatureFlags(allFlags));

      expect(result.flags).toEqual(allFlags);
    });
  });

  describe('setFeatureFlagsError', () => {
    it('should set error message', () => {
      const result = featureFlagsReducer(
        initialState,
        setFeatureFlagsError('Failed to load flags')
      );

      expect(result.error).toBe('Failed to load flags');
    });

    it('should set isLoading to false', () => {
      const state = { ...initialState, isLoading: true };
      const result = featureFlagsReducer(state, setFeatureFlagsError('Error'));

      expect(result.isLoading).toBe(false);
    });
  });

  describe('resetFeatureFlags', () => {
    it('should reset to initial state', () => {
      const modifiedState = {
        flags: { enableWorkflowsFeature: true },
        isLoading: true,
        error: 'Some error',
      };
      const result = featureFlagsReducer(modifiedState, resetFeatureFlags());

      expect(result).toEqual(initialState);
    });
  });

  describe('selectors', () => {
    describe('selectFeatureFlags', () => {
      it('should return all flags', () => {
        const state = {
          featureFlags: {
            flags: { enableWorkflowsFeature: true, enableSessionsFeature: false },
            isLoading: false,
            error: null,
          },
        };
        const result = selectFeatureFlags(state);

        expect(result).toEqual({
          enableWorkflowsFeature: true,
          enableSessionsFeature: false,
        });
      });

      it('should return empty object when no flags set', () => {
        const state = { featureFlags: initialState };
        const result = selectFeatureFlags(state);

        expect(result).toEqual({});
      });
    });

    describe('selectFeatureFlagsLoading', () => {
      it('should return loading state true', () => {
        const state = {
          featureFlags: { ...initialState, isLoading: true },
        };
        const result = selectFeatureFlagsLoading(state);

        expect(result).toBe(true);
      });

      it('should return loading state false', () => {
        const state = {
          featureFlags: { ...initialState, isLoading: false },
        };
        const result = selectFeatureFlagsLoading(state);

        expect(result).toBe(false);
      });
    });

    describe('selectFeatureFlag', () => {
      it('should return true for enabled flag', () => {
        const state = {
          featureFlags: {
            ...initialState,
            flags: { enableWorkflowsFeature: true },
          },
        };
        const selector = selectFeatureFlag('enableWorkflowsFeature');
        const result = selector(state);

        expect(result).toBe(true);
      });

      it('should return false for disabled flag', () => {
        const state = {
          featureFlags: {
            ...initialState,
            flags: { enableWorkflowsFeature: false },
          },
        };
        const selector = selectFeatureFlag('enableWorkflowsFeature');
        const result = selector(state);

        expect(result).toBe(false);
      });

      it('should return false for undefined flag', () => {
        const state = {
          featureFlags: initialState,
        };
        const selector = selectFeatureFlag('enableWorkflowsFeature');
        const result = selector(state);

        expect(result).toBe(false);
      });

      it('should work with different flag names', () => {
        const state = {
          featureFlags: {
            ...initialState,
            flags: {
              enableCostDashboard: true,
              enableMCPWebsocket: false,
            },
          },
        };

        expect(selectFeatureFlag('enableCostDashboard')(state)).toBe(true);
        expect(selectFeatureFlag('enableMCPWebsocket')(state)).toBe(false);
        expect(selectFeatureFlag('enableAISuggestions')(state)).toBe(false);
      });
    });
  });
});
