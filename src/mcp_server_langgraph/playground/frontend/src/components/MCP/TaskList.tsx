/**
 * TaskList Component
 *
 * Displays MCP tasks (SEP-1686: Durable Request Tracking).
 * Shows task status, progress, and allows cancellation.
 */

import React, { useCallback } from 'react';
import clsx from 'clsx';
import { useMCPTasks } from '../../hooks/useMCPTasks';
import type { MCPTask, MCPTaskState } from '../../api/mcp-types';

export interface TaskListProps {
  className?: string;
  showCompleted?: boolean;
  pollEnabled?: boolean;
  pollInterval?: number;
}

// Task state to visual indicator mapping
const STATE_CONFIG: Record<MCPTaskState, { label: string; color: string; icon: string }> = {
  pending: {
    label: 'Pending',
    color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    icon: '⏳',
  },
  running: {
    label: 'Running',
    color: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300',
    icon: '▶️',
  },
  completed: {
    label: 'Completed',
    color: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300',
    icon: '✅',
  },
  failed: {
    label: 'Failed',
    color: 'bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300',
    icon: '❌',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300',
    icon: '🚫',
  },
};

export function TaskList({
  className,
  showCompleted = true,
  pollEnabled = true,
  pollInterval = 2000,
}: TaskListProps): React.ReactElement {
  const {
    tasks,
    isLoading,
    error,
    refreshTasks,
    cancelTask,
    getActiveTasks,
    getCompletedTasks,
  } = useMCPTasks({ pollEnabled, pollInterval, pollActiveOnly: true });

  const handleCancelTask = useCallback(
    async (taskId: string) => {
      try {
        await cancelTask(taskId);
      } catch (err) {
        console.error('Failed to cancel task:', err);
      }
    },
    [cancelTask]
  );

  const activeTasks = getActiveTasks();
  const completedTasks = showCompleted ? getCompletedTasks() : [];

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-dark-border">
        <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary uppercase tracking-wider">
          Tasks ({tasks.length})
        </h3>
        <button
          onClick={refreshTasks}
          disabled={isLoading}
          className={clsx(
            'p-1.5 rounded-lg text-gray-500 dark:text-dark-textMuted',
            'hover:bg-gray-100 dark:hover:bg-dark-hover',
            'disabled:opacity-50'
          )}
          title="Refresh tasks"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-3 bg-error-50 dark:bg-error-900/20 border-b border-error-200 dark:border-error-800">
          <p className="text-sm text-error-700 dark:text-error-400">{error}</p>
        </div>
      )}

      {/* Task list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {/* Active Tasks */}
        {activeTasks.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase px-2">
              Active
            </h4>
            {activeTasks.map((task) => (
              <TaskCard key={task.id} task={task} onCancel={handleCancelTask} />
            ))}
          </div>
        )}

        {/* Completed Tasks */}
        {completedTasks.length > 0 && (
          <div className="space-y-2 mt-4">
            <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase px-2">
              Completed
            </h4>
            {completedTasks.map((task) => (
              <TaskCard key={task.id} task={task} onCancel={handleCancelTask} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {tasks.length === 0 && !isLoading && (
          <div className="text-center py-8 text-gray-500 dark:text-dark-textMuted">
            <p>No tasks.</p>
          </div>
        )}

        {/* Loading state */}
        {isLoading && tasks.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-dark-textMuted animate-pulse">
            <p>Loading tasks...</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface TaskCardProps {
  task: MCPTask;
  onCancel: (taskId: string) => void;
}

function TaskCard({ task, onCancel }: TaskCardProps): React.ReactElement {
  const stateConfig = STATE_CONFIG[task.state];
  const isActive = task.state === 'pending' || task.state === 'running';

  return (
    <div
      className={clsx(
        'p-3 rounded-lg border transition-colors',
        'bg-white dark:bg-dark-surface border-gray-200 dark:border-dark-border'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {/* Task method */}
          <h5 className="font-medium text-gray-900 dark:text-dark-text truncate text-sm">
            {task.method}
          </h5>

          {/* Task ID */}
          <p className="text-xs text-gray-400 dark:text-dark-textMuted truncate">
            {task.id}
          </p>
        </div>

        {/* State badge */}
        <span
          className={clsx(
            'flex-shrink-0 px-2 py-0.5 text-xs font-medium rounded',
            stateConfig.color
          )}
        >
          {stateConfig.icon} {stateConfig.label}
        </span>
      </div>

      {/* Progress bar */}
      {task.progress !== undefined && isActive && (
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-dark-textMuted mb-1">
            <span>{task.progressMessage || 'Processing...'}</span>
            <span>{task.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-dark-border rounded-full h-1.5">
            <div
              className="bg-primary-500 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${task.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {task.error && (
        <div className="mt-2 p-2 bg-error-50 dark:bg-error-900/20 rounded text-xs text-error-700 dark:text-error-400">
          {task.error.message}
        </div>
      )}

      {/* Cancel button for active tasks */}
      {isActive && (
        <button
          onClick={() => onCancel(task.id)}
          className={clsx(
            'mt-2 px-3 py-1 text-xs font-medium rounded',
            'bg-gray-100 dark:bg-dark-bg text-gray-700 dark:text-dark-textSecondary',
            'hover:bg-gray-200 dark:hover:bg-dark-hover'
          )}
        >
          Cancel
        </button>
      )}
    </div>
  );
}
