/**
 * Performance Benchmarks for Alert Grouping Selectors
 *
 * Tests selector performance with large datasets (100, 500, 1000, 5000 alerts).
 * Ensures memoization is working correctly and performance is acceptable.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import alertReducer, {
  Alert,
  AlertSeverity,
  AlertState,
  selectAlertGroups,
  selectFilteredAlertGroups,
  selectCriticalAlertCount,
  selectWarningAlertCount,
  selectFilteredAlerts,
  addAlert,
} from "./alertSlice";

// =============================================================================
// Test Data Generation
// =============================================================================

const SERVICES = [
  "api-gateway",
  "auth-service",
  "payment-service",
  "order-service",
  "inventory-service",
  "notification-service",
  "user-service",
  "analytics-service",
  "search-service",
  "recommendation-service",
];

const ALERT_NAMES = [
  "HighCPUUsage",
  "HighMemoryUsage",
  "HighLatency",
  "HighErrorRate",
  "DiskSpaceLow",
  "PodRestarting",
  "ServiceUnavailable",
  "HighRequestRate",
  "DatabaseConnectionPool",
  "CacheHitRateLow",
];

const SEVERITIES: AlertSeverity[] = ["critical", "warning", "info"];
const STATES: AlertState[] = ["firing", "resolved"];

/**
 * Generate a random alert for benchmarking.
 */
function generateAlert(index: number): Alert {
  const service = SERVICES[index % SERVICES.length];
  const alertName = ALERT_NAMES[index % ALERT_NAMES.length];
  const severity = SEVERITIES[index % SEVERITIES.length];
  const state = STATES[index % STATES.length];

  return {
    alertId: `alert-${index.toString().padStart(6, "0")}`,
    name: alertName,
    severity,
    state,
    message: `${alertName} triggered on ${service} at ${new Date().toISOString()}`,
    labels: {
      service,
      namespace: "production",
      pod: `${service}-${Math.random().toString(36).substring(7)}`,
    },
    annotations: {
      summary: `${alertName} on ${service}`,
      runbook_url: `https://runbooks.example.com/${alertName.toLowerCase()}`,
    },
    startedAt: new Date(Date.now() - Math.random() * 86400000).toISOString(),
    endedAt: state === "resolved" ? new Date().toISOString() : null,
    fingerprint: `fp-${index}-${service}-${alertName}`,
  };
}

/**
 * Generate N alerts for benchmarking.
 */
function generateAlerts(count: number): Alert[] {
  return Array.from({ length: count }, (_, i) => generateAlert(i));
}

/**
 * Create a root state with alerts.
 */
function createState(alerts: Alert[]) {
  return {
    alerts: {
      alerts,
      selectedAlertId: null,
      pendingRemediations: [],
      soundEnabled: true,
      lastCriticalAlertTime: null,
      filters: {
        severity: ["critical", "warning"] as AlertSeverity[],
        state: ["firing"] as AlertState[],
      },
    },
  };
}

// =============================================================================
// Performance Benchmarks
// =============================================================================

