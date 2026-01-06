/**
 * CostPage
 *
 * Cost tracking dashboard page showing LLM usage costs
 * with summary metrics and breakdown by model.
 * Uses RTK Query for data fetching with automatic caching.
 * Supports real-time WebSocket updates for live cost tracking.
 */

import { useState, useEffect, useMemo, Suspense } from "react";
import {
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Wifi,
  WifiOff,
  X,
  Building2,
  Calendar,
} from "lucide-react";
import { Skeleton, SkeletonCard, ErrorState } from "../components/UI";
import {
  LazyOrganizationCostDashboard,
  LazyBudgetStatusCard,
  LazyBudgetForecastChart,
} from "../components/Cost";
import type { BudgetStatus, CostForecast } from "../components/Cost";
import {
  useGetCostSummaryQuery,
  useGetCostByModelQuery,
  useGetCostHistoryQuery,
  useGetBudgetStatusQuery,
  useGetCostForecastQuery,
} from "../api";
import { useCostTrackingWebSocket } from "../hooks/useCostTrackingWebSocket";
import {
  useBudgetAlertsWebSocket,
  type BudgetAlert,
} from "../hooks/useBudgetAlertsWebSocket";
import { usePersonaContext } from "../persona/PersonaContext";

type Period = "day" | "week" | "month";

interface CostPageProps {
  /** Enable real-time WebSocket updates (default: true) */
  enableRealtime?: boolean;
  /** User ID for budget tracking */
  userId?: string;
  /** Current session ID for session cost tracking */
  sessionId?: string;
}

type DashboardView = "personal" | "organizational";

// Helper function to get date range for preset periods
function getDateRangeForPeriod(period: Period): { start: string; end: string } {
  const end = new Date();
  const start = new Date();

  switch (period) {
    case "day":
      start.setDate(start.getDate() - 1);
      break;
    case "week":
      start.setDate(start.getDate() - 7);
      break;
    case "month":
      start.setMonth(start.getMonth() - 1);
      break;
  }

  return {
    start: start.toISOString().split("T")[0],
    end: end.toISOString().split("T")[0],
  };
}

