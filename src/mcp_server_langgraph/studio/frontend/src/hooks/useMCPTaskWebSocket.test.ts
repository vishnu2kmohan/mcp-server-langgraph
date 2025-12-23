/**
 * useMCPTaskWebSocket Hook Tests
 *
 * Tests for MCP task status WebSocket hook following TDD.
 * GREEN phase: Tests should now pass with implementation.
 */

import { renderHook, act, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useMCPTaskWebSocket, type MCPTask } from "./useMCPTaskWebSocket";

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnConnect: (() => void) | undefined;
let mockOnDisconnect: (() => void) | undefined;
let mockStatus = "connected" as const;

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn((options) => {
    mockOnMessage = options.onMessage;
    mockOnConnect = options.onConnect;
    mockOnDisconnect = options.onDisconnect;
    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
    };
  }),
}));

describe("useMCPTaskWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "connected";
    mockOnMessage = undefined;
    mockOnConnect = undefined;
    mockOnDisconnect = undefined;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("connection management", () => {
    it("should return status from useRealtimeSync", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());
      expect(result.current.status).toBe("connected");
    });

    it("should have empty tasks initially", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());
      expect(result.current.tasks).toEqual([]);
    });

    it("should expose disconnect and reconnect functions", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());
      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");
    });

    it("should call disconnect when disconnect is called", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());
      result.current.disconnect();
      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should call reconnect when reconnect is called", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());
      result.current.reconnect();
      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("message handling", () => {
    it("should update tasks when task_list message is received", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      const tasks: MCPTask[] = [
        {
          task_id: "task-1",
          status: "running",
          created_at: "2025-01-15T10:00:00Z",
          last_updated_at: "2025-01-15T10:01:00Z",
          ttl: 3600,
          poll_interval: 1000,
          status_message: "Processing...",
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "task_list", tasks });
      });

      expect(result.current.tasks).toEqual(tasks);
    });

    it("should update specific task when task_update message is received", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Set initial tasks
      const initialTasks: MCPTask[] = [
        {
          task_id: "task-1",
          status: "running",
          created_at: "2025-01-15T10:00:00Z",
          last_updated_at: "2025-01-15T10:01:00Z",
          ttl: 3600,
          poll_interval: 1000,
          status_message: "Processing...",
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "task_list", tasks: initialTasks });
      });

      // Update the task
      const updatedTask: MCPTask = {
        ...initialTasks[0],
        status: "completed",
        status_message: "Done!",
      };

      act(() => {
        mockOnMessage?.({ type: "task_update", task: updatedTask });
      });

      expect(result.current.tasks[0].status).toBe("completed");
      expect(result.current.tasks[0].status_message).toBe("Done!");
    });

    it("should add new task when task_update for unknown task is received", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      const newTask: MCPTask = {
        task_id: "task-new",
        status: "running",
        created_at: "2025-01-15T10:00:00Z",
        last_updated_at: "2025-01-15T10:01:00Z",
        ttl: 3600,
        poll_interval: 1000,
        status_message: "New task",
      };

      act(() => {
        mockOnMessage?.({ type: "task_update", task: newTask });
      });

      expect(result.current.tasks).toContainEqual(newTask);
    });

    it("should handle pong message", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Should not throw when pong is received
      act(() => {
        mockOnMessage?.({ type: "pong" });
      });

      // Tasks should remain unchanged
      expect(result.current.tasks).toEqual([]);
    });

    it("should handle error message", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        mockOnMessage?.({ type: "error", message: "Something went wrong" });
      });

      expect(result.current.error).toBe("Something went wrong");
    });
  });

  describe("commands", () => {
    it("should send ping command", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.sendPing();
      });

      expect(mockSend).toHaveBeenCalledWith({ type: "ping" });
    });

    it("should send refresh command", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.refresh();
      });

      expect(mockSend).toHaveBeenCalledWith({ type: "refresh" });
    });

    it("should send subscribe command with task_id", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.subscribe("task-123");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        task_id: "task-123",
      });
    });

    it("should send unsubscribe command with task_id", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.unsubscribe("task-123");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "unsubscribe",
        task_id: "task-123",
      });
    });

    it("should track subscribed tasks", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.subscribe("task-1");
        result.current.subscribe("task-2");
      });

      expect(result.current.subscribedTasks.has("task-1")).toBe(true);
      expect(result.current.subscribedTasks.has("task-2")).toBe(true);
    });

    it("should remove from subscribed tasks on unsubscribe", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.subscribe("task-1");
        result.current.unsubscribe("task-1");
      });

      expect(result.current.subscribedTasks.has("task-1")).toBe(false);
    });
  });

  describe("callbacks", () => {
    it("should call onTaskUpdate callback when task updates", () => {
      const onTaskUpdate = vi.fn();
      renderHook(() => useMCPTaskWebSocket({ onTaskUpdate }));

      const task: MCPTask = {
        task_id: "task-1",
        status: "completed",
        created_at: "2025-01-15T10:00:00Z",
        last_updated_at: "2025-01-15T10:01:00Z",
        ttl: 3600,
        poll_interval: 1000,
        status_message: "Done",
      };

      act(() => {
        mockOnMessage?.({ type: "task_update", task });
      });

      expect(onTaskUpdate).toHaveBeenCalledWith(task);
    });

    it("should call onTasksLoaded callback when tasks list is received", () => {
      const onTasksLoaded = vi.fn();
      renderHook(() => useMCPTaskWebSocket({ onTasksLoaded }));

      const tasks: MCPTask[] = [
        {
          task_id: "task-1",
          status: "running",
          created_at: "2025-01-15T10:00:00Z",
          last_updated_at: "2025-01-15T10:01:00Z",
          ttl: 3600,
          poll_interval: 1000,
          status_message: "Processing",
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "task_list", tasks });
      });

      expect(onTasksLoaded).toHaveBeenCalledWith(tasks);
    });
  });

  describe("URL configuration", () => {
    it("should use default URL if not provided", async () => {
      renderHook(() => useMCPTaskWebSocket());

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("/mcp/tasks/ws"),
        }),
      );
    });

    it("should use custom URL if provided", async () => {
      renderHook(() => useMCPTaskWebSocket({ url: "ws://custom:8000/ws" }));

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: "ws://custom:8000/ws",
        }),
      );
    });
  });

  describe("connection lifecycle", () => {
    it("should clear error on connect", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // First set an error
      act(() => {
        mockOnMessage?.({ type: "error", message: "Connection error" });
      });

      expect(result.current.error).toBe("Connection error");

      // Simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      expect(result.current.error).toBeNull();
    });

    it("should keep tasks on disconnect for resumption", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Set some tasks
      const tasks: MCPTask[] = [
        {
          task_id: "task-1",
          status: "running",
          created_at: "2025-01-15T10:00:00Z",
          last_updated_at: "2025-01-15T10:01:00Z",
          ttl: 3600,
          poll_interval: 1000,
          status_message: "Processing",
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "task_list", tasks });
      });

      // Simulate disconnect
      act(() => {
        mockOnDisconnect?.();
      });

      // Tasks should be preserved
      expect(result.current.tasks).toEqual(tasks);
    });
  });
});
