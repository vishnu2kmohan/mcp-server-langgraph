/**
 * SuggestionChips
 *
 * AI suggestion chips component for workflow improvements.
 * Features:
 * - Display AI suggestions as interactive chips
 * - Loading state
 * - Error handling
 * - Apply/dismiss suggestion callbacks
 * - Confidence indicators
 * - Collapsible behavior
 */

import { useState } from "react";
import {
  Plus,
  Zap,
  AlertTriangle,
  Lightbulb,
  RefreshCw,
  Check,
  X,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { AISuggestion } from "../../types/api";

export interface SuggestionChipsProps {
  suggestions: AISuggestion[];
  isLoading: boolean;
  error: string | null;
  onApply: (suggestion: AISuggestion) => void;
  onDismiss: (suggestion: AISuggestion) => void;
  onRefresh: () => void;
  maxVisible?: number;
}

/**
 * Get confidence level from confidence score
 */
function getConfidenceLevel(confidence: number): "high" | "medium" | "low" {
  if (confidence >= 0.9) return "high";
  if (confidence >= 0.7) return "medium";
  return "low";
}

/**
 * Get icon for suggestion type
 */
function SuggestionIcon({ type }: { type: string }) {
  switch (type) {
    case "add_node":
      return <Plus className="w-4 h-4" data-icon="add" />;
    case "optimize":
      return <Zap className="w-4 h-4" data-icon="optimize" />;
    case "warning":
      return <AlertTriangle className="w-4 h-4" data-icon="warning" />;
    default:
      return <Lightbulb className="w-4 h-4" data-icon="hint" />;
  }
}

/**
 * Get confidence color classes
 */
function getConfidenceColorClass(level: "high" | "medium" | "low"): string {
  switch (level) {
    case "high":
      return "border-green-500 bg-green-50 dark:bg-green-900/20";
    case "medium":
      return "border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20";
    case "low":
      return "border-gray-400 bg-gray-50 dark:bg-gray-800/50";
  }
}

export function SuggestionChips({
  suggestions,
  isLoading,
  error,
  onApply,
  onDismiss,
  onRefresh,
  maxVisible = 10,
}: SuggestionChipsProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showAll, setShowAll] = useState(false);

  // Determine visible suggestions
  const visibleSuggestions = showAll
    ? suggestions
    : suggestions.slice(0, maxVisible);
  const hiddenCount = suggestions.length - maxVisible;

  // Loading state
  if (isLoading && suggestions.length === 0) {
    return (
      <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Analyzing workflow...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
        <div className="flex items-center justify-between">
          <span className="text-red-600 dark:text-red-400">{error}</span>
          <button
            onClick={onRefresh}
            className="text-sm text-red-600 dark:text-red-400 hover:underline"
            aria-label="Retry"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (suggestions.length === 0) {
    return (
      <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <span className="text-gray-500 dark:text-gray-400">
            No suggestions available
          </span>
          <button
            onClick={onRefresh}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            aria-label="Refresh suggestions"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="suggestions-container"
      data-expanded={isExpanded.toString()}
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-yellow-500" />
          <span className="font-medium text-sm text-gray-700 dark:text-gray-300">
            AI Suggestions
          </span>
          {!isExpanded && (
            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400">
              {suggestions.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label="Refresh suggestions"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label={
              isExpanded ? "Collapse suggestions" : "Expand suggestions"
            }
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Suggestions list */}
      {isExpanded && (
        <ul role="list" className="p-2 space-y-2">
          {visibleSuggestions.map((suggestion, index) => {
            const confidenceLevel = getConfidenceLevel(suggestion.confidence);
            return (
              <li
                key={index}
                role="listitem"
                data-testid="suggestion-chip"
                data-confidence={confidenceLevel}
                className={`flex items-start gap-3 p-3 rounded-lg border ${getConfidenceColorClass(confidenceLevel)}`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  <SuggestionIcon type={suggestion.type} />
                </div>
                <div className="flex-grow min-w-0">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {suggestion.description}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {Math.round(suggestion.confidence * 100)}% confidence
                  </p>
                </div>
                <div className="flex-shrink-0 flex items-center gap-1">
                  <button
                    onClick={() => onApply(suggestion)}
                    className="p-1.5 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 rounded"
                    aria-label="Apply suggestion"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onDismiss(suggestion)}
                    className="p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    aria-label="Dismiss suggestion"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </li>
            );
          })}

          {/* Show more button */}
          {hiddenCount > 0 && !showAll && (
            <li className="text-center">
              <button
                onClick={() => setShowAll(true)}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                Show {hiddenCount} more
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

export default SuggestionChips;
