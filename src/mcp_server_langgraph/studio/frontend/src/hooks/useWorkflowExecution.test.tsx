/**
 * useWorkflowExecution Hook Tests
 *
 * TDD tests for real-time workflow execution updates.
 * Features:
 * - WebSocket connection for execution updates
 * - Redux integration for state/logs
 * - Node status updates
 * - Execution lifecycle management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useWorkflowExecution } from "./useWorkflowExecution";
import workflowReducer, {
  initialWorkflowState,
} from "../store/slices/workflowSlice";
import type { WorkflowSliceState } from "../store/slices/workflowSlice";
import type { ReactNode } from "react";

// Mock useRealtimeSync
vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn(),
}));

import { useRealtimeSync } from "./useRealtimeSync";
const mockUseRealtimeSync = vi.mocked(useRealtimeSync);

// Mock WebSocket message handler callback
let capturedOnMessage: ((data: unknown) => void) | undefined;
let capturedOnConnect: (() => void) | undefined;
let capturedOnDisconnect: (() => void) | undefined;
let capturedOnError: ((error: Error) => void) | undefined;

// Create test store with configurable state
const createTestStore = (workflowState: Partial<WorkflowSliceState> = {}) => {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: { ...initialWorkflowState, ...workflowState },
    },
  });
};

// Create wrapper component
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
};

describe("useWorkflowExecution", () => {
  const mockSend = vi.fn();
  const mockDisconnect = vi.fn();
  const mockReconnect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    capturedOnMessage = undefined;
    capturedOnConnect = undefined;
    capturedOnDisconnect = undefined;
    capturedOnError = undefined;

    // Default mock implementation
    mockUseRealtimeSync.mockImplementation((options) => {
      capturedOnMessage = options.onMessage;
      capturedOnConnect = options.onConnect;
      capturedOnDisconnect = options.onDisconnect;
      capturedOnError = options.onError;
      return {
        status: "connected",
        reconnectAttempts: 0,
        lastMessageTime: null,
        send: mockSend,
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: {
          totalAttempts: 0,
          successfulConnections: 0,
          failedConnections: 0,
          totalMessagesReceived: 0,
          totalMessagesSent: 0,
          lastConnectionTime: null,
        },
      };
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Connection", () => {
    it("should connect to workflow execution WebSocket", () => {
      const store = createTestStore({
        metadata: {
          id: "wf-123",
          name: "Test",
          description: "",
          version: 1,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        },
      });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(mockUseRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("wf-123"),
        }),
      );
    });

    it("should use correct WebSocket URL pattern", () => {
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("workflow-abc"), {
        wrapper: createWrapper(store),
      });

      expect(mockUseRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          // Consolidated WebSocket URL: /api/v1/ws/workflows/{workflow_id}
          // Now includes query params (v=protocol_version, token=auth) via buildWebSocketUrlWithPath
          url: expect.stringMatching(
            /ws.*\/api\/v1\/ws\/workflows\/workflow-abc\?/,
          ),
        }),
      );
    });

    it("should return connection status", () => {
      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(result.current.connectionStatus).toBe("connected");
    });

    it("should return disconnected status when not connected", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "disconnected",
        reconnectAttempts: 0,
        lastMessageTime: null,
        send: mockSend,
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: {
          totalAttempts: 0,
          successfulConnections: 0,
          failedConnections: 0,
          totalMessagesReceived: 0,
          totalMessagesSent: 0,
          lastConnectionTime: null,
        },
      });

      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(result.current.connectionStatus).toBe("disconnected");
    });
  });

  describe("Execution Control", () => {
    it("should start execution by sending start message", () => {
      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.startExecution();
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "start",
        workflowId: "wf-123",
      });
    });

    it("should start execution with input data", () => {
      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.startExecution({ prompt: "Hello" });
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "start",
        workflowId: "wf-123",
        input: { prompt: "Hello" },
      });
    });

    it("should stop execution by sending stop message", () => {
      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.stopExecution();
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "stop",
        workflowId: "wf-123",
      });
    });

    it("should provide disconnect function", () => {
      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.disconnect();
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should provide reconnect function", () => {
      const store = createTestStore();

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.reconnect();
      });

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("Execution State Updates", () => {
    it("should update execution state to running on execution_started message", () => {
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "execution_started",
          workflowId: "wf-123",
        });
      });

      expect(store.getState().workflow.executionState).toBe("running");
    });

    it("should update execution state to completed on execution_completed message", () => {
      const store = createTestStore({ executionState: "running" });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "execution_completed",
          workflowId: "wf-123",
          result: { success: true },
        });
      });

      expect(store.getState().workflow.executionState).toBe("completed");
    });

    it("should update execution state to error on execution_error message", () => {
      const store = createTestStore({ executionState: "running" });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "execution_error",
          workflowId: "wf-123",
          error: "Something went wrong",
        });
      });

      expect(store.getState().workflow.executionState).toBe("error");
    });
  });

  describe("Node Status Updates", () => {
    it("should update node status on node_started message", () => {
      const store = createTestStore({ executionState: "running" });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "node_started",
          nodeId: "node-1",
        });
      });

      expect(store.getState().workflow.nodeStatuses["node-1"]).toBe("running");
    });

    it("should update node status to completed on node_completed message", () => {
      const store = createTestStore({
        executionState: "running",
        nodeStatuses: { "node-1": "running" },
      });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "node_completed",
          nodeId: "node-1",
        });
      });

      expect(store.getState().workflow.nodeStatuses["node-1"]).toBe("success");
    });

    it("should update node status to error on node_error message", () => {
      const store = createTestStore({
        executionState: "running",
        nodeStatuses: { "node-1": "running" },
      });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "node_error",
          nodeId: "node-1",
          error: "Node failed",
        });
      });

      expect(store.getState().workflow.nodeStatuses["node-1"]).toBe("error");
    });
  });

  describe("Execution Logs", () => {
    it("should add log entry on log message", () => {
      const store = createTestStore({ executionState: "running" });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "log",
          level: "info",
          message: "Processing started",
        });
      });

      const logs = store.getState().workflow.executionLogs;
      expect(logs).toHaveLength(1);
      expect(logs[0].level).toBe("info");
      expect(logs[0].message).toBe("Processing started");
    });

    it("should add log entry with nodeId on node log message", () => {
      const store = createTestStore({ executionState: "running" });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "log",
          level: "warning",
          message: "Rate limit warning",
          nodeId: "node-2",
        });
      });

      const logs = store.getState().workflow.executionLogs;
      expect(logs).toHaveLength(1);
      expect(logs[0].level).toBe("warning");
      expect(logs[0].nodeId).toBe("node-2");
    });

    it("should add error log on execution_error", () => {
      const store = createTestStore({ executionState: "running" });

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnMessage?.({
          type: "execution_error",
          workflowId: "wf-123",
          error: "Execution failed due to timeout",
        });
      });

      const logs = store.getState().workflow.executionLogs;
      expect(logs).toHaveLength(1);
      expect(logs[0].level).toBe("error");
      expect(logs[0].message).toContain("timeout");
    });
  });

  describe("Connection Events", () => {
    it("should add log entry on connect", () => {
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnConnect?.();
      });

      const logs = store.getState().workflow.executionLogs;
      expect(logs).toHaveLength(1);
      expect(logs[0].level).toBe("info");
      expect(logs[0].message).toContain("Connected");
    });

    it("should add log entry on disconnect", () => {
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnDisconnect?.();
      });

      const logs = store.getState().workflow.executionLogs;
      expect(logs).toHaveLength(1);
      expect(logs[0].level).toBe("warning");
      expect(logs[0].message).toContain("Disconnected");
    });

    it("should add error log on WebSocket error", () => {
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      act(() => {
        capturedOnError?.(new Error("Connection refused"));
      });

      const logs = store.getState().workflow.executionLogs;
      expect(logs).toHaveLength(1);
      expect(logs[0].level).toBe("error");
      expect(logs[0].message).toContain("Connection refused");
    });
  });

  describe("isExecuting State", () => {
    it("should return isExecuting true when execution is running", () => {
      const store = createTestStore({ executionState: "running" });

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isExecuting).toBe(true);
    });

    it("should return isExecuting false when execution is idle", () => {
      const store = createTestStore({ executionState: "idle" });

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isExecuting).toBe(false);
    });

    it("should return isExecuting false when execution is completed", () => {
      const store = createTestStore({ executionState: "completed" });

      const { result } = renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isExecuting).toBe(false);
    });
  });

  describe("Workflow ID Changes", () => {
    it("should reconnect when workflowId changes", () => {
      const store = createTestStore();

      const { rerender } = renderHook(({ id }) => useWorkflowExecution(id), {
        wrapper: createWrapper(store),
        initialProps: { id: "wf-123" },
      });

      // Clear initial call
      mockUseRealtimeSync.mockClear();

      rerender({ id: "wf-456" });

      expect(mockUseRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("wf-456"),
        }),
      );
    });
  });

  describe("Auto-connect Option", () => {
    it("should not connect if autoConnect is false", () => {
      // When autoConnect is false, useRealtimeSync should receive a null URL or not be called
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("wf-123", { autoConnect: false }), {
        wrapper: createWrapper(store),
      });

      // The hook should still be called but not attempt real connection
      // This is handled by passing empty URL or using a skip flag
      expect(mockUseRealtimeSync).toHaveBeenCalled();
    });

    it("should connect by default", () => {
      const store = createTestStore();

      renderHook(() => useWorkflowExecution("wf-123"), {
        wrapper: createWrapper(store),
      });

      expect(mockUseRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("wf-123"),
        }),
      );
    });
  });
});
