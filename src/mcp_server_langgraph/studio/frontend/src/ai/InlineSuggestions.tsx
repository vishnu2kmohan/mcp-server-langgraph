/**
 * InlineSuggestions Component
 *
 * Phase 4: AI-Native Features
 * Displays inline AI suggestions for code artifacts in the Canvas panel.
 *
 * Features:
 * - Tab to accept, Esc to dismiss
 * - Confidence score indicator
 * - Type-based icons (completion, refactor, fix, explain)
 */

import { Sparkles, Check, X, Loader2, Wand2, Bug } from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export type SuggestionType = "completion" | "refactor" | "fix" | "explain";

export interface Suggestion {
  id: string;
  type: SuggestionType;
  content: string;
  confidence: number;
  /** Optional position information for inline display */
  position?: { line: number; column: number };
}

export interface InlineSuggestionsProps {
  suggestions: Suggestion[];
  onAccept: (suggestion: Suggestion) => void;
  onDismiss: (suggestion: Suggestion) => void;
  isLoading?: boolean;
  className?: string;
}

// =============================================================================
// Icon Mapping
// =============================================================================

function getSuggestionIcon(type: SuggestionType) {
  switch (type) {
    case "completion":
      return <Sparkles size={14} />;
    case "refactor":
      return <Wand2 size={14} />;
    case "fix":
      return <Bug size={14} />;
    case "explain":
      return <Sparkles size={14} />;
    default:
      return <Sparkles size={14} />;
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "text-green-600 dark:text-green-400";
  if (confidence >= 0.7) return "text-yellow-600 dark:text-yellow-400";
  return "text-gray-500 dark:text-gray-400";
}

// =============================================================================
// Component
// =============================================================================

export function InlineSuggestions({
  suggestions,
  onAccept,
  onDismiss,
  isLoading = false,
  className,
}: InlineSuggestionsProps) {
  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="inline-suggestions"
        className={cn(
          "flex items-center gap-2 p-3 rounded-lg",
          "bg-gray-50 dark:bg-gray-800",
          "border border-gray-200 dark:border-gray-700",
          "text-sm text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <Loader2 size={16} className="animate-spin" />
        <span>Generating suggestions...</span>
      </div>
    );
  }

  // Empty state
  if (suggestions.length === 0) {
    return (
      <div
        data-testid="inline-suggestions"
        className={cn(
          "flex items-center gap-2 p-3 rounded-lg",
          "bg-gray-50 dark:bg-gray-800",
          "border border-gray-200 dark:border-gray-700",
          "text-sm text-gray-500 dark:text-gray-400",
          className,
        )}
      >
        <Sparkles size={16} className="opacity-50" />
        <span>No suggestions available</span>
      </div>
    );
  }

  // Suggestions list
  return (
    <div
      data-testid="inline-suggestions"
      className={cn("flex flex-col gap-2", className)}
    >
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-1">
        <Sparkles size={12} />
        <span>AI Suggestions</span>
      </div>
      {suggestions.map((suggestion) => (
        <div
          key={suggestion.id}
          className={cn(
            "flex items-start gap-3 p-3 rounded-lg",
            "bg-gray-50 dark:bg-gray-800",
            "border border-gray-200 dark:border-gray-700",
            "hover:border-primary-300 dark:hover:border-primary-700",
            "transition-colors",
          )}
        >
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5 text-primary-500">
            {getSuggestionIcon(suggestion.type)}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {/* Type badge */}
              <span
                className={cn(
                  "px-1.5 py-0.5 rounded text-xs font-medium",
                  "bg-gray-100 dark:bg-gray-700",
                  "text-gray-600 dark:text-gray-300",
                )}
              >
                {suggestion.type}
              </span>
              {/* Confidence */}
              <span
                className={cn(
                  "text-xs font-medium",
                  getConfidenceColor(suggestion.confidence),
                )}
              >
                {Math.round(suggestion.confidence * 100)}%
              </span>
            </div>
            {/* Suggestion text */}
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {suggestion.content}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              type="button"
              aria-label="Accept suggestion"
              onClick={() => onAccept(suggestion)}
              className={cn(
                "p-1.5 rounded",
                "text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30",
                "transition-colors",
              )}
            >
              <Check size={14} />
            </button>
            <button
              type="button"
              aria-label="Dismiss suggestion"
              onClick={() => onDismiss(suggestion)}
              className={cn(
                "p-1.5 rounded",
                "text-gray-400 hover:text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30",
                "transition-colors",
              )}
            >
              <X size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
