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

import { Button } from "@/components/UI";

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
      return "border-success-9 bg-success-1 dark:bg-success-a3";
    case "medium":
      return "border-warning-9 bg-warning-3 bg-warning-3";
    case "low":
      return "border-neutral-6 bg-neutral-1";
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
      <div className="p-4 bg-neutral-1 rounded-lg border border-neutral-5">
        <div className="flex items-center gap-2 text-neutral-10">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Analyzing workflow...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-4 bg-error-1 dark:bg-error-a3 rounded-lg border border-error-4 dark:border-error-11">
        <div className="flex items-center justify-between">
          <span className="text-error-10 dark:text-error-7">{error}</span>
          <Button
            variant="primary"
            className="text-sm text-error-10 dark:text-error-7 hover:underline"
            onClick={onRefresh}
            aria-label="Retry"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // Empty state
  if (suggestions.length === 0) {
    return (
      <div className="p-4 bg-neutral-1 rounded-lg border border-neutral-5">
        <div className="flex items-center justify-between">
          <span className="text-neutral-10">No suggestions available</span>
          <Button
            size="icon"
            variant="ghost"
            className="text-sm text-primary-10 dark:text-primary-7 hover:underline"
            onClick={onRefresh}
            aria-label="Refresh suggestions"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="suggestions-container"
      data-expanded={isExpanded.toString()}
      className="bg-neutral-1 rounded-lg border border-neutral-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-warning-9" />
          <span className="font-medium text-sm text-neutral-11">
            AI Suggestions
          </span>
          {!isExpanded && (
            <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-primary-3 text-primary-10 dark:bg-primary-a6 dark:text-primary-7">
              {suggestions.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="icon"
            variant="ghost"
            className="p-1 text-neutral-10 hover:text-neutral-11"
            onClick={onRefresh}
            aria-label="Refresh suggestions"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button
            variant="primary"
            className="p-1 text-neutral-10 hover:text-neutral-11"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={
              isExpanded ? "Collapse suggestions" : "Expand suggestions"
            }
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
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
                  <p className="text-sm text-neutral-11">
                    {suggestion.description}
                  </p>
                  <p className="text-xs text-neutral-10 mt-1">
                    {Math.round(suggestion.confidence * 100)}% confidence
                  </p>
                </div>
                <div className="flex-shrink-0 flex items-center gap-1">
                  <Button
                    variant="success"
                    className="p-1.5 text-success-10 hover:bg-success-3 dark:hover:bg-success-a4 rounded"
                    onClick={() => onApply(suggestion)}
                    aria-label="Apply suggestion"
                  >
                    <Check className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="secondary"
                    className="p-1.5 text-neutral-9 hover:bg-neutral-2 rounded"
                    onClick={() => onDismiss(suggestion)}
                    aria-label="Dismiss suggestion"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </li>
            );
          })}

          {/* Show more button */}
          {hiddenCount > 0 && !showAll && (
            <li className="text-center">
              <Button
                variant="primary"
                className="text-sm text-primary-10 dark:text-primary-7 hover:underline"
                onClick={() => setShowAll(true)}
              >
                Show {hiddenCount} more
              </Button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

export default SuggestionChips;
