/**
 * TokenUsageDashboard Component
 *
 * Dashboard displaying token usage metrics for a chat session.
 * Features:
 * - Total token count display
 * - Input/output token breakdown
 * - Cost estimation (when pricing available)
 * - Context window usage indicator
 * - Historical usage chart
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on Claude Code data tracking patterns.
 */

import { RefreshCw, ArrowDown, ArrowUp, Coins, Gauge } from "lucide-react";
import { useTokenUsage } from "../../hooks/useTokenUsage";

// ==============================================================================
// Types
// ==============================================================================

export interface TokenUsageDashboardProps {
  /** Session ID to fetch usage for */
  sessionId: string;
  /** Show in compact mode */
  compact?: boolean;
  /** Show loading skeleton */
  showLoading?: boolean;
  /** Show historical usage chart */
  showHistory?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function formatNumber(num: number): string {
  return num.toLocaleString();
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(2)}`;
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}

// ==============================================================================
// Metric Card Component
// ==============================================================================

interface MetricCardProps {
  label: string;
  value: string;
  icon?: React.ReactNode;
  subtext?: string;
  color?: "blue" | "green" | "purple" | "orange";
}

function MetricCard({
  label,
  value,
  icon,
  subtext,
  color = "blue",
}: MetricCardProps) {
  const colorClasses = {
    blue: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30",
    green:
      "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30",
    purple:
      "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30",
    orange:
      "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30",
  };

  return (
    <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <div className={`p-1.5 rounded ${colorClasses[color]}`}>{icon}</div>
        )}
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {label}
        </span>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {subtext}
        </div>
      )}
    </div>
  );
}

// ==============================================================================
// Progress Bar Component
// ==============================================================================

interface ProgressBarProps {
  value: number;
  max: number;
  label: string;
  showWarning?: boolean;
}

function ProgressBar({ value, max, label, showWarning }: ProgressBarProps) {
  const percentage = Math.min((value / max) * 100, 100);
  const barColor = showWarning
    ? "bg-orange-500"
    : percentage > 90
      ? "bg-red-500"
      : "bg-blue-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="text-gray-900 dark:text-gray-100">
          {formatPercentage(percentage)}
        </span>
      </div>
      <div
        data-testid="context-window-progress"
        role="progressbar"
        aria-label={label}
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
      >
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// ==============================================================================
// History Chart Component
// ==============================================================================

interface HistoryChartProps {
  history: { timestamp: string; tokens: number }[];
}

function HistoryChart({ history }: HistoryChartProps) {
  if (!history || history.length === 0) {
    return (
      <div className="text-center text-gray-500 dark:text-gray-400 py-8">
        No usage history available
      </div>
    );
  }

  const maxTokens = Math.max(...history.map((h) => h.tokens));

  return (
    <div data-testid="usage-history-chart" className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Usage Over Time
      </h4>
      <div className="flex items-end gap-1 h-24">
        {history.map((entry, index) => {
          const height = (entry.tokens / maxTokens) * 100;
          return (
            <div
              key={index}
              className="flex-1 bg-blue-500 dark:bg-blue-400 rounded-t transition-all hover:bg-blue-600 dark:hover:bg-blue-300"
              style={{ height: `${height}%` }}
              title={`${formatNumber(entry.tokens)} tokens at ${new Date(entry.timestamp).toLocaleTimeString()}`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
          {history[0]
            ? new Date(history[0].timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })
            : ""}
        </span>
        <span>
          {(() => {
            const lastEntry = history[history.length - 1];
            return lastEntry
              ? new Date(lastEntry.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })
              : "";
          })()}
        </span>
      </div>
    </div>
  );
}

// ==============================================================================
// Main Component
// ==============================================================================

export function TokenUsageDashboard({
  sessionId,
  compact = false,
  showLoading = false,
  showHistory = false,
  className = "",
}: TokenUsageDashboardProps) {
  const {
    inputTokens,
    outputTokens,
    totalTokens,
    estimatedCost,
    contextWindowSize,
    contextWindowUsage: _contextWindowUsage,
    isContextWindowNearLimit,
    history,
    refresh,
  } = useTokenUsage(sessionId);

  return (
    <div
      data-testid="token-usage-dashboard"
      data-compact={compact}
      className={`space-y-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Token Usage
        </h3>
        <button
          type="button"
          onClick={refresh}
          aria-label="Refresh token usage"
          className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Metrics Grid */}
      <div
        className={`grid gap-4 ${compact ? "grid-cols-2" : "grid-cols-2 lg:grid-cols-4"}`}
      >
        <MetricCard
          label="Total Tokens"
          value={formatNumber(totalTokens)}
          icon={<Gauge size={16} />}
          color="blue"
        />

        <MetricCard
          label="Input"
          value={formatNumber(inputTokens)}
          icon={<ArrowDown size={16} />}
          color="green"
        />

        <MetricCard
          label="Output"
          value={formatNumber(outputTokens)}
          icon={<ArrowUp size={16} />}
          color="purple"
        />

        {estimatedCost !== null && (
          <MetricCard
            label="Estimated Cost"
            value={formatCost(estimatedCost)}
            icon={<Coins size={16} />}
            color="orange"
          />
        )}
      </div>

      {/* Context Window Usage */}
      {contextWindowSize && (
        <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
          <ProgressBar
            value={totalTokens}
            max={contextWindowSize}
            label={`Context Window (${formatNumber(contextWindowSize)} max)`}
            showWarning={isContextWindowNearLimit}
          />
          {isContextWindowNearLimit && (
            <p className="text-sm text-orange-600 dark:text-orange-400 mt-2">
              Warning: Context window usage is high. Consider starting a new
              session.
            </p>
          )}
        </div>
      )}

      {/* History Chart */}
      {showHistory && history && (
        <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
          <HistoryChart history={history} />
        </div>
      )}

      {/* Loading overlay */}
      {showLoading && (
        <div className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      )}
    </div>
  );
}

export default TokenUsageDashboard;
