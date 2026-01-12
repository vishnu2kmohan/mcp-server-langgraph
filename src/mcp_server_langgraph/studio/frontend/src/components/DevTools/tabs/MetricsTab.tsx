/**
 * MetricsTab Component
 *
 * OTEL/HEART metrics dashboard with sparkline visualizations.
 * Grafana-like metric visualization for observability.
 */
import React, { useMemo, useCallback } from "react";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { cn } from "../../../utils/cn";
import {
  SPARKLINE_COLORS,
  STATUS_TEXT_COLORS,
  getTrendTextColor,
  getSparklineColor,
} from "../utils/devToolsColors";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type MetricTrend = "up" | "down" | "stable";

export interface MetricData {
  name: string;
  value: number;
  unit: string;
  trend: MetricTrend;
  change: number;
  sparkline: number[];
  timestamp?: number;
}

export interface HeartDimension {
  score: number;
  trend: MetricTrend;
  change: number;
}

export interface HeartMetrics {
  happiness: HeartDimension;
  engagement: HeartDimension;
  adoption: HeartDimension;
  retention: HeartDimension;
  taskSuccess: HeartDimension;
}

export type TimeRangeOption = "15m" | "1h" | "24h" | "7d";

export interface MetricsTabProps {
  metrics?: MetricData[];
  heartMetrics?: HeartMetrics;
  timeRange?: TimeRangeOption;
  autoRefreshInterval?: number;
  isLoading?: boolean;
  error?: string;
  grafanaUrl?: string;
  onTimeRangeChange?: (range: TimeRangeOption) => void;
  onRefresh?: () => void;
  className?: string;
}

// =============================================================================
// Utility Components
// =============================================================================

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

