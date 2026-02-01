/**
 * InteractiveChart Component
 *
 * @deprecated This component uses Recharts and is being phased out in favor of
 * VegaLiteArtifact which provides richer interactivity (tooltips, zoom, pan, export).
 *
 * Migration path:
 * - For AI-generated charts: Use `vega-lite` or `altair` code blocks instead of `chart`
 * - For static dashboards: Continue using Recharts directly (CostPage, DevToolsPanel)
 *
 * This component remains for backward compatibility with existing `chart` code blocks.
 *
 * Features (legacy):
 * - Switch between chart types (line, bar, pie)
 * - Fullscreen view
 * - Copy data as JSON
 * - Toggle data table view
 */

import { useState, useCallback } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Maximize2,
  Minimize2,
  Copy,
  Check,
  Table,
  TrendingUp,
  BarChart2,
  PieChartIcon,
} from "lucide-react";

import { Button } from "@/components/UI";

// Chart color palette
const CHART_COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
];

export interface ChartData {
  type: "line" | "bar" | "pie";
  title?: string;
  data: Array<{ name: string; value: number; [key: string]: string | number }>;
  xKey?: string;
  yKey?: string;
}

export interface InteractiveChartProps {
  /** Chart data and configuration */
  chartData: ChartData;
  /** Optional className for the container */
  className?: string;
}

export function InteractiveChart({
  chartData,
  className = "",
}: InteractiveChartProps) {
  const [chartType, setChartType] = useState<"line" | "bar" | "pie">(
    chartData.type,
  );
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showDataTable, setShowDataTable] = useState(false);
  const [copied, setCopied] = useState(false);

  const xKey = chartData.xKey || "name";
  const yKey = chartData.yKey || "value";

  // Copy chart data as JSON
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(chartData, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }, [chartData]);

  // Toggle fullscreen
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Toggle data table
  const handleToggleDataTable = useCallback(() => {
    setShowDataTable((prev) => !prev);
  }, []);

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          if (isFullscreen) {
            e.preventDefault();
            setIsFullscreen(false);
          }
          break;
      }
    },
    [isFullscreen],
  );

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-modal bg-neutral-2 p-4"
    : `my-4 p-4 bg-neutral-1 rounded-lg border border-neutral-5 ${className}`;

  return (
    <div
      data-testid="chart-container"
      className={containerClasses}
      onKeyDown={handleKeyDown}
      tabIndex={0}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 mb-3">
        {/* Title */}
        <div className="flex-1">
          {chartData.title && (
            <h4 className="text-sm font-medium text-neutral-11">
              {chartData.title}
            </h4>
          )}
        </div>

        {/* Chart type toggles */}
        <div className="flex items-center gap-1 bg-neutral-2 rounded-lg p-0.5">
          <Button
            variant="ghost"
            size="icon"
            className={
              chartType === "line" ? "bg-primary-3 dark:bg-primary-12" : ""
            }
            type="button"
            onClick={() => setChartType("line")}
            aria-label="Line chart"
            aria-pressed={chartType === "line"}
          >
            <TrendingUp size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={
              chartType === "bar" ? "bg-primary-3 dark:bg-primary-12" : ""
            }
            type="button"
            onClick={() => setChartType("bar")}
            aria-label="Bar chart"
            aria-pressed={chartType === "bar"}
          >
            <BarChart2 size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={
              chartType === "pie" ? "bg-primary-3 dark:bg-primary-12" : ""
            }
            type="button"
            onClick={() => setChartType("pie")}
            aria-label="Pie chart"
            aria-pressed={chartType === "pie"}
          >
            <PieChartIcon size={14} />
          </Button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            type="button"
            onClick={handleToggleDataTable}
            aria-label="Toggle data table"
          >
            <Table size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            type="button"
            onClick={handleCopy}
            aria-label="Copy data"
          >
            {copied ? (
              <Check size={14} className="text-success-9" />
            ) : (
              <Copy size={14} />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            type="button"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </Button>
        </div>
      </div>
      {/* Chart */}
      <div
        className={isFullscreen ? "h-[calc(100vh-200px)]" : "h-64"}
        role="img"
        aria-label={`${chartData.title || "Interactive chart"} - ${chartType} chart with ${chartData.data.length} data points`}
      >
        {/* Visually hidden description for screen readers */}
        <span className="sr-only">
          {chartType} chart displaying {chartData.title || "data"}. Use the data
          table toggle for accessible values.
        </span>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "line" ? (
            <LineChart data={chartData.data} aria-hidden="true">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--neutral-7)" />
              <XAxis dataKey={xKey} stroke="var(--neutral-8)" fontSize={12} />
              <YAxis stroke="var(--neutral-8)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey={yKey}
                stroke={CHART_COLORS[0]}
                strokeWidth={2}
                dot={{ fill: CHART_COLORS[0] }}
              />
            </LineChart>
          ) : chartType === "bar" ? (
            <BarChart data={chartData.data} aria-hidden="true">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--neutral-7)" />
              <XAxis dataKey={xKey} stroke="var(--neutral-8)" fontSize={12} />
              <YAxis stroke="var(--neutral-8)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Bar
                dataKey={yKey}
                fill={CHART_COLORS[0]}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          ) : (
            <PieChart aria-hidden="true">
              <Pie
                data={chartData.data}
                dataKey={yKey}
                nameKey={xKey}
                cx="50%"
                cy="50%"
                outerRadius={isFullscreen ? 200 : 80}
                label={(props) =>
                  `${props.name ?? "Unknown"}: ${((props.percent ?? 0) * 100).toFixed(0)}%`
                }
              >
                {chartData.data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                }}
              />
              <Legend />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
      {/* Data Table */}
      {showDataTable && (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-neutral-5">
                <th className="px-4 py-2 text-left font-medium text-neutral-11">
                  {xKey}
                </th>
                <th className="px-4 py-2 text-right font-medium text-neutral-11">
                  {yKey}
                </th>
              </tr>
            </thead>
            <tbody>
              {chartData.data.map((row, index) => (
                <tr key={index} className="border-b border-neutral-5">
                  <td className="px-4 py-2 text-neutral-11">
                    {String(row[xKey])}
                  </td>
                  <td className="px-4 py-2 text-right text-neutral-11">
                    {String(row[yKey])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default InteractiveChart;
