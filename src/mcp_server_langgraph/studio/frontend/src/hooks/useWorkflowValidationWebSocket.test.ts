/**
 * useWorkflowValidationWebSocket Hook Tests
 *
 * Tests for WebSocket-based real-time workflow validation events.
 * Listens to orchestrator_status for workflow_validation_* events.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock the useRealtimeSync hook
vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn(),
}));

// Mock auth utilities
vi.mock("../utils/storage", () => ({
  getAuthToken: vi.fn(() => "mock-token"),
}));

// Mock websocket utilities
vi.mock("../utils/websocket", () => ({
  buildWebSocketUrl: vi.fn(
    () => "ws://localhost/api/v1/ws/orchestrator/status",
  ),
  WS_ENDPOINTS: {
    ORCHESTRATOR_STATUS: "/api/v1/ws/orchestrator/status",
  },
}));

// Mock Redux store
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => vi.fn(),
  useAppSelector: vi.fn(() => true), // isAuthenticated
}));

vi.mock("../store/slices/authSlice", () => ({
  logout: vi.fn(),
  selectIsAuthenticated: vi.fn(),
}));

import { useRealtimeSync } from "./useRealtimeSync";
import { useWorkflowValidationWebSocket } from "./useWorkflowValidationWebSocket";

describe("useWorkflowValidationWebSocket", () => {
  const mockSend = vi.fn();
  const mockDisconnect = vi.fn();
  const mockReconnect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock for useRealtimeSync
    (useRealtimeSync as ReturnType<typeof vi.fn>).mockReturnValue({
      status: "connected",
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      metrics: { totalAttempts: 0 },
    });
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("initialization", () => {
    it("should initialize with default state", () => {
      const { result } = renderHook(() => useWorkflowValidationWebSocket());

      expect(result.current.isConnected).toBe(true);
      expect(result.current.validationState).toBeNull();
      expect(result.current.errors).toEqual([]);
      expect(result.current.warnings).toEqual([]);
    });

    it("should connect to orchestrator_status WebSocket", () => {
      renderHook(() => useWorkflowValidationWebSocket());

      expect(useRealtimeSync).toHaveBeenCalled();
    });
  });

  describe("workflow validation events", () => {
    it("should handle workflow_validation_started event", () => {
      let onMessageHandler: ((data: unknown) => void) | undefined;

      (useRealtimeSync as ReturnType<typeof vi.fn>).mockImplementation(
        (options: { onMessage?: (data: unknown) => void }) => {
          onMessageHandler = options.onMessage;
          return {
            status: "connected",
            send: mockSend,
            disconnect: mockDisconnect,
            reconnect: mockReconnect,
            metrics: { totalAttempts: 0 },
          };
        },
      );

      const onValidationStarted = vi.fn();
      const { result } = renderHook(() =>
        useWorkflowValidationWebSocket({
          workflowId: "wf-123",
          onValidationStarted,
        }),
      );

      // Simulate receiving validation started event
      act(() => {
        onMessageHandler?.({
          type: "workflow_validation_started",
          workflow_id: "wf-123",
          user_id: "user-456",
        });
      });

      expect(result.current.validationState).toBe("validating");
      expect(onValidationStarted).toHaveBeenCalledWith("wf-123");
    });

    it("should handle workflow_validation_passed event", () => {
      let onMessageHandler: ((data: unknown) => void) | undefined;

      (useRealtimeSync as ReturnType<typeof vi.fn>).mockImplementation(
        (options: { onMessage?: (data: unknown) => void }) => {
          onMessageHandler = options.onMessage;
          return {
            status: "connected",
            send: mockSend,
            disconnect: mockDisconnect,
            reconnect: mockReconnect,
            metrics: { totalAttempts: 0 },
          };
        },
      );

      const onValidationPassed = vi.fn();
      const { result } = renderHook(() =>
        useWorkflowValidationWebSocket({
          workflowId: "wf-123",
          onValidationPassed,
        }),
      );

      // Simulate receiving validation passed event
      act(() => {
        onMessageHandler?.({
          type: "workflow_validation_passed",
          workflow_id: "wf-123",
          warnings: ["Consider adding error handling"],
        });
      });

      expect(result.current.validationState).toBe("valid");
      expect(result.current.warnings).toEqual([
        "Consider adding error handling",
      ]);
      expect(onValidationPassed).toHaveBeenCalledWith([
        "Consider adding error handling",
      ]);
    });

    it("should handle workflow_validation_failed event", () => {
      let onMessageHandler: ((data: unknown) => void) | undefined;

      (useRealtimeSync as ReturnType<typeof vi.fn>).mockImplementation(
        (options: { onMessage?: (data: unknown) => void }) => {
          onMessageHandler = options.onMessage;
          return {
            status: "connected",
            send: mockSend,
            disconnect: mockDisconnect,
            reconnect: mockReconnect,
            metrics: { totalAttempts: 0 },
          };
        },
      );

      const onValidationFailed = vi.fn();
      const { result } = renderHook(() =>
        useWorkflowValidationWebSocket({
          workflowId: "wf-123",
          onValidationFailed,
        }),
      );

      // Simulate receiving validation failed event
      act(() => {
        onMessageHandler?.({
          type: "workflow_validation_failed",
          workflow_id: "wf-123",
          errors: ["Missing start node"],
          warnings: [],
        });
      });

      expect(result.current.validationState).toBe("invalid");
      expect(result.current.errors).toEqual(["Missing start node"]);
      expect(onValidationFailed).toHaveBeenCalledWith(
        ["Missing start node"],
        [],
      );
    });

    it("should filter events by workflowId", () => {
      let onMessageHandler: ((data: unknown) => void) | undefined;

      (useRealtimeSync as ReturnType<typeof vi.fn>).mockImplementation(
        (options: { onMessage?: (data: unknown) => void }) => {
          onMessageHandler = options.onMessage;
          return {
            status: "connected",
            send: mockSend,
            disconnect: mockDisconnect,
            reconnect: mockReconnect,
            metrics: { totalAttempts: 0 },
          };
        },
      );

      const onValidationStarted = vi.fn();
      renderHook(() =>
        useWorkflowValidationWebSocket({
          workflowId: "wf-123",
          onValidationStarted,
        }),
      );

      // Event for different workflow should be ignored
      act(() => {
        onMessageHandler?.({
          type: "workflow_validation_started",
          workflow_id: "wf-other",
          user_id: "user-456",
        });
      });

      expect(onValidationStarted).not.toHaveBeenCalled();
    });
  });

  describe("connection management", () => {
    it("should expose disconnect method", () => {
      const { result } = renderHook(() => useWorkflowValidationWebSocket());

      result.current.disconnect();

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should expose reconnect method", () => {
      const { result } = renderHook(() => useWorkflowValidationWebSocket());

      result.current.reconnect();

      expect(mockReconnect).toHaveBeenCalled();
    });
  });
});