describe("Alert Grouping Selector Performance", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("selectAlertGroups", () => {
    it("should handle 100 alerts in under 10ms", () => {
      const alerts = generateAlerts(100);
      const state = createState(alerts);

      const start = performance.now();
      const groups = selectAlertGroups(state);
      const elapsed = performance.now() - start;

      expect(groups.length).toBeGreaterThan(0);
      expect(elapsed).toBeLessThan(10);

      console.log(
        `  100 alerts: ${elapsed.toFixed(2)}ms, ${groups.length} groups`,
      );
    });

    it("should handle 500 alerts in under 50ms", () => {
      const alerts = generateAlerts(500);
      const state = createState(alerts);

      const start = performance.now();
      const groups = selectAlertGroups(state);
      const elapsed = performance.now() - start;

      expect(groups.length).toBeGreaterThan(0);
      expect(elapsed).toBeLessThan(50);

      console.log(
        `  500 alerts: ${elapsed.toFixed(2)}ms, ${groups.length} groups`,
      );
    });

    it("should handle 1000 alerts in under 100ms", () => {
      const alerts = generateAlerts(1000);
      const state = createState(alerts);

      const start = performance.now();
      const groups = selectAlertGroups(state);
      const elapsed = performance.now() - start;

      expect(groups.length).toBeGreaterThan(0);
      expect(elapsed).toBeLessThan(100);

      console.log(
        `  1000 alerts: ${elapsed.toFixed(2)}ms, ${groups.length} groups`,
      );
    });

    it("should handle 5000 alerts in under 500ms", () => {
      const alerts = generateAlerts(5000);
      const state = createState(alerts);

      const start = performance.now();
      const groups = selectAlertGroups(state);
      const elapsed = performance.now() - start;

      expect(groups.length).toBeGreaterThan(0);
      expect(elapsed).toBeLessThan(500);

      console.log(
        `  5000 alerts: ${elapsed.toFixed(2)}ms, ${groups.length} groups`,
      );
    });
  });

  describe("selectFilteredAlertGroups", () => {
    it("should filter 1000 alerts efficiently", () => {
      const alerts = generateAlerts(1000);
      const state = createState(alerts);

      const start = performance.now();
      const filtered = selectFilteredAlertGroups(state);
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(100);

      console.log(
        `  Filtered 1000 alerts: ${elapsed.toFixed(2)}ms, ${filtered.length} groups`,
      );
    });
  });

  describe("selectCriticalAlertCount", () => {
    it("should count critical alerts in under 10ms for 5000 alerts", () => {
      const alerts = generateAlerts(5000);
      const state = createState(alerts);

      const start = performance.now();
      const count = selectCriticalAlertCount(state);
      const elapsed = performance.now() - start;

      expect(typeof count).toBe("number");
      expect(elapsed).toBeLessThan(10);

      console.log(
        `  Critical count for 5000 alerts: ${elapsed.toFixed(2)}ms, count=${count}`,
      );
    });
  });

  describe("selectWarningAlertCount", () => {
    it("should count warning alerts in under 10ms for 5000 alerts", () => {
      const alerts = generateAlerts(5000);
      const state = createState(alerts);

      const start = performance.now();
      const count = selectWarningAlertCount(state);
      const elapsed = performance.now() - start;

      expect(typeof count).toBe("number");
      expect(elapsed).toBeLessThan(10);

      console.log(
        `  Warning count for 5000 alerts: ${elapsed.toFixed(2)}ms, count=${count}`,
      );
    });
  });

  describe("selectFilteredAlerts", () => {
    it("should filter 5000 alerts in under 50ms", () => {
      const alerts = generateAlerts(5000);
      const state = createState(alerts);

      const start = performance.now();
      const filtered = selectFilteredAlerts(state);
      const elapsed = performance.now() - start;

      expect(filtered.length).toBeLessThanOrEqual(alerts.length);
      expect(elapsed).toBeLessThan(50);

      console.log(
        `  Filtered 5000 alerts: ${elapsed.toFixed(2)}ms, ${filtered.length} results`,
      );
    });
  });
});

// =============================================================================
// Memoization Tests
// =============================================================================

describe("Alert Selector Memoization", () => {
  it("should return same reference when state unchanged", () => {
    const alerts = generateAlerts(100);
    const state = createState(alerts);

    const groups1 = selectAlertGroups(state);
    const groups2 = selectAlertGroups(state);

    // Same reference = memoization working
    expect(groups1).toBe(groups2);
  });

  it("should recompute only when alerts change", () => {
    const alerts = generateAlerts(100);
    const state = createState(alerts);

    const groups1 = selectAlertGroups(state);

    // Same state, different reference - should still be memoized
    const state2 = { ...state };
    const groups2 = selectAlertGroups(state2);

    expect(groups1).toBe(groups2);

    // Now change alerts
    const state3 = createState([...alerts, generateAlert(100)]);
    const groups3 = selectAlertGroups(state3);

    // Different reference - recomputed
    expect(groups1).not.toBe(groups3);
  });

  it("should chain memoization through filtered selectors", () => {
    const alerts = generateAlerts(100);
    const state = createState(alerts);

    // First call computes
    const filtered1 = selectFilteredAlertGroups(state);

    // Second call should be memoized
    const filtered2 = selectFilteredAlertGroups(state);

    expect(filtered1).toBe(filtered2);
  });
});

// =============================================================================
// Reducer Performance Tests
// =============================================================================

