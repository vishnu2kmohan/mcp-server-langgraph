/**
 * Alert Slice Selectors Tests
 *
 * Tests for alert Redux slice selectors, filtering, and grouping.
 *
 * Features:
 * - Critical alert count selector
 * - Warning alert count selector
 * - Filtered alerts selector
 * - Alert grouping selectors (Phase 6)
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import _alertReducer, {
  selectSelectedAlert,
  selectCriticalAlertCount,
  selectWarningAlertCount,
  selectFilteredAlerts,
  selectAlertGroups as _selectAlertGroups,
  selectFilteredAlertGroups as _selectFilteredAlertGroups,
  selectAlertGroupCount as _selectAlertGroupCount,
  setSelectedAlertId,
} from "../alertSlice";
import { createTestStore, createMockAlert } from "./alertSlice.fixtures";

describe("alertSlice selectors", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("selectSelectedAlert", () => {
    it("should return the selected alert", () => {
      const alert = createMockAlert({ alertId: "alert-001", name: "Selected" });
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
          alertId: "1",
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({ alertId: "2", severity: "warning", state: "firing" }),
        createMockAlert({
          alertId: "3",
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
          alertId: "1",
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alertId: "2",
          severity: "critical",
          state: "resolved",
        }),
        createMockAlert({ alertId: "3", severity: "warning", state: "firing" }),
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
          alertId: "1",
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alertId: "2",
          severity: "critical",
          state: "resolved",
        }),
        createMockAlert({ alertId: "3", severity: "warning", state: "firing" }),
      ];
      const store = createTestStore(alerts, [], true, {
        severity: ["critical"],
        state: ["firing"],
      });
      const state = store.getState();
      const filtered = selectFilteredAlerts(state);
      expect(filtered).toHaveLength(1);
      expect(filtered[0].alertId).toBe("1");
    });
  });
});

describe("alertSlice grouping selectors", () => {
  describe("selectAlertGroups", () => {
    it("should group alerts by service and alertname", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          startedAt: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "warning",
          state: "firing",
          startedAt: "2025-12-20T10:05:00Z",
        }),
        createMockAlert({
          alertId: "3",
          name: "MemoryHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          startedAt: "2025-12-20T10:10:00Z",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "warning",
          state: "firing",
          startedAt: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          startedAt: "2025-12-20T10:05:00Z",
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
      expect(cpuGroup?.severity).toBe("critical");
    });

    it("should set state to firing if any alert in group is firing", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
          startedAt: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
          startedAt: "2025-12-20T10:05:00Z",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
          startedAt: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "resolved",
          startedAt: "2025-12-20T10:05:00Z",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          startedAt: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
          startedAt: "2025-12-20T10:30:00Z",
        }),
        createMockAlert({
          alertId: "3",
          name: "CPUHigh",
          labels: { service: "api-server" },
          startedAt: "2025-12-20T10:15:00Z",
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
      expect(cpuGroup?.mostRecentAlert.alertId).toBe("2");
    });

    it("should use unknown for service when not present in labels", async () => {
      const { default: alertReducer, selectAlertGroups } =
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "SystemAlert",
          labels: {},
          startedAt: "2025-12-20T10:00:00Z",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          startedAt: "2025-12-20T10:00:00Z",
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "worker-service" },
          startedAt: "2025-12-20T10:05:00Z",
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
        await import("../alertSlice");
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alertId: "2",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alertId: "2",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
          severity: "critical",
          state: "firing",
        }),
        createMockAlert({
          alertId: "2",
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
        await import("../alertSlice");
      const alerts = [
        createMockAlert({
          alertId: "1",
          name: "CPUHigh",
          labels: { service: "api-server" },
        }),
        createMockAlert({
          alertId: "2",
          name: "CPUHigh",
          labels: { service: "api-server" },
        }),
        createMockAlert({
          alertId: "3",
          name: "MemoryHigh",
          labels: { service: "api-server" },
        }),
        createMockAlert({
          alertId: "4",
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
      expect(count).toBe(3);
    });
  });
});
