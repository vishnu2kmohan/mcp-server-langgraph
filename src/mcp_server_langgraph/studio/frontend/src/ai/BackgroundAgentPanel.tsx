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
  AlertTriangle,
  HelpCircle,
} from "lucide-react";
import { cn } from "../utils/cn";
import type {
  BackgroundAgent,
  AgentStatus,
} from "../store/slices/backgroundAgentSlice";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

// Re-export types for backwards compatibility
export type { AgentStatus, BackgroundAgent };

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
      return <Loader2 size={14} className="animate-spin text-primary-500" />;
    case "queued":
      return (
        <Clock size={14} className="text-neutral-400 dark:text-neutral-400" />
      );
    case "completed":
      return <CheckCircle size={14} className="text-success-500" />;
    case "failed":
      return <XCircle size={14} className="text-error-500" />;
    case "awaiting_approval":
      return <AlertTriangle size={14} className="text-warning-500" />;
    case "awaiting_clarification":
      return <HelpCircle size={14} className="text-insight-500" />;
    default:
      return (
        <Circle size={14} className="text-neutral-400 dark:text-neutral-400" />
      );
  }
}

function getStatusColor(status: AgentStatus): string {
  switch (status) {
    case "running":
      return "text-primary-600 dark:text-primary-400";
    case "queued":
      return "text-neutral-500 dark:text-neutral-400";
    case "completed":
      return "text-success-600 dark:text-success-400";
    case "failed":
      return "text-error-600 dark:text-error-400";
    case "awaiting_approval":
      return "text-warning-600 dark:text-warning-400";
    case "awaiting_clarification":
      return "text-insight-600 dark:text-insight-400";
    default:
      return "text-neutral-500 dark:text-neutral-400";
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
        "rounded-lg border border-neutral-200 dark:border-neutral-700",
        "bg-white dark:bg-neutral-900",
        className,
      )}
    >
      {/* Header */}
      <Button
        type="button"
        aria-label={collapsed ? "Expand agents" : "Collapse agents"}
        onClick={() => setCollapsed(!collapsed)}
        className={cn(
          "w-full flex items-center justify-between px-3 py-2",
          "hover:bg-neutral-50 dark:hover:bg-neutral-800",
          "transition-colors",
        )}
      >
        <div className="flex items-center gap-2">
          <Bot size={16} className="text-primary-500" />
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Background Agents
          </span>
          <span
            className={cn(
              "px-1.5 py-0.5 rounded-full text-xs font-medium",
              "bg-neutral-100 dark:bg-neutral-700",
              "text-neutral-600 dark:text-neutral-300",
            )}
          >
            {agents.length}
          </span>
        </div>
        {collapsed ? (
          <ChevronDown
            size={16}
            className="text-neutral-400 dark:text-neutral-400"
          />
        ) : (
          <ChevronUp
            size={16}
            className="text-neutral-400 dark:text-neutral-400"
          />
        )}
      </Button>
      {/* Content */}
      {!collapsed && (
        <div className="border-t border-neutral-200 dark:border-neutral-700">
          {agents.length === 0 ? (
            <div className="flex items-center justify-center py-6 text-sm text-neutral-500 dark:text-neutral-400">
              <Bot size={20} className="mr-2 opacity-50" />
              No active agents
            </div>
          ) : (
            <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
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
                      <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                        {agent.name}
                      </span>
                      <span
                        className={cn("text-xs", getStatusColor(agent.status))}
                      >
                        {agent.status}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate">
                      {agent.task}
                    </p>

                    {/* Progress bar for running */}
                    {agent.status === "running" && (
                      <div className="mt-1 flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary-500 transition-all"
                            style={{ width: `${agent.progress}%` }}
                          />
                        </div>
                        <span className="text-xs text-neutral-500 dark:text-neutral-400">
                          {agent.progress}%
                        </span>
                      </div>
                    )}

                    {/* Error message for failed */}
                    {agent.status === "failed" && agent.error && (
                      <p className="mt-1 text-xs text-error-500">
                        {agent.error}
                      </p>
                    )}

                    {/* Elapsed time */}
                    <span className="text-xs text-neutral-400 dark:text-neutral-400 mt-1">
                      {formatElapsedTime(agent.startedAt)}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex-shrink-0">
                    {(agent.status === "running" ||
                      agent.status === "queued") && (
                      <Button
                        type="button"
                        aria-label="Cancel agent"
                        onClick={() => onCancel(agent.id)}
                        className={cn(
                          "p-1 rounded",
                          "text-neutral-400 dark:text-neutral-400 hover:text-error-500",
                          "hover:bg-error-100 dark:hover:bg-error-900/30",
                          "transition-colors",
                        )}
                      >
                        <X size={14} />
                      </Button>
                    )}
                    {agent.status === "failed" && (
                      <Button
                        type="button"
                        aria-label="Retry agent"
                        onClick={() => onRetry(agent.id)}
                        className={cn(
                          "p-1 rounded",
                          "text-neutral-400 dark:text-neutral-400 hover:text-primary-500",
                          "hover:bg-primary-100 dark:hover:bg-primary-900/30",
                          "transition-colors",
                        )}
                      >
                        <RefreshCw size={14} />
                      </Button>
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
