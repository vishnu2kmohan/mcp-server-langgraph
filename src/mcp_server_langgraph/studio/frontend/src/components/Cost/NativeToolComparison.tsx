/**
 * NativeToolComparison
 *
 * Dashboard component for comparing native vs builtin tool performance.
 * Shows latency, error rates, and selection counts.
 *
 * v7: Part of the Native LLM Provider Tools Integration
 */

import { useMemo } from "react";
import { Zap, AlertTriangle, Clock, Activity } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { Skeleton } from "../UI/Skeleton";
import { ErrorState } from "../UI/ErrorState";
import { useGetToolMetricsComparisonQuery } from "../../api";

interface NativeToolComparisonProps {
  /** Polling interval in ms (default: 30000) */
  pollingInterval?: number;
}

export function NativeToolComparison({
  pollingInterval = 30000,
}: NativeToolComparisonProps) {
  const { data, isLoading, isError, error, refetch } =
    useGetToolMetricsComparisonQuery(undefined, {
      pollingInterval,
    });

  // Transform data for charts
  const chartData = useMemo(() => {
    if (!data?.tools) return [];

    return data.tools
      .filter((tool) => tool.native || tool.builtin)
      .map((tool) => ({
        name: tool.toolName
          .replace(/_/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase()),
        nativeLatency: tool.native?.avgLatencyMs ?? 0,
        builtinLatency: tool.builtin?.avgLatencyMs ?? 0,
        nativeP95: tool.native?.p95LatencyMs ?? 0,
        builtinP95: tool.builtin?.p95LatencyMs ?? 0,
        nativeErrors: tool.native?.errorCount ?? 0,
        builtinErrors: tool.builtin?.errorCount ?? 0,
        nativeSelections: tool.native?.selectionCount ?? 0,
        builtinSelections: tool.builtin?.selectionCount ?? 0,
      }));
  }, [data]);

  const formatMs = (value: number): string => `${value.toFixed(1)}ms`;
  const formatPercent = (value: number): string => `${value.toFixed(1)}%`;

  if (isLoading) {
    return (
      <div className="bg-neutral-2 rounded-lg border border-neutral-6 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Skeleton className="w-5 h-5 rounded" />
          <Skeleton className="w-48 h-6" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        title="Failed to load tool metrics"
        message={
          (error as { message?: string })?.message || "Unable to fetch metrics"
        }
        onRetry={refetch}
      />
    );
  }

  if (!data || chartData.length === 0) {
    return (
      <div className="bg-neutral-2 rounded-lg border border-neutral-6 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={20} className="text-primary-9" />
          <h2 className="text-lg font-semibold text-neutral-12">
            Native vs Builtin Tool Comparison
          </h2>
        </div>
        <div className="text-center py-8 text-neutral-11">
          No tool execution data available yet.
          <br />
          Use tools with native preference enabled to see comparison metrics.
        </div>
      </div>
    );
  }

  const { summary } = data;
  const totalSelections = summary.nativeSelections + summary.builtinSelections;
  const nativePercent =
    totalSelections > 0
      ? (summary.nativeSelections / totalSelections) * 100
      : 0;
  const builtinPercent =
    totalSelections > 0
      ? (summary.builtinSelections / totalSelections) * 100
      : 0;

  return (
    <div className="bg-neutral-2 rounded-lg border border-neutral-6">
      {/* Header */}
      <div className="px-6 py-4 border-b border-neutral-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={20} className="text-primary-9" />
            <h2 className="text-lg font-semibold text-neutral-12">
              Native vs Builtin Tool Comparison
            </h2>
          </div>
          <div className="text-xs text-neutral-11">
            Uptime: {Math.floor(summary.uptimeSeconds / 60)}m
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
        {/* Selection Distribution */}
        <div className="p-4 bg-neutral-1 rounded-lg border border-neutral-5">
          <div className="flex items-center gap-2 mb-2">
            <Activity size={16} className="text-primary-9" />
            <h3 className="text-sm font-medium text-neutral-11">
              Selection Distribution
            </h3>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-2xl font-bold text-neutral-12">
              {totalSelections}
            </span>
            <span className="text-sm text-neutral-11">total</span>
          </div>
          <div className="flex gap-2 text-xs">
            <span className="px-2 py-1 bg-primary-3 text-primary-11 rounded">
              Native: {formatPercent(nativePercent)}
            </span>
            <span className="px-2 py-1 bg-neutral-3 text-neutral-11 rounded">
              Builtin: {formatPercent(builtinPercent)}
            </span>
          </div>
        </div>

        {/* Error Comparison */}
        <div className="p-4 bg-neutral-1 rounded-lg border border-neutral-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-warning-9" />
            <h3 className="text-sm font-medium text-neutral-11">Error Count</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xl font-bold text-neutral-12">
                {summary.nativeErrors}
              </div>
              <div className="text-xs text-neutral-11">Native</div>
            </div>
            <div>
              <div className="text-xl font-bold text-neutral-12">
                {summary.builtinErrors}
              </div>
              <div className="text-xs text-neutral-11">Builtin</div>
            </div>
          </div>
        </div>

        {/* Average Latency Summary */}
        <div className="p-4 bg-neutral-1 rounded-lg border border-neutral-5">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-success-9" />
            <h3 className="text-sm font-medium text-neutral-11">
              Latency Comparison
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xl font-bold text-neutral-12">
                {formatMs(
                  chartData.reduce((sum, d) => sum + d.nativeLatency, 0) /
                    (chartData.length || 1),
                )}
              </div>
              <div className="text-xs text-neutral-11">Native avg</div>
            </div>
            <div>
              <div className="text-xl font-bold text-neutral-12">
                {formatMs(
                  chartData.reduce((sum, d) => sum + d.builtinLatency, 0) /
                    (chartData.length || 1),
                )}
              </div>
              <div className="text-xs text-neutral-11">Builtin avg</div>
            </div>
          </div>
        </div>
      </div>

      {/* Latency Comparison Chart */}
      <div className="px-6 pb-6">
        <h3 className="text-sm font-medium text-neutral-11 mb-4">
          Average Latency by Tool (ms)
        </h3>
        <div
          className="h-64"
          role="img"
          aria-label="Bar chart comparing native and builtin tool latencies"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                className="stroke-neutral-3 dark:stroke-neutral-10"
              />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 12 }}
                className="text-neutral-11"
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `${value}ms`}
                className="text-neutral-11"
              />
              <Tooltip
                formatter={(value, name) => [
                  formatMs(value as number),
                  name === "nativeLatency" ? "Native" : "Builtin",
                ]}
                contentStyle={{
                  backgroundColor: "var(--color-neutral-1)",
                  border: "1px solid var(--color-neutral-3)",
                  borderRadius: "8px",
                }}
              />
              <Legend
                formatter={(value) =>
                  value === "nativeLatency"
                    ? "Native (Provider)"
                    : "Builtin (Server)"
                }
              />
              <Bar
                dataKey="nativeLatency"
                fill="var(--color-primary-500)"
                radius={[4, 4, 0, 0]}
                name="nativeLatency"
              />
              <Bar
                dataKey="builtinLatency"
                fill="var(--color-neutral-8)"
                radius={[4, 4, 0, 0]}
                name="builtinLatency"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Per-Tool Details Table */}
      <div className="border-t border-neutral-6">
        <div className="px-6 py-4">
          <h3 className="text-sm font-medium text-neutral-11 mb-4">
            Detailed Metrics by Tool
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-1/50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-neutral-11 uppercase">
                    Tool
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-neutral-11 uppercase">
                    Native Latency
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-neutral-11 uppercase">
                    Builtin Latency
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-neutral-11 uppercase">
                    P95 Native
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-neutral-11 uppercase">
                    P95 Builtin
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-neutral-11 uppercase">
                    Executions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-3 dark:divide-neutral-10">
                {chartData.map((tool) => (
                  <tr
                    key={tool.name}
                    className="hover:bg-neutral-1 dark:hover:bg-neutral-10/50"
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-neutral-12 font-medium">
                      {tool.name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-neutral-12">
                      {tool.nativeLatency > 0
                        ? formatMs(tool.nativeLatency)
                        : "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-neutral-12">
                      {tool.builtinLatency > 0
                        ? formatMs(tool.builtinLatency)
                        : "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-neutral-11">
                      {tool.nativeP95 > 0 ? formatMs(tool.nativeP95) : "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-neutral-11">
                      {tool.builtinP95 > 0 ? formatMs(tool.builtinP95) : "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-neutral-11">
                      {tool.nativeSelections + tool.builtinSelections}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default NativeToolComparison;
