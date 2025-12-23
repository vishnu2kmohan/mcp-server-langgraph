/**
 * Alert Slice
 *
 * Redux slice for managing infrastructure alerts for Admin dashboard.
 *
 * Features:
 * - Add/update/remove alerts from OTEL/Mimir
 * - Severity filtering (critical, warning)
 * - Selected alert tracking for detail panel
 * - Pending remediations queue
 * - Sound notifications toggle
 * - Critical/warning alert counts
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { createSlice, createSelector, PayloadAction } from "@reduxjs/toolkit";
import { storage } from "../../utils/storage";

// =============================================================================
// Storage Keys
// =============================================================================

const SOUND_ENABLED_KEY = "alert-sound-enabled";

// =============================================================================
// Persistence Helpers
// =============================================================================

/**
 * Load sound preference from localStorage.
 * Returns true (default) if not set.
 */
export function loadSoundPreference(): boolean {
  const stored = storage.get<boolean>(SOUND_ENABLED_KEY);
  return stored ?? true;
}

/**
 * Save sound preference to localStorage.
 */
export function saveSoundPreference(enabled: boolean): void {
  storage.set(SOUND_ENABLED_KEY, enabled);
}

// =============================================================================
// Types
// =============================================================================

/**
 * Alert severity levels (matching backend AlertSeverity)
 */
export type AlertSeverity = "critical" | "warning" | "info";

/**
 * Alert state (firing or resolved)
 */
export type AlertState = "firing" | "resolved";

/**
 * Remediation approval status
 */
export type RemediationStatus = "pending" | "approved" | "rejected";

/**
 * Alert data structure (matching backend Alert model)
 *
 * Field names match backend broadcaster.py alert_to_message():
 * - started_at: ISO8601 timestamp when alert started
 * - ended_at: ISO8601 timestamp when alert resolved (null if still firing)
 */
export interface Alert {
  alert_id: string;
  name: string;
  severity: AlertSeverity;
  state: AlertState;
  message: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  started_at: string;
  ended_at: string | null;
  fingerprint: string;
}

/**
 * Remediation request data structure (matching backend RemediationRequest)
 */
export interface RemediationRequest {
  remediation_id: string;
  alert_id: string;
  alert_name: string;
  severity: string;
  step_number: number;
  action: string;
  description: string;
  command: string | null;
  risk_level: string;
  status: RemediationStatus;
  requested_at: string;
  approved_by: string | null;
  approved_at: string | null;
  reason: string | null;
  recommendation_id: string | null;
}

/**
 * Alert filters
 */
export interface AlertFilters {
  severity: AlertSeverity[];
  state: AlertState[];
}

/**
 * Grouped alert for reducing noise in Admin Dashboard.
 * Groups alerts by service + alertname.
 */
export interface AlertGroup {
  /** Composite key: "service:alertname" */
  groupKey: string;
  /** Service name from alert labels (may be undefined) */
  service?: string;
  /** Alert name (alertname label) */
  alertName: string;
  /** Highest severity in the group */
  severity: AlertSeverity;
  /** "firing" if any alert is firing, else "resolved" */
  state: AlertState;
  /** Number of alerts in this group */
  count: number;
  /** Most recent alert for display */
  mostRecentAlert: Alert;
  /** All alerts in this group */
  alerts: Alert[];
  /** Earliest start time (ISO8601) */
  firstFiredAt: string;
  /** Most recent update time (ISO8601) */
  lastUpdatedAt: string;
}

/**
 * Alert state shape
 */
