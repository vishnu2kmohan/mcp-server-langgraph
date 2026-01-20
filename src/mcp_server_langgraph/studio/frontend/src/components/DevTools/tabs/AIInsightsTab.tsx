/**
 * AIInsightsTab Component
 *
 * Displays AI-generated insights, anomalies, and suggestions.
 * Uses the useDevToolsAI hook for AI-powered analysis.
 * Phase 8: Integrated with useObservabilityAI for observability insights.
 *
 * Design System Compliance:
 * - Uses CVA for severity and type badge variants
 * - Uses Motion.dev for card and button animations
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import { useState, useMemo, useCallback } from "react";
import {
  RefreshCw,
  X,
  AlertTriangle,
  Zap,
  DollarSign,
  Lightbulb,
  AlertCircle,
  Sparkles,
  Loader2,
  Activity,
  BarChart3,
  Clock,
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  Send,
  History,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import {
  buttonVariants as motionButtonVariants,
  insightCardVariants,
} from "@/design-system/micro-interactions";

import { cn } from "../../../utils/cn";
import { useDevToolsAI } from "../hooks/useDevToolsAI";
import { useObservabilityAI } from "../hooks/useObservabilityAI";
import { useAppSelector } from "../../../store/hooks";
import { selectUser } from "../../../store/slices/authSlice";
import { useStudioAnalyzeMutation } from "../../../api";
import type { AIInsightsTabProps, AIInsight, AIInsightType } from "../types";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";

// =============================================================================
// Types
// =============================================================================

type FilterType = "all" | "anomaly" | "performance" | "cost" | "suggestion";
type ViewMode = "insights" | "observability";

interface NLQueryState {
  query: string;
  isLoading: boolean;
  response: string | null;
  error: string | null;
  history: Array<{ query: string; response: string; timestamp: number }>;
}

// Default suggested queries for NL interface
const SUGGESTED_QUERIES = [
  "What caused the latency spike?",
  "Show me error patterns",
  "Why are costs increasing?",
  "What's the root cause of failures?",
];

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Severity card variants for insight cards
 */
// eslint-disable-next-line react-refresh/only-export-components
export const severityCardVariants = cva(
  "relative border rounded-lg p-3 transition-colors",
  {
    variants: {
      severity: {
        critical: "bg-error-3 dark:bg-error-4 border-error-9 dark:border-error-11",
        high: "bg-warning-3 dark:bg-warning-a4 border-warning-6 dark:border-warning-10",
        medium: "bg-warning-3 dark:bg-warning-3 border-warning-6 dark:border-warning-11",
        low: "bg-primary-3 dark:bg-primary-4 border-primary-5 dark:border-primary-11",
        default: "bg-neutral-2 border-neutral-5",
      },
    },
    defaultVariants: {
      severity: "default",
    },
  },
);

/**
 * Severity indicator bar variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const severityIndicatorVariants = cva(
  "absolute left-0 top-0 bottom-0 w-1 rounded-l-lg",
  {
    variants: {
      severity: {
        critical: "bg-error-9",
        high: "bg-warning-9",
        medium: "bg-warning-9",
        low: "bg-primary-9",
        default: "bg-neutral-5",
      },
    },
    defaultVariants: {
      severity: "default",
    },
  },
);

/**
 * Type badge variants for insight type
 */
// eslint-disable-next-line react-refresh/only-export-components
export const typeBadgeVariants = cva(
  "text-xs px-1.5 py-0.5 rounded-full font-medium",
  {
    variants: {
      type: {
        anomaly: "bg-error-3 dark:bg-error-a6 text-error-11 dark:text-error-9",
        performance: "bg-insight-2 dark:bg-insight-a6 text-insight-11 dark:text-insight-5",
        cost: "bg-success-3 dark:bg-success-a6 text-success-11 dark:text-success-5",
        suggestion: "bg-primary-3 dark:bg-primary-a6 text-primary-11 dark:text-primary-5",
        warning: "bg-warning-3 dark:bg-warning-a6 text-warning-10 dark:text-warning-6",
        default: "bg-neutral-2 text-neutral-11",
      },
    },
    defaultVariants: {
      type: "default",
    },
  },
);

