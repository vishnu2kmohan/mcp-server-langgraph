/**
 * CostPage
 *
 * Cost tracking dashboard page showing LLM usage costs
 * with summary metrics and breakdown by model.
 * Uses RTK Query for data fetching with automatic caching.
 * Supports real-time WebSocket updates for live cost tracking.
 */

import { useState, useEffect } from "react";
import {
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { Skeleton, SkeletonCard, ErrorState } from "../components/UI";
import {
  useGetCostSummaryQuery,
  useGetCostByModelQuery,
  useGetCostHistoryQuery,
} from "../api";
import { useCostTrackingWebSocket } from "../hooks/useCostTrackingWebSocket";

type Period = "day" | "week" | "month";

interface CostPageProps {
  /** Enable real-time WebSocket updates (default: true) */
  enableRealtime?: boolean;
  /** User ID for budget tracking */
  userId?: string;
  /** Current session ID for session cost tracking */
  sessionId?: string;
}

export function CostPage({
  enableRealtime = true,
  userId,
  sessionId,
}: CostPageProps = {}) {
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

  // Real-time WebSocket for cost tracking
  const {
    status: wsStatus,
    sessionCosts,
    userBudget,
    budgetWarnings,
    error: _wsError,
    subscribeSession,
    subscribeUser,
    clearBudgetWarnings,
  } = useCostTrackingWebSocket(
    enableRealtime
      ? {
          onBudgetWarning: (warning) => {
            console.log("Budget warning received:", warning);
          },
        }
      : undefined,
  );

  // Subscribe to session and user when connected
  useEffect(() => {
    if (enableRealtime && wsStatus === "connected") {
      if (sessionId) {
        subscribeSession(sessionId);
      }
      if (userId) {
        subscribeUser(userId);
      }
    }
  }, [
    enableRealtime,
    wsStatus,
    sessionId,
    userId,
    subscribeSession,
    subscribeUser,
  ]);

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

  // Convert session costs to array for display
  const liveSessionCostsList = Object.values(sessionCosts);

  // Get WebSocket status display text and color
  const getWsStatusDisplay = () => {
    switch (wsStatus) {
      case "connected":
        return { text: "Live", color: "text-green-500", Icon: Wifi };
      case "connecting":
        return { text: "Connecting...", color: "text-yellow-500", Icon: Wifi };
      case "reconnecting":
        return {
          text: "Reconnecting...",
          color: "text-yellow-500",
          Icon: Wifi,
        };
      case "disconnected":
        return { text: "Offline", color: "text-gray-500", Icon: WifiOff };
      case "error":
        return { text: "Error", color: "text-red-500", Icon: WifiOff };
      default:
        return { text: "Unknown", color: "text-gray-500", Icon: WifiOff };
    }
  };

  const wsStatusDisplay = enableRealtime ? getWsStatusDisplay() : null;

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
            {/* WebSocket Status Indicator */}
            {enableRealtime && wsStatusDisplay && (
              <div
                data-testid="ws-status-indicator"
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
                  wsStatus === "connected"
                    ? "bg-green-100 dark:bg-green-900/30"
                    : wsStatus === "error"
                      ? "bg-red-100 dark:bg-red-900/30"
                      : "bg-yellow-100 dark:bg-yellow-900/30"
                }`}
              >
                <wsStatusDisplay.Icon
                  size={14}
                  className={wsStatusDisplay.color}
                />
                <span className={wsStatusDisplay.color}>
                  {wsStatusDisplay.text}
                </span>
              </div>
            )}
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

      {/* Budget Warnings */}
      {enableRealtime && budgetWarnings.length > 0 && (
        <div
          data-testid="budget-warning-banner"
          className="mx-6 mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className="text-amber-500 flex-shrink-0 mt-0.5"
            />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Budget Warning
              </h3>
              <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                {budgetWarnings[budgetWarnings.length - 1].message}
              </p>
            </div>
            <button
              onClick={clearBudgetWarnings}
              className="text-amber-500 hover:text-amber-700 dark:hover:text-amber-300"
              aria-label="Dismiss warning"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

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

            {/* User Budget Progress */}
            {enableRealtime && userBudget && (
              <div
                data-testid="budget-progress-bar"
                className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Budget Usage
                  </h3>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {formatCurrency(userBudget.remaining)} remaining
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      userBudget.current_usage / userBudget.budget_limit > 0.9
                        ? "bg-red-500"
                        : userBudget.current_usage / userBudget.budget_limit >
                            0.75
                          ? "bg-amber-500"
                          : "bg-green-500"
                    }`}
                    style={{
                      width: `${Math.min(100, (userBudget.current_usage / userBudget.budget_limit) * 100)}%`,
                    }}
                  />
                </div>
                <div className="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{formatCurrency(userBudget.current_usage)} used</span>
                  <span>{formatCurrency(userBudget.budget_limit)} limit</span>
                </div>
              </div>
            )}

            {/* Live Session Costs */}
            {enableRealtime && liveSessionCostsList.length > 0 && (
              <div
                data-testid="live-session-costs"
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    Live Session Costs
                  </h2>
                </div>
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {liveSessionCostsList.map((session) => (
                    <div
                      key={session.session_id}
                      className="px-6 py-4 flex items-center justify-between"
                    >
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {session.session_id.slice(0, 8)}...
                        </span>
                        {session.model && (
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                            {session.model}
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {formatCurrency(session.total_cost)}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {formatNumber(session.token_count)} tokens
                        </div>
                      </div>
                    </div>
                  ))}
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
