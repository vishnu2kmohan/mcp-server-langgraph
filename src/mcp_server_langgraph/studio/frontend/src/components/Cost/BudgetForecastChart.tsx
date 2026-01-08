/**
 * BudgetForecastChart
 *
 * Component for visualizing cost forecasts with confidence ranges.
 * Shows projected spend, trend indicators, and budget warnings.
 */

import { TrendingUp, TrendingDown, Minus, AlertTriangle } from "lucide-react";
import { Skeleton } from "../UI";

export type TrendType = "increasing" | "decreasing" | "stable";

export interface CostForecast {
  projectedTotal: string;
  confidenceLow: string;
  confidenceHigh: string;
  trend: TrendType;
  daysAnalyzed: number;
  message: string;
  monthlyLimit: string;
}

export interface BudgetForecastChartProps {
  /** Forecast data */
  forecast: CostForecast | null;
  /** Loading state */
  loading?: boolean;
  /** Additional class name */
  className?: string;
}

/** Format currency */
function formatCurrency(value: string): string {
  const num = parseFloat(value);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(num);
}

/** Get trend icon component */
function TrendIcon({ trend }: { trend: TrendType }) {
  const className = "w-4 h-4 inline-block mr-1";

  switch (trend) {
    case "increasing":
      return <TrendingUp className={`${className} text-warning-500`} />;
    case "decreasing":
      return <TrendingDown className={`${className} text-success-500`} />;
    case "stable":
      return (
        <Minus className={`${className} text-gray-500 dark:text-gray-400`} />
      );
  }
}

/** Get trend styling */
function getTrendStyles(trend: TrendType): {
  textColor: string;
  bgColor: string;
} {
  switch (trend) {
    case "increasing":
      return {
        textColor: "text-warning-600 dark:text-warning-400",
        bgColor: "bg-warning-100 dark:bg-warning-900/30",
      };
    case "decreasing":
      return {
        textColor: "text-success-600 dark:text-success-400",
        bgColor: "bg-success-100 dark:bg-success-900/30",
      };
    case "stable":
      return {
        textColor: "text-gray-600 dark:text-gray-400",
        bgColor: "bg-gray-100 dark:bg-gray-800",
      };
  }
}

export function BudgetForecastChart({
  forecast,
  loading = false,
  className = "",
}: BudgetForecastChartProps) {
  // Loading skeleton
  if (loading || !forecast) {
    return (
      <div
        data-testid="budget-forecast-skeleton"
        className={`p-6 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}
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
    );
  }

  const projectedNum = parseFloat(forecast.projectedTotal);
  const limitNum = parseFloat(forecast.monthlyLimit);
  const lowNum = parseFloat(forecast.confidenceLow);
  const highNum = parseFloat(forecast.confidenceHigh);

  const projectedPercent =
    limitNum > 0 ? Math.round((projectedNum / limitNum) * 100) : 0;
  const isOverBudget = projectedNum > limitNum;
  const trendStyles = getTrendStyles(forecast.trend);

  // Empty state
  if (forecast.daysAnalyzed === 0) {
    return (
      <div
        data-testid="budget-forecast-chart"
        className={`p-6 rounded-lg border border-gray-200 dark:border-gray-700 ${className}`}
      >
        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
          <p className="text-lg">No data available for forecasting</p>
          <p className="text-sm mt-2">
            Cost data will appear here once usage is recorded.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="budget-forecast-chart"
      className={`p-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Cost Forecast
        </h3>
        <span
          className={`text-sm font-medium px-2 py-1 rounded ${trendStyles.textColor} ${trendStyles.bgColor}`}
        >
          <TrendIcon trend={forecast.trend} />
          {forecast.trend.charAt(0).toUpperCase() + forecast.trend.slice(1)}
        </span>
      </div>

      {/* Days analyzed */}
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Based on {forecast.daysAnalyzed} days of data
      </p>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-1">
          <span>Projected</span>
          <span>Budget Limit: {formatCurrency(forecast.monthlyLimit)}</span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={projectedPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          className="w-full h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden relative"
        >
          {/* Confidence range band */}
          <div
            data-testid="confidence-range"
            className="absolute h-full bg-primary-200 dark:bg-primary-800 opacity-50"
            style={{
              left: `${Math.max(0, (lowNum / limitNum) * 100)}%`,
              width: `${Math.min(100, ((highNum - lowNum) / limitNum) * 100)}%`,
            }}
          />
          {/* Projected bar */}
          <div
            className={`h-full transition-all duration-300 ${
              isOverBudget ? "bg-error-500" : "bg-primary-500"
            }`}
            style={{ width: `${Math.min(projectedPercent, 100)}%` }}
          />
          {/* Budget limit marker */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-gray-800 dark:bg-gray-300 dark:bg-gray-600"
            style={{ left: "100%" }}
          />
        </div>
      </div>

      {/* Projections */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            Low Estimate
          </p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            {formatCurrency(forecast.confidenceLow)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            Projected
          </p>
          <p
            className={`text-2xl font-bold ${
              isOverBudget
                ? "text-error-600 dark:text-error-400"
                : "text-primary-600 dark:text-primary-400"
            }`}
          >
            {formatCurrency(forecast.projectedTotal)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            High Estimate
          </p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            {formatCurrency(forecast.confidenceHigh)}
          </p>
        </div>
      </div>

      {/* Over budget warning */}
      {isOverBudget && (
        <div
          data-testid="over-budget-warning"
          className="flex items-center gap-2 p-3 rounded bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800"
        >
          <AlertTriangle className="w-5 h-5 text-error-500" />
          <p className="text-sm text-error-700 dark:text-error-400">
            Projected spend exceeds monthly budget by{" "}
            {formatCurrency((projectedNum - limitNum).toString())}
          </p>
        </div>
      )}

      {/* Forecast message */}
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-4 text-center">
        {forecast.message}
      </p>
    </div>
  );
}

export default BudgetForecastChart;
