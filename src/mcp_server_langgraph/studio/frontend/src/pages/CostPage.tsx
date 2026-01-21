/**
 * CostPage
 *
 * Cost tracking dashboard page showing LLM usage costs
 * with summary metrics and breakdown by model.
 * Uses RTK Query for data fetching with automatic caching.
 * Supports real-time WebSocket updates for live cost tracking.
 */

import { useState, useEffect, useMemo, Suspense } from "react";
import { toast } from "sonner";
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
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Skeleton, SkeletonCard } from "../components/UI/Skeleton";
import { ErrorState } from "../components/UI/ErrorState";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Select } from "../components/UI/Select";
import {
  LazyOrganizationCostDashboard,
  LazyBudgetStatusCard,
  LazyBudgetForecastChart,
  LazyNativeToolComparison,
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

  // Build cost query params - use custom date range if enabled, otherwise use period
  const costQueryParams = useMemo(() => {
    if (useCustomDateRange && startDate && endDate) {
      return { startDate, endDate };
    }
    return { period };
  }, [useCustomDateRange, startDate, endDate, period]);

  // RTK Query hooks for cost data
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    error: summaryErrorData,
    refetch: refetchSummary,
  } = useGetCostSummaryQuery(costQueryParams);

  const {
    data: modelCosts,
    isLoading: modelLoading,
    refetch: refetchModel,
  } = useGetCostByModelQuery(costQueryParams);

  const {
    data: historyData,
    isLoading: historyLoading,
    refetch: refetchHistory,
  } = useGetCostHistoryQuery(costQueryParams);

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
    error: wsError,
    subscribeSession,
    unsubscribeSession,
    subscribeUser,
    unsubscribeUser,
    clearBudgetWarnings,
  } = useCostTrackingWebSocket(
    enableRealtime
      ? {
          onBudgetWarning: (warning) => {
            const percentUsed =
              warning.budgetLimit && warning.budgetLimit > 0
                ? Math.round((warning.currentUsage / warning.budgetLimit) * 100)
                : warning.threshold;
            toast.warning(`Budget Warning: ${warning.message}`, {
              description: `${percentUsed}% of budget used`,
              duration: 5000,
            });
          },
        }
      : undefined,
  );

  // Show toast when WebSocket error occurs
  useEffect(() => {
    if (wsError) {
      toast.error("Cost Tracking Connection Error", {
        description: wsError,
        duration: 5000,
      });
    }
  }, [wsError]);

  // Dedicated Budget Alerts WebSocket for comprehensive budget monitoring
  // This provides more detailed budget threshold alerts beyond session-level cost tracking
  const { alerts: budgetAlerts, clearAlerts: clearBudgetAlerts } =
    useBudgetAlertsWebSocket({
      enabled: enableRealtime,
      subscribeAll: isAdmin, // Admins subscribe to all org/project budget alerts
      onAlert: (alert: BudgetAlert) => {
        // Show toast notification based on alert severity
        const toastFn =
          alert.status === "exceeded" || alert.status === "critical"
            ? toast.error
            : toast.warning;
        toastFn(
          `Budget ${alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}: ${alert.message}`,
          {
            description: `${alert.entityType}: ${alert.percentUsed}% used`,
            duration: alert.status === "exceeded" ? 10000 : 5000,
          },
        );

        // Request browser notification permission and show notification
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Budget Alert", { body: alert.message });
        }
      },
    });

  // Subscribe to session and user when connected, with cleanup on prop changes
  useEffect(() => {
    if (!enableRealtime || wsStatus !== "connected") {
      return;
    }

    // Subscribe to current session and user
    if (sessionId) {
      subscribeSession(sessionId);
    }
    if (userId) {
      subscribeUser(userId);
    }

    // Cleanup: unsubscribe when props change or component unmounts
    return () => {
      if (sessionId) {
        unsubscribeSession(sessionId);
      }
      if (userId) {
        unsubscribeUser(userId);
      }
    };
  }, [
    enableRealtime,
    wsStatus,
    sessionId,
    userId,
    subscribeSession,
    unsubscribeSession,
    subscribeUser,
    unsubscribeUser,
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
        return { text: "Live", color: "text-success-9", Icon: Wifi };
      case "connecting":
        return { text: "Connecting...", color: "text-warning-9", Icon: Wifi };
      case "reconnecting":
        return {
          text: "Reconnecting...",
          color: "text-warning-9",
          Icon: Wifi,
        };
      case "disconnected":
        return {
          text: "Offline",
          color: "text-neutral-11",
          Icon: WifiOff,
        };
      case "error":
        return { text: "Error", color: "text-error-9", Icon: WifiOff };
      default:
        return {
          text: "Unknown",
          color: "text-neutral-11",
          Icon: WifiOff,
        };
    }
  };

  const wsStatusDisplay = enableRealtime ? getWsStatusDisplay() : null;

  return (
    <div className="h-screen flex flex-col bg-neutral-1">
      {/* Header */}
      <header className="px-6 py-4 bg-neutral-2 border-b border-neutral-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-12">
              Cost Dashboard
            </h1>
            <p className="text-sm text-neutral-11">
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
                    ? "bg-success-3 bg-success-4"
                    : wsStatus === "error"
                      ? "bg-error-3 bg-error-4"
                      : "bg-warning-3/30"
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
                <Select
                  className="px-3 py-2 text-neutral-12"
                  value={period}
                  onChange={(e) => handlePeriodChange(e.target.value as Period)}
                >
                  <option value="day">Day</option>
                  <option value="week">Week</option>
                  <option value="month">Month</option>
                </Select>
              )}

              {/* Custom Date Range Inputs */}
              {useCustomDateRange && (
                <div className="flex items-center gap-2">
                  <Input
                    className="px-3 py-2 text-neutral-12"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    aria-label="Start date"
                  />
                  <span className="text-neutral-11">
                    to
                  </span>
                  <Input
                    className="px-3 py-2 text-neutral-12"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    aria-label="End date"
                  />
                </div>
              )}

              {/* Toggle Custom Date Range */}
              <Button
                variant="ghost"
                className="flex .5 px-3 py-2 rounded-lg text-sm"
                onClick={() => {
                  setUseCustomDateRange(!useCustomDateRange);
                  if (!useCustomDateRange) {
                    // Initialize with current period's range
                    const range = getDateRangeForPeriod(period);
                    setStartDate(range.start);
                    setEndDate(range.end);
                  }
                }}
                aria-label={
                  useCustomDateRange
                    ? "Use preset periods"
                    : "Use custom date range"
                }>
                <Calendar size={16} />
                {useCustomDateRange ? "Preset" : "Custom"}
              </Button>
            </div>
          </div>
        </div>
      </header>
      {/* Admin View Toggle */}
      {isAdmin && (
        <div className="px-6 py-2 bg-neutral-2 border-b border-neutral-6">
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              className="flex px-4 py-2 rounded-lg text-sm"
              onClick={() => setDashboardView("personal")}>
              <DollarSign size={16} />
              Personal Costs
            </Button>
            <Button
              variant="primary"
              className="flex px-4 py-2 rounded-lg text-sm"
              onClick={() => setDashboardView("organizational")}>
              <Building2 size={16} />
              Organizational View
            </Button>
          </div>
        </div>
      )}
      {/* Budget Warnings (from Cost Tracking WebSocket) */}
      {enableRealtime && budgetWarnings.length > 0 && (
        <div
          data-testid="budget-warning-banner"
          className="mx-6 mt-4 p-4 bg-warning-3 border border-warning-6 rounded-lg"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className="text-warning-9 flex-shrink-0 mt-0.5"
            />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-warning-11">
                Budget Warning
              </h3>
              <p className="text-sm text-warning-10 mt-1">
                {budgetWarnings[budgetWarnings.length - 1].message}
              </p>
            </div>
            <Button
              variant="secondary"
              className="text-warning-9 hover:text-warning-10 dark:hover:text-warning-6"
              onClick={clearBudgetWarnings}
              aria-label="Dismiss warning">
              <X size={16} />
            </Button>
          </div>
        </div>
      )}
      {/* Budget Alerts (from dedicated Budget Alerts WebSocket) */}
      {enableRealtime && budgetAlerts.length > 0 && (
        <div
          data-testid="budget-alerts-banner"
          className={`mx-6 mt-4 p-4 rounded-lg border ${
            budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
              ? "bg-error-1/20 border-error-4"
              : budgetAlerts[budgetAlerts.length - 1].status === "critical"
                ? "bg-grafana-1 border-grafana-4"
                : "bg-warning-3 border-warning-6"
          }`}
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className={`flex-shrink-0 mt-0.5 ${
                budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                  ? "text-error-9"
                  : budgetAlerts[budgetAlerts.length - 1].status === "critical"
                    ? "text-grafana-9"
                    : "text-warning-9"
              }`}
            />
            <div className="flex-1">
              <h3
                className={`text-sm font-medium ${
                  budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                    ? "text-error-11"
                    : budgetAlerts[budgetAlerts.length - 1].status ===
                        "critical"
                      ? "text-grafana-11"
                      : "text-warning-11"
                }`}
              >
                Budget Alert (
                {budgetAlerts[budgetAlerts.length - 1].status.toUpperCase()})
              </h3>
              <p
                className={`text-sm mt-1 ${
                  budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                    ? "text-error-11"
                    : budgetAlerts[budgetAlerts.length - 1].status ===
                        "critical"
                      ? "text-grafana-10"
                      : "text-warning-10"
                }`}
              >
                {budgetAlerts[budgetAlerts.length - 1].message}
              </p>
              <p
                className={`text-xs mt-1 ${
                  budgetAlerts[budgetAlerts.length - 1].status === "exceeded"
                    ? "text-error-10"
                    : budgetAlerts[budgetAlerts.length - 1].status ===
                        "critical"
                      ? "text-grafana-9"
                      : "text-warning-9"
                }`}
              >
                {budgetAlerts[budgetAlerts.length - 1].entityType}:{" "}
                {budgetAlerts[budgetAlerts.length - 1].percentUsed}% used
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={clearBudgetAlerts}
              aria-label="Dismiss alert">
              <X size={16} />
            </Button>
          </div>
        </div>
      )}
      {/* User Budget Progress Bar (from Cost Tracking WebSocket) */}
      {enableRealtime && userBudget && (
        <div
          data-testid="budget-progress-bar"
          className="mx-6 mt-4 p-4 bg-neutral-2 border border-neutral-6 rounded-lg"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-neutral-11">
              Your Budget
            </h3>
            <span className="text-sm text-neutral-11">
              ${userBudget.remaining.toFixed(2)} remaining
            </span>
          </div>
          <div className="relative h-2 bg-neutral-3 rounded-full overflow-hidden">
            <div
              className={`absolute left-0 top-0 h-full rounded-full transition-all ${
                (userBudget.currentUsage / userBudget.budgetLimit) * 100 >= 90
                  ? "bg-error-9"
                  : (userBudget.currentUsage / userBudget.budgetLimit) * 100 >=
                      75
                    ? "bg-warning-9"
                    : "bg-primary-9"
              }`}
              style={{
                width: `${Math.min(100, (userBudget.currentUsage / userBudget.budgetLimit) * 100)}%`,
              }}
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-neutral-11">
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
                    className="p-4 rounded-lg border border-neutral-6"
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
            <div className="bg-neutral-2 rounded-lg border border-neutral-6 p-6">
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
                <div className="p-6 bg-neutral-2 rounded-lg border border-neutral-6">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-primary-9" />
                    <h3 className="text-sm font-medium text-neutral-11">
                      Total Cost
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-neutral-12">
                      {formatCurrency(summary.totalCost)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-neutral-11">
                    Past {period}
                  </div>
                </div>

                {/* Total Tokens */}
                <div className="p-6 bg-neutral-2 rounded-lg border border-neutral-6">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp size={20} className="text-success-9" />
                    <h3 className="text-sm font-medium text-neutral-11">
                      Total Tokens
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-neutral-12">
                      {formatNumber(summary.totalTokens ?? 0)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-neutral-11">
                    Past {period}
                  </div>
                </div>

                {/* Average Cost per Token */}
                <div className="p-6 bg-neutral-2 rounded-lg border border-neutral-6">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-insight-9" />
                    <h3 className="text-sm font-medium text-neutral-11">
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
                    <span className="text-sm text-neutral-11">
                      /1K
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-neutral-11">
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
                    className="p-4 rounded-lg border border-neutral-6"
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
                    className="p-6 rounded-lg border border-neutral-6"
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

            {/* Native vs Builtin Tool Comparison (v7) */}
            <Suspense
              fallback={
                <div
                  data-testid="native-tool-comparison-skeleton"
                  className="p-6 rounded-lg border border-neutral-6"
                >
                  <div className="space-y-4">
                    <Skeleton className="w-48 h-6" />
                    <div className="grid grid-cols-3 gap-4">
                      <Skeleton className="h-24" />
                      <Skeleton className="h-24" />
                      <Skeleton className="h-24" />
                    </div>
                    <Skeleton className="w-full h-64" />
                  </div>
                </div>
              }
            >
              <LazyNativeToolComparison pollingInterval={30000} />
            </Suspense>

            {/* Live Session Costs */}
            {enableRealtime && liveSessionCostsList.length > 0 && (
              <div
                data-testid="live-session-costs"
                className="bg-neutral-2 rounded-lg border border-neutral-6"
              >
                <div className="px-6 py-4 border-b border-neutral-6 flex items-center gap-2">
                  <div className="w-2 h-2 bg-success-9 rounded-full animate-pulse" />
                  <h2 className="text-lg font-semibold text-neutral-12">
                    Live Session Costs
                  </h2>
                </div>
                <div className="divide-y divide-neutral-3 dark:divide-neutral-10">
                  {liveSessionCostsList.map((session) => (
                    <div
                      key={session.sessionId}
                      className="px-6 py-4 flex items-center justify-between"
                    >
                      <div>
                        <span className="text-sm font-medium text-neutral-12">
                          {session.sessionId.slice(0, 8)}...
                        </span>
                        {session.model && (
                          <span className="ml-2 text-xs text-neutral-11">
                            {session.model}
                          </span>
                        )}
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-neutral-12">
                          {formatCurrency(session.totalCost)}
                        </div>
                        <div className="text-xs text-neutral-11">
                          {formatNumber(session.tokenCount)} tokens
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Cost by Model */}
            <div className="bg-neutral-2 rounded-lg border border-neutral-6">
              <div className="px-6 py-4 border-b border-neutral-6">
                <h2 className="text-lg font-semibold text-neutral-12">
                  Cost by Model
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-neutral-1/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Model
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Requests
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Avg Cost/Req
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-3 dark:divide-neutral-10">
                    {modelCostsArray.map((modelCost) => (
                      <tr
                        key={modelCost.model}
                        className="hover:bg-neutral-1 dark:hover:bg-neutral-10/50"
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-neutral-12">
                          {modelCost.model}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-12">
                          {formatCurrency(modelCost.cost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-11">
                          {formatNumber(modelCost.requests)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-neutral-11">
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
            <div className="bg-neutral-2 rounded-lg border border-neutral-6">
              <div className="px-6 py-4 border-b border-neutral-6">
                <h2 className="text-lg font-semibold text-neutral-12">
                  Cost Trend
                </h2>
              </div>
              <div className="p-6">
                {historyItems.length === 0 ? (
                  <div className="text-center py-8 text-neutral-11">
                    No cost data for this period
                  </div>
                ) : (
                  <div
                    data-testid="cost-history-chart"
                    className="h-64"
                    role="img"
                    aria-label={`Cost trend bar chart showing ${historyItems.length} data points. Total cost: ${summary ? formatCurrency(summary.totalCost) : "N/A"} over the selected ${period} period.`}
                  >
                    {/* Visually hidden description for screen readers */}
                    <span className="sr-only">
                      Bar chart displaying daily cost breakdown. Use the data
                      table below for detailed values.
                    </span>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={historyItems.map((point) => ({
                          date: formatDate(point.date),
                          cost: point.cost,
                          fullDate: point.date,
                        }))}
                        margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
                        aria-hidden="true"
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          className="stroke-neutral-3 dark:stroke-neutral-10"
                        />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 12 }}
                          className="text-neutral-11"
                        />
                        <YAxis
                          tick={{ fontSize: 12 }}
                          tickFormatter={(value) => `$${value}`}
                          className="text-neutral-11"
                        />
                        <Tooltip
                          formatter={(value) => [
                            formatCurrency(value as number),
                            "Cost",
                          ]}
                          labelFormatter={(label) => `Date: ${label}`}
                          contentStyle={{
                            backgroundColor: "var(--color-neutral-1)",
                            border: "1px solid var(--color-neutral-3)",
                            borderRadius: "8px",
                          }}
                        />
                        <Bar
                          dataKey="cost"
                          fill="var(--color-primary-500)"
                          radius={[4, 4, 0, 0]}
                          className="cursor-pointer hover:opacity-80 transition-opacity"
                        />
                      </BarChart>
                    </ResponsiveContainer>
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
