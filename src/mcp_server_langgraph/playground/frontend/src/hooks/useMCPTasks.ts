/**
 * useMCPTasks Hook
 *
 * Provides access to MCP tasks (SEP-1686: Durable Request Tracking).
 * Supports polling for task status updates.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useMCPHost } from '../contexts/MCPHostContext';
import type { MCPTask, MCPTaskState } from '../api/mcp-types';

// =============================================================================
// Types
// =============================================================================

export interface UseMCPTasksOptions {
  /** Enable automatic polling for task updates */
  pollEnabled?: boolean;
  /** Polling interval in milliseconds (default: 2000) */
  pollInterval?: number;
  /** Only poll for active tasks (pending/running) */
  pollActiveOnly?: boolean;
}

export interface UseMCPTasksResult {
  // Task list
  tasks: MCPTask[];
  isLoading: boolean;
  error: string | null;

  // Task operations
  refreshTasks: () => Promise<void>;
  getTask: (taskId: string) => Promise<MCPTask>;
  cancelTask: (taskId: string) => Promise<void>;

  // Task filtering helpers
  getTasksByState: (state: MCPTaskState) => MCPTask[];
  getActiveTasks: () => MCPTask[];
  getCompletedTasks: () => MCPTask[];
}

// =============================================================================
// Hook
// =============================================================================

export function useMCPTasks(options: UseMCPTasksOptions = {}): UseMCPTasksResult {
  const { pollEnabled = false, pollInterval = 2000, pollActiveOnly = true } = options;
  const { getClient, primaryServerId } = useMCPHost();

  const [tasks, setTasks] = useState<MCPTask[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshTasks = useCallback(async () => {
    if (!primaryServerId) {
      setError('No primary server connected');
      return;
    }

    const client = getClient(primaryServerId);
    if (!client) {
      setError('Primary server client not available');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const taskList = await client.listTasks();
      setTasks(taskList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to list tasks');
    } finally {
      setIsLoading(false);
    }
  }, [getClient, primaryServerId]);

  const getTask = useCallback(
    async (taskId: string): Promise<MCPTask> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }

      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }

      return client.getTask(taskId);
    },
    [getClient, primaryServerId]
  );

  const cancelTask = useCallback(
    async (taskId: string): Promise<void> => {
      if (!primaryServerId) {
        throw new Error('No primary server connected');
      }

      const client = getClient(primaryServerId);
      if (!client) {
        throw new Error('Primary server client not available');
      }

      await client.cancelTask(taskId);
      // Refresh tasks after cancellation
      await refreshTasks();
    },
    [getClient, primaryServerId, refreshTasks]
  );

  const getTasksByState = useCallback(
    (state: MCPTaskState): MCPTask[] => {
      return tasks.filter((task) => task.state === state);
    },
    [tasks]
  );

  const getActiveTasks = useCallback((): MCPTask[] => {
    return tasks.filter((task) => task.state === 'pending' || task.state === 'running');
  }, [tasks]);

  const getCompletedTasks = useCallback((): MCPTask[] => {
    return tasks.filter(
      (task) => task.state === 'completed' || task.state === 'failed' || task.state === 'cancelled'
    );
  }, [tasks]);

  // Polling effect
  useEffect(() => {
    if (!pollEnabled || !primaryServerId) {
      return;
    }

    const poll = async () => {
      // If only polling active tasks, check if we have any
      if (pollActiveOnly) {
        const activeTasks = getActiveTasks();
        if (activeTasks.length === 0) {
          // No active tasks, schedule next poll anyway
          pollTimeoutRef.current = setTimeout(poll, pollInterval);
          return;
        }
      }

      await refreshTasks();
      pollTimeoutRef.current = setTimeout(poll, pollInterval);
    };

    // Start polling
    pollTimeoutRef.current = setTimeout(poll, pollInterval);

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, [pollEnabled, pollInterval, pollActiveOnly, primaryServerId, getActiveTasks, refreshTasks]);

  return {
    tasks,
    isLoading,
    error,
    refreshTasks,
    getTask,
    cancelTask,
    getTasksByState,
    getActiveTasks,
    getCompletedTasks,
  };
}
