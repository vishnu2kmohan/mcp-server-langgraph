/**
 * useWebSocketMetricsReporter Hook Tests
 *
 * TDD tests for WebSocket metrics Redux integration.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { useWebSocketMetricsReporter } from "./useWebSocketMetricsReporter";
import observabilityReducer, {
  selectWebSocketMetrics,
  type ObservabilityState,
} from "../store/slices/observabilitySlice";
import {
  createInitialReconnectionMetrics,
  type ReconnectionMetrics,
} from "../types/websocket-metrics";
import type { EnhancedStore } from "@reduxjs/toolkit";

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

describe("useWebSocketMetricsReporter", () => {
  let store: TestStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createTestStore();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("metrics reporting", () => {
    it("should dispatch metrics to Redux store", () => {
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      metrics.totalReconnections = 3;
      metrics.successRate = 60;

      renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics,
          }),
        { wrapper: createWrapper(store) },
      );

      const state = store.getState();
      const wsMetrics = selectWebSocketMetrics(state);

      expect(wsMetrics["notifications"]).toBeDefined();
      expect(wsMetrics["notifications"].metrics.totalAttempts).toBe(5);
    });

    it("should update metrics when they change", () => {
      const initialMetrics = createInitialReconnectionMetrics();
      initialMetrics.totalAttempts = 2;

      const { rerender } = renderHook(
        ({ metrics }: { metrics: ReconnectionMetrics }) =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics,
          }),
        {
          wrapper: createWrapper(store),
          initialProps: { metrics: initialMetrics },
        },
      );

      // Verify initial state
      let state = store.getState();
      expect(
        selectWebSocketMetrics(state)["notifications"].metrics.totalAttempts,
      ).toBe(2);

      // Update with new metrics
      const updatedMetrics = createInitialReconnectionMetrics();
      updatedMetrics.totalAttempts = 5;
      updatedMetrics.totalReconnections = 3;

      act(() => {
        rerender({ metrics: updatedMetrics });
      });

      // Verify updated state
      state = store.getState();
      expect(
        selectWebSocketMetrics(state)["notifications"].metrics.totalAttempts,
      ).toBe(5);
    });

    it("should track multiple endpoints independently", () => {
      const metricsA = createInitialReconnectionMetrics();
      metricsA.totalAttempts = 2;

      const metricsB = createInitialReconnectionMetrics();
      metricsB.totalAttempts = 5;

      renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics: metricsA,
          }),
        { wrapper: createWrapper(store) },
      );

      renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "traces",
            metrics: metricsB,
          }),
        { wrapper: createWrapper(store) },
      );

      const state = store.getState();
      const wsMetrics = selectWebSocketMetrics(state);

      expect(Object.keys(wsMetrics)).toHaveLength(2);
      expect(wsMetrics["notifications"].metrics.totalAttempts).toBe(2);
      expect(wsMetrics["traces"].metrics.totalAttempts).toBe(5);
    });
  });

  describe("cleanup on unmount", () => {
    it("should remove metrics on unmount when cleanup is enabled", () => {
      const metrics = createInitialReconnectionMetrics();

      const { unmount } = renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics,
            cleanupOnUnmount: true,
          }),
        { wrapper: createWrapper(store) },
      );

      // Verify metrics are present
      let state = store.getState();
      expect(selectWebSocketMetrics(state)["notifications"]).toBeDefined();

      // Unmount
      unmount();

      // Verify metrics are removed
      state = store.getState();
      expect(selectWebSocketMetrics(state)["notifications"]).toBeUndefined();
    });

    it("should preserve metrics on unmount when cleanup is disabled (default)", () => {
      const metrics = createInitialReconnectionMetrics();

      const { unmount } = renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics,
          }),
        { wrapper: createWrapper(store) },
      );

      // Verify metrics are present
      let state = store.getState();
      expect(selectWebSocketMetrics(state)["notifications"]).toBeDefined();

      // Unmount
      unmount();

      // Verify metrics are preserved
      state = store.getState();
      expect(selectWebSocketMetrics(state)["notifications"]).toBeDefined();
    });
  });

  describe("enabled flag", () => {
    it("should not dispatch metrics when disabled", () => {
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;

      renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics,
            enabled: false,
          }),
        { wrapper: createWrapper(store) },
      );

      const state = store.getState();
      const wsMetrics = selectWebSocketMetrics(state);

      expect(wsMetrics["notifications"]).toBeUndefined();
    });

    it("should dispatch metrics when enabled", () => {
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;

      renderHook(
        () =>
          useWebSocketMetricsReporter({
            endpointId: "notifications",
            metrics,
            enabled: true,
          }),
        { wrapper: createWrapper(store) },
      );

      const state = store.getState();
      const wsMetrics = selectWebSocketMetrics(state);

      expect(wsMetrics["notifications"]).toBeDefined();
    });
  });
});
