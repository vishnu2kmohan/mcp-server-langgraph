/**
 * AIInsightsPanel Component
 *
 * Displays AI-generated HEART metrics insights.
 * Phase 6.6: Analytics Dashboard Component
 *
 * Features:
 * - Insights categorized by type (anomaly, trend, pattern)
 * - Predictions with confidence indicators
 * - Severity and sentiment indicators
 * - Suggested actions for anomalies
 * - Refresh capability
 * - Last updated tracking
 *
 * @example
 * ```tsx
 * <AIInsightsPanel />
 * ```
 */

import {
  useAIMetricsInsights,
  type AnomalyInsight,
  type TrendInsight,
  type PatternInsight,
  type Prediction,
} from "../../hooks/useAIMetricsInsights";

import { Button } from "@/components/UI";

/**
 * Props for the panel
 */
export interface AIInsightsPanelProps {
  /** Optional CSS class name */
  className?: string;
  /** Polling interval for auto-refresh (default: no polling) */
  pollingIntervalMs?: number;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(date: Date | null): string {
  if (!date) return "Never";
  return date.toLocaleString();
}

/**
 * Severity badge component
 */
function SeverityBadge({ severity }: { severity: string }) {
  const colorClasses = {
    critical:
      "bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200",
    warning:
      "bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200",
    info: "bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        colorClasses[severity as keyof typeof colorClasses] || colorClasses.info
      }`}
    >
      {severity}
    </span>
  );
}

/**
 * Sentiment badge component
 */
function SentimentBadge({ sentiment }: { sentiment: string }) {
  const colorClasses = {
    positive:
      "bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200",
    negative:
      "bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200",
    neutral:
      "bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:bg-neutral-700 dark:text-neutral-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        colorClasses[sentiment as keyof typeof colorClasses] ||
        colorClasses.neutral
      }`}
    >
      {sentiment}
    </span>
  );
}

/**
 * Anomaly card component
 */
