/**
 * useCostTrackingWebSocket Hook Tests
 *
 * TDD tests for real-time cost tracking WebSocket hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useCostTrackingWebSocket } from "./useCostTrackingWebSocket";

// Type for test WebSocket handlers
interface TestWsHandlers {
  onMessage: (data: unknown) => void;
  onConnect: () => void;
}

// Module-scoped handler storage for tests
let testWsHandlers: TestWsHandlers | null = null;

// Mock Redux hooks to avoid needing Provider wrapper
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  // Return values for selectors: isAuthenticated=true, wsPermissions={cost_tracking: true}
  useAppSelector: vi.fn((selector) => {
    if (selector.name?.includes("Authenticated")) return true;
    if (selector.name?.includes("WebSocketPermissions"))
      return { cost_tracking: true };
    return true;
  }),
}));

// Mock getAuthToken to return test token
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => "mock-test-token"),
  };
});

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn(({ onMessage, onConnect }) => {
    // Store handlers for test access
    testWsHandlers = { onMessage, onConnect };
    return {
      status: "connected" as const,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      metrics: { totalAttempts: 0 },
    };
  }),
}));

describe("useCostTrackingWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    testWsHandlers = null;
  });

  afterEach(() => {
    testWsHandlers = null;
    cleanup();
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should initialize with default state", () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      expect(result.current.status).toBe("connected");
      expect(result.current.sessionCosts).toEqual({});
      expect(result.current.userBudget).toBeNull();
      expect(result.current.budgetWarnings).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it("should use default WebSocket URL", async () => {
      renderHook(() => useCostTrackingWebSocket());

      // useRealtimeSync should be called with correct URL pattern
      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(vi.mocked(useRealtimeSync)).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("/api/v1/ws/usage/cost"),
        }),
      );
    });
  });

  describe("session subscription", () => {
    it("should subscribe to session cost updates", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      act(() => {
        result.current.subscribeSession("session-123");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe_session",
        session_id: "session-123",
      });
    });

    it("should track subscribed sessions", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      act(() => {
        result.current.subscribeSession("session-123");
      });

      expect(result.current.subscribedSessions.has("session-123")).toBe(true);
    });

    it("should handle session_total message", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());
      const handlers = testWsHandlers;

      // Backend sends snake_case format
      act(() => {
        handlers.onMessage({
          type: "session_total",
          payload: {
            session_id: "session-123",
            total_cost: 0.25,
            token_count: 5000,
          },
        });
      });

      // Hook transforms to camelCase
      expect(result.current.sessionCosts["session-123"]).toEqual({
        sessionId: "session-123",
        totalCost: 0.25,
        tokenCount: 5000,
      });
    });

    it("should handle cost_event message", async () => {
      const onCostEvent = vi.fn();
      renderHook(() => useCostTrackingWebSocket({ onCostEvent }));
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "cost_event",
          payload: {
            session_id: "session-123",
            cost: 0.05,
            model: "gpt-4",
            tokens: { input: 100, output: 50 },
          },
        });
      });

      // Callback should be invoked
      expect(onCostEvent).toHaveBeenCalled();
    });
  });

  describe("user budget subscription", () => {
    it("should subscribe to user budget updates", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      act(() => {
        result.current.subscribeUser("user-456");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe_user",
        user_id: "user-456",
      });
    });

    it("should handle user_budget message", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());
      const handlers = testWsHandlers;

      // Backend sends snake_case format
      act(() => {
        handlers.onMessage({
          type: "user_budget",
          payload: {
            user_id: "user-456",
            budget_limit: 100.0,
            current_usage: 45.0,
            remaining: 55.0,
          },
        });
      });

      // Hook transforms to camelCase
      expect(result.current.userBudget).toEqual({
        userId: "user-456",
        budgetLimit: 100.0,
        currentUsage: 45.0,
        remaining: 55.0,
      });
    });

    it("should handle budget_warning message", async () => {
      const onBudgetWarning = vi.fn();
      const { result } = renderHook(() =>
        useCostTrackingWebSocket({ onBudgetWarning }),
      );
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "budget_warning",
          payload: {
            user_id: "user-456",
            threshold: 0.8,
            current_usage: 82.0,
            budget_limit: 100.0,
            message: "You have used 82% of your budget",
          },
        });
      });

      expect(result.current.budgetWarnings.length).toBe(1);
      expect(result.current.budgetWarnings[0].threshold).toBe(0.8);
    });
  });

  describe("unsubscription", () => {
    it("should unsubscribe from session", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      act(() => {
        result.current.subscribeSession("session-123");
        result.current.unsubscribeSession("session-123");
      });

      expect(mockSend).toHaveBeenLastCalledWith({
        type: "unsubscribe",
        session_id: "session-123",
      });
    });

    it("should unsubscribe from user", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      act(() => {
        result.current.subscribeUser("user-456");
        result.current.unsubscribeUser("user-456");
      });

      expect(mockSend).toHaveBeenLastCalledWith({
        type: "unsubscribe",
        user_id: "user-456",
      });
    });
  });

  describe("error handling", () => {
    it("should handle error messages", async () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useCostTrackingWebSocket({ onError }),
      );
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "error",
          payload: {
            code: "session_cost_error",
            message: "Session not found",
          },
        });
      });

      expect(result.current.error).toBe("Session not found");
      expect(onError).toHaveBeenCalledWith("Session not found");
    });
  });

  describe("utility methods", () => {
    it("should get session cost", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());
      const handlers = testWsHandlers;

      // Backend sends snake_case format
      act(() => {
        handlers.onMessage({
          type: "session_total",
          payload: {
            session_id: "session-123",
            total_cost: 0.5,
            token_count: 10000,
          },
        });
      });

      // Hook transforms to camelCase
      const cost = result.current.getSessionCost("session-123");
      expect(cost?.totalCost).toBe(0.5);
    });

    it("should return undefined for unknown session", () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      const cost = result.current.getSessionCost("unknown-session");
      expect(cost).toBeUndefined();
    });

    it("should clear budget warnings", async () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "budget_warning",
          payload: {
            user_id: "user-456",
            threshold: 0.8,
            message: "Budget warning",
          },
        });
      });

      expect(result.current.budgetWarnings.length).toBe(1);

      act(() => {
        result.current.clearBudgetWarnings();
      });

      expect(result.current.budgetWarnings.length).toBe(0);
    });

    it("should provide disconnect and reconnect methods", () => {
      const { result } = renderHook(() => useCostTrackingWebSocket());

      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");

      act(() => {
        result.current.disconnect();
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });
  });
});
