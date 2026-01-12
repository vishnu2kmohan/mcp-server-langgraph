/**
 * AIQualityMetricsCard Component
 *
 * Displays AI quality metrics including hallucination reports and category
 * breakdowns for the admin dashboard. Uses the feedback summary API endpoint.
 */

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Flag,
  TrendingUp,
  Grid3X3,
  PieChart as PieChartIcon,
} from "lucide-react";
import { PieChart, Pie, Cell, Legend, ResponsiveContainer } from "recharts";
import { useGetFeedbackSummaryQuery } from "../../api";
import { Skeleton } from "../UI/Skeleton";
import { Button } from "../UI/Button";

export interface AIQualityMetricsCardProps {
  /** Time period for metrics (default: "7d") */
  timeframe?: string;
  /** Compact display mode (hides category breakdown) */
  compact?: boolean;
  /** Visualization mode for category breakdown (default: "grid") */
  visualization?: "grid" | "pie";
  /** Show toggle button to switch between grid and pie views */
  showToggle?: boolean;
}

/**
 * Category display configuration
 */
const CATEGORY_CONFIG = {
  factualError: {
    label: "Factual Error",
    color: "text-error-600 dark:text-error-400",
    bgColor: "bg-error-100 dark:bg-error-900",
    pieColor: "#dc2626", // error-600
  },
  outdatedInfo: {
    label: "Outdated Info",
    color: "text-warning-600 dark:text-warning-400",
    bgColor: "bg-warning-100 dark:bg-warning-900",
    pieColor: "#d97706", // warning-600
  },
  madeUpSource: {
    label: "Made Up Source",
    color: "text-error-600 dark:text-error-400",
    bgColor: "bg-error-100 dark:bg-error-900",
    pieColor: "#be123c", // rose-700
  },
  other: {
    label: "Other",
    color: "text-neutral-600 dark:text-neutral-400",
    bgColor: "bg-neutral-100 dark:bg-neutral-700",
    pieColor: "#737373", // neutral-500
  },
} as const;

/**
 * Loading skeleton for the card
 */
