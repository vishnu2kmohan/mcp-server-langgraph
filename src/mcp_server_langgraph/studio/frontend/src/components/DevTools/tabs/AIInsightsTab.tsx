/**
 * AIInsightsTab Component
 *
 * Displays AI-generated insights, anomalies, and suggestions.
 * Uses the useDevToolsAI hook for AI-powered analysis.
 * Phase 8: Integrated with useObservabilityAI for observability insights.
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

import { cn } from "../../../utils/cn";
import { useDevToolsAI } from "../hooks/useDevToolsAI";
import { useObservabilityAI } from "../hooks/useObservabilityAI";
import { useAppSelector } from "../../../store/hooks";
import { selectUser } from "../../../store/slices/authSlice";
import type { AIInsightsTabProps, AIInsight, AIInsightType } from "../types";

// =============================================================================
// Types
// =============================================================================

type FilterType = "all" | "anomaly" | "performance" | "cost" | "suggestion";
type ViewMode = "insights" | "observability";

interface NLQueryState {
  query: string;
  isLoading: boolean;
  response: string | null;
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

function getSeverityColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700";
    case "high":
      return "bg-orange-100 dark:bg-orange-900/30 border-orange-300 dark:border-orange-700";
    case "medium":
      return "bg-amber-100 dark:bg-amber-900/30 border-amber-300 dark:border-amber-700";
    case "low":
      return "bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700";
    default:
      return "bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600";
  }
}

function getSeverityIndicatorColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "bg-red-500";
    case "high":
      return "bg-orange-500";
    case "medium":
      return "bg-amber-500";
    case "low":
      return "bg-blue-500";
    default:
      return "bg-gray-500";
  }
}

function getTypeBadgeColor(type: AIInsightType): string {
  switch (type) {
    case "anomaly":
      return "bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300";
    case "performance":
      return "bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300";
    case "cost":
      return "bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300";
    case "suggestion":
      return "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300";
    case "warning":
      return "bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300";
    default:
      return "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300";
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
  const [isHovered, setIsHovered] = useState(false);
  const Icon = getInsightIcon(insight.type);

  return (
    <div
      data-testid={`ai-insight-${insight.id}`}
      className={cn(
        "relative border rounded-lg p-3 transition-colors",
        getSeverityColor(insight.severity),
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Severity indicator */}
      <div
        data-testid={`severity-${insight.id}`}
        data-severity={insight.severity}
        className={cn(
          "absolute left-0 top-0 bottom-0 w-1 rounded-l-lg",
          getSeverityIndicatorColor(insight.severity),
        )}
      />

      {/* Header row */}
      <div className="flex items-start gap-2 pl-2">
        <Icon
          size={16}
          className="mt-0.5 flex-shrink-0 text-gray-600 dark:text-gray-400"
        />
        <div className="flex-1 min-w-0">
          {/* Title and badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-gray-800 dark:text-gray-200">
              {insight.title}
            </span>
            <span
              className={cn(
                "text-xs px-1.5 py-0.5 rounded-full font-medium",
                getTypeBadgeColor(insight.type),
              )}
            >
              {insight.type}
            </span>
          </div>

          {/* Description */}
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            {insight.description}
          </p>

          {/* Suggested action */}
          {insight.suggestedAction && (
            <p className="text-xs text-primary-600 dark:text-primary-400 mt-2 flex items-center gap-1">
              <Lightbulb size={12} />
              {insight.suggestedAction}
            </p>
          )}
        </div>

        {/* Confidence score */}
        <div
          data-testid={`confidence-${insight.id}`}
          className="text-xs text-gray-500 dark:text-gray-400 font-medium"
        >
          {Math.round(insight.confidence * 100)}%
        </div>
      </div>

      {/* Dismiss button (appears on hover) */}
      {isHovered && (
        <button
          type="button"
          data-testid="dismiss-insight-button"
          onClick={() => onDismiss(insight.id)}
          className={cn(
            "absolute top-1 right-1 p-1 rounded",
            "bg-gray-200/80 dark:bg-gray-700/80",
            "hover:bg-gray-300 dark:hover:bg-gray-600",
            "text-gray-600 dark:text-gray-400",
          )}
          aria-label="Dismiss insight"
        >
          <X size={12} />
        </button>
      )}
    </div>
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
        "bg-primary-50 dark:bg-primary-900/20",
        "border border-primary-200 dark:border-primary-700 rounded-lg",
      )}
    >
      <div className="flex items-center gap-2">
        <Sparkles
          size={16}
          className="text-primary-500 dark:text-primary-400"
        />
        <div>
          <p className="text-sm font-medium text-primary-700 dark:text-primary-300">
            AI Layout Suggestion
          </p>
          <p className="text-xs text-primary-600 dark:text-primary-400">
            Confidence: {Math.round(confidence * 100)}% • Suggested:{" "}
            {suggestedLayout.join(", ")}
          </p>
        </div>
      </div>
      <button
        type="button"
        data-testid="apply-layout-button"
        onClick={onApply}
        className={cn(
          "px-3 py-1.5 text-xs font-medium rounded",
          "bg-primary-500 hover:bg-primary-600",
          "text-white",
        )}
      >
        Apply
      </button>
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
        <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
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
            className="border rounded-lg p-3 dark:border-gray-700"
          >
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
              <Clock size={14} />
              Slow Spans ({insights.traceAnomalies.slowSpans.length})
            </h3>
            <div className="space-y-1">
              {insights.traceAnomalies.slowSpans.map((span) => (
                <div
                  key={span.span_id}
                  className="text-xs p-2 bg-orange-50 dark:bg-orange-900/20 rounded flex justify-between"
                >
                  <span className="font-mono">{span.name}</span>
                  <span className="text-orange-600 dark:text-orange-400">
                    {span.duration_ms}ms
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
            className="border rounded-lg p-3 dark:border-gray-700"
          >
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
              <AlertTriangle size={14} />
              Error Patterns
            </h3>
            <div className="space-y-1">
              {insights.traceAnomalies.errorPatterns.map((pattern) => (
                <div
                  key={pattern.name}
                  className="text-xs p-2 bg-red-50 dark:bg-red-900/20 rounded flex justify-between"
                >
                  <span className="font-mono">{pattern.name}</span>
                  <span className="text-red-600 dark:text-red-400">
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
          className="border rounded-lg p-3 dark:border-gray-700"
        >
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <BarChart3 size={14} />
            Latency Percentiles
          </h3>
          <div className="flex gap-4 text-xs">
            <div className="flex-1 p-2 bg-gray-50 dark:bg-gray-800 rounded text-center">
              <div className="text-gray-500">p50</div>
              <div className="font-medium">
                p50: {insights.traceAnomalies.percentiles.p50}ms
              </div>
            </div>
            <div className="flex-1 p-2 bg-gray-50 dark:bg-gray-800 rounded text-center">
              <div className="text-gray-500">p95</div>
              <div className="font-medium">
                p95: {insights.traceAnomalies.percentiles.p95}ms
              </div>
            </div>
            <div className="flex-1 p-2 bg-gray-50 dark:bg-gray-800 rounded text-center">
              <div className="text-gray-500">p99</div>
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
          className="border rounded-lg p-3 dark:border-gray-700"
        >
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <Activity size={14} />
            Alert Correlations
          </h3>
          <div className="space-y-2">
            {insights.alertCorrelations.map((correlation, idx) => (
              <div
                key={idx}
                className="text-xs p-2 bg-amber-50 dark:bg-amber-900/20 rounded"
              >
                <div className="font-medium">
                  {correlation.alerts.length} alerts correlated
                </div>
                <div className="text-gray-600 dark:text-gray-400 mt-1">
                  Services:{" "}
                  {correlation.services.map((s) => (
                    <span
                      key={s}
                      className="inline-block bg-gray-200 dark:bg-gray-700 px-1 rounded mr-1"
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
          className="border rounded-lg p-3 dark:border-gray-700"
        >
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <DollarSign size={14} />
            Cost Prediction
          </h3>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              {insights.costPrediction.trend === "increasing" && (
                <TrendingUp size={14} className="text-red-500" />
              )}
              {insights.costPrediction.trend === "decreasing" && (
                <TrendingDown size={14} className="text-green-500" />
              )}
              {insights.costPrediction.trend === "stable" && (
                <Minus size={14} className="text-gray-500" />
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
                className="text-red-500 flex items-center gap-1"
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
          className="border rounded-lg p-3 dark:border-gray-700"
        >
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
            <Search size={14} />
            Root Cause Analysis
          </h3>
          <div className="text-xs space-y-2">
            <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded">
              <div className="flex justify-between">
                <span className="font-medium">Hypothesis</span>
                <span className="text-purple-600">
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
                  className="p-2 bg-gray-50 dark:bg-gray-800 rounded flex justify-between"
                >
                  <span>{cause.description}</span>
                  <span className="text-gray-500">
                    {Math.round(cause.likelihood * 100)}%
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-2">
              <div className="text-gray-500 mb-1">Suggested Actions:</div>
              {insights.rootCauseAnalysis.suggestedActions.map(
                (action, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-1 text-primary-600 dark:text-primary-400"
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
          className="border rounded-lg p-3 dark:border-gray-700"
        >
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
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
                    ? "bg-red-100 dark:bg-red-900/30"
                    : alert.probability >= 0.7
                      ? "bg-orange-50 dark:bg-orange-900/20"
                      : "bg-yellow-50 dark:bg-yellow-900/20",
                )}
              >
                <div className="flex justify-between">
                  <span className="font-medium">{alert.message}</span>
                  <span>
                    {Math.round(alert.probability * 100)}% probability
                  </span>
                </div>
                <div className="text-gray-600 dark:text-gray-400 mt-1">
                  in {Math.round(alert.estimatedTimeToFire / 60000)} minutes
                </div>
                <button
                  data-testid={`predictive-alert-action-${alert.id}`}
                  className="mt-2 px-2 py-1 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded"
                >
                  {alert.suggestedAction}
                </button>
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
        <input
          data-testid="nl-query-input"
          type="text"
          value={state.query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your traces, alerts, or metrics..."
          className={cn(
            "w-full px-3 py-2 pr-10 text-sm rounded-lg border",
            "bg-white dark:bg-gray-800",
            "border-gray-300 dark:border-gray-600",
            "focus:ring-2 focus:ring-primary-500 focus:border-primary-500",
          )}
        />
        <button
          onClick={onSubmit}
          disabled={state.isLoading || !state.query.trim()}
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded",
            "text-gray-400 hover:text-primary-500 disabled:opacity-50",
          )}
        >
          {state.isLoading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </div>

      {/* Loading State */}
      {state.isLoading && (
        <div
          data-testid="nl-query-loading"
          className="flex items-center gap-2 text-xs text-gray-500"
        >
          <Loader2 size={12} className="animate-spin" />
          Analyzing...
        </div>
      )}

      {/* Query Response */}
      {state.response && (
        <div
          data-testid="nl-query-response"
          className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg text-sm"
        >
          {state.response}
        </div>
      )}

      {/* Suggested Queries */}
      <div data-testid="nl-query-suggestions" className="flex flex-wrap gap-1">
        {SUGGESTED_QUERIES.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestionClick(suggestion)}
            className={cn(
              "px-2 py-1 text-xs rounded-full",
              "bg-gray-100 dark:bg-gray-700",
              "hover:bg-gray-200 dark:hover:bg-gray-600",
              "text-gray-600 dark:text-gray-400",
            )}
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* Query History */}
      {state.history.length > 0 && (
        <div data-testid="nl-query-history" className="space-y-1">
          <div className="text-xs text-gray-500 flex items-center gap-1">
            <History size={12} />
            Recent queries
          </div>
          {state.history.slice(-3).map((item, idx) => (
            <button
              key={idx}
              onClick={() => onSuggestionClick(item.query)}
              className="block w-full text-left text-xs p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
            >
              {item.query}
            </button>
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
      className="mb-4 border rounded-lg p-3 dark:border-gray-700"
    >
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
        <Lightbulb size={14} />
        Suggested Actions
      </h3>
      <div className="space-y-1">
        {sortedActions.map((action) => (
          <div
            key={action.id}
            data-testid={`suggested-action-${action.id}`}
            data-priority={action.priority}
            className={cn(
              "text-xs p-2 rounded flex items-start gap-2",
              action.priority === "high" && "bg-red-50 dark:bg-red-900/20",
              action.priority === "medium" &&
                "bg-yellow-50 dark:bg-yellow-900/20",
              action.priority === "low" && "bg-blue-50 dark:bg-blue-900/20",
            )}
          >
            <div className="flex-1">
              <div className="font-medium">{action.title}</div>
              <div className="text-gray-600 dark:text-gray-400">
                {action.description}
              </div>
            </div>
            <span
              className={cn(
                "px-1.5 py-0.5 rounded text-[10px] uppercase",
                action.priority === "high" &&
                  "bg-red-200 dark:bg-red-800 text-red-700 dark:text-red-300",
                action.priority === "medium" &&
                  "bg-yellow-200 dark:bg-yellow-800 text-yellow-700 dark:text-yellow-300",
                action.priority === "low" &&
                  "bg-blue-200 dark:bg-blue-800 text-blue-700 dark:text-blue-300",
              )}
            >
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
  const [filter, setFilter] = useState<FilterType>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("insights");
  const [nlQueryState, setNLQueryState] = useState<NLQueryState>({
    query: "",
    isLoading: false,
    response: null,
    history: [],
  });

  // Get current user from auth state
  const user = useAppSelector(selectUser);

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

  const handleQuerySubmit = useCallback(() => {
    if (!nlQueryState.query.trim()) return;

    setNLQueryState((prev) => ({ ...prev, isLoading: true }));

    // Simulate AI response (in production, this would call an API)
    setTimeout(() => {
      const response = `Based on the analysis of your traces and metrics, ${nlQueryState.query.toLowerCase().includes("error") ? "the primary error patterns appear in the api.request and auth.validate operations." : nlQueryState.query.toLowerCase().includes("cost") ? "token usage is trending upward with projected daily costs of $25.50." : "I found several slow operations in the db.query and llm.completion spans."}`;

      setNLQueryState((prev) => ({
        ...prev,
        isLoading: false,
        response,
        history: [
          ...prev.history,
          { query: prev.query, response, timestamp: Date.now() },
        ],
      }));
    }, 1000);
  }, [nlQueryState.query]);

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
        className="flex flex-col h-full bg-white dark:bg-gray-900"
      >
        <div
          data-testid="ai-insights-loading"
          className="flex-1 flex items-center justify-center"
        >
          <Loader2 className="h-6 w-6 animate-spin text-primary-500" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="ai-insights-tab"
        className="flex flex-col h-full bg-white dark:bg-gray-900"
      >
        <div
          data-testid="ai-insights-error"
          className="flex-1 flex flex-col items-center justify-center text-red-500 dark:text-red-400 p-4"
        >
          <AlertCircle size={32} className="mb-2 opacity-70" />
          <p className="text-sm font-medium">Error loading insights</p>
          <p className="text-xs text-gray-500 mt-1">{error.message}</p>
        </div>
      </div>
    );
  }

  // Empty state (only when not in observability mode)
  if (insights.length === 0 && viewMode === "insights") {
    return (
      <div
        data-testid="ai-insights-tab"
        className="flex flex-col h-full bg-white dark:bg-gray-900"
      >
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h2
            role="heading"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            AI Insights
          </h2>
          {enableObservability && (
            <button
              data-testid="observability-insights-toggle"
              type="button"
              onClick={() => setViewMode("observability")}
              className={cn(
                "px-2 py-1 text-xs rounded flex items-center gap-1",
                "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
              )}
            >
              <Activity size={12} />
              Observability
            </button>
          )}
          <div className="flex-1" />
          <button
            type="button"
            data-testid="refresh-insights-button"
            onClick={handleRefresh}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
            aria-label="Refresh insights"
          >
            <RefreshCw size={14} />
          </button>
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
            className="flex flex-col items-center justify-center text-gray-400 py-8"
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
      className="flex flex-col h-full bg-white dark:bg-gray-900"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <h2
          role="heading"
          className="text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          AI Insights
        </h2>

        {/* Observability Toggle */}
        {enableObservability && (
          <button
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
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
            )}
          >
            <Activity size={12} />
            Observability
          </button>
        )}

        {/* Filter buttons (only show in insights view) */}
        {viewMode === "insights" && (
          <div className="flex items-center gap-1 ml-2">
            <button
              data-testid="filter-all"
              type="button"
              onClick={() => setFilter("all")}
              className={cn(
                "px-2 py-1 text-xs rounded",
                filter === "all"
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                  : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
              )}
            >
              All
            </button>
            <button
              data-testid="filter-anomaly"
              type="button"
              onClick={() => setFilter("anomaly")}
              className={cn(
                "px-2 py-1 text-xs rounded",
                filter === "anomaly"
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                  : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
              )}
            >
              Anomaly
            </button>
            <button
              data-testid="filter-suggestion"
              type="button"
              onClick={() => setFilter("suggestion")}
              className={cn(
                "px-2 py-1 text-xs rounded",
                filter === "suggestion"
                  ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                  : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500",
              )}
            >
              Suggestion
            </button>
          </div>
        )}

        <div className="flex-1" />

        {/* Refresh button */}
        <button
          type="button"
          data-testid="refresh-insights-button"
          onClick={handleRefresh}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
          aria-label="Refresh insights"
        >
          <RefreshCw size={14} />
        </button>

        {/* Insight count */}
        <span className="text-xs text-gray-500">
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
