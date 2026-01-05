/**
 * useWebSocketMetricsPush Hook Tests
 *
 * TDD tests for the hook that periodically pushes WebSocket metrics
 * from Redux store to the backend Prometheus exporter.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { useWebSocketMetricsPush } from "./useWebSocketMetricsPush";
import observabilityReducer, {
  updateWebSocketMetrics,
} from "../store/slices/observabilitySlice";
import authReducer from "../store/slices/authSlice";
import { createInitialReconnectionMetrics } from "../types/websocket-metrics";

// Create test store factory
const createTestStore = (authenticated = true) =>
  configureStore({
    reducer: {
      observability: observabilityReducer,
      auth: authReducer,
    },
    preloadedState: {
      auth: {
        isAuthenticated: authenticated,
        user: authenticated ? { id: "test-user", email: "test@example.com" } : null,
        token: authenticated ? "test-token" : null,
        refreshToken: null,
        expiresAt: null,
        isLoading: false,
        error: null,
      },
    },
  });

// Wrapper with Redux provider
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
};

describe("useWebSocketMetricsPush", () => {
  let originalFetch: typeof globalThis.fetch;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    originalFetch = globalThis.fetch;
    mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "accepted" }), { status: 200 })
    );
    globalThis.fetch = mockFetch;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    globalThis.fetch = originalFetch;
  });

  describe("Initial State", () => {
    it("should not push metrics immediately on mount", () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      renderHook(() => useWebSocketMetricsPush(), { wrapper });

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should return push function and last push time", () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const { result } = renderHook(() => useWebSocketMetricsPush(), { wrapper });

      expect(typeof result.current.pushNow).toBe("function");
      expect(result.current.lastPushTime).toBeNull();
      expect(result.current.isPushing).toBe(false);
    });
  });

  describe("Periodic Push", () => {
    it("should push metrics after interval when enabled", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      // Add metrics to store
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      metrics.totalReconnections = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "notifications",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      renderHook(
        () => useWebSocketMetricsPush({ enabled: true, intervalMs: 30000 }),
        { wrapper }
      );

      // Fast-forward 30 seconds
      await act(async () => {
        vi.advanceTimersByTime(30000);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/websocket/metrics/batch"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        })
      );
    });

    it("should not push if no metrics in store", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      renderHook(
        () => useWebSocketMetricsPush({ enabled: true, intervalMs: 30000 }),
        { wrapper }
      );

      // Fast-forward 30 seconds
      await act(async () => {
        vi.advanceTimersByTime(30000);
      });

      // No metrics = no push
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should not push if disabled", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "alerts",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      renderHook(
        () => useWebSocketMetricsPush({ enabled: false, intervalMs: 30000 }),
        { wrapper }
      );

      await act(async () => {
        vi.advanceTimersByTime(60000);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("Manual Push", () => {
    it("should allow manual push via pushNow()", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 10;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "traces",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      const { result } = renderHook(
        () => useWebSocketMetricsPush({ enabled: false }),
        { wrapper }
      );

      await act(async () => {
        await result.current.pushNow();
      });

      expect(mockFetch).toHaveBeenCalled();
    });

    it("should update lastPushTime after successful push", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 3;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "devtools",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      const { result } = renderHook(() => useWebSocketMetricsPush(), { wrapper });

      expect(result.current.lastPushTime).toBeNull();

      await act(async () => {
        await result.current.pushNow();
      });

      expect(result.current.lastPushTime).not.toBeNull();
    });
  });

  describe("Authentication", () => {
    it("should not push if not authenticated", async () => {
      const store = createTestStore(false); // Not authenticated
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "test",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      renderHook(
        () => useWebSocketMetricsPush({ enabled: true, intervalMs: 30000 }),
        { wrapper }
      );

      await act(async () => {
        vi.advanceTimersByTime(30000);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should include auth token in request headers", async () => {
      const store = createTestStore(true);
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "test",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      const { result } = renderHook(() => useWebSocketMetricsPush(), { wrapper });

      await act(async () => {
        await result.current.pushNow();
      });

      expect(mockFetch).toHaveBeenCalled();
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toContain("/api/v1/websocket/metrics/batch");
      expect(options.headers.Authorization).toBe("Bearer test-token");
    });
  });

  describe("Error Handling", () => {
    it("should handle fetch errors gracefully", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "test",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      // Set up mock to reject
      globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() => useWebSocketMetricsPush(), { wrapper });

      // Should not throw
      await act(async () => {
        await result.current.pushNow();
      });

      // lastPushTime should still be null on error
      expect(result.current.lastPushTime).toBeNull();
    });

    it("should handle non-ok responses gracefully", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "test",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      // Set up mock to return non-ok response
      globalThis.fetch = vi.fn().mockResolvedValue(
        new Response("Internal Server Error", { status: 500, statusText: "Internal Server Error" })
      );

      const { result } = renderHook(() => useWebSocketMetricsPush(), { wrapper });

      // Should not throw
      await act(async () => {
        await result.current.pushNow();
      });

      expect(result.current.lastPushTime).toBeNull();
    });
  });

  describe("Payload Format", () => {
    it("should send metrics in correct batch format", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics1 = createInitialReconnectionMetrics();
      metrics1.totalAttempts = 10;
      metrics1.totalReconnections = 8;
      metrics1.consecutiveFailures = 0;
      metrics1.successRate = 80;
      metrics1.failuresByReason = { network_error: 2 };

      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "notifications",
          metrics: metrics1,
          lastUpdated: Date.now(),
        })
      );

      const { result } = renderHook(() => useWebSocketMetricsPush(), { wrapper });

      await act(async () => {
        await result.current.pushNow();
      });

      expect(mockFetch).toHaveBeenCalled();
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toContain("/api/v1/websocket/metrics/batch");

      const body = JSON.parse(options.body);

      expect(body.endpoints).toHaveLength(1);
      expect(body.endpoints[0]).toMatchObject({
        endpoint_id: "notifications",
        total_attempts: 10,
        total_reconnections: 8,
        consecutive_failures: 0,
        success_rate: 80,
        failures_by_reason: { network_error: 2 },
      });
    });
  });

  describe("Cleanup", () => {
    it("should clear interval on unmount", async () => {
      const store = createTestStore();
      const wrapper = createWrapper(store);

      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      store.dispatch(
        updateWebSocketMetrics({
          endpointId: "test",
          metrics,
          lastUpdated: Date.now(),
        })
      );

      const { unmount } = renderHook(
        () => useWebSocketMetricsPush({ enabled: true, intervalMs: 30000 }),
        { wrapper }
      );

      unmount();

      // Fast-forward - should NOT trigger push after unmount
      await act(async () => {
        vi.advanceTimersByTime(60000);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
