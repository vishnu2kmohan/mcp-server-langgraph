/**
 * useMCPTasks Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useMCPTasks } from './useMCPTasks';
import type { MCPTask } from '../api/mcp-types';

// Mock tasks
const mockTasks: MCPTask[] = [
  {
    id: 'task-1',
    method: 'tools/call',
    state: 'running',
    progress: 50,
    progressMessage: 'Processing...',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:01:00Z',
  },
  {
    id: 'task-2',
    method: 'tools/call',
    state: 'completed',
    result: { success: true },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:02:00Z',
  },
  {
    id: 'task-3',
    method: 'resources/read',
    state: 'pending',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

// Mock MCPHost context
const mockClient = {
  listTasks: vi.fn().mockResolvedValue(mockTasks),
  getTask: vi.fn().mockResolvedValue(mockTasks[0]),
  cancelTask: vi.fn().mockResolvedValue(undefined),
};

vi.mock('../contexts/MCPHostContext', () => ({
  useMCPHost: () => ({
    getClient: () => mockClient,
    primaryServerId: 'test-server',
  }),
}));

describe('useMCPTasks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should_initialize_with_empty_tasks', () => {
    const { result } = renderHook(() => useMCPTasks());

    expect(result.current.tasks).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should_refresh_tasks', async () => {
    const { result } = renderHook(() => useMCPTasks());

    await act(async () => {
      await result.current.refreshTasks();
    });

    expect(mockClient.listTasks).toHaveBeenCalled();
    expect(result.current.tasks).toEqual(mockTasks);
  });

  it('should_get_single_task', async () => {
    const { result } = renderHook(() => useMCPTasks());

    const task = await result.current.getTask('task-1');

    expect(mockClient.getTask).toHaveBeenCalledWith('task-1');
    expect(task).toEqual(mockTasks[0]);
  });

  it('should_cancel_task', async () => {
    const { result } = renderHook(() => useMCPTasks());

    await act(async () => {
      await result.current.cancelTask('task-1');
    });

    expect(mockClient.cancelTask).toHaveBeenCalledWith('task-1');
    // Should refresh tasks after cancellation
    expect(mockClient.listTasks).toHaveBeenCalled();
  });

  it('should_filter_tasks_by_state', async () => {
    const { result } = renderHook(() => useMCPTasks());

    await act(async () => {
      await result.current.refreshTasks();
    });

    const runningTasks = result.current.getTasksByState('running');
    expect(runningTasks).toHaveLength(1);
    expect(runningTasks[0].id).toBe('task-1');

    const completedTasks = result.current.getTasksByState('completed');
    expect(completedTasks).toHaveLength(1);
    expect(completedTasks[0].id).toBe('task-2');
  });

  it('should_get_active_tasks', async () => {
    const { result } = renderHook(() => useMCPTasks());

    await act(async () => {
      await result.current.refreshTasks();
    });

    const activeTasks = result.current.getActiveTasks();
    expect(activeTasks).toHaveLength(2); // running + pending
    expect(activeTasks.map((t) => t.id)).toEqual(['task-1', 'task-3']);
  });

  it('should_get_completed_tasks', async () => {
    const { result } = renderHook(() => useMCPTasks());

    await act(async () => {
      await result.current.refreshTasks();
    });

    const completedTasks = result.current.getCompletedTasks();
    expect(completedTasks).toHaveLength(1);
    expect(completedTasks[0].id).toBe('task-2');
  });

  it('should_handle_errors', async () => {
    mockClient.listTasks.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useMCPTasks());

    await act(async () => {
      await result.current.refreshTasks();
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.tasks).toEqual([]);
  });
});
