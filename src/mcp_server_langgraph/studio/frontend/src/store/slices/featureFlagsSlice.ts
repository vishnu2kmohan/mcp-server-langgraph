/**
 * Feature Flags Slice
 *
 * Manages UI feature visibility based on server-provided flags.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface FeatureFlags {
  enableWorkflowsFeature?: boolean;
  enableSessionsFeature?: boolean;
  enableCostDashboard?: boolean;
  enableCostDashboardUsers?: boolean;
  enableObservabilityUI?: boolean;
  enableCodeExport?: boolean;
  enableAISuggestions?: boolean;
  enableMCPWebsocket?: boolean;
}

interface FeatureFlagsState {
  flags: FeatureFlags;
  isLoading: boolean;
  error: string | null;
}

const initialState: FeatureFlagsState = {
  flags: {},
  isLoading: false,
  error: null,
};

export const featureFlagsSlice = createSlice({
  name: 'featureFlags',
  initialState,
  reducers: {
    setFeatureFlagsLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setFeatureFlags: (state, action: PayloadAction<FeatureFlags>) => {
      state.flags = { ...state.flags, ...action.payload };
      state.isLoading = false;
    },
    setFeatureFlagsError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.isLoading = false;
    },
    resetFeatureFlags: () => initialState,
  },
});

export const {
  setFeatureFlagsLoading,
  setFeatureFlags,
  setFeatureFlagsError,
  resetFeatureFlags,
} = featureFlagsSlice.actions;

// Selectors
export const selectFeatureFlags = (state: { featureFlags: FeatureFlagsState }) =>
  state.featureFlags.flags;
export const selectFeatureFlagsLoading = (state: { featureFlags: FeatureFlagsState }) =>
  state.featureFlags.isLoading;
export const selectFeatureFlag = (flagName: keyof FeatureFlags) => (state: { featureFlags: FeatureFlagsState }) =>
  state.featureFlags.flags[flagName] ?? false;

export default featureFlagsSlice.reducer;
