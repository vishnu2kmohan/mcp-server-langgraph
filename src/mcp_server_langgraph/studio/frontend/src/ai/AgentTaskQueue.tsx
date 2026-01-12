/**
 * AgentTaskQueue
 *
 * Task queue management component for background AI agents.
 * Displays queued/running/completed tasks with actions.
 */
import { useMemo } from "react";
import {
  X,
  Trash2,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  ListTodo,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectAllAgents,
  selectRunningAgentCount,
  removeAgent,
  clearCompletedAgents,
  type BackgroundAgent,
  type AgentStatus,
} from "../store/slices/backgroundAgentSlice";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface AgentTaskQueueProps {
  /** Callback when a task is cancelled */
  onCancel?: (agentId: string) => void;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Status Config
// =============================================================================

const STATUS_CONFIG: Record<
  AgentStatus,
  { icon: React.ReactNode; color: string; bgColor: string }
> = {
  queued: {
    icon: <Clock className="h-3 w-3" />,
    color: "text-warning-600",
    bgColor: "bg-warning-500",
  },
  running: {
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
    color: "text-primary-600",
    bgColor: "bg-primary-500",
  },
  completed: {
    icon: <CheckCircle className="h-3 w-3" />,
    color: "text-success-600",
    bgColor: "bg-success-500",
  },
  failed: {
    icon: <AlertCircle className="h-3 w-3" />,
    color: "text-error-600",
    bgColor: "bg-error-500",
  },
  awaiting_approval: {
    icon: <AlertCircle className="h-3 w-3" />,
    color: "text-warning-600",
    bgColor: "bg-warning-500",
  },
  awaiting_clarification: {
    icon: <Clock className="h-3 w-3" />,
    color: "text-insight-600",
    bgColor: "bg-insight-500",
  },
};

// =============================================================================
// Task Item Component
// =============================================================================

interface TaskItemProps {
  agent: BackgroundAgent;
  onCancel?: (agentId: string) => void;
  onDismiss: (agentId: string) => void;
}

function TaskItem({ agent, onCancel, onDismiss }: TaskItemProps) {
  const config = STATUS_CONFIG[agent.status];
  const canCancel = agent.status === "queued" || agent.status === "running";
  const canDismiss = agent.status === "failed" || agent.status === "completed";

  return (
    <li
      className={cn(
        "p-3 rounded-lg border",
        "bg-white dark:bg-neutral-800",
        "border-neutral-200 dark:border-neutral-700",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              data-testid={`status-badge-${agent.id}`}
              className={cn(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
                config.bgColor,
                "text-white",
              )}
            >
              {config.icon}
              {agent.status}
            </span>
            <h4 className="text-sm font-medium text-neutral-900 dark:text-white truncate">
              {agent.name}
            </h4>
          </div>
          <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400 truncate">
            {agent.task}
          </p>
          {agent.error && (
            <p className="mt-1 text-xs text-error-500">{agent.error}</p>
          )}
        </div>

        <div className="flex items-center gap-1">
          {canCancel && (
            <Button
              type="button"
              onClick={() => onCancel?.(agent.id)}
              aria-label={`Cancel ${agent.name}`}
              className={cn(
                "p-1 rounded",
                "text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300",
                "dark:hover:text-neutral-300",
                "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
              )}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
          {canDismiss && (
            <Button
              type="button"
              onClick={() => onDismiss(agent.id)}
              aria-label={`Dismiss ${agent.name}`}
              className={cn(
                "p-1 rounded",
                "text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300",
                "dark:hover:text-neutral-300",
                "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
              )}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
      {/* Progress bar for running tasks */}
      {agent.status === "running" && (
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            <span>Progress</span>
            <span>{agent.progress}%</span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={agent.progress}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden"
          >
            <div
              className="h-full bg-primary-500 transition-all duration-300"
              style={{ width: `${agent.progress}%` }}
            />
          </div>
        </div>
      )}
    </li>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AgentTaskQueue({ onCancel, className }: AgentTaskQueueProps) {
  const dispatch = useAppDispatch();
  const agents = useAppSelector(selectAllAgents);
  const runningCount = useAppSelector(selectRunningAgentCount);

  const hasCompletedOrFailed = useMemo(
    () => agents.some((a) => a.status === "completed" || a.status === "failed"),
    [agents],
  );

  const handleDismiss = (agentId: string) => {
    dispatch(removeAgent(agentId));
  };

  const handleClearCompleted = () => {
    dispatch(clearCompletedAgents());
  };

  // Empty state
  if (agents.length === 0) {
    return (
      <div
        data-testid="agent-task-queue"
        className={cn(
          "flex flex-col items-center justify-center p-8 text-center",
          "text-neutral-500 dark:text-neutral-400",
          className,
        )}
      >
        <div data-testid="empty-queue">
          <ListTodo className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-sm font-medium">No tasks in queue</p>
          <p className="text-xs mt-1">
            Background agents will appear here when running
          </p>
        </div>
      </div>
    );
  }

  const taskLabel = agents.length === 1 ? "task" : "tasks";

  return (
    <div
      data-testid="agent-task-queue"
      className={cn("flex flex-col h-full", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
        <div>
          <h3
            className="text-sm font-semibold text-neutral-900 dark:text-white"
            role="heading"
          >
            Task Queue
          </h3>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            {agents.length} {taskLabel}
            {runningCount > 0 && ` (${runningCount} running)`}
          </p>
        </div>

        {hasCompletedOrFailed && (
          <Button
            type="button"
            onClick={handleClearCompleted}
            className={cn(
              "text-xs px-2 py-1 rounded",
              "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200",
              "dark:text-neutral-400 dark:hover:text-neutral-200",
              "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
            )}
          >
            Clear completed
          </Button>
        )}
      </div>
      {/* Task list */}
      <ul role="list" className="flex-1 overflow-y-auto p-4 space-y-3">
        {agents.map((agent) => (
          <TaskItem
            key={agent.id}
            agent={agent}
            onCancel={onCancel}
            onDismiss={handleDismiss}
          />
        ))}
      </ul>
    </div>
  );
}
