/**
 * useHeartDashboard Real-time Integration Tests (TDD RED Phase)
 *
 * Tests verify that useHeartDashboard integrates with WebSocket for real-time updates.
 * These tests should FAIL initially until we implement the WebSocket integration.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { useHeartDashboard } from "./useHeartDashboard";
import type { HeartMetricsSnapshot } from "./useHeartMetricsWebSocket";

// Create a minimal mock store for testing
const createMockStore = () =>
  configureStore({
    reducer: {
      // Minimal reducer that satisfies the store requirements
      auth: () => ({ user: null, isAuthenticated: false }),
      session: () => ({ currentSession: null, sessions: [] }),
    },
  });

// Wrapper with Router and Redux Provider context
const RouterWrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createMockStore()}>
    <MemoryRouter>{children}</MemoryRouter>
  </Provider>
);

// Mock metrics object matching ReconnectionMetrics interface
const createMockMetrics = () => ({
  totalReconnections: 0,
  totalAttempts: 0,
  consecutiveFailures: 0,
  lastReconnectionTime: null,
  lastDisconnectionTime: null,
  avgReconnectionDurationMs: null,
  totalReconnectionTimeMs: 0,
  failuresByReason: {
    max_attempts_exceeded: 0,
    token_expired: 0,
    token_refresh_failed: 0,
    network_error: 0,
    server_error: 0,
    invalid_url: 0,
    manual_disconnect: 0,
    unknown: 0,
    protocol_version_mismatch: 0,
  },
  recentAttempts: [],
  successRate: null,
});

// Mock useRealtimeSync for WebSocket simulation
vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn(() => ({
    status: "connected",
    send: vi.fn(),
    disconnect: vi.fn(),
    reconnect: vi.fn(),
    metrics: createMockMetrics(),
    resetMetrics: vi.fn(),
  })),
}));

// Mock storage - use importOriginal to preserve STORAGE_KEYS export
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => "test-token"),
  };
});

// Mock fetch for initial data
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("useHeartDashboard Real-time Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock API response matches MetricsSummary from analytics/gsm
    // with DimensionScore format (overallScore, hasData, goalProgresses)
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          dimensions: [
            {
              dimension: "happiness",
              overallScore: 85,
              hasData: true,
              goalProgresses: [{ goalId: "g1" }],
            },
            {
              dimension: "engagement",
              overallScore: 78,
              hasData: true,
              goalProgresses: [{ goalId: "g2" }],
            },
            {
              dimension: "adoption",
              overallScore: 92,
              hasData: true,
              goalProgresses: [{ goalId: "g3" }],
            },
            {
              dimension: "retention",
              overallScore: 88,
              hasData: true,
              goalProgresses: [{ goalId: "g4" }],
            },
            {
              dimension: "task_success",
              overallScore: 95,
              hasData: true,
              goalProgresses: [{ goalId: "g5" }],
            },
          ],
          overallHealthScore: 87.6,
          dataPointCount: 1250,
        }),
    });
  });

  afterEach(async () => {
    cleanup();
    vi.clearAllMocks();
    // Restore useRealtimeSync to default mock for next test
    const { useRealtimeSync } = await import("./useRealtimeSync");
    vi.mocked(useRealtimeSync).mockImplementation(() => ({
      status: "connected" as const,
      send: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
      metrics: createMockMetrics(),
      resetMetrics: vi.fn(),
    }));
  });

  describe("WebSocket Connection Status", () => {
    it("should expose WebSocket connection status when enableRealtime is true", async () => {
      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // wsStatus should be present and have a valid value
      expect(result.current).toHaveProperty("wsStatus");
      expect(["connecting", "connected", "disconnected", "error"]).toContain(
        result.current.wsStatus,
      );
    });

    it("should have undefined wsStatus when enableRealtime is false", async () => {
      const { result } = renderHook(() => useHeartDashboard(), {
        wrapper: RouterWrapper,
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // wsStatus should be undefined when real-time is disabled
      expect(result.current.wsStatus).toBeUndefined();
    });

    it("should indicate when receiving real-time updates", async () => {
      const { result } = renderHook(() => useHeartDashboard(), {
        wrapper: RouterWrapper,
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // TDD RED: This property doesn't exist yet
      expect(result.current).toHaveProperty("isRealtime");
    });
  });

  describe("Real-time Data Updates", () => {
    it("should update dimensions when WebSocket receives metrics_snapshot", async () => {
      const { useRealtimeSync } = await import("./useRealtimeSync");
      let onMessageCallback: ((data: unknown) => void) | undefined;

      // Capture the onMessage callback
      vi.mocked(useRealtimeSync).mockImplementation((options) => {
        onMessageCallback = options?.onMessage;
        return {
          status: "connected" as const,
          send: vi.fn(),
          disconnect: vi.fn(),
          reconnect: vi.fn(),
          metrics: createMockMetrics(),
          resetMetrics: vi.fn(),
        };
      });

      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Simulate WebSocket message
      const wsSnapshot: HeartMetricsSnapshot = {
        happiness: { score: 90, trend: "up", samples: 100 },
        engagement: { score: 82, trend: "up", samples: 100 },
        adoption: { score: 94, trend: "stable", samples: 100 },
        retention: { score: 91, trend: "up", samples: 100 },
        task_success: { score: 97, trend: "up", samples: 100 },
      };

      act(() => {
        onMessageCallback?.({
          type: "metrics_snapshot",
          snapshot: wsSnapshot,
          time_range: "30d",
        });
      });

      // TDD RED: Real-time update should change dimensions
      await waitFor(() => {
        expect(result.current.dimensions[0].score).toBe(90); // Updated from 85
      });
    });

    it("should handle threshold alerts from WebSocket", async () => {
      const { useRealtimeSync } = await import("./useRealtimeSync");
      let onMessageCallback: ((data: unknown) => void) | undefined;

      vi.mocked(useRealtimeSync).mockImplementation((options) => {
        onMessageCallback = options?.onMessage;
        return {
          status: "connected" as const,
          send: vi.fn(),
          disconnect: vi.fn(),
          reconnect: vi.fn(),
          metrics: createMockMetrics(),
          resetMetrics: vi.fn(),
        };
      });

      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Simulate threshold alert
      act(() => {
        onMessageCallback?.({
          type: "threshold_alert",
          alert: {
            dimension: "engagement",
            current_score: 45,
            threshold: 50,
            severity: "critical",
            message: "Engagement below threshold",
          },
        });
      });

      // TDD RED: alerts property doesn't exist yet
      expect(result.current).toHaveProperty("alerts");
      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0].severity).toBe("critical");
    });
  });

  describe("Fallback to Polling", () => {
    it("should indicate isRealtime=false when WebSocket disconnects", async () => {
      // Set up the useRealtimeSync mock to return disconnected status
      const { useRealtimeSync } = await import("./useRealtimeSync");
      vi.mocked(useRealtimeSync).mockImplementation(() => ({
        status: "disconnected" as const,
        send: vi.fn(),
        disconnect: vi.fn(),
        reconnect: vi.fn(),
        metrics: createMockMetrics(),
        resetMetrics: vi.fn(),
      }));

      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      // When WebSocket is disconnected, isRealtime should be false
      // This triggers fallback to polling data
      expect(result.current.isRealtime).toBe(false);
      expect(result.current.wsStatus).toBe("disconnected");
    });

    it("should disable WebSocket when enableRealtime is false", async () => {
      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: false }),
        { wrapper: RouterWrapper },
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // wsStatus should be undefined when real-time disabled
      expect(result.current.wsStatus).toBeUndefined();
    });
  });

  describe("Configuration Options", () => {
    it("should accept enableRealtime option", () => {
      // TDD RED: enableRealtime option doesn't exist in interface yet
      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      expect(result.current).toBeDefined();
    });

    it("should use custom WebSocket URL when provided", async () => {
      const { useRealtimeSync } = await import("./useRealtimeSync");

      renderHook(
        () =>
          useHeartDashboard({
            enableRealtime: true,
            wsUrl: "ws://custom:8000/metrics",
          }),
        { wrapper: RouterWrapper },
      );

      // TDD RED: wsUrl option doesn't exist
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("ws://custom:8000/metrics"),
        }),
      );
    });
  });

  describe("Error Handling", () => {
    it("should report WebSocket errors", async () => {
      const { useRealtimeSync } = await import("./useRealtimeSync");
      let onMessageCallback: ((data: unknown) => void) | undefined;

      vi.mocked(useRealtimeSync).mockImplementation((options) => {
        onMessageCallback = options?.onMessage;
        return {
          status: "error" as const,
          send: vi.fn(),
          disconnect: vi.fn(),
          reconnect: vi.fn(),
          metrics: createMockMetrics(),
          resetMetrics: vi.fn(),
        };
      });

      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // Simulate error message
      act(() => {
        onMessageCallback?.({
          type: "error",
          message: "Authentication failed",
        });
      });

      // TDD RED: wsError property doesn't exist yet
      expect(result.current).toHaveProperty("wsError");
      expect(result.current.wsError).toBe("Authentication failed");
    });
  });

  describe("Subscription Management", () => {
    it("should allow subscribing to specific dimensions", async () => {
      const sendMock = vi.fn();
      const { useRealtimeSync } = await import("./useRealtimeSync");

      vi.mocked(useRealtimeSync).mockReturnValue({
        status: "connected" as const,
        send: sendMock,
        disconnect: vi.fn(),
        reconnect: vi.fn(),
        metrics: createMockMetrics(),
        resetMetrics: vi.fn(),
        reconnectAttempts: 0,
        lastMessageTime: null,
      });

      const { result } = renderHook(
        () => useHeartDashboard({ enableRealtime: true }),
        { wrapper: RouterWrapper },
      );

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      // TDD RED: subscribeDimension doesn't exist
      act(() => {
        result.current.subscribeDimension?.("happiness");
      });

      expect(sendMock).toHaveBeenCalledWith(
        JSON.stringify({
          type: "subscribe",
          dimension: "happiness",
        }),
      );
    });
  });
});