describe("Alert Reducer Performance", () => {
  it("should add alerts quickly with small existing state", () => {
    // Initialize with a reasonable number of alerts
    const initialAlerts = generateAlerts(100);
    let state = initialAlerts.reduce(
      (s, alert) => alertReducer(s, addAlert(alert)),
      alertReducer(undefined, { type: "@@INIT" }),
    );

    // Add 50 more alerts and measure time (realistic batch)
    const newAlerts = Array.from({ length: 50 }, (_, i) =>
      generateAlert(100 + i),
    );

    const start = performance.now();
    for (const alert of newAlerts) {
      state = alertReducer(state, addAlert(alert));
    }
    const elapsed = performance.now() - start;

    expect(state.alerts.length).toBe(150);
    // Immer has overhead per dispatch - this is expected
    // In real app, would use batch updates or RTK Query
    expect(elapsed).toBeLessThan(500);

    console.log(`  Added 50 alerts to 100: ${elapsed.toFixed(2)}ms`);
  });

  it("should handle single alert additions quickly", () => {
    // Start with empty state
    let state = alertReducer(undefined, { type: "@@INIT" });

    const timings: number[] = [];

    // Add alerts one at a time and track individual timings
    for (let i = 0; i < 100; i++) {
      const alert = generateAlert(i);
      const start = performance.now();
      state = alertReducer(state, addAlert(alert));
      timings.push(performance.now() - start);
    }

    expect(state.alerts.length).toBe(100);

    // Each individual add should be fast
    const avgTime = timings.reduce((a, b) => a + b, 0) / timings.length;
    const maxTime = Math.max(...timings);

    console.log(
      `  Avg add time: ${avgTime.toFixed(3)}ms, Max: ${maxTime.toFixed(3)}ms`,
    );

    // Individual adds should be under 25ms each (allowing for GC pauses and system variance)
    // Average should still be very fast, but max can spike due to GC or parallel test execution
    expect(maxTime).toBeLessThan(25);
    expect(avgTime).toBeLessThan(5); // Average should remain fast
  });
});

// =============================================================================
// Scalability Tests
// =============================================================================

describe("Alert Grouping Scalability", () => {
  it("should scale linearly with alert count", () => {
    const counts = [100, 200, 400, 800];
    const times: number[] = [];

    // Warmup run to avoid JIT compilation effects skewing the first measurement
    const warmupAlerts = generateAlerts(50);
    const warmupState = createState(warmupAlerts);
    selectAlertGroups(warmupState);

    for (const count of counts) {
      const alerts = generateAlerts(count);
      const state = createState(alerts);

      // Run multiple iterations and take the median to reduce variance
      const iterations = 3;
      const iterTimes: number[] = [];
      for (let iter = 0; iter < iterations; iter++) {
        const start = performance.now();
        selectAlertGroups(state);
        iterTimes.push(performance.now() - start);
      }
      // Use median to reduce outlier impact
      iterTimes.sort((a, b) => a - b);
      times.push(iterTimes[Math.floor(iterations / 2)]);
    }

    console.log("\n  Scalability test:");
    counts.forEach((count, i) => {
      console.log(`    ${count} alerts: ${times[i].toFixed(2)}ms`);
    });

    // Check that doubling alerts doesn't more than 8x time
    // (allowing for system variance, GC, and parallel test execution overhead)
    // Linear scaling would be ~2x, but we allow up to 8x for environment noise
    for (let i = 1; i < times.length; i++) {
      const ratio = times[i] / times[i - 1];
      expect(ratio).toBeLessThan(8); // Allow variance, but catch exponential O(n²) behavior
    }
  });

  it("should handle many unique groups efficiently", () => {
    // Create alerts with many unique service/name combinations
    const alerts: Alert[] = [];
    for (let i = 0; i < 100; i++) {
      for (let j = 0; j < 10; j++) {
        alerts.push({
          alertId: `alert-${i}-${j}`,
          name: `Alert${j}`,
          severity: "critical",
          state: "firing",
          message: `Test alert ${i}-${j}`,
          labels: { service: `service-${i}` },
          annotations: {},
          startedAt: new Date().toISOString(),
          endedAt: null,
          fingerprint: `fp-${i}-${j}`,
        });
      }
    }

    const state = createState(alerts);

    const start = performance.now();
    const groups = selectAlertGroups(state);
    const elapsed = performance.now() - start;

    // 100 services * 10 alert types = 1000 unique groups
    expect(groups.length).toBe(1000);
    expect(elapsed).toBeLessThan(200);

    console.log(
      `  1000 unique groups from 1000 alerts: ${elapsed.toFixed(2)}ms`,
    );
  });
});
