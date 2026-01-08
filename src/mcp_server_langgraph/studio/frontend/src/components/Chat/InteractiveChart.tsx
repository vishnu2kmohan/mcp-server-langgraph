/**
 * InteractiveChart Component
 *
 * Enhanced chart renderer with interactive controls:
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
    ? "fixed inset-0 z-50 bg-gray-900 p-4"
    : `my-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`;

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
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {chartData.title}
            </h4>
          )}
        </div>

        {/* Chart type toggles */}
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setChartType("line")}
            aria-label="Line chart"
            className={`p-1.5 rounded ${
              chartType === "line"
                ? "bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
            }`}
          >
            <TrendingUp size={14} />
          </button>
          <button
            type="button"
            onClick={() => setChartType("bar")}
            aria-label="Bar chart"
            className={`p-1.5 rounded ${
              chartType === "bar"
                ? "bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
            }`}
          >
            <BarChart2 size={14} />
          </button>
          <button
            type="button"
            onClick={() => setChartType("pie")}
            aria-label="Pie chart"
            className={`p-1.5 rounded ${
              chartType === "pie"
                ? "bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
            }`}
          >
            <PieChartIcon size={14} />
          </button>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handleToggleDataTable}
            aria-label="Toggle data table"
            className={`p-1.5 rounded ${
              showDataTable
                ? "bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400"
                : "text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
            }`}
          >
            <Table size={14} />
          </button>
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Copy data"
            className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
          >
            {copied ? (
              <Check size={14} className="text-success-500" />
            ) : (
              <Copy size={14} />
            )}
          </button>
          <button
            type="button"
            onClick={handleToggleFullscreen}
            aria-label="Toggle fullscreen"
            className="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Chart */}
      <div className={isFullscreen ? "h-[calc(100vh-200px)]" : "h-64"}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "line" ? (
            <LineChart data={chartData.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
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
            <BarChart data={chartData.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey={xKey} stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
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
            <PieChart>
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
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                  {xKey}
                </th>
                <th className="px-4 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                  {yKey}
                </th>
              </tr>
            </thead>
            <tbody>
              {chartData.data.map((row, index) => (
                <tr
                  key={index}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-400">
                    {String(row[xKey])}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-600 dark:text-gray-400">
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