function LoadingSkeleton() {
  return (
    <div data-testid="ai-quality-loading" className="space-y-4">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-10 w-24" />
      <div className="grid grid-cols-2 gap-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}

/**
 * AIQualityMetricsCard displays hallucination report counts and category
 * breakdown for admin visibility into AI accuracy issues.
 *
 * @example
 * ```tsx
 * // Default usage
 * <AIQualityMetricsCard />
 *
 * // With custom timeframe
 * <AIQualityMetricsCard timeframe="30d" />
 *
 * // Compact mode for smaller spaces
 * <AIQualityMetricsCard compact />
 * ```
 */
export function AIQualityMetricsCard({
  timeframe = "7d",
  compact = false,
  visualization = "grid",
  showToggle = false,
}: AIQualityMetricsCardProps) {
  const [currentVisualization, setCurrentVisualization] = useState<
    "grid" | "pie"
  >(visualization);
  const { data, isLoading, isError } = useGetFeedbackSummaryQuery({
    timeframe,
  });

  const paddingClass = compact ? "p-3" : "p-6";

  const handleToggleVisualization = () => {
    setCurrentVisualization((prev) => (prev === "grid" ? "pie" : "grid"));
  };

  // Loading state
  if (isLoading) {
    return (
      <section
        data-testid="ai-quality-card"
        className={`bg-white dark:bg-neutral-800 rounded-lg shadow ${paddingClass}`}
        role="region"
        aria-label="AI quality metrics"
      >
        <LoadingSkeleton />
      </section>
    );
  }

  // Error state
  if (isError) {
    return (
      <section
        data-testid="ai-quality-card"
        className={`bg-white dark:bg-neutral-800 rounded-lg shadow ${paddingClass}`}
        role="region"
        aria-label="AI quality metrics"
      >
        <div className="flex items-center gap-2 text-error-600 dark:text-error-400">
          <AlertTriangle className="w-5 h-5" />
          <span>Failed to load AI quality metrics</span>
        </div>
      </section>
    );
  }

  const hallucinationReports = data?.hallucinationReports ?? 0;
  const positiveRate = data?.positiveRate ?? 0;
  const categories = data?.hallucinationCategories;
  const displayTimeframe = data?.timeframe ?? timeframe;
  const hasNoReports = hallucinationReports === 0;

  return (
    <section
      data-testid="ai-quality-card"
      className={`bg-white dark:bg-neutral-800 rounded-lg shadow ${paddingClass}`}
      role="region"
      aria-label="AI quality metrics"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
          <Flag className="w-5 h-5 text-primary-500" aria-hidden="true" />
          AI Quality
        </h2>
        <div className="flex items-center gap-2">
          {/* Toggle button - only show when not compact and has reports */}
          {showToggle && !compact && !hasNoReports && categories && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggleVisualization}
              className="p-1.5 text-neutral-500 dark:text-neutral-400"
              aria-label={
                currentVisualization === "grid"
                  ? "Switch to pie chart view"
                  : "Switch to grid view"
              }
            >
              {currentVisualization === "grid" ? (
                <PieChartIcon className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Grid3X3 className="w-4 h-4" aria-hidden="true" />
              )}
            </Button>
          )}
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {displayTimeframe}
          </span>
        </div>
      </div>

      {/* Main metrics row */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Hallucination reports */}
        <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-3">
          <div className="text-sm text-neutral-600 dark:text-neutral-300 mb-1">
            Hallucination Reports
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-neutral-900 dark:text-white">
              {hallucinationReports}
            </span>
            {hasNoReports && (
              <CheckCircle
                className="w-5 h-5 text-success-500"
                aria-hidden="true"
              />
            )}
          </div>
          {hasNoReports && (
            <div className="text-xs text-success-600 dark:text-success-400 mt-1">
              No reports in this period
            </div>
          )}
        </div>

        {/* Positive rate */}
        <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-3">
          <div className="text-sm text-neutral-600 dark:text-neutral-300 mb-1">
            Response Approval Rate
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold ${
                positiveRate >= 0.8
                  ? "text-success-600"
                  : positiveRate >= 0.6
                    ? "text-warning-600"
                    : "text-error-600"
              }`}
            >
              {Math.round(positiveRate * 100)}%
            </span>
            {positiveRate >= 0.8 && (
              <TrendingUp
                className="w-4 h-4 text-success-500"
                aria-hidden="true"
              />
            )}
          </div>
        </div>
      </div>

      {/* Category breakdown (hidden in compact mode) */}
      {!compact && categories && !hasNoReports && (
        <div className="border-t border-neutral-200 dark:border-neutral-600 pt-4">
          <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
            Reports by Category
          </h3>

          {/* Pie chart visualization */}
          {currentVisualization === "pie" && (
            <div
              data-testid="ai-quality-pie-chart"
              aria-label="Hallucination reports category breakdown"
              className="h-48"
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={Object.entries(CATEGORY_CONFIG).map(
                      ([key, config]) => ({
                        name: config.label,
                        value: categories[key as keyof typeof categories] ?? 0,
                        color: config.pieColor,
                      }),
                    )}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                  >
                    {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                      <Cell key={key} fill={config.pieColor} />
                    ))}
                  </Pie>
                  <Legend
                    layout="vertical"
                    align="right"
                    verticalAlign="middle"
                    formatter={(value: string) => (
                      <span className="text-sm text-neutral-700 dark:text-neutral-300">
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Grid visualization (default) */}
          {currentVisualization === "grid" && (
            <div className="grid grid-cols-2 gap-2">
              {(
                Object.entries(CATEGORY_CONFIG) as [
                  keyof typeof CATEGORY_CONFIG,
                  (typeof CATEGORY_CONFIG)[keyof typeof CATEGORY_CONFIG],
                ][]
              ).map(([key, config]) => {
                const count = categories[key as keyof typeof categories] ?? 0;
                return (
                  <div
                    key={key}
                    className={`flex items-center justify-between rounded-md px-3 py-2 ${config.bgColor}`}
                  >
                    <span className={`text-sm ${config.color}`}>
                      {config.label}
                    </span>
                    <span className={`text-sm font-semibold ${config.color}`}>
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default AIQualityMetricsCard;