function Sparkline({
  data,
  width = 80,
  height = 24,
  color = SPARKLINE_COLORS.primary,
  className,
}: SparklineProps): React.ReactElement {
  const path = useMemo(() => {
    if (data.length === 0) return "";

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((value, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x},${y}`;
    });

    return `M ${points.join(" L ")}`;
  }, [data, width, height]);

  return (
    <svg
      data-testid="metric-sparkline"
      width={width}
      height={height}
      className={className}
      viewBox={`0 0 ${width} ${height}`}
    >
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

interface TrendIndicatorProps {
  trend: MetricTrend;
  change: number;
  className?: string;
}

function TrendIndicator({
  trend,
  change,
  className,
}: TrendIndicatorProps): React.ReactElement {
  const icon = {
    up: "\u2191", // ↑
    down: "\u2193", // ↓
    stable: "\u2192", // →
  }[trend];

  // Use semantic colors from design system
  const color = getTrendTextColor(trend);

  return (
    <span
      data-testid="trend-indicator"
      className={cn(
        "flex items-center gap-1 text-xs font-medium",
        color,
        className,
      )}
    >
      <span>{icon}</span>
      <span>
        {change > 0 ? "+" : ""}
        {change.toFixed(1)}%
      </span>
    </span>
  );
}

interface MetricCardProps {
  metric: MetricData;
}

function MetricCard({ metric }: MetricCardProps): React.ReactElement {
  const displayName = metric.name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());

  // Defensive coding: handle undefined/null values from runtime data
  // TypeScript says value: number, but runtime data may be incomplete
  const formattedValue =
    metric.value == null
      ? "N/A"
      : metric.value >= 1000
        ? metric.value.toLocaleString()
        : metric.value.toString();

  return (
    <div
      data-metric={metric.name}
      className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-neutral-500 dark:text-neutral-400">
            {displayName}
          </div>
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-2xl font-semibold text-neutral-900 dark:text-white">
              {formattedValue}
            </span>
            {metric.unit !== "%" ? (
              <span className="text-sm text-neutral-500 dark:text-neutral-400">
                {metric.unit}
              </span>
            ) : (
              <span className="text-2xl font-semibold text-neutral-900 dark:text-white">
                %
              </span>
            )}
          </div>
        </div>
        <Sparkline
          data={metric.sparkline}
          color={getSparklineColor(metric.trend)}
        />
      </div>
      <div className="mt-2">
        <TrendIndicator trend={metric.trend} change={metric.change} />
      </div>
    </div>
  );
}

interface HeartDimensionCardProps {
  name: string;
  dimension: HeartDimension;
}

function HeartDimensionCard({
  name,
  dimension,
}: HeartDimensionCardProps): React.ReactElement {
  const displayName = name.replace(/([A-Z])/g, " $1").trim();

  return (
    <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-3 text-center">
      <div className="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
        {displayName}
      </div>
      <div className="mt-1 text-xl font-bold text-neutral-900 dark:text-white">
        {dimension.score}
        {name === "taskSuccess" && "%"}
      </div>
      <div className="mt-1 flex justify-center">
        <TrendIndicator trend={dimension.trend} change={dimension.change} />
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

const TIME_RANGES: TimeRangeOption[] = ["15m", "1h", "24h", "7d"];

export function MetricsTab({
  metrics = [],
  heartMetrics,
  timeRange = "15m",
  autoRefreshInterval,
  isLoading = false,
  error,
  grafanaUrl,
  onTimeRangeChange,
  onRefresh,
  className,
}: MetricsTabProps): React.ReactElement {
  const timeline = useTimelineContext();

  // Filter metrics by time window from timeline context
  const filteredMetrics = useMemo(() => {
    if (!timeline?.timeWindow) return metrics;

    return metrics.filter((metric) => {
      if (!metric.timestamp) return true;
      return (
        metric.timestamp >= timeline.timeWindow!.start &&
        metric.timestamp <= timeline.timeWindow!.end
      );
    });
  }, [metrics, timeline?.timeWindow]);

  const handleTimeRangeChange = useCallback(
    (range: TimeRangeOption) => {
      onTimeRangeChange?.(range);
    },
    [onTimeRangeChange],
  );

  const handleRefresh = useCallback(() => {
    onRefresh?.();
  }, [onRefresh]);

  const handleOpenGrafana = useCallback(() => {
    if (grafanaUrl) {
      window.open(grafanaUrl, "_blank");
    }
  }, [grafanaUrl]);

  const handleRetry = useCallback(() => {
    onRefresh?.();
  }, [onRefresh]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="metrics-tab"
        className={cn("flex flex-col h-full", className)}
      >
        <div data-testid="metrics-loading" className="p-4 space-y-4">
          {/* Header skeleton */}
          <div className="flex items-center justify-between">
            <div className="h-6 w-32 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse" />
            <div className="flex gap-2">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-8 w-12 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse"
                />
              ))}
            </div>
          </div>
          {/* Cards skeleton */}
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="h-24 bg-neutral-200 dark:bg-neutral-700 rounded-lg animate-pulse"
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="metrics-tab"
        className={cn(
          "flex flex-col items-center justify-center h-full p-8 text-center",
          className,
        )}
      >
        <div className={cn(STATUS_TEXT_COLORS.error, "mb-4")}>
          <svg
            className="w-12 h-12 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <p className={cn(STATUS_TEXT_COLORS.error, "mb-4")}>{error}</p>
        <Button
          variant="primary"
          className="px-4 py-2 bg-primary-500 text-white rounded-md hover:bg-primary-600"
          onClick={handleRetry}
          aria-label="Retry"
        >
          Retry
        </Button>
      </div>
    );
  }

  const hasMetrics = filteredMetrics.length > 0;
  const hasHeartMetrics = heartMetrics !== undefined;

  return (
    <div
      data-testid="metrics-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-3">
          {/* Time range selector */}
          <div className="flex gap-1">
            {TIME_RANGES.map((range) => (
              <Button
                key={range}
                onClick={() => handleTimeRangeChange(range)}
                data-active={timeRange === range}
                className={cn(
                  "px-3 py-1 text-sm rounded-md transition-colors",
                  timeRange === range
                    ? "bg-primary-500 text-white"
                    : "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700",
                )}
                aria-label={range}
              >
                {range}
              </Button>
            ))}
          </div>

          {/* Auto-refresh indicator */}
          {autoRefreshInterval && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              Auto-refresh: {Math.round(autoRefreshInterval / 1000)}s
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Grafana button */}
          {grafanaUrl && (
            <Button
              className="px-3 py-1.5 text-sm bg-grafana-500 text-white rounded-md hover:bg-grafana-600 flex"
              onClick={handleOpenGrafana}
              aria-label="View in Grafana"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
              View in Grafana
            </Button>
          )}

          {/* Refresh button */}
          <Button
            variant="secondary"
            className="p-1.5 rounded-md hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800"
            onClick={handleRefresh}
            aria-label="Refresh"
          >
            <svg
              className="w-4 h-4 text-neutral-600 dark:text-neutral-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </Button>
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {!hasMetrics && !hasHeartMetrics ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg
              className="w-12 h-12 text-neutral-400 dark:text-neutral-400 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <p className="text-neutral-500 dark:text-neutral-400">
              No metrics available
            </p>
            <p className="text-sm text-neutral-400 dark:text-neutral-400 mt-1">
              Metrics will appear when data is collected
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* System Metrics */}
            {hasMetrics && (
              <div>
                <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
                  System Metrics
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredMetrics.map((metric) => (
                    <MetricCard key={metric.name} metric={metric} />
                  ))}
                </div>
              </div>
            )}

            {/* HEART Metrics */}
            {hasHeartMetrics && (
              <div>
                <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
                  HEART Metrics
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  <HeartDimensionCard
                    name="happiness"
                    dimension={heartMetrics.happiness}
                  />
                  <HeartDimensionCard
                    name="engagement"
                    dimension={heartMetrics.engagement}
                  />
                  <HeartDimensionCard
                    name="adoption"
                    dimension={heartMetrics.adoption}
                  />
                  <HeartDimensionCard
                    name="retention"
                    dimension={heartMetrics.retention}
                  />
                  <HeartDimensionCard
                    name="taskSuccess"
                    dimension={heartMetrics.taskSuccess}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default MetricsTab;
