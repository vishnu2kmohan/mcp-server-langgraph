/**
 * useMCPTaskWebSocket Hook
 *
 * WebSocket hook for MCP task status monitoring.
 * Provides real-time task status updates, subscription management,
 * and task list synchronization.
 *
 * Based on backend endpoint: /api/v1/mcp/tasks/ws
 */

import { useState, useCallback, useRef, useMemo } from "react";
import { useRealtimeSync } from "./useRealtimeSync";
import { useAppSelector } from "../store/hooks";
import { selectIsAuthenticated } from "../store/slices/authSlice";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

/**
 * MCP Task status values
 */
export type MCPTaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/**
 * MCP Task structure matching backend schema
 */
export interface MCPTask {
  task_id: string;
  status: MCPTaskStatus;
  created_at: string;
  last_updated_at: string;
  ttl: number;
  poll_interval: number;
  status_message?: string;
  result?: unknown;
  error?: string;
}

/**
 * WebSocket message types from server
 */
interface TaskListMessage {
  type: "task_list";
  tasks: MCPTask[];
}

interface TaskUpdateMessage {
  type: "task_update";
  task: MCPTask;
}

interface PongMessage {
  type: "pong";
}

interface ErrorMessage {
  type: "error";
  message: string;
}

type ServerMessage =
  | TaskListMessage
  | TaskUpdateMessage
  | PongMessage
  | ErrorMessage;

/**
 * Options for useMCPTaskWebSocket hook
 */
export interface UseMCPTaskWebSocketOptions {
  /** Custom WebSocket URL (defaults to /api/v1/mcp/tasks/ws) */
  url?: string;
  /** Callback when a task is updated */
  onTaskUpdate?: (task: MCPTask) => void;
  /** Callback when task list is loaded */
  onTasksLoaded?: (tasks: MCPTask[]) => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * Return type for useMCPTaskWebSocket hook
 */
export interface UseMCPTaskWebSocketReturn {
  /** Current connection status */
  status:
    | "connecting"
    | "connected"
    | "disconnected"
    | "reconnecting"
    | "error";
  /** List of all known tasks */
  tasks: MCPTask[];
  /** Set of task IDs currently subscribed to */
  subscribedTasks: Set<string>;
  /** Current error message, if any */
  error: string | null;
  /** Send a ping to keep connection alive */
  sendPing: () => void;
  /** Request a refresh of the task list */
  refresh: () => void;
  /** Subscribe to updates for a specific task */
  subscribe: (taskId: string) => void;
  /** Unsubscribe from updates for a specific task */
  unsubscribe: (taskId: string) => void;
  /** Manually disconnect from WebSocket */
  disconnect: () => void;
  /** Manually reconnect to WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Default URL
// =============================================================================

function getDefaultWebSocketUrl(token?: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${protocol}//${host}/api/v1/ws/mcp/tasks${tokenParam}`;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useMCPTaskWebSocket(
  options: UseMCPTaskWebSocketOptions = {},
): UseMCPTaskWebSocketReturn {
  const { url: customUrl, onTaskUpdate, onTasksLoaded, onError } = options;

  // Get auth state and token for WebSocket authentication
  const isAuthenticated = useAppSelector(selectIsAuthenticated);
  const authToken = isAuthenticated ? (getAuthToken() ?? undefined) : undefined;

  // Compute WebSocket URL - only generate URL when authenticated
  // Passing empty string prevents connection attempt before auth is ready
  const url = useMemo(
    () =>
      isAuthenticated ? (customUrl ?? getDefaultWebSocketUrl(authToken)) : "",
    [customUrl, authToken, isAuthenticated],
  );

  // State
  const [tasks, setTasks] = useState<MCPTask[]>([]);
  const [subscribedTasks, setSubscribedTasks] = useState<Set<string>>(
    new Set(),
  );
  const [error, setError] = useState<string | null>(null);

  // Refs for callbacks and state to avoid stale closures
  const callbacksRef = useRef({ onTaskUpdate, onTasksLoaded, onError });
  callbacksRef.current = { onTaskUpdate, onTasksLoaded, onError };

  // Ref to track subscribed tasks for restoration on reconnect
  const subscribedTasksRef = useRef<Set<string>>(new Set());

  // Ref for send function to use in handleConnect
  const sendRef = useRef<(data: unknown) => void>(() => {});

  // Handle incoming messages
  const handleMessage = useCallback((data: unknown) => {
    const message = data as ServerMessage;

    switch (message.type) {
      case "task_list":
        setTasks(message.tasks);
        callbacksRef.current.onTasksLoaded?.(message.tasks);
        break;

      case "task_update":
        setTasks((prevTasks) => {
          const taskIndex = prevTasks.findIndex(
            (t) => t.task_id === message.task.task_id,
          );
          if (taskIndex >= 0) {
            // Update existing task
            const newTasks = [...prevTasks];
            newTasks[taskIndex] = message.task;
            return newTasks;
          } else {
            // Add new task
            return [...prevTasks, message.task];
          }
        });
        callbacksRef.current.onTaskUpdate?.(message.task);
        break;

      case "pong":
        // Heartbeat response - no action needed
        break;

      case "error":
        setError(message.message);
        callbacksRef.current.onError?.(message.message);
        break;
    }
  }, []);

  // Handle connection established - restore subscriptions
  const handleConnect = useCallback(() => {
    setError(null);

    // Restore subscriptions on reconnect
    subscribedTasksRef.current.forEach((taskId) => {
      sendRef.current({ type: "subscribe", task_id: taskId });
    });
  }, []);

  // Handle disconnection - keep tasks for resumption
  const handleDisconnect = useCallback(() => {
    // Tasks are preserved for when we reconnect
  }, []);

  // Use the realtime sync hook for WebSocket management
  // Enable exponential backoff for better reconnection behavior
  const { status, send, disconnect, reconnect } = useRealtimeSync({
    url,
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    exponentialBackoff: true,
    reconnectInterval: 1000, // Start with 1 second
    maxDelayMs: 30000, // Max 30 seconds between attempts
    maxReconnectAttempts: 10, // Try up to 10 times
  });

  // Keep sendRef in sync for use in handleConnect
  sendRef.current = send;

  // Commands
  const sendPing = useCallback(() => {
    send({ type: "ping" });
  }, [send]);

  const refresh = useCallback(() => {
    send({ type: "refresh" });
  }, [send]);

  const subscribe = useCallback(
    (taskId: string) => {
      send({ type: "subscribe", task_id: taskId });
      subscribedTasksRef.current.add(taskId);
      setSubscribedTasks((prev) => new Set(prev).add(taskId));
    },
    [send],
  );

  const unsubscribe = useCallback(
    (taskId: string) => {
      send({ type: "unsubscribe", task_id: taskId });
      subscribedTasksRef.current.delete(taskId);
      setSubscribedTasks((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    },
    [send],
  );

  return {
    status,
    tasks,
    subscribedTasks,
    error,
    sendPing,
    refresh,
    subscribe,
    unsubscribe,
    disconnect,
    reconnect,
  };
}

export default useMCPTaskWebSocket;
