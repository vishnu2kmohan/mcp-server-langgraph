/**
 * Feature Flags Slice
 *
 * Manages UI feature visibility based on server-provided flags.
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface FeatureFlagsState {
  enableWorkflowsFeature: boolean;
  enableSessionsFeature: boolean;
  enableCostDashboard: boolean;
  enableCostDashboardUsers: boolean;
  enableObservabilityUI: boolean;
  enableCodeExport: boolean;
  enableAISuggestions: boolean;
  enableMCPWebsocket: boolean;
  loaded: boolean;
}

const initialState: FeatureFlagsState = {
  enableWorkflowsFeature: true,
  enableSessionsFeature: true,
  enableCostDashboard: true,
  enableCostDashboardUsers: false,
  enableObservabilityUI: true,
  enableCodeExport: true,
  enableAISuggestions: true,
  enableMCPWebsocket: false,
  loaded: false,
};

export const featureFlagsSlice = createSlice({
  name: 'featureFlags',
  initialState,
  reducers: {
    setFeatureFlags: (
      state,
      action: PayloadAction<Partial<Omit<FeatureFlagsState, 'loaded'>>>
    ) => {
      return { ...state, ...action.payload, loaded: true };
    },
    resetFeatureFlags: () => initialState,
  },
});

export const { setFeatureFlags, resetFeatureFlags } = featureFlagsSlice.actions;

export default featureFlagsSlice.reducer;