/**
 * Filter button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const filterButtonVariants = cva(
  "px-2 py-1 text-xs rounded transition-colors",
  {
    variants: {
      active: {
        true: "bg-primary-3 dark:bg-primary-4 text-primary-10",
        false: "hover:bg-neutral-3 text-neutral-10",
      },
    },
    defaultVariants: {
      active: false,
    },
  },
);

/**
 * Priority badge variants for suggested actions
 */
// eslint-disable-next-line react-refresh/only-export-components
export const priorityBadgeVariants = cva(
  "px-1.5 py-0.5 rounded text-xs uppercase font-medium",
  {
    variants: {
      priority: {
        high: "bg-error-3 dark:bg-error-a6 text-error-11 dark:text-error-9",
        medium: "bg-warning-3 dark:bg-warning-a6 text-warning-10 dark:text-warning-6",
        low: "bg-primary-3 dark:bg-primary-a6 text-primary-11 dark:text-primary-5",
      },
    },
    defaultVariants: {
      priority: "low",
    },
  },
);

/**
 * Priority action row variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const priorityActionRowVariants = cva(
  "text-xs p-2 rounded flex items-start gap-2",
  {
    variants: {
      priority: {
        high: "bg-error-1 dark:bg-error-a3",
        medium: "bg-warning-3 dark:bg-warning-3",
        low: "bg-primary-1 dark:bg-primary-a3",
      },
    },
    defaultVariants: {
      priority: "low",
    },
  },
);

// =============================================================================
// Utility Functions
// =============================================================================

function getInsightIcon(type: AIInsightType) {
  switch (type) {
    case "anomaly":
      return AlertTriangle;
    case "performance":
      return Zap;
    case "cost":
      return DollarSign;
    case "suggestion":
      return Lightbulb;
    case "warning":
      return AlertCircle;
    default:
      return Sparkles;
  }
}

// =============================================================================
// Subcomponents
// =============================================================================

interface InsightCardProps {
  insight: AIInsight;
  onDismiss: (id: string) => void;
}

function InsightCard({ insight, onDismiss }: InsightCardProps) {
  const prefersReducedMotion = useReducedMotion();
  const [isHovered, setIsHovered] = useState(false);
  const Icon = getInsightIcon(insight.type);

  // Map severity string to CVA variant key
  const severityKey = (["critical", "high", "medium", "low"].includes(insight.severity)
    ? insight.severity
    : "default") as "critical" | "high" | "medium" | "low" | "default";

  // Map type string to CVA variant key
  const typeKey = (["anomaly", "performance", "cost", "suggestion", "warning"].includes(insight.type)
    ? insight.type
    : "default") as "anomaly" | "performance" | "cost" | "suggestion" | "warning" | "default";

  return (
    <motion.div
      data-testid={`ai-insight-${insight.id}`}
      className={severityCardVariants({ severity: severityKey })}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      variants={prefersReducedMotion ? undefined : insightCardVariants}
      initial="rest"
      whileHover="hover"
    >
      {/* Severity indicator */}
      <div
        data-testid={`severity-${insight.id}`}
        data-severity={insight.severity}
        className={severityIndicatorVariants({ severity: severityKey })}
      />
      {/* Header row */}
      <div className="flex items-start gap-2 pl-2">
        <Icon
          size={16}
          className="mt-0.5 flex-shrink-0 text-neutral-11"
        />
        <div className="flex-1 min-w-0">
          {/* Title and badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-neutral-12">
              {insight.title}
            </span>
            <span className={typeBadgeVariants({ type: typeKey })}>
              {insight.type}
            </span>
          </div>

          {/* Description */}
          <p className="text-xs text-neutral-11 mt-1">
            {insight.description}
          </p>

          {/* Suggested action */}
          {insight.suggestedAction && (
            <p className="text-xs text-primary-10 dark:text-primary-7 mt-2 flex items-center gap-1">
              <Lightbulb size={12} />
              {insight.suggestedAction}
            </p>
          )}
        </div>

        {/* Confidence score */}
        <div
          data-testid={`confidence-${insight.id}`}
          className="text-xs text-neutral-10 font-medium"
        >
          {Math.round(insight.confidence * 100)}%
        </div>
      </div>
      {/* Dismiss button (appears on hover) */}
      {isHovered && (
        <motion.button
          type="button"
          data-testid="dismiss-insight-button"
          onClick={() => onDismiss(insight.id)}
          className={cn(
            "absolute top-1 right-1 p-1 rounded",
            "bg-neutral-3",
            "hover:bg-neutral-4",
            "text-neutral-11",
          )}
          aria-label="Dismiss insight"
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover="hover"
          whileTap="pressed"
        >
          <X size={12} />
        </motion.button>
      )}
    </motion.div>
  );
}

