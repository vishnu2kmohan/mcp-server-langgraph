/**
 * alertSlice Test Fixtures
 *
 * Shared utilities and fixtures for alertSlice test shards.
 */

import { configureStore } from "@reduxjs/toolkit";
import alertReducer from "../alertSlice";
import type { Alert, RemediationRequest, AlertFilters } from "../alertSlice";

// =============================================================================
// STORE FACTORY
// =============================================================================

export const createTestStore = (
  initialAlerts: Alert[] = [],
  initialRemediations: RemediationRequest[] = [],
  soundEnabled = true,
  filters: AlertFilters = {
    severity: ["critical", "warning"],
    state: ["firing"],
  },
) => {
  return configureStore({
    reducer: {
      alerts: alertReducer,
    },
    preloadedState: {
      alerts: {
        alerts: initialAlerts,
        selectedAlertId: null,
        pendingRemediations: initialRemediations,
        soundEnabled,
        lastCriticalAlertTime: null,
        filters,
      },
    },
  });
};

// =============================================================================
// MOCK FACTORIES
// =============================================================================

let alertIdCounter = 0;
let remediationIdCounter = 0;

export const createMockAlert = (overrides: Partial<Alert> = {}): Alert => {
  const id = overrides.alertId ?? `alert-${++alertIdCounter}`;
  return {
    alertId: id,
    name: "TestAlert",
    severity: "critical",
    state: "firing",
    message: "Test alert message",
    labels: { service: "test-service" },
    annotations: {},
    startedAt: new Date().toISOString(),
    endedAt: null,
    fingerprint: `fp-${alertIdCounter}`,
    ...overrides,
  };
};

export const createMockRemediation = (
  overrides: Partial<RemediationRequest> = {},
): RemediationRequest => {
  const id = overrides.remediationId ?? `rem-${++remediationIdCounter}`;
  return {
    remediationId: id,
    alertId: "alert-001",
    alertName: "TestAlert",
    severity: "critical",
    stepNumber: 1,
    action: "restart",
    description: "Restart the service",
    command: "kubectl rollout restart deployment/test",
    riskLevel: "medium",
    status: "pending",
    requestedAt: new Date().toISOString(),
    approvedBy: null,
    approvedAt: null,
    reason: null,
    recommendationId: "rec-001",
    ...overrides,
  };
};

// Re-export types
export type { Alert, RemediationRequest, AlertFilters };
