/**
 * useWebSocketTelemetrySync Hook Tests
 *
 * TDD tests for syncing websocketTelemetry singleton to Redux observabilitySlice.
 * This enables React components to subscribe to WebSocket metrics changes.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { useWebSocketTelemetrySync } from "./useWebSocketTelemetrySync";
import observabilityReducer, {
  selectWebSocketMetrics,
  selectTotalWebSocketConnections,
} from "../store/slices/observabilitySlice";
import { websocketTelemetry } from "../utils/websocketTelemetry";
import { createInitialReconnectionMetrics } from "../types/websocket-metrics";
import type { EnhancedStore } from "@reduxjs/toolkit";
import type { ObservabilityState } from "../store/slices/observabilitySlice";

// Create a test store factory
const createTestStore = () =>
  configureStore({
    reducer: {
      observability: observabilityReducer,
    },
  });

type TestStore = EnhancedStore<{ observability: ObservabilityState }>;

// Wrapper with Redux provider
const createWrapper = (store: TestStore) => {
  return ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

describe("useWebSocketTelemetrySync", () => {
  let store: TestStore;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    store = createTestStore();
    // Reset telemetry singleton
    websocketTelemetry.reset();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    websocketTelemetry.reset();
  });

  describe("initial sync", () => {
    it("should sync existing telemetry data to Redux on mount", async () => {
      // Add some data to the singleton before mounting
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      metrics.totalReconnections = 3;
      websocketTelemetry.trackReconnectionMetrics("notifications", metrics);

      renderHook(() => useWebSocketTelemetrySync(), {
        wrapper: createWrapper(store),
      });

      // Should sync immediately on mount
      const state = store.getState();
      const wsMetrics = selectWebSocketMetrics(state);

      expect(wsMetrics["notifications"]).toBeDefined();
      expect(wsMetrics["notifications"].metrics.totalAttempts).toBe(5);
    });

    it("should sync multiple endpoints from singleton", async () => {
      const metricsA = createInitialReconnectionMetrics();
      metricsA.totalAttempts = 2;
      websocketTelemetry.trackReconnectionMetrics("notifications", metricsA);

      const metricsB = createInitialReconnectionMetrics();
      metricsB.totalAttempts = 8;
      websocketTelemetry.trackReconnectionMetrics("traces", metricsB);

      renderHook(() => useWebSocketTelemetrySync(), {
        wrapper: createWrapper(store),
      });

      const state = store.getState();
      const total = selectTotalWebSocketConnections(state);
      expect(total).toBe(2);
    });
  });

  describe("periodic sync", () => {
    it("should sync telemetry changes on interval", async () => {
      renderHook(() => useWebSocketTelemetrySync({ syncIntervalMs: 1000 }), {
        wrapper: createWrapper(store),
      });

      // Initially empty
      let state = store.getState();
      expect(selectTotalWebSocketConnections(state)).toBe(0);

      // Add data after mount
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 10;
      websocketTelemetry.trackReconnectionMetrics("alerts", metrics);

      // Advance timer to trigger sync
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      // Should now be synced
      state = store.getState();
      expect(selectWebSocketMetrics(state)["alerts"]).toBeDefined();
      expect(selectWebSocketMetrics(state)["alerts"].metrics.totalAttempts).toBe(10);
    });

    it("should use default sync interval of 2000ms", async () => {
      renderHook(() => useWebSocketTelemetrySync(), {
        wrapper: createWrapper(store),
      });

      const metrics = createInitialReconnectionMetrics();
      websocketTelemetry.trackReconnectionMetrics("test", metrics);

      // At 1000ms, should not have synced yet (beyond initial)
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      // At 2000ms, should sync
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      const state = store.getState();
      expect(selectWebSocketMetrics(state)["test"]).toBeDefined();
    });

    it("should cleanup interval on unmount", async () => {
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");

      const { unmount } = renderHook(
        () => useWebSocketTelemetrySync({ syncIntervalMs: 1000 }),
        { wrapper: createWrapper(store) },
      );

      unmount();

      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe("enabled flag", () => {
    it("should not sync when disabled", async () => {
      const metrics = createInitialReconnectionMetrics();
      websocketTelemetry.trackReconnectionMetrics("notifications", metrics);

      renderHook(() => useWebSocketTelemetrySync({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      const state = store.getState();
      expect(selectTotalWebSocketConnections(state)).toBe(0);
    });

    it("should sync when enabled", async () => {
      const metrics = createInitialReconnectionMetrics();
      websocketTelemetry.trackReconnectionMetrics("notifications", metrics);

      renderHook(() => useWebSocketTelemetrySync({ enabled: true }), {
        wrapper: createWrapper(store),
      });

      const state = store.getState();
      expect(selectTotalWebSocketConnections(state)).toBe(1);
    });
  });

  describe("return value", () => {
    it("should return sync function for manual triggering", async () => {
      const { result } = renderHook(() => useWebSocketTelemetrySync(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.sync).toBe("function");
    });

    it("should return connection count", async () => {
      const metrics = createInitialReconnectionMetrics();
      websocketTelemetry.trackReconnectionMetrics("test", metrics);

      const { result } = renderHook(() => useWebSocketTelemetrySync(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.connectionCount).toBe(1);
    });

    it("should return last sync timestamp", async () => {
      const { result } = renderHook(() => useWebSocketTelemetrySync(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.lastSyncTime).toBe("number");
      expect(result.current.lastSyncTime).toBeGreaterThan(0);
    });

    it("should allow manual sync via returned function", async () => {
      const { result } = renderHook(
        () => useWebSocketTelemetrySync({ syncIntervalMs: 10000 }),
        { wrapper: createWrapper(store) },
      );

      // Add data
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 42;
      websocketTelemetry.trackReconnectionMetrics("manual", metrics);

      // Manual sync (don't wait for interval)
      act(() => {
        result.current.sync();
      });

      const state = store.getState();
      expect(selectWebSocketMetrics(state)["manual"].metrics.totalAttempts).toBe(42);
    });
  });

  describe("removed endpoints", () => {
    it("should remove endpoints from Redux when removed from singleton", async () => {
      // Setup with endpoint
      const metrics = createInitialReconnectionMetrics();
      websocketTelemetry.trackReconnectionMetrics("temporary", metrics);

      const { result } = renderHook(
        () => useWebSocketTelemetrySync({ syncIntervalMs: 1000 }),
        { wrapper: createWrapper(store) },
      );

      // Verify synced
      let state = store.getState();
      expect(selectWebSocketMetrics(state)["temporary"]).toBeDefined();

      // Remove from singleton
      websocketTelemetry.removeEndpoint("temporary");

      // Trigger sync
      act(() => {
        result.current.sync();
      });

      // Should be removed from Redux
      state = store.getState();
      expect(selectWebSocketMetrics(state)["temporary"]).toBeUndefined();
    });
  });
});
