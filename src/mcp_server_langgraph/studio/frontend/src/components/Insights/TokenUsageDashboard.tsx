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

import { Button } from "@/components/UI";

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
    blue: "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30",
    green:
      "text-success-600 dark:text-success-400 bg-success-50 dark:bg-success-900/30",
    purple:
      "text-insight-600 dark:text-insight-400 bg-insight-50 dark:bg-insight-900/30",
    orange:
      "text-grafana-600 dark:text-grafana-400 bg-grafana-50 dark:bg-grafana-900/30",
  };

  return (
    <div className="p-4 rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <div className={`p-1.5 rounded ${colorClasses[color]}`}>{icon}</div>
        )}
        <span className="text-sm text-neutral-500 dark:text-neutral-400">
          {label}
        </span>
      </div>
      <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
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
    ? "bg-grafana-500"
    : percentage > 90
      ? "bg-error-500"
      : "bg-primary-500";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-neutral-600 dark:text-neutral-400">{label}</span>
        <span className="text-neutral-900 dark:text-neutral-100">
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
        className="h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden"
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
      <div className="text-center text-neutral-500 dark:text-neutral-400 py-8">
        No usage history available
      </div>
    );
  }

  const maxTokens = Math.max(...history.map((h) => h.tokens));

  return (
    <div data-testid="usage-history-chart" className="space-y-2">
      <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
        Usage Over Time
      </h4>
      <div className="flex items-end gap-1 h-24">
        {history.map((entry, index) => {
          const height = (entry.tokens / maxTokens) * 100;
          return (
            <div
              key={index}
              className="flex-1 bg-primary-500 dark:bg-primary-400 rounded-t transition-all hover:bg-primary-600 dark:hover:bg-primary-300"
              style={{ height: `${height}%` }}
              title={`${formatNumber(entry.tokens)} tokens at ${new Date(entry.timestamp).toLocaleTimeString()}`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400">
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
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          Token Usage
        </h3>
        <Button
          variant="secondary"
          className="p-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg focus:ring-primary-500"
          type="button"
          onClick={refresh}
          aria-label="Refresh token usage"
        >
          <RefreshCw size={16} />
        </Button>
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
        <div className="p-4 rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <ProgressBar
            value={totalTokens}
            max={contextWindowSize}
            label={`Context Window (${formatNumber(contextWindowSize)} max)`}
            showWarning={isContextWindowNearLimit}
          />
          {isContextWindowNearLimit && (
            <p className="text-sm text-grafana-600 dark:text-grafana-400 mt-2">
              Warning: Context window usage is high. Consider starting a new
              session.
            </p>
          )}
        </div>
      )}
      {/* History Chart */}
      {showHistory && history && (
        <div className="p-4 rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <HistoryChart history={history} />
        </div>
      )}
      {/* Loading overlay */}
      {showLoading && (
        <div className="absolute inset-0 bg-white/50 dark:bg-neutral-900/50 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
        </div>
      )}
    </div>
  );
}

export default TokenUsageDashboard;
