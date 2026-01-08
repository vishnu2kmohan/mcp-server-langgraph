/**
 * AIFollowUpSuggestions Component
 *
 * Displays AI-generated follow-up suggestions after AI responses.
 * Helps users explore related topics and continue the conversation.
 *
 * Features:
 * - Context-aware suggestions
 * - Clickable suggestion chips
 * - Loading state with skeleton
 * - Category labels
 * - Compact mode
 */

import { useMemo } from "react";
import {
  Sparkles,
  HelpCircle,
  Lightbulb,
  BookOpen,
  Code,
  MessageCircle,
  ArrowRight,
  GitCompare,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";

/** Feedback type for suggestions */
export type SuggestionFeedbackType = "positive" | "negative";

// =============================================================================
// Types
// =============================================================================

/**
 * Suggestion categories aligned with backend API.
 * Supports both legacy frontend categories and new backend categories.
 */
export type SuggestionCategory =
  | "clarify" // Get simpler explanation
  | "explain" // Legacy: similar to clarify
  | "example" // Request practical examples
  | "code" // Code-specific suggestions
  | "explore" // Dig deeper into topic
  | "general" // Catch-all
  | "alternative" // Compare options/trade-offs (from backend)
  | "continue"; // Next steps/what to do next (from backend)

export interface FollowUpSuggestion {
  /** Unique identifier */
  id: string;
  /** Suggestion text */
  text: string;
  /** Optional category */
  category?: SuggestionCategory;
}

export interface AIFollowUpSuggestionsProps {
  /** List of suggestions */
  suggestions: FollowUpSuggestion[];
  /** Callback when a suggestion is selected */
  onSelect: (suggestion: FollowUpSuggestion) => void;
  /** Callback when feedback is provided (thumbs up/down) */
  onFeedback?: (
    suggestion: FollowUpSuggestion,
    feedback: SuggestionFeedbackType,
  ) => void;
  /** Whether suggestions are loading */
  isLoading?: boolean;
  /** Whether suggestions are disabled */
  disabled?: boolean;
  /** Maximum number of suggestions to show */
  maxSuggestions?: number;
  /** Whether to show category labels */
  showCategories?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Constants
// =============================================================================

const CATEGORY_ICONS: Record<SuggestionCategory, typeof HelpCircle> = {
  clarify: HelpCircle,
  explain: Lightbulb,
  example: BookOpen,
  code: Code,
  explore: Sparkles,
  general: MessageCircle,
  alternative: GitCompare,
  continue: ArrowRight,
};

const CATEGORY_LABELS: Record<SuggestionCategory, string> = {
  clarify: "Clarify",
  explain: "Explain",
  example: "Example",
  code: "Code",
  explore: "Explore",
  general: "General",
  alternative: "Compare",
  continue: "Next Step",
};

// =============================================================================
// Component
// =============================================================================

export function AIFollowUpSuggestions({
  suggestions,
  onSelect,
  onFeedback,
  isLoading = false,
  disabled = false,
  maxSuggestions = 4,
  showCategories = false,
  compact = false,
  className = "",
}: AIFollowUpSuggestionsProps) {
  // Limit suggestions to max count
  const visibleSuggestions = useMemo(
    () => suggestions.slice(0, maxSuggestions),
    [suggestions, maxSuggestions],
  );

  // Show loading state
  if (isLoading) {
    return (
      <div
        data-testid="suggestions-loading"
        className={`flex flex-col gap-2 ${className}`}
      >
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          <Sparkles size={12} className="animate-pulse" />
          <span>Generating follow-up questions...</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              data-testid="skeleton-suggestion"
              className="h-8 rounded-full bg-gray-100 dark:bg-gray-700 animate-pulse"
              style={{ width: `${80 + i * 20}px` }}
            />
          ))}
        </div>
      </div>
    );
  }

  // Don't render if no suggestions
  if (suggestions.length === 0) {
    return null;
  }

  const textSize = compact ? "text-xs" : "text-sm";

  return (
    <div
      data-testid="follow-up-suggestions"
      className={`flex flex-col gap-2 ${textSize} ${className}`}
    >
      {/* Header */}
      <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
        <Sparkles size={compact ? 10 : 12} />
        <span className="text-xs">Related questions to explore</span>
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2">
        {visibleSuggestions.map((suggestion) => {
          const category = suggestion.category || "general";
          const Icon = CATEGORY_ICONS[category];

          return (
            <div
              key={suggestion.id}
              className="group relative inline-flex items-center"
            >
              <button
                type="button"
                onClick={() => onSelect(suggestion)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(suggestion);
                  }
                }}
                disabled={disabled}
                className={`
                  inline-flex items-center gap-1.5
                  px-3 py-1.5 rounded-full
                  bg-primary-50 dark:bg-primary-900/20
                  text-primary-700 dark:text-primary-300
                  hover:bg-primary-100 dark:hover:bg-primary-900/40
                  border border-primary-200 dark:border-primary-800
                  transition-colors cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${compact ? "px-2 py-1" : "px-3 py-1.5"}
                  ${onFeedback ? "pr-14" : ""}
                `}
              >
                <span data-testid="suggestion-icon">
                  <Icon size={compact ? 10 : 12} />
                </span>
                {showCategories && (
                  <span className="text-xs uppercase font-semibold text-primary-500 dark:text-primary-400">
                    {CATEGORY_LABELS[category]}
                  </span>
                )}
                <span className="truncate max-w-[200px]">
                  {suggestion.text}
                </span>
              </button>

              {/* Feedback buttons (thumbs up/down) */}
              {onFeedback && (
                <div className="absolute right-1 flex items-center gap-0.5">
                  <button
                    type="button"
                    data-testid="feedback-positive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onFeedback(suggestion, "positive");
                    }}
                    disabled={disabled}
                    className={`
                      p-1 rounded-full
                      text-gray-400 dark:text-gray-500
                      hover:text-success-600 dark:hover:text-success-400
                      hover:bg-success-50 dark:hover:bg-success-900/20
                      transition-colors
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                    aria-label="Helpful suggestion"
                  >
                    <ThumbsUp size={compact ? 10 : 12} />
                  </button>
                  <button
                    type="button"
                    data-testid="feedback-negative"
                    onClick={(e) => {
                      e.stopPropagation();
                      onFeedback(suggestion, "negative");
                    }}
                    disabled={disabled}
                    className={`
                      p-1 rounded-full
                      text-gray-400 dark:text-gray-500
                      hover:text-error-600 dark:hover:text-error-400
                      hover:bg-error-50 dark:hover:bg-error-900/20
                      transition-colors
                      disabled:opacity-50 disabled:cursor-not-allowed
                    `}
                    aria-label="Not helpful suggestion"
                  >
                    <ThumbsDown size={compact ? 10 : 12} />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default AIFollowUpSuggestions;
