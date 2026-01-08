/**
 * SuggestionsPanel Component
 *
 * Phase 4: AI-Native Features
 * Displays AI suggestions in a collapsible table format for better user control.
 * Users can review all suggestions at once instead of seeing them as overlays.
 *
 * Features:
 * - Collapsible panel with expand/collapse toggle
 * - Table view with type, content, confidence columns
 * - Accept/dismiss actions per suggestion
 * - Refresh button for manual fetch trigger
 * - Loading and empty states
 */

import {
  Sparkles,
  Check,
  X,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Wand2,
  Bug,
} from "lucide-react";
import { cn } from "../utils/cn";
import type { Suggestion, SuggestionType } from "./InlineSuggestions";

// =============================================================================
// Types
// =============================================================================

export interface SuggestionsPanelProps {
  /** List of suggestions to display */
  suggestions: Suggestion[];
  /** Called when user accepts a suggestion */
  onAccept: (suggestion: Suggestion) => void;
  /** Called when user dismisses a suggestion */
  onDismiss: (suggestion: Suggestion) => void;
  /** Called when user requests to refresh suggestions */
  onRefresh: () => void;
  /** Whether suggestions are being loaded */
  isLoading?: boolean;
  /** Whether the panel is expanded */
  isExpanded?: boolean;
  /** Called when user toggles expand/collapse */
  onToggleExpand?: () => void;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Helper Functions
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
  if (confidence >= 0.9) return "text-success-600 dark:text-success-400";
  if (confidence >= 0.7) return "text-warning-600 dark:text-warning-400";
  return "text-gray-500 dark:text-gray-400";
}

// =============================================================================
// Component
// =============================================================================

export function SuggestionsPanel({
  suggestions,
  onAccept,
  onDismiss,
  onRefresh,
  isLoading = false,
  isExpanded = true,
  onToggleExpand,
  className,
}: SuggestionsPanelProps) {
  const count = suggestions.length;

  return (
    <div
      data-testid="suggestions-panel"
      className={cn(
        "rounded-lg border",
        "bg-white dark:bg-gray-900",
        "border-gray-200 dark:border-gray-700",
        "shadow-sm",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={onToggleExpand}
          className={cn(
            "flex items-center gap-2 text-sm font-medium",
            "text-gray-700 dark:text-gray-300",
            "hover:text-gray-900 dark:hover:text-gray-100",
            "transition-colors",
          )}
          aria-label="AI Suggestions"
        >
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <Sparkles size={14} className="text-primary-500" />
          <span>AI Suggestions</span>
          <span
            className={cn(
              "px-1.5 py-0.5 rounded-full text-xs font-medium",
              "bg-primary-100 dark:bg-primary-900/30",
              "text-primary-700 dark:text-primary-300",
            )}
          >
            {count}
          </span>
        </button>

        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          aria-label="Refresh suggestions"
          className={cn(
            "p-1.5 rounded",
            "text-gray-400 dark:text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-200",
            "hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800",
            "transition-colors",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
        >
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="p-2">
          {/* Loading state */}
          {isLoading && (
            <div
              data-testid="suggestions-loading"
              className="flex items-center justify-center gap-2 py-4 text-sm text-gray-500 dark:text-gray-400"
            >
              <Loader2 size={16} className="animate-spin" />
              <span>Loading suggestions...</span>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && count === 0 && (
            <div className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
              No suggestions available. Click refresh to fetch.
            </div>
          )}

          {/* Suggestions table */}
          {!isLoading && count > 0 && (
            <table className="w-full" role="table">
              <thead>
                <tr className="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800">
                  <th className="text-left py-2 px-2 font-medium">Type</th>
                  <th className="text-left py-2 px-2 font-medium">
                    Suggestion
                  </th>
                  <th className="text-right py-2 px-2 font-medium w-16">
                    Conf
                  </th>
                  <th className="text-right py-2 px-2 font-medium w-20">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {suggestions.map((suggestion) => (
                  <tr
                    key={suggestion.id}
                    className={cn(
                      "border-b border-gray-50 dark:border-gray-800 last:border-0",
                      "hover:bg-gray-50 dark:hover:bg-gray-800/50",
                      "transition-colors",
                    )}
                  >
                    {/* Type */}
                    <td className="py-2 px-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium",
                          "bg-gray-100 dark:bg-gray-700",
                          "text-gray-600 dark:text-gray-300",
                        )}
                      >
                        {getSuggestionIcon(suggestion.type)}
                        {suggestion.type}
                      </span>
                    </td>

                    {/* Content */}
                    <td className="py-2 px-2 text-sm text-gray-700 dark:text-gray-300">
                      {suggestion.content}
                    </td>

                    {/* Confidence */}
                    <td className="py-2 px-2 text-right">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          getConfidenceColor(suggestion.confidence),
                        )}
                      >
                        {Math.round(suggestion.confidence * 100)}%
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-2 px-2">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => onAccept(suggestion)}
                          aria-label="Accept suggestion"
                          className={cn(
                            "p-1 rounded",
                            "text-success-600 hover:bg-success-100 dark:hover:bg-success-900/30",
                            "transition-colors",
                          )}
                        >
                          <Check size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => onDismiss(suggestion)}
                          aria-label="Dismiss suggestion"
                          className={cn(
                            "p-1 rounded",
                            "text-gray-400 dark:text-gray-400 hover:text-error-500 hover:bg-error-100 dark:hover:bg-error-900/30",
                            "transition-colors",
                          )}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

export default SuggestionsPanel;
