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

import { useReducedMotion } from "motion/react";
import {
  useAIMetricsInsights,
  type AnomalyInsight,
  type TrendInsight,
  type PatternInsight,
  type Prediction,
} from "../../hooks/useAIMetricsInsights";

import { Button } from "@/components/UI";
import { cn } from "../../utils/cn";

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
      "bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-4",
    warning:
      "bg-warning-3 text-warning-11 dark:bg-warning-12 dark:text-warning-6",
    info: "bg-primary-3 text-primary-11 dark:bg-primary-12 dark:text-primary-4",
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
      "bg-success-3 text-success-11 dark:bg-success-12 dark:text-success-4",
    negative:
      "bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-4",
    neutral:
      "bg-neutral-2 text-neutral-12",
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
    <div className="p-4 border border-warning-6 dark:border-warning-11 rounded-lg bg-warning-3 bg-warning-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-11">
          {anomaly.dimension}
        </span>
        <SeverityBadge severity={anomaly.severity} />
      </div>
      <p className="text-sm text-neutral-12 mb-2">
        {anomaly.message}
      </p>
      {anomaly.suggestedActions && anomaly.suggestedActions.length > 0 && (
        <div className="mt-2">
          <span className="text-xs font-medium text-neutral-10">
            Suggested actions:
          </span>
          <ul className="mt-1 text-xs text-neutral-11 list-disc list-inside">
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
    <div className="p-4 border border-neutral-5 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-11">
          {trend.dimension}
        </span>
        <SentimentBadge sentiment={trend.sentiment} />
      </div>
      <p className="text-sm text-neutral-12">
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
    <div className="p-4 border border-neutral-5 rounded-lg bg-neutral-1">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-11">
          {pattern.dimension}
        </span>
        {pattern.sentiment && <SentimentBadge sentiment={pattern.sentiment} />}
      </div>
      <p className="text-sm text-neutral-12">
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
    <div className="p-4 border border-neutral-5 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-neutral-12">
          {prediction.metric}
        </span>
        <span className="text-xs text-neutral-10">
          {Math.round(prediction.confidence * 100)}% confidence
        </span>
      </div>
      <div className="flex items-center gap-4 mb-2">
        <div>
          <span className="text-xs text-neutral-10">
            Current
          </span>
          <p className="text-lg font-semibold text-neutral-12">
            {typeof prediction.current === "number" && prediction.current < 1
              ? prediction.current.toFixed(2)
              : prediction.current}
          </p>
        </div>
        <div className="text-neutral-9">→</div>
        <div>
          <span className="text-xs text-neutral-10">
            Predicted
          </span>
          <p
            className={`text-lg font-semibold ${
              isPositive
                ? "text-success-10 dark:text-success-7"
                : "text-error-10 dark:text-error-7"
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
          <span className="text-xs text-neutral-10">
            Drivers:
          </span>
          <div className="flex flex-wrap gap-1 mt-1">
            {prediction.drivers.map((driver) => (
              <span
                key={driver}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-neutral-2 text-neutral-11"
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

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
      className={`bg-neutral-1 rounded-lg shadow-sm ${className}`}
      data-testid="ai-insights-panel"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-5 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-12">
          AI Insights
        </h2>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-neutral-10">
              Last updated: {formatTimestamp(lastUpdated)}
            </span>
          )}
          <Button
            variant="secondary"
            size="sm"
            className="px-3 py-1 text-sm text-neutral-11 bg-neutral-2 rounded hover:bg-neutral-3"
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
            <div className={cn("text-neutral-10", !prefersReducedMotion && "animate-pulse")}>
              Loading insights...
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-8">
            <div className="text-error-10 dark:text-error-7 mb-4">
              {error.message}
            </div>
            <Button
              variant="danger"
              className="px-4 py-2 text-sm text-neutral-12 bg-error-10 rounded hover:bg-error-11"
              onClick={refresh}
              aria-label="Retry loading insights"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && !hasInsights && (
          <div className="text-center py-8 text-neutral-10">
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
                <h3 className="text-sm font-semibold text-neutral-11 mb-3">
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
                <h3 className="text-sm font-semibold text-neutral-11 mb-3">
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
                <h3 className="text-sm font-semibold text-neutral-11 mb-3">
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
                <h3 className="text-sm font-semibold text-neutral-11 mb-3">
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
