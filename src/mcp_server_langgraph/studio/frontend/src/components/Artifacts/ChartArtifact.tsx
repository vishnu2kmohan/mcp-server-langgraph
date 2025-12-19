/**
 * ChartArtifact Component
 *
 * Renders interactive charts for data visualization.
 * Features:
 * - Bar, Line, and Pie chart types
 * - Type switching
 * - Data point click handling
 * - Download functionality
 * - Expandable/collapsible view
 *
 * Note: This is a CSS-based implementation. For production,
 * consider using Recharts or Chart.js for more advanced features.
 */

import { useState, useCallback, useRef } from "react";
import {
  BarChart3,
  LineChart,
  PieChart,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { ArtifactExporter } from "./ArtifactExporter";
import type { ExportFormat } from "./ArtifactExporter";

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

export type ChartType = "bar" | "line" | "pie";

export interface ChartArtifactProps {
  title: string;
  type: ChartType;
  data: ChartDataPoint[];
  onDataPointClick?: (point: ChartDataPoint) => void;
  onDownload?: () => void;
  showTypeSwitcher?: boolean;
  expandable?: boolean;
  className?: string;
}

// Default colors for chart elements
const CHART_COLORS = [
  "#3B82F6", // blue-500
  "#10B981", // emerald-500
  "#F59E0B", // amber-500
  "#EF4444", // red-500
  "#8B5CF6", // violet-500
  "#EC4899", // pink-500
  "#06B6D4", // cyan-500
  "#84CC16", // lime-500
];

/**
 * Format large numbers with K/M suffix
 */
function formatValue(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toString();
}

/**
 * Bar Chart Renderer
 */
function BarChartRenderer({
  data,
  maxValue,
  onDataPointClick,
}: {
  data: ChartDataPoint[];
  maxValue: number;
  onDataPointClick?: (point: ChartDataPoint) => void;
}) {
  return (
    <div className="flex items-end justify-around h-48 gap-2 px-4 pt-4 pb-8">
      {data.map((point, index) => {
        const height = maxValue > 0 ? (point.value / maxValue) * 100 : 0;
        const color = point.color || CHART_COLORS[index % CHART_COLORS.length];
        return (
          <div
            key={point.label}
            className="flex flex-col items-center flex-1 max-w-20"
          >
            <div
              className="w-full rounded-t transition-all hover:opacity-80 cursor-pointer relative group"
              style={{
                height: `${height}%`,
                backgroundColor: color,
                minHeight: 4,
              }}
              onClick={() => onDataPointClick?.(point)}
              data-testid="chart-bar"
            >
              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                {formatValue(point.value)}
              </div>
            </div>
            <span className="mt-2 text-xs text-gray-600 dark:text-gray-400 truncate max-w-full text-center">
              {point.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Line Chart Renderer (simplified SVG)
 */
function LineChartRenderer({
  data,
  maxValue,
  onDataPointClick,
}: {
  data: ChartDataPoint[];
  maxValue: number;
  onDataPointClick?: (point: ChartDataPoint) => void;
}) {
  const width = 100;
  const height = 60;
  const padding = 5;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = data.map((point, index) => ({
    x: padding + (index / (data.length - 1 || 1)) * chartWidth,
    y:
      padding +
      chartHeight -
      (maxValue > 0 ? (point.value / maxValue) * chartHeight : 0),
    ...point,
  }));

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  return (
    <div className="h-48 px-4 pt-4 pb-8">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        {/* Line */}
        <path
          d={pathD}
          fill="none"
          stroke="#3B82F6"
          strokeWidth="0.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Points */}
        {points.map((point, index) => (
          <circle
            key={point.label}
            cx={point.x}
            cy={point.y}
            r="1.5"
            fill="#3B82F6"
            className="cursor-pointer hover:r-2"
            onClick={() => onDataPointClick?.(data[index])}
            data-testid="chart-point"
          >
            <title>{`${point.label}: ${formatValue(point.value)}`}</title>
          </circle>
        ))}
      </svg>
      {/* Labels */}
      <div className="flex justify-between px-2">
        {data.map((point) => (
          <span
            key={point.label}
            className="text-xs text-gray-600 dark:text-gray-400 truncate"
          >
            {point.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Pie Chart Renderer (simplified SVG)
 */
function PieChartRenderer({
  data,
  onDataPointClick,
}: {
  data: ChartDataPoint[];
  onDataPointClick?: (point: ChartDataPoint) => void;
}) {
  const total = data.reduce((sum, p) => sum + p.value, 0);
  const size = 100;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 35;

  let currentAngle = -90; // Start from top

  const slices = data.map((point, index) => {
    const angle = total > 0 ? (point.value / total) * 360 : 0;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    currentAngle = endAngle;

    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;

    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);

    const largeArc = angle > 180 ? 1 : 0;

    const pathD = [
      `M ${cx} ${cy}`,
      `L ${x1} ${y1}`,
      `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
      "Z",
    ].join(" ");

    const color = point.color || CHART_COLORS[index % CHART_COLORS.length];

    return { pathD, color, point, index };
  });

  return (
    <div className="h-48 flex items-center justify-center gap-4 px-4 py-4">
      <svg viewBox={`0 0 ${size} ${size}`} className="w-40 h-40">
        {slices.map(({ pathD, color, point }) => (
          <path
            key={point.label}
            d={pathD}
            fill={color}
            className="cursor-pointer hover:opacity-80 transition-opacity"
            onClick={() => onDataPointClick?.(point)}
            data-testid="chart-slice"
          >
            <title>{`${point.label}: ${formatValue(point.value)}`}</title>
          </path>
        ))}
      </svg>
      {/* Legend */}
      <div className="flex flex-col gap-1">
        {data.map((point, index) => (
          <div key={point.label} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{
                backgroundColor:
                  point.color || CHART_COLORS[index % CHART_COLORS.length],
              }}
            />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {point.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ChartArtifact({
  title,
  type: initialType,
  data,
  onDataPointClick,
  onDownload,
  showTypeSwitcher = false,
  expandable = false,
  className = "",
}: ChartArtifactProps) {
  const [chartType, setChartType] = useState<ChartType>(initialType);
  const [isExpanded, setIsExpanded] = useState(false);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const maxValue = Math.max(...data.map((d) => d.value), 0);

  const typeButtons: {
    type: ChartType;
    icon: React.ReactNode;
    label: string;
  }[] = [
    { type: "bar", icon: <BarChart3 size={14} />, label: "Bar" },
    { type: "line", icon: <LineChart size={14} />, label: "Line" },
    { type: "pie", icon: <PieChart size={14} />, label: "Pie" },
  ];

  /**
   * Export chart data as CSV file
   */
  const exportAsCsv = useCallback(() => {
    // Build CSV content
    const headers = ["Label", "Value"];
    const rows = data.map((point) => [point.label, point.value.toString()]);
    const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");

    // Generate filename from title
    const filename = title
      ? `${title.replace(/\s+/g, "_").toLowerCase()}.csv`
      : "chart_data.csv";

    // Create and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [data, title]);

  const handleDownload = useCallback(() => {
    if (onDownload) {
      onDownload();
    } else {
      // Default: export as CSV
      exportAsCsv();
    }
  }, [onDownload, exportAsCsv]);

  // Handle export from ArtifactExporter
  const handleExport = useCallback(
    (format: ExportFormat, blob: Blob | string) => {
      if (onDownload) {
        onDownload();
        return;
      }

      // Download the blob
      if (blob instanceof Blob) {
        const extension = format === "pdf" ? "pdf" : format === "svg" ? "svg" : "png";
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${title.replace(/\s+/g, "_")}.${extension}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    },
    [onDownload, title],
  );

  const ChartIcon =
    chartType === "bar"
      ? BarChart3
      : chartType === "line"
        ? LineChart
        : PieChart;

  return (
    <div
      className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden ${className}`}
      data-testid="chart-artifact"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ChartIcon size={16} className="text-gray-500 dark:text-gray-400" />
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            {title}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {showTypeSwitcher && (
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded p-0.5">
              {typeButtons.map(({ type, icon, label }) => (
                <button
                  key={type}
                  onClick={() => setChartType(type)}
                  className={`flex items-center gap-1 px-2 py-1 text-xs rounded transition-colors ${
                    chartType === type
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                  aria-label={label}
                >
                  {icon}
                </button>
              ))}
            </div>
          )}
          <ArtifactExporter
            artifactType="chart"
            data={data}
            elementRef={chartContainerRef}
            onExport={handleExport}
            filename={title.replace(/\s+/g, "_")}
          />
          {expandable && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              aria-label={isExpanded ? "Collapse chart" : "Expand chart"}
            >
              {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          )}
        </div>
      </div>

      {/* Chart */}
      <div ref={chartContainerRef} data-testid="chart-container">
        {data.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-500 dark:text-gray-400">
            No data available
          </div>
        ) : chartType === "bar" ? (
          <BarChartRenderer
            data={data}
            maxValue={maxValue}
            onDataPointClick={onDataPointClick}
          />
        ) : chartType === "line" ? (
          <LineChartRenderer
            data={data}
            maxValue={maxValue}
            onDataPointClick={onDataPointClick}
          />
        ) : (
          <PieChartRenderer data={data} onDataPointClick={onDataPointClick} />
        )}
      </div>
    </div>
  );
}
