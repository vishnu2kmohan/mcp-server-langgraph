/**
 * GenerativeWidget - Phase 2
 *
 * Dynamic UI widget generation from AI with support
 * for charts, tables, and text content.
 */
import { RefreshCw, AlertCircle } from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface WidgetConfig {
  id: string;
  type: "chart" | "table" | "text";
  title: string;
  data: ChartData | TableData | TextData;
}

interface ChartData {
  labels: string[];
  values: number[];
}

interface TableData {
  columns: string[];
  rows: string[][];
}

interface TextData {
  content: string;
}

export interface GenerativeWidgetProps {
  config: WidgetConfig;
  isLoading?: boolean;
  error?: string;
  onRefresh?: (id: string) => void;
  onRetry?: () => void;
  className?: string;
}

// =============================================================================
// Sub-components
// =============================================================================

function WidgetSkeleton() {
  return (
    <div data-testid="widget-skeleton" className="space-y-3 animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
      <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
    </div>
  );
}

function ChartWidget({ data }: { data: ChartData }) {
  const maxValue = Math.max(...data.values);

  return (
    <div data-testid="widget-chart" className="space-y-2">
      <div className="flex items-end gap-2 h-32">
        {data.values.map((value, index) => (
          <div key={index} className="flex-1 flex flex-col items-center">
            <div
              className="w-full bg-primary-500 rounded-t"
              style={{
                height: `${(value / maxValue) * 100}%`,
                minHeight: "4px",
              }}
            />
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
        {data.labels.map((label, index) => (
          <span key={index}>{label}</span>
        ))}
      </div>
    </div>
  );
}

function TableWidget({ data }: { data: TableData }) {
  return (
    <div data-testid="widget-table" className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            {data.columns.map((column, index) => (
              <th
                key={index}
                className="px-2 py-1 text-left font-medium text-gray-600 dark:text-gray-400"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className="border-b border-gray-100 dark:border-gray-800"
            >
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="px-2 py-1 text-gray-900 dark:text-gray-100"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TextWidget({ data }: { data: TextData }) {
  return (
    <div
      data-testid="widget-text"
      className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed"
    >
      {data.content}
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

export function GenerativeWidget({
  config,
  isLoading = false,
  error,
  onRefresh,
  onRetry,
  className,
}: GenerativeWidgetProps) {
  const renderContent = () => {
    switch (config.type) {
      case "chart":
        return <ChartWidget data={config.data as ChartData} />;
      case "table":
        return <TableWidget data={config.data as TableData} />;
      case "text":
        return <TextWidget data={config.data as TextData} />;
      default:
        return null;
    }
  };

  return (
    <div
      data-testid="generative-widget"
      role="region"
      aria-label={config.title}
      className={cn(
        "bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-gray-900 dark:text-gray-100">
          {config.title}
        </h3>
        <button
          data-testid="refresh-button"
          type="button"
          onClick={() => onRefresh?.(config.id)}
          className="p-1 text-gray-400 dark:text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-300 transition-colors"
          aria-label="Refresh widget"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <WidgetSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center py-4 text-center">
          <AlertCircle className="w-8 h-8 text-error-500 mb-2" />
          <p className="text-sm text-error-600 dark:text-error-400 mb-2">
            {error}
          </p>
          <button
            data-testid="retry-button"
            type="button"
            onClick={onRetry}
            className="px-3 py-1 text-sm bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400 rounded hover:bg-error-200 dark:hover:bg-error-900/50 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : (
        renderContent()
      )}
    </div>
  );
}
