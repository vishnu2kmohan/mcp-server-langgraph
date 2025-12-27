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
            <Activity size={24} className="text-purple-500" />
            <CardTitle>Agent Metrics</CardTitle>
          </div>
        </div>
        <CardContent>
          <div
            className="flex items-center justify-center py-8"
            data-testid="metrics-loading"
          >
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-500">Loading metrics...</span>
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
            <Activity size={24} className="text-purple-500" />
            <CardTitle>Agent Metrics</CardTitle>
          </div>
        </div>
        <CardContent>
          <div
            className="flex flex-col items-center justify-center py-8 text-center"
            data-testid="metrics-error"
          >
            <AlertTriangle className="w-8 h-8 text-yellow-500 mb-2" />
            <p className="text-gray-500 mb-4">Metrics backend unavailable</p>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded hover:bg-blue-600"
            >
              <RefreshCw size={16} />
              Retry
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const successRate =
    data.orchestrator.total_executions > 0
      ? (data.orchestrator.successful_executions /
          data.orchestrator.total_executions) *
        100
      : 0;

  return (
    <Card data-testid="agent-metrics-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Activity size={24} className="text-purple-500" />
          <CardTitle>Agent Metrics</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full">
            {data.time_range_hours}h
          </span>
          <button
            onClick={() => refetch()}
            className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded"
            aria-label="Refresh metrics"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <CardContent>
        {/* Orchestrator Metrics */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <Activity size={16} />
            Orchestrator
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(data.orchestrator.total_executions)}
              </div>
              <div className="text-xs text-gray-500">Total Executions</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-green-600">
                {formatPercent(successRate)}
              </div>
              <div className="text-xs text-gray-500">Success Rate</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {data.orchestrator.avg_duration_ms.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">Avg Duration (ms)</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-red-600">
                {formatNumber(data.orchestrator.failed_executions)}
              </div>
              <div className="text-xs text-gray-500">Failed</div>
            </div>
          </div>
        </div>

        {/* HITL Metrics */}
        <div className="mb-6" data-testid="hitl-metrics">
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <Users size={16} />
            Human-in-the-Loop
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(data.hitl.total_requests)}
              </div>
              <div className="text-xs text-gray-500">Total Requests</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded flex items-center gap-2">
              <CheckCircle size={20} className="text-green-500" />
              <div>
                <div className="text-xl font-bold text-green-600">
                  {formatNumber(data.hitl.approved_count)}
                </div>
                <div className="text-xs text-gray-500">Approved</div>
              </div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded flex items-center gap-2">
              <XCircle size={20} className="text-red-500" />
              <div>
                <div className="text-xl font-bold text-red-600">
                  {formatNumber(data.hitl.rejected_count)}
                </div>
                <div className="text-xs text-gray-500">Rejected</div>
              </div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded flex items-center gap-2">
              <Clock size={20} className="text-yellow-500" />
              <div>
                <div className="text-xl font-bold text-yellow-600">
                  {formatNumber(data.hitl.pending_count)}
                </div>
                <div className="text-xs text-gray-500">Pending</div>
              </div>
            </div>
          </div>
        </div>

        {/* Cost Metrics */}
        <div data-testid="cost-metrics">
          <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3 flex items-center gap-2">
            <DollarSign size={16} />
            Cost Tracking
          </h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(data.cost.total_cost_usd)}
              </div>
              <div className="text-xs text-gray-500">Total Cost</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatNumber(data.cost.total_tokens)}
              </div>
              <div className="text-xs text-gray-500">Total Tokens</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {formatCurrency(data.cost.avg_cost_per_request_usd)}
              </div>
              <div className="text-xs text-gray-500">Avg/Request</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
