/**
 * MetricCard Component
 *
 * Enhanced metric display card with trend indicators for admin dashboards.
 * Supports color-coding based on value, trend direction, and multiple variants.
 */

import { ReactNode } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

export interface MetricCardProps {
  /** Label for the metric */
  label: string;
  /** Current value */
  value: number;
  /** Whether to show percentage symbol */
  showPercentage?: boolean;
  /** Trend change percentage (positive = improvement, negative = decline) */
  trend?: number;
  /** Card size variant */
  variant?: "compact" | "default" | "large";
  /** Optional icon to display */
  icon?: ReactNode;
  /** Optional description text */
  description?: string;
}

/**
 * Get color class based on value (for percentage metrics)
 */
function getValueColor(value: number): string {
  if (value >= 80) return "text-green-600";
  if (value >= 60) return "text-yellow-600";
  return "text-red-600";
}

/**
 * Get padding class based on variant
 */
function getVariantPadding(variant: MetricCardProps["variant"]): string {
  switch (variant) {
    case "compact":
      return "p-3";
    case "large":
      return "p-6";
    default:
      return "p-4";
  }
}

/**
 * MetricCard component for displaying individual metrics with optional trends.
 *
 * @example
 * ```tsx
 * // Basic usage
 * <MetricCard label="Happiness" value={85} />
 *
 * // With trend
 * <MetricCard label="Engagement" value={72} trend={12} />
 *
 * // Without percentage
 * <MetricCard label="Active Users" value={150} showPercentage={false} />
 *
 * // With icon and description
 * <MetricCard
 *   label="NPS Score"
 *   value={42}
 *   icon={<Users />}
 *   description="Last 30 days"
 * />
 * ```
 */
export function MetricCard({
  label,
  value,
  showPercentage = true,
  trend,
  variant = "default",
  icon,
  description,
}: MetricCardProps) {
  const showTrend = trend !== undefined && trend !== 0;
  const isPositiveTrend = trend !== undefined && trend > 0;

  return (
    <div
      data-testid="metric-card"
      className={`bg-gray-50 dark:bg-gray-700 rounded-lg ${getVariantPadding(variant)}`}
    >
      {/* Header with label and icon */}
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <span className="text-gray-500 dark:text-gray-400">{icon}</span>
        )}
        <span className="text-sm text-gray-600 dark:text-gray-300">
          {label}
        </span>
      </div>

      {/* Value and trend */}
      <div className="flex items-baseline gap-2">
        <span className={`text-lg font-semibold ${getValueColor(value)}`}>
          {value}
          {showPercentage && "%"}
        </span>

        {showTrend && (
          <span
            className={`flex items-center text-sm ${
              isPositiveTrend ? "text-green-500" : "text-red-500"
            }`}
          >
            {isPositiveTrend ? (
              <TrendingUp
                data-testid="trend-up"
                className="w-3 h-3 mr-0.5"
                aria-hidden="true"
              />
            ) : (
              <TrendingDown
                data-testid="trend-down"
                className="w-3 h-3 mr-0.5"
                aria-hidden="true"
              />
            )}
            {isPositiveTrend ? "+" : ""}
            {trend}%
          </span>
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {description}
        </p>
      )}
    </div>
  );
}

export default MetricCard;
