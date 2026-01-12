/**
 * AgentMetricsCard
 *
 * Displays agent orchestration metrics from the OTEL/Prometheus backend.
 * Shows orchestrator execution metrics, HITL metrics, and cost tracking.
 *
 * Visible only to admin and developer personas.
 */

import { useSelector } from "react-redux";
import {
  Activity,
  Users,
  DollarSign,
  RefreshCw,
  AlertTriangle,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { selectPersona } from "../../store/slices/personaSlice";
import { Card, CardTitle, CardContent } from "../UI/Card";
import { useGetAgentMetricsQuery } from "../../api";

import { Button } from "@/components/UI";

/**
 * Format a number with commas
 */
function formatNumber(num: number): string {
  return num.toLocaleString("en-US");
}

/**
 * Format a dollar amount
 */
function formatCurrency(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

/**
 * Format a percentage
 */
function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function AgentMetricsCard() {
  const persona = useSelector(selectPersona);
  const { data, isLoading, error, refetch } = useGetAgentMetricsQuery();

  // Only show for admin and developer personas
  if (!["admin", "developer"].includes(persona)) {
    return null;
  }

  // Loading state
  if (isLoading) {
    return (
      <Card data-testid="agent-metrics-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Activity size={24} className="text-insight-500" />
            <CardTitle>Agent Metrics</CardTitle>
          </div>
        </div>
        <CardContent>
          <div
            className="flex items-center justify-center py-8"
            data-testid="metrics-loading"
          >
            <Loader2 className="w-6 h-6 animate-spin text-neutral-400 dark:text-neutral-400" />
            <span className="ml-2 text-neutral-500 dark:text-neutral-400">
              Loading metrics...
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error || !data) {
    return (
      <Card data-testid="agent-metrics-card">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Activity size={24} className="text-insight-500" />
            <CardTitle>Agent Metrics</CardTitle>
          </div>
        </div>
        <CardContent>
          <div
            className="flex flex-col items-center justify-center py-8 text-center"
            data-testid="metrics-error"
          >
            <AlertTriangle className="w-8 h-8 text-warning-500 mb-2" />
            <p className="text-neutral-500 dark:text-neutral-400 mb-4">
              Metrics backend unavailable
            </p>
            <Button
              variant="primary"
              className="flex px-4 py-2 text-sm text-white bg-primary-500 rounded hover:bg-primary-600"
              onClick={() => refetch()}
            >
              <RefreshCw size={16} />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const successRate =
    data.orchestrator.totalExecutions > 0
      ? (data.orchestrator.successfulExecutions /
          data.orchestrator.totalExecutions) *
        100
      : 0;

  return (
    <Card data-testid="agent-metrics-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Activity size={24} className="text-insight-500" />
          <CardTitle>Agent Metrics</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 rounded-full">
            {data.timeRangeHours}h
          </span>
          <Button
            className="p-1 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:hover:text-neutral-300 rounded"
            onClick={() => refetch()}
            aria-label="Refresh metrics"
          >
            <RefreshCw size={16} />
          </Button>
        </div>
      </div>
      <CardContent>
        {/* Orchestrator Metrics */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 flex items-center gap-2">
            <Activity size={16} />
            Orchestrator
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-neutral-900 dark:text-white">
                {formatNumber(data.orchestrator.totalExecutions)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Total Executions
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-success-600">
                {formatPercent(successRate)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Success Rate
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-neutral-900 dark:text-white">
                {data.orchestrator.avgDurationMs.toFixed(1)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Avg Duration (ms)
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-error-600">
                {formatNumber(data.orchestrator.failedExecutions)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Failed
              </div>
            </div>
          </div>
        </div>

        {/* HITL Metrics */}
        <div className="mb-6" data-testid="hitl-metrics">
          <h4 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 flex items-center gap-2">
            <Users size={16} />
            Human-in-the-Loop
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-neutral-900 dark:text-white">
                {formatNumber(data.hitl.totalRequests)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Total Requests
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded flex items-center gap-2">
              <CheckCircle size={20} className="text-success-500" />
              <div>
                <div className="text-xl font-bold text-success-600">
                  {formatNumber(data.hitl.approvedCount)}
                </div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">
                  Approved
                </div>
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded flex items-center gap-2">
              <XCircle size={20} className="text-error-500" />
              <div>
                <div className="text-xl font-bold text-error-600">
                  {formatNumber(data.hitl.rejectedCount)}
                </div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">
                  Rejected
                </div>
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded flex items-center gap-2">
              <Clock size={20} className="text-warning-500" />
              <div>
                <div className="text-xl font-bold text-warning-600">
                  {formatNumber(data.hitl.pendingCount)}
                </div>
                <div className="text-xs text-neutral-500 dark:text-neutral-400">
                  Pending
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Cost Metrics */}
        <div data-testid="cost-metrics">
          <h4 className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 flex items-center gap-2">
            <DollarSign size={16} />
            Cost Tracking
          </h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-neutral-900 dark:text-white">
                {formatCurrency(data.cost.totalCostUsd)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Total Cost
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-neutral-900 dark:text-white">
                {formatNumber(data.cost.totalTokens)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Total Tokens
              </div>
            </div>
            <div className="p-3 bg-neutral-50 dark:bg-neutral-800 rounded">
              <div className="text-2xl font-bold text-neutral-900 dark:text-white">
                {formatCurrency(data.cost.avgCostPerRequestUsd)}
              </div>
              <div className="text-xs text-neutral-500 dark:text-neutral-400">
                Avg/Request
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