interface AlertSliceState {
  alerts: Alert[];
  selectedAlertId: string | null;
  pendingRemediations: RemediationRequest[];
  soundEnabled: boolean;
  lastCriticalAlertTime: number | null;
  filters: AlertFilters;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: AlertSliceState = {
  alerts: [],
  selectedAlertId: null,
  pendingRemediations: [],
  soundEnabled: true,
  lastCriticalAlertTime: null,
  filters: {
    severity: ["critical", "warning"],
    state: ["firing"],
  },
};

// =============================================================================
// Slice
// =============================================================================

const alertSlice = createSlice({
  name: "alerts",
  initialState,
  reducers: {
    /**
     * Add a new alert or update existing (by alert_id)
     */
    addAlert: (state, action: PayloadAction<Alert>) => {
      const existingIndex = state.alerts.findIndex(
        (a) => a.alert_id === action.payload.alert_id,
      );

      if (existingIndex !== -1) {
        // Update existing alert
        state.alerts[existingIndex] = action.payload;
      } else {
        // Add new alert (prepend - newest first)
        state.alerts.unshift(action.payload);
      }

      // Track last critical alert time for sound debouncing
      if (action.payload.severity === "critical" && existingIndex === -1) {
        state.lastCriticalAlertTime = Date.now();
      }
    },

    /**
     * Update an existing alert by id
     */
    updateAlert: (
      state,
      action: PayloadAction<Partial<Alert> & { alert_id: string }>,
    ) => {
      const index = state.alerts.findIndex(
        (a) => a.alert_id === action.payload.alert_id,
      );

      if (index !== -1) {
        const existing = state.alerts[index];
        if (existing) {
          state.alerts[index] = { ...existing, ...action.payload };
        }
      }
    },

    /**
     * Remove an alert by id
     */
    removeAlert: (state, action: PayloadAction<string>) => {
      state.alerts = state.alerts.filter((a) => a.alert_id !== action.payload);

      // Clear selection if removed alert was selected
      if (state.selectedAlertId === action.payload) {
        state.selectedAlertId = null;
      }
    },

    /**
     * Set the selected alert id for detail view
     */
    setSelectedAlertId: (state, action: PayloadAction<string | null>) => {
      state.selectedAlertId = action.payload;
    },

    /**
     * Add a pending remediation
     */
    addPendingRemediation: (
      state,
      action: PayloadAction<RemediationRequest>,
    ) => {
      const existingIndex = state.pendingRemediations.findIndex(
        (r) => r.remediation_id === action.payload.remediation_id,
      );

      if (existingIndex === -1) {
        state.pendingRemediations.push(action.payload);
      }
    },

    /**
     * Update a remediation status
     */
    updateRemediation: (
      state,
      action: PayloadAction<
        Partial<RemediationRequest> & { remediation_id: string }
      >,
    ) => {
      const index = state.pendingRemediations.findIndex(
        (r) => r.remediation_id === action.payload.remediation_id,
      );

      if (index !== -1) {
        const existing = state.pendingRemediations[index];
        if (existing) {
          state.pendingRemediations[index] = {
            ...existing,
            ...action.payload,
          };
        }
      }
    },

    /**
     * Remove a pending remediation by id
     */
    removePendingRemediation: (state, action: PayloadAction<string>) => {
      state.pendingRemediations = state.pendingRemediations.filter(
        (r) => r.remediation_id !== action.payload,
      );
    },

    /**
     * Toggle sound notifications (persists to localStorage)
     */
    toggleSound: (state) => {
      state.soundEnabled = !state.soundEnabled;
      saveSoundPreference(state.soundEnabled);
    },

    /**
     * Set sound enabled to specific value (persists to localStorage)
     */
    setSoundEnabled: (state, action: PayloadAction<boolean>) => {
      state.soundEnabled = action.payload;
      saveSoundPreference(action.payload);
    },

    /**
     * Initialize sound state from localStorage.
     * Call this on app startup to restore user preference.
     */
    initializeSoundFromStorage: (state) => {
      state.soundEnabled = loadSoundPreference();
    },

    /**
     * Set alert filters (merges with existing)
     */
    setFilters: (state, action: PayloadAction<Partial<AlertFilters>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },

    /**
     * Clear all alerts
     */
    clearAlerts: (state) => {
      state.alerts = [];
      state.selectedAlertId = null;
    },

    /**
     * Clear only resolved alerts
     */
    clearResolvedAlerts: (state) => {
      state.alerts = state.alerts.filter((a) => a.state !== "resolved");

      // Clear selection if removed alert was selected
      if (
        state.selectedAlertId &&
        !state.alerts.some((a) => a.alert_id === state.selectedAlertId)
      ) {
        state.selectedAlertId = null;
      }
    },
  },
});

// =============================================================================
// Actions
// =============================================================================

export const {
  addAlert,
  updateAlert,
  removeAlert,
  setSelectedAlertId,
  addPendingRemediation,
  updateRemediation,
  removePendingRemediation,
  toggleSound,
  setSoundEnabled,
  initializeSoundFromStorage,
  setFilters,
  clearAlerts,
  clearResolvedAlerts,
} = alertSlice.actions;

// =============================================================================
// Selectors
// =============================================================================

interface RootState {
  alerts: AlertSliceState;
}

/**
 * Select all alerts
 */
export const selectAlerts = (state: RootState): Alert[] => state.alerts.alerts;

/**
 * Select the currently selected alert id
 */
export const selectSelectedAlertId = (state: RootState): string | null =>
  state.alerts.selectedAlertId;

/**
 * Select the currently selected alert (memoized)
 */
export const selectSelectedAlert = createSelector(
  [selectAlerts, selectSelectedAlertId],
  (alerts, selectedId): Alert | undefined =>
    selectedId ? alerts.find((a) => a.alert_id === selectedId) : undefined,
);

/**
 * Select pending remediations
 */
export const selectPendingRemediations = (
  state: RootState,
): RemediationRequest[] => state.alerts.pendingRemediations;

/**
 * Select sound enabled state
 */
export const selectSoundEnabled = (state: RootState): boolean =>
  state.alerts.soundEnabled;

/**
 * Select current filters
 */
export const selectFilters = (state: RootState): AlertFilters =>
  state.alerts.filters;

/**
 * Select count of critical firing alerts (memoized)
 */
export const selectCriticalAlertCount = createSelector(
  [selectAlerts],
  (alerts): number =>
    alerts.filter((a) => a.severity === "critical" && a.state === "firing")
      .length,
);

/**
 * Select count of warning firing alerts (memoized)
 */
export const selectWarningAlertCount = createSelector(
  [selectAlerts],
  (alerts): number =>
    alerts.filter((a) => a.severity === "warning" && a.state === "firing")
      .length,
);

/**
 * Select alerts filtered by current filter settings (memoized)
 */
export const selectFilteredAlerts = createSelector(
  [selectAlerts, selectFilters],
  (alerts, filters): Alert[] =>
    alerts.filter(
      (a) =>
        filters.severity.includes(a.severity) &&
        filters.state.includes(a.state),
    ),
);

/**
 * Select last critical alert time
 */
export const selectLastCriticalAlertTime = (state: RootState): number | null =>
  state.alerts.lastCriticalAlertTime;

// =============================================================================
// Alert Grouping Selectors (Phase 6)
// =============================================================================

/**
 * Severity priority for determining highest severity in a group.
 * Lower number = higher priority.
 */
const SEVERITY_PRIORITY: Record<AlertSeverity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

/**
 * Get the highest severity from a list of alerts.
 */
function getHighestSeverity(alerts: Alert[]): AlertSeverity {
  const firstAlert = alerts[0];
  if (alerts.length === 0 || !firstAlert) return "info";

  return alerts.reduce((highest, alert) => {
    if (SEVERITY_PRIORITY[alert.severity] < SEVERITY_PRIORITY[highest]) {
      return alert.severity;
    }
    return highest;
  }, firstAlert.severity);
}

/**
 * Select alerts grouped by service + alertname (memoized).
 *
 * Groups related alerts to reduce noise in the Admin Dashboard.
 * Composite key: "service:alertname"
 */
export const selectAlertGroups = createSelector(
  [selectAlerts],
  (alerts): AlertGroup[] => {
    if (alerts.length === 0) return [];

    const groupMap = new Map<string, Alert[]>();

    alerts.forEach((alert) => {
      const service = alert.labels?.service;
      const key = `${service || "unknown"}:${alert.name}`;
      const existing = groupMap.get(key) || [];
      groupMap.set(key, [...existing, alert]);
    });

    const groups: AlertGroup[] = [];

    Array.from(groupMap.entries()).forEach(([key, groupAlerts]) => {
      const firstAlert = groupAlerts[0];
      if (!firstAlert) return;

      // Sort by started_at to find most recent
      const sortedByTime = [...groupAlerts].sort(
        (a, b) =>
          new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
      );

      // Get timestamps
      const timestamps = groupAlerts.map((a) =>
        new Date(a.started_at).getTime(),
      );
      const firstFiredAt = new Date(Math.min(...timestamps)).toISOString();
      const lastUpdatedAt = new Date(Math.max(...timestamps)).toISOString();

      const mostRecent = sortedByTime[0];

      groups.push({
        groupKey: key,
        service: firstAlert.labels?.service,
        alertName: firstAlert.name,
        severity: getHighestSeverity(groupAlerts),
        state: groupAlerts.some((a) => a.state === "firing")
          ? ("firing" as const)
          : ("resolved" as const),
        count: groupAlerts.length,
        mostRecentAlert: mostRecent ?? firstAlert,
        alerts: groupAlerts,
        firstFiredAt,
        lastUpdatedAt,
      });
    });

    return groups;
  },
);

/**
 * Select filtered alert groups based on current filter settings (memoized).
 */
export const selectFilteredAlertGroups = createSelector(
  [selectAlertGroups, selectFilters],
  (groups, filters): AlertGroup[] =>
    groups.filter(
      (g) =>
        filters.severity.includes(g.severity) &&
        filters.state.includes(g.state),
    ),
);

/**
 * Select total count of alert groups.
 */
export const selectAlertGroupCount = createSelector(
  [selectAlertGroups],
  (groups): number => groups.length,
);

// =============================================================================
// Reducer Export
// =============================================================================

export default alertSlice.reducer;
