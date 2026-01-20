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
    blue: "text-primary-10 dark:text-primary-7 bg-primary-1 bg-primary-4",
    green:
      "text-success-10 dark:text-success-7 bg-success-1 bg-success-4",
    purple:
      "text-insight-10 dark:text-insight-9 bg-insight-1 dark:bg-insight-a4",
    orange:
      "text-grafana-10 dark:text-grafana-5 bg-grafana-1 dark:bg-grafana-12/30",
  };

  return (
    <div className="p-4 rounded-lg bg-neutral-1 border border-neutral-5">
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <div className={`p-1.5 rounded ${colorClasses[color]}`}>{icon}</div>
        )}
        <span className="text-sm text-neutral-10">
          {label}
        </span>
      </div>
      <div className="text-2xl font-bold text-neutral-12">
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-neutral-10 mt-1">
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
    ? "bg-grafana-9"
    : percentage > 90
      ? "bg-error-9"
      : "bg-primary-9";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-neutral-11">{label}</span>
        <span className="text-neutral-12">
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
        className="h-2 bg-neutral-3 rounded-full overflow-hidden"
      >
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ '--progress': `${percentage}%` } as React.CSSProperties}
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
      <div className="text-center text-neutral-10 py-8">
        No usage history available
      </div>
    );
  }

  const maxTokens = Math.max(...history.map((h) => h.tokens));

  return (
    <div data-testid="usage-history-chart" className="space-y-2">
      <h4 className="text-sm font-medium text-neutral-11">
        Usage Over Time
      </h4>
      <div className="flex items-end gap-1 h-24">
        {history.map((entry, index) => {
          const height = (entry.tokens / maxTokens) * 100;
          return (
            <div
              key={index}
              className="flex-1 bg-primary-9 dark:bg-primary-7 rounded-t transition-all hover:bg-primary-10 dark:hover:bg-primary-5 dynamic-height"
              style={{ "--height": `${height}%` } as React.CSSProperties}
              title={`${formatNumber(entry.tokens)} tokens at ${new Date(entry.timestamp).toLocaleTimeString()}`}
            />
          );
        })}
      </div>
      <div className="flex justify-between text-xs text-neutral-10">
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
        <h3 className="text-lg font-semibold text-neutral-12">
          Token Usage
        </h3>
        <Button size="icon"
          variant="secondary"
          className="p-2 text-neutral-10 hover:text-neutral-11 hover:bg-neutral-2 rounded-lg focus:ring-primary-7"
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
        <div className="p-4 rounded-lg bg-neutral-1 border border-neutral-5">
          <ProgressBar
            value={totalTokens}
            max={contextWindowSize}
            label={`Context Window (${formatNumber(contextWindowSize)} max)`}
            showWarning={isContextWindowNearLimit}
          />
          {isContextWindowNearLimit && (
            <p className="text-sm text-grafana-10 dark:text-grafana-5 mt-2">
              Warning: Context window usage is high. Consider starting a new
              session.
            </p>
          )}
        </div>
      )}
      {/* History Chart */}
      {showHistory && history && (
        <div className="p-4 rounded-lg bg-neutral-1 border border-neutral-5">
          <HistoryChart history={history} />
        </div>
      )}
      {/* Loading overlay */}
      {showLoading && (
        <div className="absolute inset-0 bg-neutral-a6 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-9" />
        </div>
      )}
    </div>
  );
}

export default TokenUsageDashboard;
