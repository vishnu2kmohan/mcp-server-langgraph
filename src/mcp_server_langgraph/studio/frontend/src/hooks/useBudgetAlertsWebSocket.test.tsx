/**
 * useBudgetAlertsWebSocket Hook Tests (TDD)
 *
 * Tests for the Budget Alerts real-time WebSocket hook.
 * This hook listens to budget alert notifications from the backend
 * and provides subscription management for budget monitoring.
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../api";

// Mock the useRealtimeSync hook
const mockUseRealtimeSync = vi.fn();
vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: unknown) => mockUseRealtimeSync(options),
}));

// Mock auth - useAppSelector must call the selector to get proper mocked values
vi.mock("../store/hooks", () => ({
  useAppSelector: (selector: () => unknown) => selector(),
  useAppDispatch: () => vi.fn(),
}));

vi.mock("../store/slices/authSlice", async () => {
  const actual = await vi.importActual("../store/slices/authSlice");
  return {
    ...actual,
    selectIsAuthenticated: () => true,
    selectWebSocketPermissions: () => ({ budget_alerts: true }),
    logout: () => ({ type: "auth/logout" }),
  };
});
vi.mock("../utils/storage", async () => {
  const actual = await vi.importActual("../utils/storage");
  return {
    ...actual,
    getAuthToken: () => "test-token",
  };
});
// Import after mocking
import { useBudgetAlertsWebSocket } from "./useBudgetAlertsWebSocket";
import type { BudgetAlert as _BudgetAlert } from "./useBudgetAlertsWebSocket";

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("useBudgetAlertsWebSocket", () => {
  const mockDisconnect = vi.fn();
  const mockReconnect = vi.fn();
  const mockSend = vi.fn();
  const capturedCallbacks: {
    onMessage: ((data: unknown) => void) | null;
    onConnect: (() => void) | null;
  } = {
    onMessage: null,
    onConnect: null,
  };

  beforeEach(() => {
    vi.resetAllMocks();
    capturedCallbacks.onMessage = null;
    capturedCallbacks.onConnect = null;

    // Default mock that captures callbacks
    mockUseRealtimeSync.mockImplementation(
      (options?: {
        onMessage?: (data: unknown) => void;
        onConnect?: () => void;
      }) => {
        if (options?.onMessage) {
          capturedCallbacks.onMessage = options.onMessage;
        }
        if (options?.onConnect) {
          capturedCallbacks.onConnect = options.onConnect;
        }
        return {
          status: "connected",
          send: mockSend,
          disconnect: mockDisconnect,
          reconnect: mockReconnect,
          reconnectAttempts: 0,
          lastMessageTime: null,
          metrics: {
            totalAttempts: 0,
            totalReconnections: 0,
            consecutiveFailures: 0,
            lastReconnectionTime: null,
            lastDisconnectionTime: null,
            avgReconnectionDurationMs: 0,
            totalReconnectionTimeMs: 0,
            failuresByReason: {},
            recentAttempts: [],
            successRate: 100,
          },
          resetMetrics: vi.fn(),
        };
      },
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    capturedCallbacks.onMessage = null;
    capturedCallbacks.onConnect = null;
  });

  // Shared mock return value structure for consistent testing
  const createMockReturn = (overrides: { status?: string } = {}) => ({
    status: overrides.status ?? "connected",
    send: mockSend,
    disconnect: mockDisconnect,
    reconnect: mockReconnect,
    reconnectAttempts: 0,
    lastMessageTime: null,
    metrics: {
      totalAttempts: 0,
      totalReconnections: 0,
      consecutiveFailures: 0,
      lastReconnectionTime: null,
      lastDisconnectionTime: null,
      avgReconnectionDurationMs: 0,
      totalReconnectionTimeMs: 0,
      failuresByReason: {},
      recentAttempts: [],
      successRate: 100,
    },
    resetMetrics: vi.fn(),
  });

  describe("connection status", () => {
    it("returns connected status when WebSocket is connected", () => {
      mockUseRealtimeSync.mockReturnValue(
        createMockReturn({ status: "connected" }),
      );

      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      expect(result.current.status).toBe("connected");
    });

    it("returns disconnected status when WebSocket is disconnected", () => {
      mockUseRealtimeSync.mockReturnValue(
        createMockReturn({ status: "disconnected" }),
      );

      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      expect(result.current.status).toBe("disconnected");
    });

    it("provides disconnect function", () => {
      mockUseRealtimeSync.mockReturnValue(
        createMockReturn({ status: "connected" }),
      );

      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      result.current.disconnect();

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("provides reconnect function", () => {
      mockUseRealtimeSync.mockReturnValue(
        createMockReturn({ status: "disconnected" }),
      );

      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      result.current.reconnect();

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("subscription management", () => {
    it("subscribeToEntities sends subscribe_entities message", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      act(() => {
        result.current.subscribeToEntities(["org-123", "project-456"]);
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "subscribe_entities",
          payload: { entity_ids: ["org-123", "project-456"] },
        }),
      );
    });

    it("subscribeToAll sends subscribe_all message", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      act(() => {
        result.current.subscribeToAll();
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "subscribe_all",
          payload: {},
        }),
      );
    });

    it("unsubscribe sends unsubscribe message", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      act(() => {
        result.current.unsubscribe();
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "unsubscribe",
          payload: {},
        }),
      );
    });

    it("auto-subscribes on connect when subscribeAll option is true", () => {
      renderHook(() => useBudgetAlertsWebSocket({ subscribeAll: true }), {
        wrapper,
      });

      // Trigger onConnect callback
      act(() => {
        capturedCallbacks.onConnect?.();
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "subscribe_all",
        }),
      );
    });

    it("auto-subscribes to entities on connect when entityIds option is provided", () => {
      renderHook(() => useBudgetAlertsWebSocket({ entityIds: ["org-123"] }), {
        wrapper,
      });

      // Trigger onConnect callback
      act(() => {
        capturedCallbacks.onConnect?.();
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "subscribe_entities",
          payload: { entity_ids: ["org-123"] },
        }),
      );
    });
  });

  describe("alert handling", () => {
    it("stores received budget alerts", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      const mockAlert = {
        type: "budget_alert",
        payload: {
          entity_type: "organization",
          entity_id: "org-123",
          status: "warning",
          percent_used: 85,
          current_spend: "850.00",
          remaining: "150.00",
          monthly_limit_usd: "1000.00",
          message: "Budget at 85%",
        },
      };

      act(() => {
        capturedCallbacks.onMessage?.(mockAlert);
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0]).toMatchObject({
        entityType: "organization",
        entityId: "org-123",
        status: "warning",
        percentUsed: 85,
      });
    });

    it("calls onAlert callback when alert is received", () => {
      const onAlert = vi.fn();
      renderHook(() => useBudgetAlertsWebSocket({ onAlert }), { wrapper });

      const mockAlert = {
        type: "budget_alert",
        payload: {
          entity_type: "project",
          entity_id: "proj-456",
          status: "exceeded",
          percent_used: 110,
          current_spend: "1100.00",
          remaining: "-100.00",
          monthly_limit_usd: "1000.00",
          message: "Budget exceeded!",
        },
      };

      act(() => {
        capturedCallbacks.onMessage?.(mockAlert);
      });

      expect(onAlert).toHaveBeenCalledWith(
        expect.objectContaining({
          entityType: "project",
          entityId: "proj-456",
          status: "exceeded",
        }),
      );
    });

    it("handles subscription confirmation", () => {
      const onSubscribed = vi.fn();
      const { result } = renderHook(
        () => useBudgetAlertsWebSocket({ onSubscribed }),
        { wrapper },
      );

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "subscribed",
          payload: {
            entity_ids: ["org-123", "org-456"],
            subscribe_all: false,
          },
        });
      });

      expect(result.current.isSubscribed).toBe(true);
      expect(result.current.subscribedEntityIds).toEqual([
        "org-123",
        "org-456",
      ]);
      expect(result.current.isSubscribedToAll).toBe(false);
      expect(onSubscribed).toHaveBeenCalledWith(["org-123", "org-456"], false);
    });

    it("handles subscribe_all confirmation", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "subscribed",
          payload: {
            entity_ids: [],
            subscribe_all: true,
          },
        });
      });

      expect(result.current.isSubscribed).toBe(true);
      expect(result.current.isSubscribedToAll).toBe(true);
    });

    it("handles unsubscribe confirmation", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      // First, set subscribed state
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "subscribed",
          payload: { entity_ids: ["org-123"], subscribe_all: false },
        });
      });

      expect(result.current.isSubscribed).toBe(true);

      // Then unsubscribe
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "unsubscribed",
          payload: {},
        });
      });

      expect(result.current.isSubscribed).toBe(false);
      expect(result.current.subscribedEntityIds).toEqual([]);
      expect(result.current.isSubscribedToAll).toBe(false);
    });

    it("clearAlerts removes all stored alerts", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      // Add some alerts
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "budget_alert",
          payload: {
            entity_type: "org",
            entity_id: "org-1",
            status: "warning",
            percent_used: 80,
          },
        });
        capturedCallbacks.onMessage?.({
          type: "budget_alert",
          payload: {
            entity_type: "org",
            entity_id: "org-2",
            status: "critical",
            percent_used: 95,
          },
        });
      });

      expect(result.current.alerts).toHaveLength(2);

      act(() => {
        result.current.clearAlerts();
      });

      expect(result.current.alerts).toHaveLength(0);
    });
  });

  describe("initial state", () => {
    it("starts with empty alerts", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      expect(result.current.alerts).toEqual([]);
    });

    it("starts with isSubscribed false", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      expect(result.current.isSubscribed).toBe(false);
    });

    it("starts with empty subscribedEntityIds", () => {
      const { result } = renderHook(() => useBudgetAlertsWebSocket(), {
        wrapper,
      });

      expect(result.current.subscribedEntityIds).toEqual([]);
    });
  });
});