function AnomalyCard({ anomaly }: { anomaly: AnomalyInsight }) {
  return (
    <div className="p-4 border border-warning-200 dark:border-warning-800 rounded-lg bg-warning-50 dark:bg-warning-900/20">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
          {anomaly.dimension}
        </span>
        <SeverityBadge severity={anomaly.severity} />
      </div>
      <p className="text-sm text-neutral-900 dark:text-neutral-100 mb-2">
        {anomaly.message}
      </p>
      {anomaly.suggestedActions && anomaly.suggestedActions.length > 0 && (
        <div className="mt-2">
          <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
            Suggested actions:
          </span>
          <ul className="mt-1 text-xs text-neutral-600 dark:text-neutral-300 list-disc list-inside">
            {anomaly.suggestedActions.map((action, idx) => (
              <li key={idx}>{action}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/**
 * Trend card component
 */
function TrendCard({ trend }: { trend: TrendInsight }) {
  return (
    <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
          {trend.dimension}
        </span>
        <SentimentBadge sentiment={trend.sentiment} />
      </div>
      <p className="text-sm text-neutral-900 dark:text-neutral-100">
        {trend.message}
      </p>
    </div>
  );
}

/**
 * Pattern card component
 */
function PatternCard({ pattern }: { pattern: PatternInsight }) {
  return (
    <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50 dark:bg-neutral-800/50">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
          {pattern.dimension}
        </span>
        {pattern.sentiment && <SentimentBadge sentiment={pattern.sentiment} />}
      </div>
      <p className="text-sm text-neutral-900 dark:text-neutral-100">
        {pattern.message}
      </p>
    </div>
  );
}

/**
 * Prediction card component
 */
function PredictionCard({ prediction }: { prediction: Prediction }) {
  const changePercent = Math.round(
    ((prediction.predicted - prediction.current) / prediction.current) * 100,
  );
  const isPositive = changePercent > 0;

  return (
    <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {prediction.metric}
        </span>
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          {Math.round(prediction.confidence * 100)}% confidence
        </span>
      </div>
      <div className="flex items-center gap-4 mb-2">
        <div>
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            Current
          </span>
          <p className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
            {typeof prediction.current === "number" && prediction.current < 1
              ? prediction.current.toFixed(2)
              : prediction.current}
          </p>
        </div>
        <div className="text-neutral-400 dark:text-neutral-400">→</div>
        <div>
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            Predicted
          </span>
          <p
            className={`text-lg font-semibold ${
              isPositive
                ? "text-success-600 dark:text-success-400"
                : "text-error-600 dark:text-error-400"
            }`}
          >
            {typeof prediction.predicted === "number" &&
            prediction.predicted < 1
              ? prediction.predicted.toFixed(2)
              : prediction.predicted}
            <span className="text-sm ml-1">
              ({isPositive ? "+" : ""}
              {changePercent}%)
            </span>
          </p>
        </div>
      </div>
      {prediction.drivers.length > 0 && (
        <div className="mt-2">
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            Drivers:
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {prediction.drivers.map((driver) => (
              <span
                key={driver}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300"
              >
                {driver}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Main AIInsightsPanel component
 */
export function AIInsightsPanel({
  className = "",
  pollingIntervalMs,
}: AIInsightsPanelProps) {
  const {
    anomalies,
    trends,
    patterns,
    predictions,
    isLoading,
    error,
    lastUpdated,
    refresh,
  } = useAIMetricsInsights({
    enabled: true,
    pollingIntervalMs,
  });

  const hasInsights =
    anomalies.length > 0 ||
    trends.length > 0 ||
    patterns.length > 0 ||
    predictions.length > 0;

  return (
    <div
      className={`bg-white dark:bg-neutral-900 rounded-lg shadow-sm ${className}`}
      data-testid="ai-insights-panel"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          AI Insights
        </h2>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-neutral-500 dark:text-neutral-400">
              Last updated: {formatTimestamp(lastUpdated)}
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            className="px-3 py-1 text-sm text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-700 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600"
            onClick={refresh}
            disabled={isLoading}
            aria-label="Refresh insights"
          >
            {isLoading ? "Loading..." : "Refresh"}
          </Button>
        </div>
      </div>
      {/* Content */}
      <div className="p-4">
        {/* Loading State */}
        {isLoading && !hasInsights && (
          <div className="text-center py-8">
            <div className="animate-pulse text-neutral-500 dark:text-neutral-400">
              Loading insights...
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-8">
            <div className="text-error-600 dark:text-error-400 mb-4">
              {error.message}
            </div>
            <Button
              variant="danger"
              className="px-4 py-2 text-sm text-white bg-error-600 rounded hover:bg-error-700"
              onClick={refresh}
              aria-label="Retry loading insights"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && !hasInsights && (
          <div className="text-center py-8 text-neutral-500 dark:text-neutral-400">
            No insights available yet. Check back later for AI-generated
            analytics.
          </div>
        )}

        {/* Insights */}
        {hasInsights && (
          <div className="space-y-6">
            {/* Anomalies */}
            {anomalies.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
                  Anomalies ({anomalies.length})
                </h3>
                <div className="space-y-3">
                  {anomalies.map((anomaly, idx) => (
                    <AnomalyCard key={idx} anomaly={anomaly} />
                  ))}
                </div>
              </section>
            )}

            {/* Trends */}
            {trends.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
                  Trends ({trends.length})
                </h3>
                <div className="space-y-3">
                  {trends.map((trend, idx) => (
                    <TrendCard key={idx} trend={trend} />
                  ))}
                </div>
              </section>
            )}

            {/* Patterns */}
            {patterns.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
                  Patterns ({patterns.length})
                </h3>
                <div className="space-y-3">
                  {patterns.map((pattern, idx) => (
                    <PatternCard key={idx} pattern={pattern} />
                  ))}
                </div>
              </section>
            )}

            {/* Predictions */}
            {predictions.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
                  Predictions ({predictions.length})
                </h3>
                <div className="space-y-3">
                  {predictions.map((prediction, idx) => (
                    <PredictionCard key={idx} prediction={prediction} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default AIInsightsPanel;
