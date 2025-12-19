/**
 * BackgroundAgentPanel Component
 *
 * Phase 4: AI-Native Features
 * Displays status of background AI agents/tasks.
 *
 * Features:
 * - Shows running, queued, completed, and failed agents
 * - Progress indicators for running tasks
 * - Cancel and retry actions
 * - Collapsible panel
 */

import { useState } from "react";
import {
  Bot,
  ChevronDown,
  ChevronUp,
  Circle,
  CheckCircle,
  XCircle,
  Loader2,
  X,
  RefreshCw,
  Clock,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type AgentStatus = "queued" | "running" | "completed" | "failed";

export interface BackgroundAgent {
  id: string;
  name: string;
  task: string;
  status: AgentStatus;
  progress: number;
  startedAt: number;
  error?: string;
}

export interface BackgroundAgentPanelProps {
  agents: BackgroundAgent[];
  onCancel: (agentId: string) => void;
  onRetry: (agentId: string) => void;
  defaultCollapsed?: boolean;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

function formatElapsedTime(startedAt: number): string {
  const elapsed = Date.now() - startedAt;
  const seconds = Math.floor(elapsed / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

// =============================================================================
// Status Icon
// =============================================================================

function StatusIcon({ status }: { status: AgentStatus }) {
  switch (status) {
    case "running":
      return <Loader2 size={14} className="animate-spin text-blue-500" />;
    case "queued":
      return <Clock size={14} className="text-gray-400" />;
    case "completed":
      return <CheckCircle size={14} className="text-green-500" />;
    case "failed":
      return <XCircle size={14} className="text-red-500" />;
    default:
      return <Circle size={14} className="text-gray-400" />;
  }
}

function getStatusColor(status: AgentStatus): string {
  switch (status) {
    case "running":
      return "text-blue-600 dark:text-blue-400";
    case "queued":
      return "text-gray-500 dark:text-gray-400";
    case "completed":
      return "text-green-600 dark:text-green-400";
    case "failed":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-gray-500 dark:text-gray-400";
  }
}

// =============================================================================
// Component
// =============================================================================

export function BackgroundAgentPanel({
  agents,
  onCancel,
  onRetry,
  defaultCollapsed = false,
  className,
}: BackgroundAgentPanelProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div
      data-testid="background-agent-panel"
      className={cn(
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900",
        className,
      )}
    >
      {/* Header */}
      <button
        type="button"
        aria-label={collapsed ? "Expand agents" : "Collapse agents"}
        onClick={() => setCollapsed(!collapsed)}
        className={cn(
          "w-full flex items-center justify-between px-3 py-2",
          "hover:bg-gray-50 dark:hover:bg-gray-800",
          "transition-colors",
        )}
      >
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-primary-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Background Agents
          </span>
          <span
            className={cn(
              "px-1.5 py-0.5 rounded-full text-xs font-medium",
              "bg-gray-100 dark:bg-gray-700",
              "text-gray-600 dark:text-gray-300",
            )}
          >
            {agents.length}
          </span>
        </div>
        {collapsed ? (
          <ChevronDown size={16} className="text-gray-400" />
        ) : (
          <ChevronUp size={16} className="text-gray-400" />
        )}
      </button>

      {/* Content */}
      {!collapsed && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          {agents.length === 0 ? (
            <div className="flex items-center justify-center py-6 text-sm text-gray-500 dark:text-gray-400">
              <Bot size={20} className="mr-2 opacity-50" />
              No active agents
            </div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-800">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-start gap-3 px-3 py-2"
                >
                  {/* Status icon */}
                  <div className="flex-shrink-0 mt-0.5">
                    <StatusIcon status={agent.status} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {agent.name}
                      </span>
                      <span
                        className={cn("text-xs", getStatusColor(agent.status))}
                      >
                        {agent.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {agent.task}
                    </p>

                    {/* Progress bar for running */}
                    {agent.status === "running" && (
                      <div className="mt-1 flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 transition-all"
                            style={{ width: `${agent.progress}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">
                          {agent.progress}%
                        </span>
                      </div>
                    )}

                    {/* Error message for failed */}
                    {agent.status === "failed" && agent.error && (
                      <p className="mt-1 text-xs text-red-500">{agent.error}</p>
                    )}

                    {/* Elapsed time */}
                    <span className="text-xs text-gray-400 mt-1">
                      {formatElapsedTime(agent.startedAt)}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex-shrink-0">
                    {(agent.status === "running" ||
                      agent.status === "queued") && (
                      <button
                        type="button"
                        aria-label="Cancel agent"
                        onClick={() => onCancel(agent.id)}
                        className={cn(
                          "p-1 rounded",
                          "text-gray-400 hover:text-red-500",
                          "hover:bg-red-100 dark:hover:bg-red-900/30",
                          "transition-colors",
                        )}
                      >
                        <X size={14} />
                      </button>
                    )}
                    {agent.status === "failed" && (
                      <button
                        type="button"
                        aria-label="Retry agent"
                        onClick={() => onRetry(agent.id)}
                        className={cn(
                          "p-1 rounded",
                          "text-gray-400 hover:text-blue-500",
                          "hover:bg-blue-100 dark:hover:bg-blue-900/30",
                          "transition-colors",
                        )}
                      >
                        <RefreshCw size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