export function CostPage({
  enableRealtime = true,
  userId,
  sessionId,
}: CostPageProps = {}) {
  const [period, setPeriod] = useState<Period>("week");
  const [dashboardView, setDashboardView] = useState<DashboardView>("personal");
  const [useCustomDateRange, setUseCustomDateRange] = useState(false);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // Calculate effective date range based on period or custom range
  const effectiveDateRange = useMemo(() => {
    if (useCustomDateRange && startDate && endDate) {
      return { start: startDate, end: endDate };
    }
    return getDateRangeForPeriod(period);
  }, [useCustomDateRange, startDate, endDate, period]);

  // Get persona context to determine if user is admin
  const { isAdmin } = usePersonaContext();

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

  // Budget status and forecast hooks (skip if no userId)
  const { data: budgetStatusData, isLoading: budgetStatusLoading } =
    useGetBudgetStatusQuery(
      { entity_type: "user", entity_id: userId ?? "" },
      { skip: !userId },
    );

  const { data: forecastData, isLoading: forecastLoading } =
    useGetCostForecastQuery(
      { entity_type: "user", entity_id: userId ?? "" },
      { skip: !userId },
    );

  // Transform API response to component props format
  // API now returns camelCase (after transformSnakeToCamel in RTK Query)
  const budgetStatus: BudgetStatus | null = budgetStatusData
    ? {
        entityType: budgetStatusData.entityType,
        entityId: budgetStatusData.entityId,
        status: budgetStatusData.status,
        percentUsed: budgetStatusData.percentUsed,
        currentSpend: budgetStatusData.currentSpend.toString(),
        remaining: budgetStatusData.remaining.toString(),
        monthlyLimitUsd: budgetStatusData.monthlyLimit.toString(),
        message: budgetStatusData.message,
      }
    : null;

  // API now returns camelCase (after transformSnakeToCamel in RTK Query)
  const costForecast: CostForecast | null = forecastData
    ? {
        projectedTotal: forecastData.projectedTotal.toString(),
        confidenceLow: forecastData.confidenceLow.toString(),
        confidenceHigh: forecastData.confidenceHigh.toString(),
        trend: forecastData.trend,
        daysAnalyzed: forecastData.daysAnalyzed,
        message: forecastData.message,
        monthlyLimit: forecastData.monthlyLimit.toString(),
      }
    : null;

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

  // Dedicated Budget Alerts WebSocket for comprehensive budget monitoring
  // This provides more detailed budget threshold alerts beyond session-level cost tracking
  const {
    alerts: budgetAlerts,
    subscribeToAll: _subscribeToBudgetAlerts,
    clearAlerts: clearBudgetAlerts,
  } = useBudgetAlertsWebSocket({
    enabled: enableRealtime,
    subscribeAll: isAdmin, // Admins subscribe to all org/project budget alerts
    onAlert: (alert: BudgetAlert) => {
      // Log budget alerts for monitoring
      console.log("Budget alert received:", alert.status, alert.message);
    },
  });

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
            {/* Date Range Controls */}
            <div className="flex items-center gap-2">
              {/* Period Selector (preset ranges) */}
              {!useCustomDateRange && (
                <select
                  value={period}
                  onChange={(e) => handlePeriodChange(e.target.value as Period)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="day">Day</option>
                  <option value="week">Week</option>
                  <option value="month">Month</option>
                </select>
              )}

              {/* Custom Date Range Inputs */}
              {useCustomDateRange && (
                <div className="flex items-center gap-2">
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    aria-label="Start date"
                  />
                  <span className="text-gray-500">to</span>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    aria-label="End date"
                  />
                </div>
              )}

              {/* Toggle Custom Date Range */}
              <button
                onClick={() => {
                  setUseCustomDateRange(!useCustomDateRange);
                  if (!useCustomDateRange) {
                    // Initialize with current period's range
                    const range = getDateRangeForPeriod(period);
                    setStartDate(range.start);
                    setEndDate(range.end);
                  }
                }}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  useCustomDateRange
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                    : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 border border-gray-300 dark:border-gray-600"
                }`}
                aria-label={
                  useCustomDateRange
                    ? "Use preset periods"
                    : "Use custom date range"
                }
              >
                <Calendar size={16} />
                {useCustomDateRange ? "Preset" : "Custom"}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Admin View Toggle */}
      {isAdmin && (
        <div className="px-6 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDashboardView("personal")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                dashboardView === "personal"
                  ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              <DollarSign size={16} />
              Personal Costs
            </button>
            <button
              onClick={() => setDashboardView("organizational")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                dashboardView === "organizational"
                  ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              <Building2 size={16} />
              Organizational View
            </button>
          </div>
        </div>
      )}

      {/* Budget Warnings (from Cost Tracking WebSocket) */}
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

      {/* Budget Alerts (from dedicated Budget Alerts WebSocket) */}
      {enableRealtime && budgetAlerts.length > 0 && (
        <div
          data-testid="budget-alerts-banner"
          className={`mx-6 mt-4 p-4 rounded-lg border ${
            budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
              ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
              : budgetAlerts[budgetAlerts.length - 1].status === "critical"
                ? "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800"
                : "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
          }`}
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className={`flex-shrink-0 mt-0.5 ${
                budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                  ? "text-red-500"
                  : budgetAlerts[budgetAlerts.length - 1].status === "critical"
                    ? "text-orange-500"
                    : "text-amber-500"
              }`}
            />
            <div className="flex-1">
              <h3
                className={`text-sm font-medium ${
                  budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                    ? "text-red-800 dark:text-red-200"
                    : budgetAlerts[budgetAlerts.length - 1].status ===
                        "critical"
                      ? "text-orange-800 dark:text-orange-200"
                      : "text-amber-800 dark:text-amber-200"
                }`}
              >
                Budget Alert (
                {budgetAlerts[budgetAlerts.length - 1].status.toUpperCase()})
              </h3>
              <p
                className={`text-sm mt-1 ${
                  budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                    ? "text-red-700 dark:text-red-300"
                    : budgetAlerts[budgetAlerts.length - 1].status ===
                        "critical"
                      ? "text-orange-700 dark:text-orange-300"
                      : "text-amber-700 dark:text-amber-300"
                }`}
              >
                {budgetAlerts[budgetAlerts.length - 1].message}
              </p>
              <p
                className={`text-xs mt-1 ${
                  budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                    ? "text-red-600 dark:text-red-400"
                    : budgetAlerts[budgetAlerts.length - 1].status ===
                        "critical"
                      ? "text-orange-600 dark:text-orange-400"
                      : "text-amber-600 dark:text-amber-400"
                }`}
              >
                {budgetAlerts[budgetAlerts.length - 1].entityType}:{" "}
                {budgetAlerts[budgetAlerts.length - 1].percentUsed}% used
              </p>
            </div>
            <button
              onClick={clearBudgetAlerts}
              className={`${
                budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                  ? "text-red-500 hover:text-red-700 dark:hover:text-red-300"
                  : budgetAlerts[budgetAlerts.length - 1].status === "critical"
                    ? "text-orange-500 hover:text-orange-700 dark:hover:text-orange-300"
                    : "text-amber-500 hover:text-amber-700 dark:hover:text-amber-300"
              }`}
              aria-label="Dismiss alert"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* User Budget Progress Bar (from Cost Tracking WebSocket) */}
      {enableRealtime && userBudget && (
        <div
          data-testid="budget-progress-bar"
          className="mx-6 mt-4 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Your Budget
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ${userBudget.remaining.toFixed(2)} remaining
            </span>
          </div>
          <div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`absolute left-0 top-0 h-full rounded-full transition-all ${
                (userBudget.currentUsage / userBudget.budgetLimit) * 100 >= 90
                  ? "bg-red-500"
                  : (userBudget.currentUsage / userBudget.budgetLimit) * 100 >=
                      75
                    ? "bg-amber-500"
                    : "bg-blue-500"
              }`}
              style={{
                width: `${Math.min(100, (userBudget.currentUsage / userBudget.budgetLimit) * 100)}%`,
              }}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
            <span>${userBudget.currentUsage.toFixed(2)} used</span>
            <span>${userBudget.budgetLimit.toFixed(2)} limit</span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Organizational View for Admins */}
        {isAdmin && dashboardView === "organizational" ? (
          <div className="space-y-6">
            {/* Budget Status in Org View */}
            {userId && (
              <Suspense
                fallback={
                  <div
                    data-testid="budget-status-skeleton"
                    className="p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <Skeleton className="w-5 h-5 rounded" />
                      <Skeleton className="w-24 h-4" />
                    </div>
                    <Skeleton className="w-full h-2 mb-2" />
                    <div className="flex justify-between">
                      <Skeleton className="w-16 h-4" />
                      <Skeleton className="w-16 h-4" />
                    </div>
                  </div>
                }
              >
                <LazyBudgetStatusCard
                  status={budgetStatus}
                  loading={budgetStatusLoading}
                />
              </Suspense>
            )}
            <Suspense
              fallback={
                <div className="space-y-4">
                  <SkeletonCard />
                  <SkeletonCard />
                  <SkeletonCard />
                </div>
              }
            >
              <LazyOrganizationCostDashboard
                startDate={effectiveDateRange.start}
                endDate={effectiveDateRange.end}
              />
            </Suspense>
          </div>
        ) : isLoading ? (
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
                      {formatCurrency(summary.totalCost)}
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
                      {formatNumber(summary.totalTokens ?? 0)}
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
                      {summary.totalTokens && summary.totalTokens > 0
                        ? formatCurrency(
                            (summary.totalCost / summary.totalTokens) * 1000,
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

            {/* Budget Status Card (replaces old User Budget Progress) */}
            {userId && (
              <Suspense
                fallback={
                  <div
                    data-testid="budget-status-skeleton"
                    className="p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <Skeleton className="w-5 h-5 rounded" />
                      <Skeleton className="w-24 h-4" />
                    </div>
                    <Skeleton className="w-full h-2 mb-2" />
                    <div className="flex justify-between">
                      <Skeleton className="w-16 h-4" />
                      <Skeleton className="w-16 h-4" />
                    </div>
                  </div>
                }
              >
                <LazyBudgetStatusCard
                  status={budgetStatus}
                  loading={budgetStatusLoading}
                />
              </Suspense>
            )}

            {/* Budget Forecast Chart (below budget status) */}
            {userId && (
              <Suspense
                fallback={
                  <div
                    data-testid="budget-forecast-skeleton"
                    className="p-6 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="space-y-4">
                      <Skeleton className="w-32 h-6" />
                      <Skeleton className="w-full h-4" />
                      <div className="flex justify-between">
                        <Skeleton className="w-20 h-8" />
                        <Skeleton className="w-20 h-8" />
                        <Skeleton className="w-20 h-8" />
                      </div>
                      <Skeleton className="w-full h-8" />
                    </div>
                  </div>
                }
              >
                <LazyBudgetForecastChart
                  forecast={costForecast}
                  loading={forecastLoading}
                />
              </Suspense>
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
                      key={session.sessionId}
                      className="px-6 py-4 flex items-center justify-between"
                    >
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {session.sessionId.slice(0, 8)}...
                        </span>
                        {session.model && (
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                            {session.model}
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                          {formatCurrency(session.totalCost)}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {formatNumber(session.tokenCount)} tokens
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
