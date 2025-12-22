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
    critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    info: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
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
    positive: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    negative: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    neutral: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        colorClasses[sentiment as keyof typeof colorClasses] || colorClasses.neutral
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
    <div className="p-4 border border-yellow-200 dark:border-yellow-800 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
          {anomaly.dimension}
        </span>
        <SeverityBadge severity={anomaly.severity} />
      </div>
      <p className="text-sm text-gray-900 dark:text-gray-100 mb-2">
        {anomaly.message}
      </p>
      {anomaly.suggestedActions && anomaly.suggestedActions.length > 0 && (
        <div className="mt-2">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Suggested actions:
          </span>
          <ul className="mt-1 text-xs text-gray-600 dark:text-gray-300 list-disc list-inside">
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
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
          {trend.dimension}
        </span>
        <SentimentBadge sentiment={trend.sentiment} />
      </div>
      <p className="text-sm text-gray-900 dark:text-gray-100">
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
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800/50">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
          {pattern.dimension}
        </span>
        {pattern.sentiment && <SentimentBadge sentiment={pattern.sentiment} />}
      </div>
      <p className="text-sm text-gray-900 dark:text-gray-100">
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
    ((prediction.predicted - prediction.current) / prediction.current) * 100
  );
  const isPositive = changePercent > 0;

  return (
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {prediction.metric}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {Math.round(prediction.confidence * 100)}% confidence
        </span>
      </div>
      <div className="flex items-center gap-4 mb-2">
        <div>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Current
          </span>
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {typeof prediction.current === "number" &&
            prediction.current < 1
              ? prediction.current.toFixed(2)
              : prediction.current}
          </p>
        </div>
        <div className="text-gray-400">→</div>
        <div>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Predicted
          </span>
          <p
            className={`text-lg font-semibold ${
              isPositive
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
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
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Drivers:
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {prediction.drivers.map((driver) => (
              <span
                key={driver}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
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
      className={`bg-white dark:bg-gray-900 rounded-lg shadow-sm ${className}`}
      data-testid="ai-insights-panel"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          AI Insights
        </h2>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Last updated: {formatTimestamp(lastUpdated)}
            </span>
          )}
          <button
            onClick={refresh}
            disabled={isLoading}
            className="px-3 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            aria-label="Refresh insights"
          >
            {isLoading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Loading State */}
        {isLoading && !hasInsights && (
          <div className="text-center py-8">
            <div className="animate-pulse text-gray-500 dark:text-gray-400">
              Loading insights...
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-8">
            <div className="text-red-600 dark:text-red-400 mb-4">
              {error.message}
            </div>
            <button
              onClick={refresh}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700"
              aria-label="Retry loading insights"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && !hasInsights && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
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
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
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
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
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
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
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
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
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
