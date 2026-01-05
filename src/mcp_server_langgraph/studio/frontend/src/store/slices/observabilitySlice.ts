/**
 * Observability State Slice
 *
 * Manages persistent filter state for the ObservabilityPage.
 * This ensures filter selections persist when navigating away and back.
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { ReconnectionMetrics } from "../../types/websocket-metrics";

type ObservabilityTab =
  | "agent-sessions"
  | "workflow-runs"
  | "traces"
  | "logs"
  | "metrics"
  | "alerts"
  | "ws-metrics";

/**
 * WebSocket connection info stored in Redux.
 */
export interface WebSocketConnectionInfo {
  /** Endpoint identifier (e.g., "notifications", "traces") */
  endpointId: string;
  /** Current reconnection metrics */
  metrics: ReconnectionMetrics;
  /** Last update timestamp */
  lastUpdated: number;
}

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

  // WebSocket connection metrics (keyed by endpointId)
  webSocketMetrics: Record<string, WebSocketConnectionInfo>;
}

const initialState: ObservabilityState = {
  statusFilter: "",
  sessionIdFilter: "",
  userIdFilter: "",
  workflowIdFilter: "",
  projectIdFilter: "",
  timeRange: "1h",
  activeTab: "agent-sessions",
  selectedTraceId: null,
  webSocketMetrics: {},
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
    // WebSocket metrics actions
    updateWebSocketMetrics: (
      state,
      action: PayloadAction<WebSocketConnectionInfo>,
    ) => {
      const { endpointId, metrics, lastUpdated } = action.payload;
      state.webSocketMetrics[endpointId] = { endpointId, metrics, lastUpdated };
    },
    removeWebSocketMetrics: (state, action: PayloadAction<string>) => {
      delete state.webSocketMetrics[action.payload];
    },
    resetWebSocketMetrics: (state) => {
      state.webSocketMetrics = {};
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
  updateWebSocketMetrics,
  removeWebSocketMetrics,
  resetWebSocketMetrics,
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

// WebSocket metrics selectors
export const selectWebSocketMetrics = (state: {
  observability: ObservabilityState;
}) => state.observability.webSocketMetrics;

export const selectWebSocketMetricsByEndpoint = (
  state: { observability: ObservabilityState },
  endpointId: string,
): WebSocketConnectionInfo | undefined =>
  state.observability.webSocketMetrics[endpointId];

export const selectTotalWebSocketConnections = (state: {
  observability: ObservabilityState;
}) => Object.keys(state.observability.webSocketMetrics).length;

export default observabilitySlice.reducer;
