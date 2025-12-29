/**
 * Observability State Slice
 *
 * Manages persistent filter state for the ObservabilityPage.
 * This ensures filter selections persist when navigating away and back.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type ObservabilityTab = "traces" | "logs" | "metrics" | "alerts" | "ws-metrics";

export interface ObservabilityState {
  // Filter state
  statusFilter: string;
  sessionIdFilter: string;
  userIdFilter: string;
  workflowIdFilter: string;
  projectIdFilter: string;

  // Time range
  timeRange: string;

  // UI state
  activeTab: ObservabilityTab;
  selectedTraceId: string | null;
}

const initialState: ObservabilityState = {
  statusFilter: "",
  sessionIdFilter: "",
  userIdFilter: "",
  workflowIdFilter: "",
  projectIdFilter: "",
  timeRange: "1h",
  activeTab: "traces",
  selectedTraceId: null,
};

export const observabilitySlice = createSlice({
  name: "observability",
  initialState,
  reducers: {
    setStatusFilter: (state, action: PayloadAction<string>) => {
      state.statusFilter = action.payload;
    },
    setSessionIdFilter: (state, action: PayloadAction<string>) => {
      state.sessionIdFilter = action.payload;
    },
    setUserIdFilter: (state, action: PayloadAction<string>) => {
      state.userIdFilter = action.payload;
    },
    setWorkflowIdFilter: (state, action: PayloadAction<string>) => {
      state.workflowIdFilter = action.payload;
    },
    setProjectIdFilter: (state, action: PayloadAction<string>) => {
      state.projectIdFilter = action.payload;
    },
    setTimeRange: (state, action: PayloadAction<string>) => {
      state.timeRange = action.payload;
    },
    setActiveTab: (state, action: PayloadAction<ObservabilityTab>) => {
      state.activeTab = action.payload;
    },
    setSelectedTraceId: (state, action: PayloadAction<string | null>) => {
      state.selectedTraceId = action.payload;
    },
    resetFilters: (state) => {
      // Reset filter values but preserve timeRange, activeTab (UX decision)
      state.statusFilter = "";
      state.sessionIdFilter = "";
      state.userIdFilter = "";
      state.workflowIdFilter = "";
      state.projectIdFilter = "";
      state.selectedTraceId = null;
    },
  },
});

export const {
  setStatusFilter,
  setSessionIdFilter,
  setUserIdFilter,
  setWorkflowIdFilter,
  setProjectIdFilter,
  setTimeRange,
  setActiveTab,
  setSelectedTraceId,
  resetFilters,
} = observabilitySlice.actions;

// Selectors
export const selectStatusFilter = (state: {
  observability: ObservabilityState;
}) => state.observability.statusFilter;

export const selectSessionIdFilter = (state: {
  observability: ObservabilityState;
}) => state.observability.sessionIdFilter;

export const selectUserIdFilter = (state: {
  observability: ObservabilityState;
}) => state.observability.userIdFilter;

export const selectWorkflowIdFilter = (state: {
  observability: ObservabilityState;
}) => state.observability.workflowIdFilter;

export const selectProjectIdFilter = (state: {
  observability: ObservabilityState;
}) => state.observability.projectIdFilter;

export const selectTimeRange = (state: { observability: ObservabilityState }) =>
  state.observability.timeRange;

export const selectActiveTab = (state: { observability: ObservabilityState }) =>
  state.observability.activeTab;

export const selectSelectedTraceId = (state: {
  observability: ObservabilityState;
}) => state.observability.selectedTraceId;

export default observabilitySlice.reducer;
