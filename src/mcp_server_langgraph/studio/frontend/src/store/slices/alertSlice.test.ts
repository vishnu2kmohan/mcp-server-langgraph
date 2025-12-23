/**
 * Alert Slice Tests
 *
 * TDD tests for the alert Redux slice.
 * Manages infrastructure alerts for Admin dashboard.
 *
 * Features:
 * - Add/update/remove alerts
 * - Severity filtering (critical, warning)
 * - Selected alert tracking
 * - Pending remediations
 * - Sound toggle
 * - Critical alert count selector
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import alertReducer, {
  addAlert,
  updateAlert,
  removeAlert,
  setSelectedAlertId,
  addPendingRemediation,
  updateRemediation,
  removePendingRemediation,
  toggleSound,
  setSoundEnabled,
  setFilters,
  clearAlerts,
  clearResolvedAlerts,
  selectAlerts,
  selectSelectedAlertId,
  selectSelectedAlert,
  selectPendingRemediations,
  selectSoundEnabled,
  selectFilters,
  selectCriticalAlertCount,
  selectWarningAlertCount,
  selectFilteredAlerts,
  type Alert,
  type RemediationRequest,
  type AlertFilters,
} from "./alertSlice";

// =============================================================================
// Test Helpers
// =============================================================================

const createTestStore = (
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

const createMockAlert = (overrides: Partial<Alert> = {}): Alert => ({
  alert_id: `alert-${Math.random().toString(36).slice(2, 9)}`,
  name: "TestAlert",
  severity: "critical",
  state: "firing",
  message: "Test alert message",
  labels: { service: "test-service" },
  annotations: {},
  started_at: new Date().toISOString(),
  ended_at: null,
  fingerprint: `fp-${Math.random().toString(36).slice(2, 9)}`,
  ...overrides,
});

const createMockRemediation = (
  overrides: Partial<RemediationRequest> = {},
): RemediationRequest => ({
  remediation_id: `rem-${Math.random().toString(36).slice(2, 9)}`,
  alert_id: "alert-001",
  alert_name: "TestAlert",
  severity: "critical",
  step_number: 1,
  action: "restart",
  description: "Restart the service",
  command: "kubectl rollout restart deployment/test",
  risk_level: "medium",
  status: "pending",
  requested_at: new Date().toISOString(),
  approved_by: null,
  approved_at: null,
  reason: null,
  recommendation_id: "rec-001",
  ...overrides,
});

// =============================================================================
// Tests
// =============================================================================

describe("alertSlice", () => {
  describe("addAlert", () => {
    it("should add an alert to the state", () => {
      const store = createTestStore();
      const alert = createMockAlert({ alert_id: "alert-001", name: "CPUHigh" });

      store.dispatch(addAlert(alert));

      const state = store.getState();
      const alerts = selectAlerts(state);

      expect(alerts).toHaveLength(1);
      expect(alerts[0].alert_id).toBe("alert-001");
      expect(alerts[0].name).toBe("CPUHigh");
    });

    it("should prepend new alerts (newest first)", () => {
      const store = createTestStore();
      const alert1 = createMockAlert({ alert_id: "alert-001", name: "First" });
      const alert2 = createMockAlert({ alert_id: "alert-002", name: "Second" });

      store.dispatch(addAlert(alert1));
      store.dispatch(addAlert(alert2));

      const state = store.getState();
      const alerts = selectAlerts(state);

      expect(alerts).toHaveLength(2);
      expect(alerts[0].name).toBe("Second");
      expect(alerts[1].name).toBe("First");
    });

    it("should update lastCriticalAlertTime for critical alerts", () => {
      const store = createTestStore();
      const alert = createMockAlert({ severity: "critical" });

      const beforeTime = Date.now();
      store.dispatch(addAlert(alert));
      const afterTime = Date.now();

      const state = store.getState();
      const lastTime = state.alerts.lastCriticalAlertTime;

      expect(lastTime).toBeGreaterThanOrEqual(beforeTime);
      expect(lastTime).toBeLessThanOrEqual(afterTime);
    });

    it("should not update lastCriticalAlertTime for warning alerts", () => {
      const store = createTestStore();
      const alert = createMockAlert({ severity: "warning" });

      store.dispatch(addAlert(alert));

      const state = store.getState();
      expect(state.alerts.lastCriticalAlertTime).toBeNull();
    });

    it("should not add duplicate alerts (same alert_id)", () => {
      const store = createTestStore();
      const alert1 = createMockAlert({ alert_id: "alert-001", name: "First" });
      const alert2 = createMockAlert({
        alert_id: "alert-001",
        name: "Duplicate",
      });

      store.dispatch(addAlert(alert1));
      store.dispatch(addAlert(alert2));

      const state = store.getState();
      const alerts = selectAlerts(state);

      expect(alerts).toHaveLength(1);
      // Should update the existing alert
      expect(alerts[0].name).toBe("Duplicate");
    });
  });

  describe("updateAlert", () => {
    it("should update an existing alert", () => {
      const alert = createMockAlert({ alert_id: "alert-001", state: "firing" });
      const store = createTestStore([alert]);

      store.dispatch(updateAlert({ alert_id: "alert-001", state: "resolved" }));

      const state = store.getState();
      const alerts = selectAlerts(state);

      expect(alerts[0].state).toBe("resolved");
    });

    it("should not update non-existent alert", () => {
      const alert = createMockAlert({ alert_id: "alert-001" });
      const store = createTestStore([alert]);

      store.dispatch(
        updateAlert({ alert_id: "non-existent", state: "resolved" }),
      );

      const state = store.getState();
      const alerts = selectAlerts(state);

      expect(alerts).toHaveLength(1);
      expect(alerts[0].state).toBe("firing");
    });
  });

  describe("removeAlert", () => {
    it("should remove an alert by id", () => {
      const alerts = [
        createMockAlert({ alert_id: "alert-001" }),
        createMockAlert({ alert_id: "alert-002" }),
      ];
      const store = createTestStore(alerts);

      store.dispatch(removeAlert("alert-001"));

      const state = store.getState();
      const currentAlerts = selectAlerts(state);

      expect(currentAlerts).toHaveLength(1);
      expect(currentAlerts[0].alert_id).toBe("alert-002");
    });

    it("should clear selectedAlertId if removed alert was selected", () => {
      const alert = createMockAlert({ alert_id: "alert-001" });
      const store = createTestStore([alert]);

      store.dispatch(setSelectedAlertId("alert-001"));
      store.dispatch(removeAlert("alert-001"));

      const state = store.getState();
      expect(selectSelectedAlertId(state)).toBeNull();
    });
  });

  describe("setSelectedAlertId", () => {
    it("should set the selected alert id", () => {
      const store = createTestStore();

      store.dispatch(setSelectedAlertId("alert-001"));

      const state = store.getState();
      expect(selectSelectedAlertId(state)).toBe("alert-001");
    });

    it("should allow clearing selection with null", () => {
      const store = createTestStore();

      store.dispatch(setSelectedAlertId("alert-001"));
      store.dispatch(setSelectedAlertId(null));

      const state = store.getState();
      expect(selectSelectedAlertId(state)).toBeNull();
    });
  });

  describe("Remediation actions", () => {
    describe("addPendingRemediation", () => {
      it("should add a pending remediation", () => {
        const store = createTestStore();
        const remediation = createMockRemediation({
          remediation_id: "rem-001",
        });

        store.dispatch(addPendingRemediation(remediation));

        const state = store.getState();
        const remediations = selectPendingRemediations(state);

        expect(remediations).toHaveLength(1);
        expect(remediations[0].remediation_id).toBe("rem-001");
      });

      it("should not add duplicate remediation with same ID", () => {
        const remediation = createMockRemediation({
          remediation_id: "rem-001",
        });
        const store = createTestStore([], [remediation]);

        // Try to add the same remediation again
        store.dispatch(addPendingRemediation(remediation));

        const state = store.getState();
        const remediations = selectPendingRemediations(state);

        expect(remediations).toHaveLength(1);
      });
    });

    describe("updateRemediation", () => {
      it("should update a remediation status", () => {
        const remediation = createMockRemediation({
          remediation_id: "rem-001",
          status: "pending",
        });
        const store = createTestStore([], [remediation]);

        store.dispatch(
          updateRemediation({
            remediation_id: "rem-001",
            status: "approved",
            approved_by: "admin@example.com",
            approved_at: new Date().toISOString(),
          }),
        );

        const state = store.getState();
        const remediations = selectPendingRemediations(state);

        expect(remediations[0].status).toBe("approved");
        expect(remediations[0].approved_by).toBe("admin@example.com");
      });
    });

    describe("removePendingRemediation", () => {
      it("should remove a remediation by id", () => {
        const remediations = [
          createMockRemediation({ remediation_id: "rem-001" }),
          createMockRemediation({ remediation_id: "rem-002" }),
        ];
        const store = createTestStore([], remediations);

        store.dispatch(removePendingRemediation("rem-001"));

        const state = store.getState();
        const currentRemediations = selectPendingRemediations(state);

        expect(currentRemediations).toHaveLength(1);
        expect(currentRemediations[0].remediation_id).toBe("rem-002");
      });
    });
  });

  describe("Sound actions", () => {
    describe("toggleSound", () => {
      it("should toggle sound enabled state", () => {
        const store = createTestStore([], [], true);

        store.dispatch(toggleSound());
        expect(selectSoundEnabled(store.getState())).toBe(false);

        store.dispatch(toggleSound());
        expect(selectSoundEnabled(store.getState())).toBe(true);
      });
    });

    describe("setSoundEnabled", () => {
      it("should set sound enabled to specific value", () => {
        const store = createTestStore([], [], true);

        store.dispatch(setSoundEnabled(false));
        expect(selectSoundEnabled(store.getState())).toBe(false);

        store.dispatch(setSoundEnabled(true));
        expect(selectSoundEnabled(store.getState())).toBe(true);
      });
    });
  });

  describe("Filter actions", () => {
    describe("setFilters", () => {
      it("should set severity filter", () => {
        const store = createTestStore();

        store.dispatch(setFilters({ severity: ["critical"] }));

        const state = store.getState();
        const filters = selectFilters(state);

        expect(filters.severity).toEqual(["critical"]);
      });

      it("should set state filter", () => {
        const store = createTestStore();

        store.dispatch(setFilters({ state: ["resolved"] }));

        const state = store.getState();
        const filters = selectFilters(state);

        expect(filters.state).toEqual(["resolved"]);
      });

      it("should merge filters with existing", () => {
        const store = createTestStore();

        store.dispatch(setFilters({ severity: ["critical"] }));
        store.dispatch(setFilters({ state: ["resolved"] }));

        const state = store.getState();
        const filters = selectFilters(state);

        expect(filters.severity).toEqual(["critical"]);
        expect(filters.state).toEqual(["resolved"]);
      });
    });
  });

  describe("Clear actions", () => {
    describe("clearAlerts", () => {
      it("should clear all alerts", () => {
        const alerts = [
          createMockAlert({ alert_id: "alert-001" }),
          createMockAlert({ alert_id: "alert-002" }),
        ];
        const store = createTestStore(alerts);

        store.dispatch(clearAlerts());

        const state = store.getState();
        expect(selectAlerts(state)).toHaveLength(0);
      });

      it("should clear selected alert id", () => {
        const alert = createMockAlert({ alert_id: "alert-001" });
        const store = createTestStore([alert]);

        store.dispatch(setSelectedAlertId("alert-001"));
        store.dispatch(clearAlerts());

        const state = store.getState();
        expect(selectSelectedAlertId(state)).toBeNull();
      });
    });

    describe("clearResolvedAlerts", () => {
      it("should remove only resolved alerts", () => {
        const alerts = [
          createMockAlert({ alert_id: "alert-001", state: "firing" }),
          createMockAlert({ alert_id: "alert-002", state: "resolved" }),
          createMockAlert({ alert_id: "alert-003", state: "firing" }),
        ];
        const store = createTestStore(alerts);

        store.dispatch(clearResolvedAlerts());

        const state = store.getState();
        const currentAlerts = selectAlerts(state);

        expect(currentAlerts).toHaveLength(2);
        expect(currentAlerts.every((a) => a.state === "firing")).toBe(true);
      });

      it("should clear selection if selected alert is resolved", () => {
        const alerts = [
          createMockAlert({ alert_id: "alert-001", state: "firing" }),
          createMockAlert({ alert_id: "alert-002", state: "resolved" }),
        ];
        const store = createTestStore(alerts);

        // Select the resolved alert
        store.dispatch(setSelectedAlertId("alert-002"));
        expect(selectSelectedAlertId(store.getState())).toBe("alert-002");

        // Clear resolved alerts
        store.dispatch(clearResolvedAlerts());

        // Selection should be cleared
        expect(selectSelectedAlertId(store.getState())).toBeNull();
      });
    });
  });

  describe("Selectors", () => {
    describe("selectSelectedAlert", () => {
      it("should return the selected alert", () => {
        const alert = createMockAlert({
          alert_id: "alert-001",
          name: "Selected",
        });
        const store = createTestStore([alert]);

        store.dispatch(setSelectedAlertId("alert-001"));

        const state = store.getState();
        const selected = selectSelectedAlert(state);

        expect(selected).toBeDefined();
        expect(selected?.name).toBe("Selected");
      });

      it("should return undefined if no alert selected", () => {
        const store = createTestStore();

        const state = store.getState();
        const selected = selectSelectedAlert(state);

        expect(selected).toBeUndefined();
      });
    });

    describe("selectCriticalAlertCount", () => {
      it("should return count of critical firing alerts", () => {
        const alerts = [
          createMockAlert({ severity: "critical", state: "firing" }),
          createMockAlert({ severity: "critical", state: "firing" }),
          createMockAlert({ severity: "warning", state: "firing" }),
          createMockAlert({ severity: "critical", state: "resolved" }),
        ];
        const store = createTestStore(alerts);

        const state = store.getState();
        const count = selectCriticalAlertCount(state);

        expect(count).toBe(2);
      });
    });

    describe("selectWarningAlertCount", () => {
      it("should return count of warning firing alerts", () => {
        const alerts = [
          createMockAlert({ severity: "critical", state: "firing" }),
          createMockAlert({ severity: "warning", state: "firing" }),
          createMockAlert({ severity: "warning", state: "firing" }),
          createMockAlert({ severity: "warning", state: "resolved" }),
        ];
        const store = createTestStore(alerts);

        const state = store.getState();
        const count = selectWarningAlertCount(state);

        expect(count).toBe(2);
      });
    });

    describe("selectFilteredAlerts", () => {
      it("should filter alerts by severity", () => {
        const alerts = [
          createMockAlert({
            alert_id: "1",
            severity: "critical",
            state: "firing",
          }),
          createMockAlert({
            alert_id: "2",
            severity: "warning",
            state: "firing",
          }),
          createMockAlert({
            alert_id: "3",
            severity: "critical",
            state: "firing",
          }),
        ];
        const store = createTestStore(alerts, [], true, {
          severity: ["critical"],
          state: ["firing"],
        });

        const state = store.getState();
        const filtered = selectFilteredAlerts(state);

        expect(filtered).toHaveLength(2);
        expect(filtered.every((a) => a.severity === "critical")).toBe(true);
      });

      it("should filter alerts by state", () => {
        const alerts = [
          createMockAlert({
            alert_id: "1",
            severity: "critical",
            state: "firing",
          }),
          createMockAlert({
            alert_id: "2",
            severity: "critical",
            state: "resolved",
          }),
          createMockAlert({
            alert_id: "3",
            severity: "warning",
            state: "firing",
          }),
        ];
        const store = createTestStore(alerts, [], true, {
          severity: ["critical", "warning"],
          state: ["firing"],
        });

        const state = store.getState();
        const filtered = selectFilteredAlerts(state);

        expect(filtered).toHaveLength(2);
        expect(filtered.every((a) => a.state === "firing")).toBe(true);
      });

      it("should filter by both severity and state", () => {
        const alerts = [
          createMockAlert({
            alert_id: "1",
            severity: "critical",
            state: "firing",
          }),
          createMockAlert({
            alert_id: "2",
            severity: "critical",
            state: "resolved",
          }),
          createMockAlert({
            alert_id: "3",
            severity: "warning",
            state: "firing",
          }),
        ];
        const store = createTestStore(alerts, [], true, {
          severity: ["critical"],
          state: ["firing"],
        });

        const state = store.getState();
        const filtered = selectFilteredAlerts(state);

        expect(filtered).toHaveLength(1);
        expect(filtered[0].alert_id).toBe("1");
      });
    });
  });

  describe("Backend compatibility", () => {
    it("Alert interface should use started_at/ended_at field names matching backend", () => {
      // This test ensures the frontend Alert type matches backend Alert model field names
      // Backend sends: started_at, ended_at (from broadcaster.py alert_to_message)
      // Frontend must accept: started_at, ended_at
      const backendAlert = {
        alert_id: "alert-001",
        name: "CPUHigh",
        severity: "critical" as const,
        state: "firing" as const,
        message: "High CPU usage",
        labels: { instance: "node-1" },
        annotations: {},
        started_at: "2025-12-20T10:00:00Z", // Backend field name
        ended_at: null, // Backend field name
        fingerprint: "fp-123",
      };

      const store = createTestStore();
      store.dispatch(addAlert(backendAlert));

      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts).toHaveLength(1);
      expect(alerts[0].started_at).toBe("2025-12-20T10:00:00Z");
      expect(alerts[0].ended_at).toBeNull();
    });

    it("should accept backend format with resolved alert having ended_at", () => {
      const resolvedAlert = {
        alert_id: "alert-002",
        name: "DiskWarning",
        severity: "warning" as const,
        state: "resolved" as const,
        message: "Disk space warning",
        labels: {},
        annotations: {},
        started_at: "2025-12-20T10:00:00Z",
        ended_at: "2025-12-20T10:30:00Z",
        fingerprint: "fp-456",
      };

      const store = createTestStore();
      store.dispatch(addAlert(resolvedAlert));

      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts[0].started_at).toBe("2025-12-20T10:00:00Z");
      expect(alerts[0].ended_at).toBe("2025-12-20T10:30:00Z");
    });
  });
});

describe("alertSlice localStorage persistence", () => {
  const STORAGE_KEY = "studio-alert-sound-enabled";

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("loadSoundPreference", () => {
    it("should return true (default) when localStorage is empty", async () => {
      const { loadSoundPreference } = await import("./alertSlice");
      expect(loadSoundPreference()).toBe(true);
    });

    it("should return false when localStorage has false", async () => {
      localStorage.setItem(STORAGE_KEY, "false");
      const { loadSoundPreference } = await import("./alertSlice");
      expect(loadSoundPreference()).toBe(false);
    });

    it("should return true when localStorage has true", async () => {
      localStorage.setItem(STORAGE_KEY, "true");
      const { loadSoundPreference } = await import("./alertSlice");
      expect(loadSoundPreference()).toBe(true);
    });
  });

  describe("saveSoundPreference", () => {
    it("should save sound preference to localStorage", async () => {
      const { saveSoundPreference } = await import("./alertSlice");

      saveSoundPreference(false);
      expect(localStorage.getItem(STORAGE_KEY)).toBe("false");

      saveSoundPreference(true);
      expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
    });
  });

  describe("toggleSound with persistence", () => {
    it("should persist sound state when toggling", async () => {
      const { default: alertReducer, toggleSound } =
        await import("./alertSlice");

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts: [],
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      // Toggle to false
      store.dispatch(toggleSound());

      // Should persist to localStorage
      expect(localStorage.getItem(STORAGE_KEY)).toBe("false");
    });
  });

  describe("setSoundEnabled with persistence", () => {
    it("should persist sound state when setting value", async () => {
      const { default: alertReducer, setSoundEnabled } =
        await import("./alertSlice");

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts: [],
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      // Set to false
      store.dispatch(setSoundEnabled(false));
      expect(localStorage.getItem(STORAGE_KEY)).toBe("false");

      // Set to true
      store.dispatch(setSoundEnabled(true));
      expect(localStorage.getItem(STORAGE_KEY)).toBe("true");
    });
  });

  describe("initializeSoundFromStorage action", () => {
    it("should initialize sound state from localStorage", async () => {
      // Set localStorage before importing
      localStorage.setItem(STORAGE_KEY, "false");

      const {
        default: alertReducer,
        initializeSoundFromStorage,
        selectSoundEnabled,
      } = await import("./alertSlice");

      const store = configureStore({
        reducer: { alerts: alertReducer },
      });

      // Initially true (default)
      expect(selectSoundEnabled(store.getState())).toBe(true);

      // Dispatch init action
      store.dispatch(initializeSoundFromStorage());

      // Should now be false from localStorage
      expect(selectSoundEnabled(store.getState())).toBe(false);
    });

    it("should keep default true when localStorage has no value", async () => {
      // Clear localStorage
      localStorage.clear();

      const {
        default: alertReducer,
        initializeSoundFromStorage,
        selectSoundEnabled,
      } = await import("./alertSlice");

      const store = configureStore({
        reducer: { alerts: alertReducer },
      });

      store.dispatch(initializeSoundFromStorage());

      // Should remain true (default)
      expect(selectSoundEnabled(store.getState())).toBe(true);
    });
  });
});

// =============================================================================
// Alert Grouping Selectors Tests (Phase 6)
// =============================================================================

describe("alertSlice grouping selectors", () => {
  describe("selectAlertGroups", () => {
    it("should group alerts by service and alertname", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          started_at: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "warning",
          state: "firing",
          started_at: "2025-12-20T10:05:00Z",
        }),
        createMockAlert({
          alert_id: "3",
          name: "MemoryHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          started_at: "2025-12-20T10:10:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());

      expect(groups).toHaveLength(2); // CPUHigh and MemoryHigh

      const cpuGroup = groups.find((g) => g.alertName === "CPUHigh");
      expect(cpuGroup).toBeDefined();
      expect(cpuGroup?.count).toBe(2);
      expect(cpuGroup?.service).toBe("api-server");

      const memoryGroup = groups.find((g) => g.alertName === "MemoryHigh");
      expect(memoryGroup).toBeDefined();
      expect(memoryGroup?.count).toBe(1);
    });

    it("should use highest severity in group", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "warning",
          state: "firing",
          started_at: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          started_at: "2025-12-20T10:05:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());
      const cpuGroup = groups.find((g) => g.alertName === "CPUHigh");

      // Critical is higher severity than warning
      expect(cpuGroup?.severity).toBe("critical");
    });

    it("should set state to firing if any alert in group is firing", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
          started_at: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          started_at: "2025-12-20T10:05:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: {
              severity: ["critical", "warning"],
              state: ["firing", "resolved"],
            },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());
      const cpuGroup = groups.find((g) => g.alertName === "CPUHigh");

      expect(cpuGroup?.state).toBe("firing");
    });

    it("should set state to resolved if all alerts are resolved", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
          started_at: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
          started_at: "2025-12-20T10:05:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: {
              severity: ["critical", "warning"],
              state: ["firing", "resolved"],
            },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());
      const cpuGroup = groups.find((g) => g.alertName === "CPUHigh");

      expect(cpuGroup?.state).toBe("resolved");
    });

    it("should identify most recent alert in group", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          started_at: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          started_at: "2025-12-20T10:30:00Z", // Most recent
        }),
        createMockAlert({
          alert_id: "3",
          name: "CPUHigh",
          labels: { service: "api-server" },
          started_at: "2025-12-20T10:15:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());
      const cpuGroup = groups.find((g) => g.alertName === "CPUHigh");

      expect(cpuGroup?.mostRecentAlert.alert_id).toBe("2");
    });

    it("should use unknown for service when not present in labels", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "SystemAlert",
          labels: {}, // No service label
          started_at: "2025-12-20T10:00:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());
      expect(groups[0].groupKey).toBe("unknown:SystemAlert");
      expect(groups[0].service).toBeUndefined();
    });

    it("should group alerts from different services separately", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          started_at: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "worker-service" },
          started_at: "2025-12-20T10:05:00Z",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());

      expect(groups).toHaveLength(2);
      expect(groups.some((g) => g.service === "api-server")).toBe(true);
      expect(groups.some((g) => g.service === "worker-service")).toBe(true);
    });

    it("should return empty array when no alerts", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("./alertSlice");

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts: [],
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectAlertGroups(store.getState());
      expect(groups).toHaveLength(0);
    });
  });

  describe("selectFilteredAlertGroups", () => {
    it("should filter groups by severity", async () => {
      const { default: alertReducer, selectFilteredAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alert_id: "2",
          name: "MemoryWarning",
          labels: { service: "api-server" },
          severity: "warning",
          state: "firing",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical"], state: ["firing"] },
          },
        },
      });

      const groups = selectFilteredAlertGroups(store.getState());

      expect(groups).toHaveLength(1);
      expect(groups[0].alertName).toBe("CPUHigh");
    });

    it("should filter groups by state", async () => {
      const { default: alertReducer, selectFilteredAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alert_id: "2",
          name: "MemoryHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const groups = selectFilteredAlertGroups(store.getState());

      expect(groups).toHaveLength(1);
      expect(groups[0].alertName).toBe("CPUHigh");
    });

    it("should return all groups when no filters applied", async () => {
      const { default: alertReducer, selectFilteredAlertGroups } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alert_id: "2",
          name: "MemoryWarning",
          labels: { service: "api-server" },
          severity: "warning",
          state: "resolved",
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: {
              severity: ["critical", "warning"],
              state: ["firing", "resolved"],
            },
          },
        },
      });

      const groups = selectFilteredAlertGroups(store.getState());

      expect(groups).toHaveLength(2);
    });
  });

  describe("selectAlertGroupCount", () => {
    it("should return total count of alert groups", async () => {
      const { default: alertReducer, selectAlertGroupCount } =
        await import("./alertSlice");

      const alerts = [
        createMockAlert({
          alert_id: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
        }),
        createMockAlert({
          alert_id: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
        }),
        createMockAlert({
          alert_id: "3",
          name: "MemoryHigh",
          labels: { service: "api-server" },
        }),
        createMockAlert({
          alert_id: "4",
          name: "DiskHigh",
          labels: { service: "worker" },
        }),
      ];

      const store = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts,
            selectedAlertId: null,
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      const count = selectAlertGroupCount(store.getState());
      expect(count).toBe(3); // CPUHigh, MemoryHigh, DiskHigh
    });
  });
});