interface LayoutSuggestionBannerProps {
  suggestedLayout: string[];
  confidence: number;
  onApply: () => void;
}

function LayoutSuggestionBanner({
  suggestedLayout,
  confidence,
  onApply,
}: LayoutSuggestionBannerProps) {
  return (
    <div
      data-testid="layout-suggestion-banner"
      className={cn(
        "flex items-center justify-between gap-4 p-3 mb-3",
        "bg-primary-1 dark:bg-primary-a3",
        "border border-primary-4 dark:border-primary-11 rounded-lg",
      )}
    >
      <div className="flex items-center gap-2">
        <Sparkles
          size={16}
          className="text-primary-9 dark:text-primary-7"
        />
        <div>
          <p className="text-sm font-medium text-primary-11 dark:text-primary-5">
            AI Layout Suggestion
          </p>
          <p className="text-xs text-primary-10 dark:text-primary-7">
            Confidence: {Math.round(confidence * 100)}% • Suggested:{" "}
            {suggestedLayout.join(", ")}
          </p>
        </div>
      </div>
      <Button variant="primary"
        type="button"
        data-testid="apply-layout-button"
        onClick={onApply}
        className={cn(
          "px-3 py-1.5 text-xs font-medium rounded",
          "bg-primary-9 hover:bg-primary-10",
          "text-neutral-12",
        )}
      >Apply</Button>
    </div>
  );
}

// =============================================================================
// Observability Panel Components
// =============================================================================

import type {
  ObservabilityInsights,
  SuggestedAction,
  PredictiveAlert,
} from "../hooks/useObservabilityAI";

import { Button, Input } from "@/components/UI";

interface ObservabilityPanelProps {
  insights: ObservabilityInsights;
  isAnalyzing: boolean;
}

