/**
 * useAIOrchestratorStatus Hook Tests
 *
 * TDD tests for AI orchestrator status hook that provides
 * real-time orchestrator status updates to the StatusBar.
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

// Mock auth - useAppSelector is called with selectIsAuthenticated (returns boolean)
// and selectWebSocketPermissions (returns permissions object).
// Since vi.mock is hoisted, we use a call-counting approach: first call returns
// isAuthenticated, second call returns wsPermissions.
const mockUseAppSelector = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppSelector: (...args: unknown[]) => mockUseAppSelector(...args),
  useAppDispatch: () => vi.fn(),
}));

vi.mock("../store/slices/authSlice", async () => {
  const actual = await vi.importActual("../store/slices/authSlice");
  return {
    ...actual,
    selectIsAuthenticated: () => true,
    selectWebSocketPermissions: () => ({ orchestrator_status: true }),
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
// Mock WebSocket URL builders
vi.mock("../utils/websocket", () => ({
  buildWebSocketUrl: () => "ws://localhost/test",
  WS_ENDPOINTS: {
    AI_SUGGESTIONS: "/api/v1/ws/ai/suggestions",
  },
}));

vi.mock("../utils/websocketAuth", () => ({
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION: { id: "test", message: "test" },
  showProtocolVersionMismatchToast: vi.fn(),
}));

vi.mock("../utils/websocketTelemetry", () => ({
  reportWebSocketMetrics: vi.fn(),
}));

vi.mock("../store/slices/notificationSlice", () => ({
  addNotification: vi.fn(),
}));

// Import after mocking
import {
  useAIOrchestratorStatus,
  type OrchestratorStatus as _OrchestratorStatus,
  type TaskCategory,
} from "./useAIOrchestratorStatus";

// ============================================================================
// Test Store Setup
// ============================================================================

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

// ============================================================================
// Tests
// ============================================================================

describe("useAIOrchestratorStatus", () => {
  const mockDisconnect = vi.fn();
  const mockReconnect = vi.fn();
  const mockSend = vi.fn();
  const capturedCallbacks: {
    onMessage: ((data: unknown) => void) | null;
  } = {
    onMessage: null,
  };

  beforeEach(() => {
    vi.resetAllMocks();
    capturedCallbacks.onMessage = null;

    // Configure useAppSelector to return correct values per selector.
    // The hook calls useAppSelector with selectIsAuthenticated and
    // selectWebSocketPermissions. We pass the selector a mock state
    // so it returns the expected value for each.
    const mockAuthState = {
      auth: {
        user: {
          websocketPermissions: { orchestrator_status: true },
        },
      },
    };
    mockUseAppSelector.mockImplementation(
      (selector: (state: unknown) => unknown) => {
        return selector(mockAuthState);
      },
    );

    // Default mock that captures callbacks
    mockUseRealtimeSync.mockImplementation(
      (options?: { onMessage?: (data: unknown) => void }) => {
        if (options?.onMessage) {
          capturedCallbacks.onMessage = options.onMessage;
        }
        return {
          status: "connected" as const,
          send: mockSend,
          disconnect: mockDisconnect,
          reconnect: mockReconnect,
          metrics: { totalAttempts: 0 },
        };
      },
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    capturedCallbacks.onMessage = null;
  });

  // ============================================================================
  // Basic Hook Tests
  // ============================================================================

  describe("initial state", () => {
    it("should return idle status when connected but no messages", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      expect(result.current.status).toBe("idle");
      expect(result.current.currentTask).toBeNull();
      expect(result.current.taskHistory).toHaveLength(0);
    });

    it("should return disconnected connectionStatus when disabled", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "disconnected" as const,
        send: mockSend,
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: { totalAttempts: 0 },
      });

      const { result } = renderHook(
        () => useAIOrchestratorStatus({ enabled: false }),
        { wrapper },
      );

      expect(result.current.connectionStatus).toBe("disconnected");
    });

    it("should return connected connectionStatus when enabled", () => {
      const { result } = renderHook(
        () => useAIOrchestratorStatus({ enabled: true }),
        { wrapper },
      );

      expect(result.current.connectionStatus).toBe("connected");
    });
  });

  // ============================================================================
  // Status Update Tests
  // ============================================================================

  describe("status updates", () => {
    it("should update status when orchestrator_status message received", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Simulate receiving orchestrator_status message
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "orchestrator_status",
          payload: {
            status: "processing",
            message: "Analyzing persona...",
            task_type: "persona_analysis",
            category: "ux",
          },
        });
      });

      expect(result.current.status).toBe("processing");
      expect(result.current.statusMessage).toBe("Analyzing persona...");
    });

    it("should update status when task_started message received", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-123",
            task_type: "error_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      expect(result.current.status).toBe("processing");
      expect(result.current.currentTask).not.toBeNull();
      expect(result.current.currentTask?.taskId).toBe("task-123");
      expect(result.current.currentTask?.taskType).toBe("error_analysis");
    });

    it("should update status when task_completed message received", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // First start a task
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-123",
            task_type: "disclosure_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      expect(result.current.status).toBe("processing");

      // Then complete it
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_completed",
          payload: {
            task_id: "task-123",
            task_type: "disclosure_analysis",
            category: "ux",
            completed_at: new Date().toISOString(),
            success: true,
          },
        });
      });

      expect(result.current.status).toBe("idle");
      expect(result.current.currentTask).toBeNull();
      expect(result.current.taskHistory.length).toBeGreaterThan(0);
    });

    it("should handle task_failed message", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start and fail a task
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-456",
            task_type: "nudge_recommendation",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_failed",
          payload: {
            task_id: "task-456",
            task_type: "nudge_recommendation",
            category: "ux",
            failed_at: new Date().toISOString(),
            error: "LLM rate limit exceeded",
          },
        });
      });

      expect(result.current.status).toBe("error");
      expect(result.current.lastError).toBe("LLM rate limit exceeded");
      expect(result.current.currentTask).toBeNull();
    });
  });

  // ============================================================================
  // Task Category Tests
  // ============================================================================

  describe("task categories", () => {
    const categories: TaskCategory[] = [
      "ux",
      "session",
      "conversation",
      "canvas",
      "diagram",
      "trace",
      "hitl",
      "command",
      "alert",
    ];

    categories.forEach((category) => {
      it(`should handle ${category} category tasks`, () => {
        const { result } = renderHook(() => useAIOrchestratorStatus(), {
          wrapper,
        });

        act(() => {
          capturedCallbacks.onMessage?.({
            type: "task_started",
            payload: {
              task_id: `task-${category}`,
              task_type: "test_task",
              category,
              started_at: new Date().toISOString(),
            },
          });
        });

        expect(result.current.currentTask?.category).toBe(category);
      });
    });
  });

  // ============================================================================
  // StatusBar Integration Tests
  // ============================================================================

  describe("StatusBar integration", () => {
    it("should provide agentStatus for StatusBar", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "orchestrator_status",
          payload: {
            status: "processing",
            message: "Thinking...",
            task_type: "intent_detect",
            category: "conversation",
          },
        });
      });

      // The statusMessage should be suitable for StatusBar's agentStatus prop
      expect(result.current.statusMessage).toBe("Thinking...");
      expect(result.current.statusForStatusBar).toBe("Thinking...");
    });

    it("should return undefined for statusForStatusBar when idle", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // No status message when idle - StatusBar should derive from other sources
      expect(result.current.statusForStatusBar).toBeUndefined();
    });

    it("should clear statusForStatusBar after task completion", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start task
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-789",
            task_type: "artifact_suggest_type",
            category: "canvas",
            started_at: new Date().toISOString(),
          },
        });
      });

      expect(result.current.statusForStatusBar).toBeDefined();

      // Complete task
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_completed",
          payload: {
            task_id: "task-789",
            task_type: "artifact_suggest_type",
            category: "canvas",
            completed_at: new Date().toISOString(),
            success: true,
          },
        });
      });

      // Should be undefined after completion
      expect(result.current.statusForStatusBar).toBeUndefined();
    });
  });

  // ============================================================================
  // Callback Tests
  // ============================================================================

  describe("callbacks", () => {
    it("should call onStatusChange when status changes", () => {
      const onStatusChange = vi.fn();

      renderHook(() => useAIOrchestratorStatus({ onStatusChange }), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "orchestrator_status",
          payload: {
            status: "processing",
            message: "Analyzing...",
            task_type: "trace_summarize",
            category: "trace",
          },
        });
      });

      expect(onStatusChange).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "processing",
          message: "Analyzing...",
        }),
      );
    });

    it("should call onTaskComplete when task completes", () => {
      const onTaskComplete = vi.fn();

      renderHook(() => useAIOrchestratorStatus({ onTaskComplete }), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-complete-test",
            task_type: "risk_assess",
            category: "hitl",
            started_at: new Date().toISOString(),
          },
        });
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_completed",
          payload: {
            task_id: "task-complete-test",
            task_type: "risk_assess",
            category: "hitl",
            completed_at: new Date().toISOString(),
            success: true,
          },
        });
      });

      expect(onTaskComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: "task-complete-test",
          taskType: "risk_assess",
        }),
      );
    });
  });

  // ============================================================================
  // Progress Tracking Tests
  // ============================================================================

  describe("task progress", () => {
    it("should return empty taskProgress initially", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      expect(result.current.taskProgress).toEqual({});
    });

    it("should update taskProgress when task_progress message received", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start a task first
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-progress-1",
            task_type: "persona_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      // Send progress update
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_progress",
          payload: {
            task_id: "task-progress-1",
            progress: 50,
            message: "Processing step 2 of 4...",
          },
        });
      });

      expect(result.current.taskProgress["task-progress-1"]).toBe(50);
    });

    it("should update task in activeTasks with progress", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start a task
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-progress-2",
            task_type: "error_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      // Send progress
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_progress",
          payload: {
            task_id: "task-progress-2",
            progress: 75,
          },
        });
      });

      const task = result.current.activeTasks.find(
        (t) => t.taskId === "task-progress-2",
      );
      expect(task?.progress).toBe(75);
    });

    it("should update statusMessage when progress includes message", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-progress-3",
            task_type: "disclosure_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_progress",
          payload: {
            task_id: "task-progress-3",
            progress: 25,
            message: "Analyzing disclosures...",
          },
        });
      });

      expect(result.current.statusMessage).toBe("Analyzing disclosures...");
    });

    it("should clear progress when task completes", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start and progress
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-progress-4",
            task_type: "nudge_recommendation",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_progress",
          payload: {
            task_id: "task-progress-4",
            progress: 100,
          },
        });
      });

      expect(result.current.taskProgress["task-progress-4"]).toBe(100);

      // Complete
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_completed",
          payload: {
            task_id: "task-progress-4",
            task_type: "nudge_recommendation",
            category: "ux",
            completed_at: new Date().toISOString(),
            success: true,
          },
        });
      });

      expect(result.current.taskProgress["task-progress-4"]).toBeUndefined();
    });

    it("should clear progress when task fails", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start and progress
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-progress-5",
            task_type: "intent_detect",
            category: "conversation",
            started_at: new Date().toISOString(),
          },
        });
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_progress",
          payload: {
            task_id: "task-progress-5",
            progress: 50,
          },
        });
      });

      // Fail
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_failed",
          payload: {
            task_id: "task-progress-5",
            task_type: "intent_detect",
            category: "conversation",
            failed_at: new Date().toISOString(),
            error: "LLM timeout",
          },
        });
      });

      expect(result.current.taskProgress["task-progress-5"]).toBeUndefined();
    });
  });

  // ============================================================================
  // Queue Depth Tests
  // ============================================================================

  describe("queue depth", () => {
    it("should return 0 queueDepth initially", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      expect(result.current.queueDepth).toBe(0);
    });

    it("should update queueDepth when queue_update message received", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "queue_update",
          payload: {
            action: "added",
            task_id: "queued-task-1",
            task_type: "persona_analysis",
            category: "ux",
            queue_depth: 3,
          },
        });
      });

      expect(result.current.queueDepth).toBe(3);
    });

    it("should handle queue depth changes", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Add to queue
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "queue_update",
          payload: {
            action: "added",
            task_id: "queued-task-2",
            queue_depth: 5,
          },
        });
      });

      expect(result.current.queueDepth).toBe(5);

      // Task starts (removed from queue)
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "queue_update",
          payload: {
            action: "removed",
            task_id: "queued-task-2",
            queue_depth: 4,
          },
        });
      });

      expect(result.current.queueDepth).toBe(4);
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe("edge cases", () => {
    it("should handle multiple concurrent tasks", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Start multiple tasks
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-a",
            task_type: "persona_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_started",
          payload: {
            task_id: "task-b",
            task_type: "error_analysis",
            category: "ux",
            started_at: new Date().toISOString(),
          },
        });
      });

      // activeTasks should track all running tasks
      expect(result.current.activeTasks.length).toBe(2);

      // Complete one task
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "task_completed",
          payload: {
            task_id: "task-a",
            task_type: "persona_analysis",
            category: "ux",
            completed_at: new Date().toISOString(),
            success: true,
          },
        });
      });

      expect(result.current.activeTasks.length).toBe(1);
      expect(result.current.status).toBe("processing"); // Still processing task-b
    });

    it("should handle disconnection gracefully", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "disconnected" as const,
        send: mockSend,
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: { totalAttempts: 0 },
      });

      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      // Should show disconnected status
      expect(result.current.connectionStatus).toBe("disconnected");
    });

    it("should return functions for disconnect and reconnect", () => {
      const { result } = renderHook(() => useAIOrchestratorStatus(), {
        wrapper,
      });

      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");
    });
  });
});
