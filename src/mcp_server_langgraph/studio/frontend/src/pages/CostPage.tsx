/**
 * CostPage
 *
 * Cost tracking dashboard page showing LLM usage costs
 * with summary metrics and breakdown by model.
 * Uses RTK Query for data fetching with automatic caching.
 */

import { useState } from "react";
import { DollarSign, TrendingUp } from "lucide-react";
import { Skeleton, SkeletonCard, ErrorState } from "../components/UI";
import {
  useGetCostSummaryQuery,
  useGetCostByModelQuery,
  useGetCostHistoryQuery,
} from "../api";

type Period = "day" | "week" | "month";

export function CostPage() {
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
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Cost Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Track and analyze LLM usage costs
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Period Selector */}
            <select
              value={period}
              onChange={(e) => handlePeriodChange(e.target.value as Period)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </select>
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
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
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
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-blue-500" />
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Total Cost
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                      {formatCurrency(summary.total_cost)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Past {period}
                  </div>
                </div>

                {/* Total Tokens */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp size={20} className="text-green-500" />
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Total Tokens
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                      {formatNumber(summary.total_tokens ?? 0)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Past {period}
                  </div>
                </div>

                {/* Average Cost per Token */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-purple-500" />
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Avg Cost/Token
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                      {summary.total_tokens && summary.total_tokens > 0
                        ? formatCurrency(
                            (summary.total_cost / summary.total_tokens) * 1000,
                          )
                        : "$0.00"}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      /1K
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Past {period}
                  </div>
                </div>
              </div>
            )}

            {/* Cost by Model */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Cost by Model
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Model
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Requests
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Avg Cost/Req
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {modelCostsArray.map((modelCost) => (
                      <tr
                        key={modelCost.model}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          {modelCost.model}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-gray-100">
                          {formatCurrency(modelCost.cost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-400">
                          {formatNumber(modelCost.requests)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-400">
                          {modelCost.requests > 0
                            ? formatCurrency(
                                modelCost.cost / modelCost.requests,
                              )
                            : "$0.00"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Cost History Chart */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Cost Trend
                </h2>
              </div>
              <div className="p-6">
                {historyItems.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
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
                              className="w-full bg-blue-500 rounded-t transition-all hover:bg-blue-600"
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
                          className="flex-1 text-center text-xs text-gray-500 dark:text-gray-400"
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

export default CostPage;
