/**
 * AIInsightsTab Component
 *
 * Displays AI-generated insights, anomalies, and suggestions.
 * Uses the useDevToolsAI hook for AI-powered analysis.
 */
import { useState, useMemo } from "react";
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
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useDevToolsAI } from "../hooks/useDevToolsAI";
import type { AIInsightsTabProps, AIInsight, AIInsightType } from "../types";

// =============================================================================
// Types
// =============================================================================

type FilterType = "all" | "anomaly" | "performance" | "cost" | "suggestion";

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
        getSeverityColor(insight.severity)
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
          getSeverityIndicatorColor(insight.severity)
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
                getTypeBadgeColor(insight.type)
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
            "text-gray-600 dark:text-gray-400"
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
        "border border-primary-200 dark:border-primary-700 rounded-lg"
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
          "text-white"
        )}
      >
        Apply
      </button>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AIInsightsTab({ context, contextEntityId }: AIInsightsTabProps) {
  const [filter, setFilter] = useState<FilterType>("all");

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
    userId: "current-user", // TODO: Get from auth context
    enabled: true,
  });

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

  // Empty state
  if (insights.length === 0) {
    return (
      <div
        data-testid="ai-insights-tab"
        className="flex flex-col h-full bg-white dark:bg-gray-900"
      >
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <h2 role="heading" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            AI Insights
          </h2>
          <div className="flex-1" />
          <button
            type="button"
            data-testid="refresh-insights-button"
            onClick={fetchSuggestions}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
            aria-label="Refresh insights"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        <div
          data-testid="ai-insights-empty"
          className="flex-1 flex flex-col items-center justify-center text-gray-400"
        >
          <Sparkles size={32} className="mb-2 opacity-50" />
          <p className="text-sm">No AI insights</p>
          <p className="text-xs mt-1">AI analysis will appear here</p>
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
        <h2 role="heading" className="text-sm font-medium text-gray-700 dark:text-gray-300">
          AI Insights
        </h2>

        {/* Filter buttons */}
        <div className="flex items-center gap-1 ml-2">
          <button
            data-testid="filter-all"
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "all"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-600"
                : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"
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
                : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"
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
                : "hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"
            )}
          >
            Suggestion
          </button>
        </div>

        <div className="flex-1" />

        {/* Refresh button */}
        <button
          type="button"
          data-testid="refresh-insights-button"
          onClick={fetchSuggestions}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
          aria-label="Refresh insights"
        >
          <RefreshCw size={14} />
        </button>

        {/* Insight count */}
        <span className="text-xs text-gray-500">
          {filteredInsights.length} insight{filteredInsights.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-2">
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
      </div>
    </div>
  );
}

export default AIInsightsTab;