function ObservabilityPanel({
  insights,
  isAnalyzing,
}: ObservabilityPanelProps) {
  if (isAnalyzing) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary-9" />
      </div>
    );
  }

  return (
    <div data-testid="observability-insights-panel" className="space-y-4">
      {/* Slow Spans Section */}
      {insights.traceAnomalies &&
        insights.traceAnomalies.slowSpans.length > 0 && (
          <div
            data-testid="slow-spans-section"
            className="border rounded-lg p-3"
          >
            <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
              <Clock size={14} />
              Slow Spans ({insights.traceAnomalies.slowSpans.length})
            </h3>
            <div className="space-y-1">
              {insights.traceAnomalies.slowSpans.map((span) => (
                <div
                  key={span.spanId}
                  className="text-xs p-2 bg-grafana-1 dark:bg-grafana-12/20 rounded flex justify-between"
                >
                  <span className="font-mono">{span.name}</span>
                  <span className="text-grafana-10 dark:text-grafana-5">
                    {span.durationMs}ms
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      {/* Error Patterns Section */}
      {insights.traceAnomalies &&
        insights.traceAnomalies.errorPatterns.length > 0 && (
          <div
            data-testid="error-patterns-section"
            className="border rounded-lg p-3"
          >
            <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
              <AlertTriangle size={14} />
              Error Patterns
            </h3>
            <div className="space-y-1">
              {insights.traceAnomalies.errorPatterns.map((pattern) => (
                <div
                  key={pattern.name}
                  className="text-xs p-2 bg-error-1 dark:bg-error-a3 rounded flex justify-between"
                >
                  <span className="font-mono">{pattern.name}</span>
                  <span className={STATUS_TEXT_COLORS.error}>
                    {pattern.count} occurrences
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      {/* Latency Percentiles */}
      {insights.traceAnomalies && (
        <div
          data-testid="latency-percentiles"
          className="border rounded-lg p-3"
        >
          <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
            <BarChart3 size={14} />
            Latency Percentiles
          </h3>
          <div className="flex gap-4 text-xs">
            <div className="flex-1 p-2 bg-neutral-1 rounded text-center">
              <div className="text-neutral-10">p50</div>
              <div className="font-medium">
                p50: {insights.traceAnomalies.percentiles.p50}ms
              </div>
            </div>
            <div className="flex-1 p-2 bg-neutral-1 rounded text-center">
              <div className="text-neutral-10">p95</div>
              <div className="font-medium">
                p95: {insights.traceAnomalies.percentiles.p95}ms
              </div>
            </div>
            <div className="flex-1 p-2 bg-neutral-1 rounded text-center">
              <div className="text-neutral-10">p99</div>
              <div className="font-medium">
                p99: {insights.traceAnomalies.percentiles.p99}ms
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Alert Correlations Section */}
      {insights.alertCorrelations.length > 0 && (
        <div
          data-testid="alert-correlations-section"
          className="border rounded-lg p-3"
        >
          <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
            <Activity size={14} />
            Alert Correlations
          </h3>
          <div className="space-y-2">
            {insights.alertCorrelations.map((correlation, idx) => (
              <div
                key={idx}
                className="text-xs p-2 bg-warning-3 bg-warning-3 rounded"
              >
                <div className="font-medium">
                  {correlation.alerts.length} alerts correlated
                </div>
                <div className="text-neutral-11 mt-1">
                  Services:{" "}
                  {correlation.services.map((s) => (
                    <span
                      key={s}
                      className="inline-block bg-neutral-3 px-1 rounded mr-1"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* Cost Prediction Section */}
      {insights.costPrediction && (
        <div
          data-testid="cost-prediction-section"
          className="border rounded-lg p-3"
        >
          <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
            <DollarSign size={14} />
            Cost Prediction
          </h3>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              {insights.costPrediction.trend === "increasing" && (
                <TrendingUp size={14} className={STATUS_TEXT_COLORS.error} />
              )}
              {insights.costPrediction.trend === "decreasing" && (
                <TrendingDown
                  size={14}
                  className={STATUS_TEXT_COLORS.success}
                />
              )}
              {insights.costPrediction.trend === "stable" && (
                <Minus size={14} className={STATUS_TEXT_COLORS.neutral} />
              )}
              <span className="capitalize">
                {insights.costPrediction.trend}
              </span>
            </div>
            <div>
              Projected: ${insights.costPrediction.projectedDaily.toFixed(2)}
              /day
            </div>
            {insights.costPrediction.anomalies.length > 0 && (
              <div
                data-testid="cost-anomaly-indicator"
                className={cn(
                  STATUS_TEXT_COLORS.error,
                  "flex items-center gap-1",
                )}
              >
                <AlertCircle size={12} />
                {insights.costPrediction.anomalies.length} anomalies
              </div>
            )}
          </div>
        </div>
      )}
      {/* Root Cause Analysis Section */}
      {insights.rootCauseAnalysis && (
        <div
          data-testid="root-cause-analysis-section"
          className="border rounded-lg p-3"
        >
          <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
            <Search size={14} />
            Root Cause Analysis
          </h3>
          <div className="text-xs space-y-2">
            <div className="p-2 bg-insight-1 dark:bg-insight-a3 rounded">
              <div className="flex justify-between">
                <span className="font-medium">Hypothesis</span>
                <span className="text-insight-10">
                  {Math.round(insights.rootCauseAnalysis.confidence * 100)}%
                </span>
              </div>
              <div className="mt-1">
                {insights.rootCauseAnalysis.hypothesis}
              </div>
            </div>
            <div className="space-y-1">
              {insights.rootCauseAnalysis.rootCauses.map((cause, idx) => (
                <div
                  key={idx}
                  data-testid={`root-cause-${idx}`}
                  className="p-2 bg-neutral-1 rounded flex justify-between"
                >
                  <span>{cause.description}</span>
                  <span className="text-neutral-10">
                    {Math.round(cause.likelihood * 100)}%
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-2">
              <div className="text-neutral-10 mb-1">
                Suggested Actions:
              </div>
              {insights.rootCauseAnalysis.suggestedActions.map(
                (action, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-1 text-primary-10 dark:text-primary-7"
                  >
                    <Lightbulb size={12} />
                    {action}
                  </div>
                ),
              )}
            </div>
          </div>
        </div>
      )}
      {/* Predictive Alerts Section */}
      {insights.predictiveAlerts && insights.predictiveAlerts.length > 0 && (
        <div
          data-testid="predictive-alerts-section"
          className="border rounded-lg p-3"
        >
          <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
            <AlertTriangle size={14} />
            Predictive Alerts
          </h3>
          <div className="space-y-2">
            {insights.predictiveAlerts.map((alert: PredictiveAlert) => (
              <div
                key={alert.id}
                data-testid={`predictive-alert-${alert.id}`}
                className={cn(
                  "text-xs p-2 rounded",
                  alert.probability >= 0.9
                    ? "bg-error-3 bg-error-4"
                    : alert.probability >= 0.7
                      ? "bg-warning-3 bg-warning-3"
                      : "bg-warning-3 bg-warning-3",
                )}
              >
                <div className="flex justify-between">
                  <span className="font-medium">{alert.message}</span>
                  <span>
                    {Math.round(alert.probability * 100)}% probability
                  </span>
                </div>
                <div className="text-neutral-11 mt-1">
                  in {Math.round(alert.estimatedTimeToFire / 60000)} minutes
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  className="mt-2 px-2 py-1 text-xs bg-primary-3 bg-primary-4 text-primary-11 dark:text-primary-5 rounded"
                  data-testid={`predictive-alert-action-${alert.id}`}
                >
                  {alert.suggestedAction}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Natural Language Query Components
// =============================================================================

interface NLQueryInputProps {
  state: NLQueryState;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onSuggestionClick: (suggestion: string) => void;
}

function NLQueryInput({
  state,
  onQueryChange,
  onSubmit,
  onSuggestionClick,
}: NLQueryInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="space-y-2 mb-4">
      {/* Query Input */}
      <div className="relative">
        <Input
          data-testid="nl-query-input"
          value={state.query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your traces, alerts, or metrics..."
          className={cn(
            "w-full px-3 py-2 pr-10 text-sm rounded-lg border",
            "bg-neutral-1",
            "border-neutral-5",
            "focus:ring-2 focus:ring-primary-7 focus:border-primary-9",
          )}
        />
        <Button
          onClick={onSubmit}
          disabled={state.isLoading || !state.query.trim()}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded",
            "text-neutral-9 hover:text-primary-9 disabled:opacity-50",
          )}
        >
          {state.isLoading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} />
          )}
        </Button>
      </div>
      {/* Loading State */}
      {state.isLoading && (
        <div
          data-testid="nl-query-loading"
          className="flex items-center gap-2 text-xs text-neutral-10"
        >
          <Loader2 size={12} className="animate-spin" />
          Analyzing...
        </div>
      )}
      {/* Query Response */}
      {state.response && (
        <div
          data-testid="nl-query-response"
          className="p-3 bg-primary-1 dark:bg-primary-a3 rounded-lg text-sm"
        >
          {state.response}
        </div>
      )}
      {/* Error State */}
      {state.error && (
        <div
          data-testid="nl-query-error"
          className="p-3 bg-error-1 dark:bg-error-a3 rounded-lg text-sm text-error-11 dark:text-error-9 flex items-center gap-2"
        >
          <AlertCircle size={16} />
          {state.error}
        </div>
      )}
      {/* Suggested Queries */}
      <div data-testid="nl-query-suggestions" className="flex flex-wrap gap-1">
        {SUGGESTED_QUERIES.map((suggestion) => (
          <Button
            key={suggestion}
            onClick={() => onSuggestionClick(suggestion)}
            className={cn(
              "px-2 py-1 text-xs rounded-full",
              "bg-neutral-2",
              "hover:bg-neutral-3",
              "text-neutral-11",
            )}
          >
            {suggestion}
          </Button>
        ))}
      </div>
      {/* Query History */}
      {state.history.length > 0 && (
        <div data-testid="nl-query-history" className="space-y-1">
          <div className="text-xs text-neutral-10 flex items-center gap-1">
            <History size={12} />
            Recent queries
          </div>
          {state.history.slice(-3).map((item, idx) => (
            <Button
              variant="secondary"
              size="sm"
              className="block w-full text-left text-xs p-1 rounded hover:bg-neutral-2 text-neutral-11"
              key={idx}
              onClick={() => onSuggestionClick(item.query)}
            >
              {item.query}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Suggested Actions Panel
// =============================================================================

interface SuggestedActionsPanelProps {
  actions: SuggestedAction[];
}

function SuggestedActionsPanel({ actions }: SuggestedActionsPanelProps) {
  if (actions.length === 0) return null;

  // Sort by priority
  const sortedActions = [...actions].sort((a, b) => {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  });

  return (
    <div
      data-testid="suggested-actions-panel"
      className="mb-4 border rounded-lg p-3"
    >
      <h3 className="text-sm font-medium text-neutral-11 mb-2 flex items-center gap-2">
        <Lightbulb size={14} />
        Suggested Actions
      </h3>
      <div className="space-y-1">
        {sortedActions.map((action) => (
          <div
            key={action.id}
            data-testid={`suggested-action-${action.id}`}
            data-priority={action.priority}
            className={priorityActionRowVariants({ priority: action.priority })}
          >
            <div className="flex-1">
              <div className="font-medium">{action.title}</div>
              <div className="text-neutral-11">
                {action.description}
              </div>
            </div>
            <span className={priorityBadgeVariants({ priority: action.priority })}>
              {action.priority}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AIInsightsTab({
  context,
  contextEntityId,
  enableObservability = false,
  enableNLQuery = false,
}: AIInsightsTabProps) {
  const prefersReducedMotion = useReducedMotion();
  const [filter, setFilter] = useState<FilterType>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("insights");
  const [nlQueryState, setNLQueryState] = useState<NLQueryState>({
    query: "",
    isLoading: false,
    response: null,
    error: null,
    history: [],
  });

  // Get current user from auth state
  const user = useAppSelector(selectUser);

  // Studio Analyze mutation for NL Query
  const [studioAnalyze] = useStudioAnalyzeMutation();

  const {
    insights,
    suggestedLayout,
    confidence,
    isLoading,
    error,
    dismissInsight,
    applyLayout,
    fetchSuggestions,
  } = useDevToolsAI({
    context,
    entityId: contextEntityId,
    userId: user?.id ?? "anonymous",
    enabled: true,
  });

  // Observability AI hook
  const {
    insights: observabilityInsights,
    suggestedActions: observabilitySuggestedActions,
    isAnalyzing,
    refresh: refreshObservability,
  } = useObservabilityAI({
    enabled: enableObservability,
  });

  // Handle refresh for both AI and observability
  const handleRefresh = useCallback(() => {
    fetchSuggestions();
    if (enableObservability) {
      refreshObservability();
    }
  }, [fetchSuggestions, refreshObservability, enableObservability]);

  // NL Query handlers
  const handleQueryChange = useCallback((query: string) => {
    setNLQueryState((prev) => ({ ...prev, query }));
  }, []);

  const handleQuerySubmit = useCallback(async () => {
    if (!nlQueryState.query.trim()) return;

    setNLQueryState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Build context from observability insights if enabled
      const contextData: Record<string, unknown> = {};
      if (enableObservability && observabilityInsights) {
        contextData.observability = observabilityInsights;
      }

      // Call the studioAnalyze API with NL query task
      const result = await studioAnalyze({
        user_id: user?.id ?? "anonymous",
        session_id: contextEntityId ?? "unknown",
        tasks: [
          {
            category: "TRACE",
            type: "nl_query",
            data: {
              query: nlQueryState.query,
            },
          },
        ],
        context: Object.keys(contextData).length > 0 ? contextData : undefined,
      }).unwrap();

      // Extract response from analysis result
      const traceNlQuery = result.analyses?.trace_nl_query as
        | { response?: string; suggestions?: string[] }
        | undefined;
      const response =
        traceNlQuery?.response ??
        "Analysis complete. No specific insights found.";

      setNLQueryState((prev) => ({
        ...prev,
        isLoading: false,
        response,
        error: null,
        history: [
          ...prev.history,
          { query: prev.query, response, timestamp: Date.now() },
        ],
      }));
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to process query";
      setNLQueryState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
    }
  }, [
    nlQueryState.query,
    studioAnalyze,
    user?.id,
    contextEntityId,
    enableObservability,
    observabilityInsights,
  ]);

  const handleSuggestionClick = useCallback((suggestion: string) => {
    setNLQueryState((prev) => ({ ...prev, query: suggestion }));
  }, []);

  // Filter insights by type
  const filteredInsights = useMemo(() => {
    if (filter === "all") {
      return insights;
    }
    return insights.filter((insight) => insight.type === filter);
  }, [insights, filter]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="ai-insights-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="ai-insights-loading"
          className="flex-1 flex items-center justify-center"
        >
          <Loader2 className="h-6 w-6 animate-spin text-primary-9" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="ai-insights-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="ai-insights-error"
          className={cn(
            "flex-1 flex flex-col items-center justify-center p-4",
            STATUS_TEXT_COLORS.error,
          )}
        >
          <AlertCircle size={32} className="mb-2 opacity-70" />
          <p className="text-sm font-medium">Error loading insights</p>
          <p className="text-xs text-neutral-10 mt-1">
            {error.message}
          </p>
        </div>
      </div>
    );
  }

  // Empty state (only when not in observability mode)
  if (insights.length === 0 && viewMode === "insights") {
    return (
      <div
        data-testid="ai-insights-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
          <h2
            role="heading"
            className="text-sm font-medium text-neutral-11"
          >
            AI Insights
          </h2>
          {enableObservability && (
            <Button
              data-testid="observability-insights-toggle"
              type="button"
              onClick={() => setViewMode("observability")}
              className={cn(
                "px-2 py-1 text-xs rounded flex items-center gap-1",
                "hover:bg-neutral-3 text-neutral-10",
              )}
            >
              <Activity size={12} />
              Observability
            </Button>
          )}
          <div className="flex-1" />
          <Button size="icon"
            variant="secondary"
            className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
            type="button"
            data-testid="refresh-insights-button"
            onClick={handleRefresh}
            aria-label="Refresh insights"
          >
            <RefreshCw size={14} />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {/* NL Query Input (if enabled) */}
          {enableNLQuery && (
            <NLQueryInput
              state={nlQueryState}
              onQueryChange={handleQueryChange}
              onSubmit={handleQuerySubmit}
              onSuggestionClick={handleSuggestionClick}
            />
          )}

          <div
            data-testid="ai-insights-empty"
            className="flex flex-col items-center justify-center text-neutral-9 py-8"
          >
            <Sparkles size={32} className="mb-2 opacity-50" />
            <p className="text-sm">No AI insights</p>
            <p className="text-xs mt-1">AI analysis will appear here</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="ai-insights-tab"
      className="flex flex-col h-full bg-neutral-1"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
        <h2
          role="heading"
          className="text-sm font-medium text-neutral-11"
        >
          AI Insights
        </h2>

        {/* Observability Toggle */}
        {enableObservability && (
          <Button
            data-testid="observability-insights-toggle"
            type="button"
            onClick={() =>
              setViewMode(
                viewMode === "insights" ? "observability" : "insights",
              )
            }
            className={cn(
              "px-2 py-1 text-xs rounded flex items-center gap-1",
              viewMode === "observability"
                ? "bg-primary-3 bg-primary-4 text-primary-10"
                : "hover:bg-neutral-3 text-neutral-10",
            )}
          >
            <Activity size={12} />
            Observability
          </Button>
        )}

        {/* Filter buttons (only show in insights view) */}
        {viewMode === "insights" && (
          <div className="flex items-center gap-1 ml-2">
            <motion.button
              data-testid="filter-all"
              type="button"
              onClick={() => setFilter("all")}
              className={filterButtonVariants({ active: filter === "all" })}
              variants={prefersReducedMotion ? undefined : motionButtonVariants}
              initial="rest"
              whileHover="hover"
              whileTap="pressed"
            >
              All
            </motion.button>
            <motion.button
              data-testid="filter-anomaly"
              type="button"
              onClick={() => setFilter("anomaly")}
              className={filterButtonVariants({ active: filter === "anomaly" })}
              variants={prefersReducedMotion ? undefined : motionButtonVariants}
              initial="rest"
              whileHover="hover"
              whileTap="pressed"
            >
              Anomaly
            </motion.button>
            <motion.button
              data-testid="filter-suggestion"
              type="button"
              onClick={() => setFilter("suggestion")}
              className={filterButtonVariants({ active: filter === "suggestion" })}
              variants={prefersReducedMotion ? undefined : motionButtonVariants}
              initial="rest"
              whileHover="hover"
              whileTap="pressed"
            >
              Suggestion
            </motion.button>
          </div>
        )}

        <div className="flex-1" />

        {/* Refresh button */}
        <Button size="icon"
          variant="secondary"
          className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
          type="button"
          data-testid="refresh-insights-button"
          onClick={handleRefresh}
          aria-label="Refresh insights"
        >
          <RefreshCw size={14} />
        </Button>

        {/* Insight count */}
        <span className="text-xs text-neutral-10">
          {filteredInsights.length} insight
          {filteredInsights.length !== 1 ? "s" : ""}
        </span>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-2">
        {/* NL Query Input (if enabled) */}
        {enableNLQuery && (
          <NLQueryInput
            state={nlQueryState}
            onQueryChange={handleQueryChange}
            onSubmit={handleQuerySubmit}
            onSuggestionClick={handleSuggestionClick}
          />
        )}

        {/* Suggested Actions Panel (from observability) */}
        {enableObservability && observabilitySuggestedActions.length > 0 && (
          <SuggestedActionsPanel actions={observabilitySuggestedActions} />
        )}

        {/* Observability Panel (when in observability mode) */}
        {viewMode === "observability" && enableObservability && (
          <ObservabilityPanel
            insights={observabilityInsights}
            isAnalyzing={isAnalyzing}
          />
        )}

        {/* Regular Insights View */}
        {viewMode === "insights" && (
          <>
            {/* Layout suggestion banner */}
            {suggestedLayout && (
              <LayoutSuggestionBanner
                suggestedLayout={suggestedLayout}
                confidence={confidence}
                onApply={applyLayout}
              />
            )}

            {/* Insights list */}
            <div className="space-y-2">
              {filteredInsights.map((insight) => (
                <InsightCard
                  key={insight.id}
                  insight={insight}
                  onDismiss={dismissInsight}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AIInsightsTab;
