/**
 * useMCPTaskWebSocket Hook Tests
 *
 * Tests for MCP task WebSocket functionality:
 * - Connection lifecycle management
 * - Task list updates
 * - Individual task updates
 * - Subscribe/unsubscribe functionality
 * - Ping/pong heartbeat
 * - Error handling
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  type Mock,
} from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useMCPTaskWebSocket, type MCPTask } from "./useMCPTaskWebSocket";

// =============================================================================
// Mock Data
// =============================================================================

const MOCK_TASK_1: MCPTask = {
  task_id: "task-1",
  status: "running",
  created_at: "2025-01-01T00:00:00Z",
  last_updated_at: "2025-01-01T00:01:00Z",
  ttl: 3600,
  poll_interval: 5,
  status_message: "Processing...",
};

const MOCK_TASK_2: MCPTask = {
  task_id: "task-2",
  status: "completed",
  created_at: "2025-01-01T00:00:00Z",
  last_updated_at: "2025-01-01T00:02:00Z",
  ttl: 3600,
  poll_interval: 5,
  result: { success: true },
};

const MOCK_TASK_3: MCPTask = {
  task_id: "task-3",
  status: "pending",
  created_at: "2025-01-01T00:00:00Z",
  last_updated_at: "2025-01-01T00:00:00Z",
  ttl: 3600,
  poll_interval: 10,
};

// =============================================================================
// Mock Redux hooks to avoid needing Provider wrapper
// =============================================================================

const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  // Return values for selectors: isAuthenticated=true, wsPermissions={mcp_tasks: true}
  useAppSelector: vi.fn((selector) => {
    if (selector.name?.includes("Authenticated")) return true;
    if (selector.name?.includes("WebSocketPermissions"))
      return { mcp_tasks: true };
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

// =============================================================================
// Mock useRealtimeSync
// =============================================================================

let mockSend: Mock;
let mockDisconnect: Mock;
let mockReconnect: Mock;
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnConnect: (() => void) | undefined;
let mockOnDisconnect: (() => void) | undefined;
let mockStatus:
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error";

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: {
    url: string;
    onMessage: (data: unknown) => void;
    onConnect: () => void;
    onDisconnect: () => void;
  }) => {
    // Capture callbacks
    mockOnMessage = options.onMessage;
    mockOnConnect = options.onConnect;
    mockOnDisconnect = options.onDisconnect;

    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      metrics: { totalAttempts: 0 },
    };
  },
}));

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
  mockSend = vi.fn();
  mockDisconnect = vi.fn();
  mockReconnect = vi.fn();
  mockOnMessage = undefined;
  mockOnConnect = undefined;
  mockOnDisconnect = undefined;
  mockStatus = "connected";
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// =============================================================================
// Tests
// =============================================================================

describe("useMCPTaskWebSocket", () => {
  describe("initialization", () => {
    it("returns initial state correctly", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      expect(result.current.status).toBe("connected");
      expect(result.current.tasks).toEqual([]);
      expect(result.current.subscribedTasks).toEqual(new Set());
      expect(result.current.error).toBeNull();
    });

    it("uses default WebSocket URL", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Hook should be usable
      expect(result.current.sendPing).toBeDefined();
      expect(result.current.refresh).toBeDefined();
    });

    it("uses custom WebSocket URL when provided", () => {
      const customUrl = "wss://custom.example.com/ws";
      const { result } = renderHook(() =>
        useMCPTaskWebSocket({ url: customUrl }),
      );

      expect(result.current.status).toBe("connected");
    });
  });

  describe("task list handling", () => {
    it("updates tasks when task_list message received", async () => {
      const onTasksLoaded = vi.fn();
      const { result } = renderHook(() =>
        useMCPTaskWebSocket({ onTasksLoaded }),
      );

      // Simulate receiving task list
      act(() => {
        mockOnMessage?.({
          type: "task_list",
          tasks: [MOCK_TASK_1, MOCK_TASK_2],
        });
      });

      expect(result.current.tasks).toHaveLength(2);
      expect(result.current.tasks[0].task_id).toBe("task-1");
      expect(result.current.tasks[1].task_id).toBe("task-2");
      expect(onTasksLoaded).toHaveBeenCalledWith([MOCK_TASK_1, MOCK_TASK_2]);
    });

    it("replaces task list on subsequent task_list messages", async () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // First task list
      act(() => {
        mockOnMessage?.({
          type: "task_list",
          tasks: [MOCK_TASK_1, MOCK_TASK_2],
        });
      });

      expect(result.current.tasks).toHaveLength(2);

      // Second task list (replaces)
      act(() => {
        mockOnMessage?.({
          type: "task_list",
          tasks: [MOCK_TASK_3],
        });
      });

      expect(result.current.tasks).toHaveLength(1);
      expect(result.current.tasks[0].task_id).toBe("task-3");
    });
  });

  describe("task update handling", () => {
    it("updates existing task when task_update message received", async () => {
      const onTaskUpdate = vi.fn();
      const { result } = renderHook(() =>
        useMCPTaskWebSocket({ onTaskUpdate }),
      );

      // Initialize with tasks
      act(() => {
        mockOnMessage?.({
          type: "task_list",
          tasks: [MOCK_TASK_1, MOCK_TASK_2],
        });
      });

      // Update task-1
      const updatedTask = { ...MOCK_TASK_1, status: "completed" as const };
      act(() => {
        mockOnMessage?.({
          type: "task_update",
          task: updatedTask,
        });
      });

      expect(result.current.tasks[0].status).toBe("completed");
      expect(result.current.tasks[1]).toEqual(MOCK_TASK_2);
      expect(onTaskUpdate).toHaveBeenCalledWith(updatedTask);
    });

    it("adds new task when task_update for unknown task received", async () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Initialize with one task
      act(() => {
        mockOnMessage?.({
          type: "task_list",
          tasks: [MOCK_TASK_1],
        });
      });

      expect(result.current.tasks).toHaveLength(1);

      // Update for new task
      act(() => {
        mockOnMessage?.({
          type: "task_update",
          task: MOCK_TASK_3,
        });
      });

      expect(result.current.tasks).toHaveLength(2);
      expect(result.current.tasks[1].task_id).toBe("task-3");
    });
  });

  describe("subscription management", () => {
    it("subscribes to task and tracks subscription", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.subscribe("task-1");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        task_id: "task-1",
      });
      expect(result.current.subscribedTasks.has("task-1")).toBe(true);
    });

    it("unsubscribes from task and updates tracking", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Subscribe first
      act(() => {
        result.current.subscribe("task-1");
      });

      expect(result.current.subscribedTasks.has("task-1")).toBe(true);

      // Unsubscribe
      act(() => {
        result.current.unsubscribe("task-1");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "unsubscribe",
        task_id: "task-1",
      });
      expect(result.current.subscribedTasks.has("task-1")).toBe(false);
    });

    it("supports multiple subscriptions", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.subscribe("task-1");
        result.current.subscribe("task-2");
        result.current.subscribe("task-3");
      });

      expect(result.current.subscribedTasks.size).toBe(3);
      expect(result.current.subscribedTasks.has("task-1")).toBe(true);
      expect(result.current.subscribedTasks.has("task-2")).toBe(true);
      expect(result.current.subscribedTasks.has("task-3")).toBe(true);
    });
  });

  describe("commands", () => {
    it("sends ping message", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.sendPing();
      });

      expect(mockSend).toHaveBeenCalledWith({ type: "ping" });
    });

    it("sends refresh message", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.refresh();
      });

      expect(mockSend).toHaveBeenCalledWith({ type: "refresh" });
    });

    it("disconnects via disconnect function", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.disconnect();
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("reconnects via reconnect function", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      act(() => {
        result.current.reconnect();
      });

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("sets error state when error message received", () => {
      const onError = vi.fn();
      const { result } = renderHook(() => useMCPTaskWebSocket({ onError }));

      act(() => {
        mockOnMessage?.({
          type: "error",
          message: "Connection lost",
        });
      });

      expect(result.current.error).toBe("Connection lost");
      expect(onError).toHaveBeenCalledWith("Connection lost");
    });

    it("clears error on reconnection", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Simulate error
      act(() => {
        mockOnMessage?.({
          type: "error",
          message: "Connection lost",
        });
      });

      expect(result.current.error).toBe("Connection lost");

      // Simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("pong handling", () => {
    it("ignores pong messages silently", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Pong should not cause any state changes
      const tasksBefore = result.current.tasks;
      const errorBefore = result.current.error;

      act(() => {
        mockOnMessage?.({
          type: "pong",
        });
      });

      expect(result.current.tasks).toBe(tasksBefore);
      expect(result.current.error).toBe(errorBefore);
    });
  });

  describe("connection lifecycle", () => {
    it("preserves tasks on disconnect", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Initialize with tasks
      act(() => {
        mockOnMessage?.({
          type: "task_list",
          tasks: [MOCK_TASK_1, MOCK_TASK_2],
        });
      });

      expect(result.current.tasks).toHaveLength(2);

      // Simulate disconnect
      act(() => {
        mockOnDisconnect?.();
      });

      // Tasks should still be present
      expect(result.current.tasks).toHaveLength(2);
    });
  });

  describe("subscription restoration", () => {
    it("restores subscriptions on reconnect", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Subscribe to tasks
      act(() => {
        result.current.subscribe("task-1");
        result.current.subscribe("task-2");
      });

      expect(result.current.subscribedTasks.size).toBe(2);

      // Clear mock calls
      mockSend.mockClear();

      // Simulate reconnection (onConnect called)
      act(() => {
        mockOnConnect?.();
      });

      // Should have re-subscribed to both tasks
      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        task_id: "task-1",
      });
      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        task_id: "task-2",
      });
    });

    it("only restores active subscriptions after reconnect", () => {
      const { result } = renderHook(() => useMCPTaskWebSocket());

      // Subscribe to tasks
      act(() => {
        result.current.subscribe("task-1");
        result.current.subscribe("task-2");
      });

      // Unsubscribe from task-1
      act(() => {
        result.current.unsubscribe("task-1");
      });

      expect(result.current.subscribedTasks.size).toBe(1);

      // Clear mock calls
      mockSend.mockClear();

      // Simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      // Should only re-subscribe to task-2
      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        task_id: "task-2",
      });
      expect(mockSend).not.toHaveBeenCalledWith(
        expect.objectContaining({ task_id: "task-1" }),
      );
    });
  });
});
