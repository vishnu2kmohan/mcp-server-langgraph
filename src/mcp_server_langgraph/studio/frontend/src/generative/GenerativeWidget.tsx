/**
 * GenerativeWidget - Phase 2
 *
 * Dynamic UI widget generation from AI with support
 * for charts, tables, and text content.
 */
import { RefreshCw, AlertCircle } from "lucide-react";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

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
      <div className="h-4 bg-neutral-3 rounded w-3/4" />
      <div className="h-32 bg-neutral-3 rounded" />
      <div className="h-4 bg-neutral-3 rounded w-1/2" />
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
              className="w-full bg-primary-9 rounded-t"
              style={{
                height: `${(value / maxValue) * 100}%`,
                minHeight: "4px",
              }}
            />
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-neutral-10">
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
          <tr className="border-b border-neutral-5">
            {data.columns.map((column, index) => (
              <th
                key={index}
                className="px-2 py-1 text-left font-medium text-neutral-11"
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
              className="border-b border-neutral-5"
            >
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="px-2 py-1 text-neutral-12"
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
      className="text-sm text-neutral-11 leading-relaxed"
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
        "bg-neutral-1 rounded-lg border border-neutral-5 p-4",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-neutral-12">
          {config.title}
        </h3>
        <Button
          className="p-1 text-neutral-9 hover:text-neutral-11"
          data-testid="refresh-button"
          type="button"
          onClick={() => onRefresh?.(config.id)}
          aria-label="Refresh widget"
        >
          <RefreshCw size={14} />
        </Button>
      </div>
      {/* Content */}
      {isLoading ? (
        <WidgetSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center py-4 text-center">
          <AlertCircle className="w-8 h-8 text-error-9 mb-2" />
          <p className="text-sm text-error-10 dark:text-error-7 mb-2">
            {error}
          </p>
          <Button
            variant="danger"
            size="sm"
            className="px-3 py-1 text-sm bg-error-3 bg-error-4 text-error-10 dark:text-error-7 rounded hover:bg-error-4 dark:hover:bg-error-a6"
            data-testid="retry-button"
            type="button"
            onClick={onRetry}
          >
            Retry
          </Button>
        </div>
      ) : (
        renderContent()
      )}
    </div>
  );
}
