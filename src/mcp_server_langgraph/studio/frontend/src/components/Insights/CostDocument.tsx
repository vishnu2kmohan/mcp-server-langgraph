/**
 * CostDocument Component
 *
 * A cost dashboard document component for use within the MainDock.
 * Embeds the full CostPage functionality with cost analytics and usage metrics.
 *
 * Features:
 * - Full cost dashboard display
 * - Period selection (day/week/month)
 * - Model cost breakdown
 * - Cost trend visualization
 * - Compact mode for docked tabs
 */

import { useState } from "react";
import { DollarSign, TrendingUp } from "lucide-react";
import { Skeleton, SkeletonCard, ErrorState } from "../UI";
import {
  useGetCostSummaryQuery,
  useGetCostByModelQuery,
  useGetCostHistoryQuery,
} from "../../api";

import { Select } from "@/components/UI";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface CostDocumentProps {
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

type Period = "day" | "week" | "month";

// =============================================================================
// Component
// =============================================================================

export function CostDocument({
  compact = false,
  className,
}: CostDocumentProps) {
  const [period, setPeriod] = useState<Period>("week");

  // RTK Query hooks for cost data
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    error: summaryErrorData,
    refetch: refetchSummary,
  } = useGetCostSummaryQuery({ period });

  const {
    data: modelCosts,
    isLoading: modelLoading,
    refetch: refetchModel,
  } = useGetCostByModelQuery({ period });

  const {
    data: historyData,
    isLoading: historyLoading,
    refetch: refetchHistory,
  } = useGetCostHistoryQuery({ period });

  const isLoading = summaryLoading || modelLoading || historyLoading;

  const formatCurrency = (amount: number): string => {
    return `$${amount.toFixed(2)}`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const handlePeriodChange = (newPeriod: Period) => {
    setPeriod(newPeriod);
  };

  const handleRetry = () => {
    refetchSummary();
    refetchModel();
    refetchHistory();
  };

  // Model costs is already an array from backend
  const modelCostsArray = modelCosts ?? [];

  // History data is already an array from backend
  const historyItems = historyData ?? [];

  return (
    <div
      data-testid="cost-document"
      className={cn(
        "flex flex-col h-full",
        "bg-neutral-1",
        compact && "text-sm",
        className,
      )}
    >
      {/* Header */}
      <header className="px-6 py-4 bg-neutral-1 border-b border-neutral-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-neutral-12">
              Cost Dashboard
            </h2>
            <p className="text-sm text-neutral-10">
              Track and analyze LLM usage costs
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Period Selector */}
            <Select
              className="px-3 py-2 text-neutral-12"
              value={period}
              onChange={(e) => handlePeriodChange(e.target.value as Period)}
            >
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </Select>
          </div>
        </div>
      </header>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="space-y-6">
            {/* Skeleton for Cost Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
            {/* Skeleton for Model Breakdown */}
            <div className="bg-neutral-1 rounded-lg border border-neutral-5 p-6">
              <Skeleton className="h-6 w-1/4 mb-4" />
              <div className="space-y-3">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-3/4" />
              </div>
            </div>
          </div>
        ) : summaryError ? (
          <ErrorState
            title="Failed to load cost data"
            message={
              (summaryErrorData as { message?: string })?.message ||
              "Unable to fetch cost information. Please try again."
            }
            onRetry={handleRetry}
          />
        ) : (
          <div className="space-y-6">
            {/* Cost Summary Cards */}
            {summary && (
              <div className="grid gap-4 md:grid-cols-3">
                {/* Total Cost */}
                <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-primary-9" />
                    <h3 className="text-sm font-medium text-neutral-10">
                      Total Cost
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-neutral-12">
                      {formatCurrency(summary.totalCost)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-neutral-10">
                    Past {period}
                  </div>
                </div>

                {/* Total Tokens */}
                <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp size={20} className="text-success-9" />
                    <h3 className="text-sm font-medium text-neutral-10">
                      Total Tokens
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-neutral-12">
                      {formatNumber(summary.totalTokens ?? 0)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-neutral-10">
                    Past {period}
                  </div>
                </div>

                {/* Average Cost per Token */}
                <div className="p-6 bg-neutral-1 rounded-lg border border-neutral-5">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-insight-9" />
                    <h3 className="text-sm font-medium text-neutral-10">
                      Avg Cost/Token
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-neutral-12">
                      {summary.totalTokens && summary.totalTokens > 0
                        ? formatCurrency(
                            (summary.totalCost / summary.totalTokens) * 1000,
                          )
                        : "$0.00"}
                    </span>
                    <span className="text-sm text-neutral-10">
                      /1K
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-neutral-10">
                    Past {period}
                  </div>
                </div>
              </div>
            )}

            {/* Cost by Model */}
            <div className="bg-neutral-1 rounded-lg border border-neutral-5">
              <div className="px-6 py-4 border-b border-neutral-5">
                <h3 className="text-lg font-semibold text-neutral-12">
                  Cost by Model
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-1">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Model
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Requests
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-10 uppercase tracking-wider">
                        Avg Cost/Req
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-5 dark:divide-neutral-6">
                    {modelCostsArray.length === 0 ? (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-6 py-8 text-center text-neutral-10"
                        >
                          No model cost data for this period
                        </td>
                      </tr>
                    ) : (
                      modelCostsArray.map((modelCost) => (
                        <tr
                          key={modelCost.model}
                          className="hover:bg-neutral-a6"
                        >
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-neutral-12">
                            {modelCost.model}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-12">
                            {formatCurrency(modelCost.cost)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                            {formatNumber(modelCost.requests)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-10">
                            {modelCost.requests > 0
                              ? formatCurrency(
                                  modelCost.cost / modelCost.requests,
                                )
                              : "$0.00"}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Cost History Chart */}
            <div className="bg-neutral-1 rounded-lg border border-neutral-5">
              <div className="px-6 py-4 border-b border-neutral-5">
                <h3 className="text-lg font-semibold text-neutral-12">
                  Cost Trend
                </h3>
              </div>
              <div className="p-6">
                {historyItems.length === 0 ? (
                  <div className="text-center py-8 text-neutral-10">
                    No cost data for this period
                  </div>
                ) : (
                  <div data-testid="cost-history-chart" className="space-y-4">
                    {/* Simple bar chart implementation */}
                    <div className="h-48 flex items-end gap-2">
                      {historyItems.map((point, index) => {
                        const maxCost = Math.max(
                          ...historyItems.map((p) => p.cost),
                        );
                        const heightPercent =
                          maxCost > 0 ? (point.cost / maxCost) * 100 : 0;
                        return (
                          <div
                            key={index}
                            className="flex-1 flex flex-col items-center gap-1"
                          >
                            <div
                              data-cost-bar
                              className="w-full bg-primary-9 rounded-t transition-all hover:bg-primary-10"
                              style={{
                                height: `${heightPercent}%`,
                                minHeight: "4px",
                              }}
                              title={`${formatDate(point.date)}: ${formatCurrency(point.cost)}`}
                            />
                          </div>
                        );
                      })}
                    </div>
                    {/* Date labels */}
                    <div className="flex gap-2">
                      {historyItems.map((point, index) => (
                        <div
                          key={index}
                          className="flex-1 text-center text-xs text-neutral-10"
                        >
                          {formatDate(point.date)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CostDocument;
