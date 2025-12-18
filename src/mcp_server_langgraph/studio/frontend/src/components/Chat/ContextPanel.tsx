/**
 * ContextPanel Component
 *
 * Right sidebar panel showing context information for the current chat session.
 * Features:
 * - Available tools list with refresh
 * - Recent activity feed
 * - Session cost tracking
 * - Collapsible/expandable panel
 */

import { useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Wrench,
  Activity,
  DollarSign,
} from "lucide-react";

export interface Tool {
  name: string;
  description: string;
}

export interface ActivityItem {
  timestamp: number;
  action: string;
  details: string;
}

export interface SessionCost {
  tokens: number;
  cost: number;
  model: string;
}

export interface ContextPanelProps {
  tools: Tool[];
  activities: ActivityItem[];
  sessionCost?: SessionCost;
  currentTraceId?: string | null;
  onRefreshTools?: () => void;
  onViewCostDetails?: () => void;
  onViewAllTraces?: () => void;
  onViewTrace?: (traceId: string) => void;
}

/**
 * Format timestamp to relative time string
 */
function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (seconds < 60) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

/**
 * Format number with commas
 */
function formatNumber(num: number): string {
  return num.toLocaleString();
}

/**
 * Format cost as currency
 */
function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

export function ContextPanel({
  tools,
  activities,
  sessionCost,
  currentTraceId,
  onRefreshTools,
  onViewCostDetails,
  onViewAllTraces,
  onViewTrace,
}: ContextPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (isCollapsed) {
    return (
      <div
        className="hidden md:flex w-12 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex-col items-center py-4"
        data-testid="context-panel"
      >
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          aria-label="Expand context panel"
        >
          <ChevronLeft size={20} />
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Mobile overlay backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 md:hidden"
        onClick={() => setIsCollapsed(true)}
        data-testid="context-panel-overlay"
      />
      <div
        className={`
          w-72 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col
          fixed md:relative right-0 z-50 h-full
          transform transition-transform duration-200 ease-in-out
          translate-x-0
        `}
        data-testid="context-panel"
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 dark:text-gray-100">
            Context
          </h2>
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            aria-label="Collapse context panel"
          >
            <ChevronRight size={18} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Tools Section */}
          <div className="border-b border-gray-200 dark:border-gray-700">
            <div className="px-4 py-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Wrench
                    size={14}
                    className="text-gray-500 dark:text-gray-400"
                  />
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    TOOLS
                  </h3>
                </div>
                <button
                  onClick={onRefreshTools}
                  className="p-1 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  aria-label="Refresh tools"
                >
                  <RefreshCw size={14} />
                </button>
              </div>
              {tools.length === 0 ? (
                <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                  No tools available
                </p>
              ) : (
                <>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    {tools.length} available
                  </p>
                  <div className="space-y-1">
                    {tools.map((tool) => (
                      <div
                        key={tool.name}
                        className="text-sm text-gray-700 dark:text-gray-300 px-2 py-1 bg-gray-50 dark:bg-gray-700/50 rounded"
                        title={tool.description}
                      >
                        {tool.name}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Activity Section */}
          <div className="border-b border-gray-200 dark:border-gray-700">
            <div className="px-4 py-3">
              <div className="flex items-center gap-2 mb-2">
                <Activity
                  size={14}
                  className="text-gray-500 dark:text-gray-400"
                />
                <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  ACTIVITY
                </h3>
              </div>
              {activities.length === 0 ? (
                <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                  No activity yet
                </p>
              ) : (
                <div className="space-y-2">
                  {activities.map((activity, index) => (
                    <div key={index} className="text-xs">
                      <span className="text-gray-400 dark:text-gray-500">
                        {formatRelativeTime(activity.timestamp)}
                      </span>
                      <span className="text-gray-700 dark:text-gray-300 ml-2">
                        {activity.action}
                      </span>
                      {activity.details && (
                        <span className="text-gray-500 dark:text-gray-400 ml-1">
                          ({activity.details})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-2 flex flex-col gap-1">
                {currentTraceId && onViewTrace && (
                  <button
                    onClick={() => onViewTrace(currentTraceId)}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline text-left"
                  >
                    View current trace →
                  </button>
                )}
                {onViewAllTraces && (
                  <button
                    onClick={onViewAllTraces}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline text-left"
                  >
                    View all traces →
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Session Cost Section */}
          <div className="px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign
                size={14}
                className="text-gray-500 dark:text-gray-400"
              />
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                SESSION COST
              </h3>
            </div>
            {!sessionCost ? (
              <p className="text-sm text-gray-400 dark:text-gray-500 italic">
                No cost data
              </p>
            ) : (
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Tokens:
                  </span>
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    {formatNumber(sessionCost.tokens)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Cost:
                  </span>
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    {formatCost(sessionCost.cost)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">
                    Model:
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">
                    {sessionCost.model}
                  </span>
                </div>
              </div>
            )}
            {sessionCost && onViewCostDetails && (
              <button
                onClick={onViewCostDetails}
                className="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                View cost details →
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
