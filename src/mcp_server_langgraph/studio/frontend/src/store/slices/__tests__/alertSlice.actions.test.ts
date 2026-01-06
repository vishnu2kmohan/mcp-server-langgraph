/**
 * Alert Slice Actions Tests
 *
 * Tests for alert Redux slice actions and reducers.
 * Manages infrastructure alerts for Admin dashboard.
 *
 * Features:
 * - Add/update/remove alerts
 * - Severity filtering (critical, warning)
 * - Selected alert tracking
 * - Pending remediations
 * - Sound toggle
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
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
  selectPendingRemediations,
  selectSoundEnabled,
  selectFilters,
} from "../alertSlice";
import {
  createTestStore,
  createMockAlert,
  createMockRemediation,
} from "./alertSlice.fixtures";

describe("alertSlice actions", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("addAlert", () => {
    it("should add an alert to the state", () => {
      const store = createTestStore();
      const alert = createMockAlert({ alertId: "alert-001", name: "CPUHigh" });
      store.dispatch(addAlert(alert));
      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts).toHaveLength(1);
      expect(alerts[0].alertId).toBe("alert-001");
      expect(alerts[0].name).toBe("CPUHigh");
    });

    it("should prepend new alerts (newest first)", () => {
      const store = createTestStore();
      const alert1 = createMockAlert({ alertId: "alert-001", name: "First" });
      const alert2 = createMockAlert({ alertId: "alert-002", name: "Second" });
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

    it("should not add duplicate alerts (same alertId)", () => {
      const store = createTestStore();
      const alert1 = createMockAlert({ alertId: "alert-001", name: "First" });
      const alert2 = createMockAlert({
        alertId: "alert-001",
        name: "Duplicate",
      });
      store.dispatch(addAlert(alert1));
      store.dispatch(addAlert(alert2));
      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts).toHaveLength(1);
      expect(alerts[0].name).toBe("Duplicate");
    });
  });

  describe("updateAlert", () => {
    it("should update an existing alert", () => {
      const alert = createMockAlert({ alertId: "alert-001", state: "firing" });
      const store = createTestStore([alert]);
      store.dispatch(updateAlert({ alertId: "alert-001", state: "resolved" }));
      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts[0].state).toBe("resolved");
    });

    it("should not update non-existent alert", () => {
      const alert = createMockAlert({ alertId: "alert-001" });
      const store = createTestStore([alert]);
      store.dispatch(
        updateAlert({ alertId: "non-existent", state: "resolved" }),
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
        createMockAlert({ alertId: "alert-001" }),
        createMockAlert({ alertId: "alert-002" }),
      ];
      const store = createTestStore(alerts);
      store.dispatch(removeAlert("alert-001"));
      const state = store.getState();
      const currentAlerts = selectAlerts(state);
      expect(currentAlerts).toHaveLength(1);
      expect(currentAlerts[0].alertId).toBe("alert-002");
    });

    it("should clear selectedAlertId if removed alert was selected", () => {
      const alert = createMockAlert({ alertId: "alert-001" });
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
        const remediation = createMockRemediation({ remediationId: "rem-001" });
        store.dispatch(addPendingRemediation(remediation));
        const state = store.getState();
        const remediations = selectPendingRemediations(state);
        expect(remediations).toHaveLength(1);
        expect(remediations[0].remediationId).toBe("rem-001");
      });

      it("should not add duplicate remediation with same ID", () => {
        const remediation = createMockRemediation({ remediationId: "rem-001" });
        const store = createTestStore([], [remediation]);
        store.dispatch(addPendingRemediation(remediation));
        const state = store.getState();
        const remediations = selectPendingRemediations(state);
        expect(remediations).toHaveLength(1);
      });
    });

    describe("updateRemediation", () => {
      it("should update a remediation status", () => {
        const remediation = createMockRemediation({
          remediationId: "rem-001",
          status: "pending",
        });
        const store = createTestStore([], [remediation]);
        store.dispatch(
          updateRemediation({
            remediationId: "rem-001",
            status: "approved",
            approvedBy: "admin@example.com",
            approvedAt: new Date().toISOString(),
          }),
        );
        const state = store.getState();
        const remediations = selectPendingRemediations(state);
        expect(remediations[0].status).toBe("approved");
        expect(remediations[0].approvedBy).toBe("admin@example.com");
      });
    });

    describe("removePendingRemediation", () => {
      it("should remove a remediation by id", () => {
        const remediations = [
          createMockRemediation({ remediationId: "rem-001" }),
          createMockRemediation({ remediationId: "rem-002" }),
        ];
        const store = createTestStore([], remediations);
        store.dispatch(removePendingRemediation("rem-001"));
        const state = store.getState();
        const currentRemediations = selectPendingRemediations(state);
        expect(currentRemediations).toHaveLength(1);
        expect(currentRemediations[0].remediationId).toBe("rem-002");
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
          createMockAlert({ alertId: "alert-001" }),
          createMockAlert({ alertId: "alert-002" }),
        ];
        const store = createTestStore(alerts);
        store.dispatch(clearAlerts());
        const state = store.getState();
        expect(selectAlerts(state)).toHaveLength(0);
      });

      it("should clear selected alert id", () => {
        const alert = createMockAlert({ alertId: "alert-001" });
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
          createMockAlert({ alertId: "alert-001", state: "firing" }),
          createMockAlert({ alertId: "alert-002", state: "resolved" }),
          createMockAlert({ alertId: "alert-003", state: "firing" }),
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
          createMockAlert({ alertId: "alert-001", state: "firing" }),
          createMockAlert({ alertId: "alert-002", state: "resolved" }),
        ];
        const store = createTestStore(alerts);
        store.dispatch(setSelectedAlertId("alert-002"));
        expect(selectSelectedAlertId(store.getState())).toBe("alert-002");
        store.dispatch(clearResolvedAlerts());
        expect(selectSelectedAlertId(store.getState())).toBeNull();
      });
    });
  });

  describe("Backend compatibility", () => {
    it("Alert interface should use startedAt/endedAt field names matching frontend", () => {
      const alert = {
        alertId: "alert-001",
        name: "CPUHigh",
        severity: "critical" as const,
        state: "firing" as const,
        message: "High CPU usage",
        labels: { instance: "node-1" },
        annotations: {},
        startedAt: "2025-12-20T10:00:00Z",
        endedAt: null,
        fingerprint: "fp-123",
      };
      const store = createTestStore();
      store.dispatch(addAlert(alert));
      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts).toHaveLength(1);
      expect(alerts[0].startedAt).toBe("2025-12-20T10:00:00Z");
      expect(alerts[0].endedAt).toBeNull();
    });

    it("should accept alert with resolved state having endedAt", () => {
      const resolvedAlert = {
        alertId: "alert-002",
        name: "DiskWarning",
        severity: "warning" as const,
        state: "resolved" as const,
        message: "Disk space warning",
        labels: {},
        annotations: {},
        startedAt: "2025-12-20T10:00:00Z",
        endedAt: "2025-12-20T10:30:00Z",
        fingerprint: "fp-456",
      };
      const store = createTestStore();
      store.dispatch(addAlert(resolvedAlert));
      const state = store.getState();
      const alerts = selectAlerts(state);
      expect(alerts[0].startedAt).toBe("2025-12-20T10:00:00Z");
      expect(alerts[0].endedAt).toBe("2025-12-20T10:30:00Z");
    });
  });
});
