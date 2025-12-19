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
import { Sparkles, HelpCircle, Lightbulb, BookOpen, Code, MessageCircle } from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type SuggestionCategory =
  | "clarify"
  | "explain"
  | "example"
  | "code"
  | "explore"
  | "general";

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
};

const CATEGORY_LABELS: Record<SuggestionCategory, string> = {
  clarify: "Clarify",
  explain: "Explain",
  example: "Example",
  code: "Code",
  explore: "Explore",
  general: "General",
};

// =============================================================================
// Component
// =============================================================================

export function AIFollowUpSuggestions({
  suggestions,
  onSelect,
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
    [suggestions, maxSuggestions]
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
            <button
              key={suggestion.id}
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
                bg-blue-50 dark:bg-blue-900/20
                text-blue-700 dark:text-blue-300
                hover:bg-blue-100 dark:hover:bg-blue-900/40
                border border-blue-200 dark:border-blue-800
                transition-colors cursor-pointer
                disabled:opacity-50 disabled:cursor-not-allowed
                ${compact ? "px-2 py-1" : "px-3 py-1.5"}
              `}
            >
              <span data-testid="suggestion-icon">
                <Icon size={compact ? 10 : 12} />
              </span>
              {showCategories && (
                <span className="text-[10px] uppercase font-semibold text-blue-500 dark:text-blue-400">
                  {CATEGORY_LABELS[category]}
                </span>
              )}
              <span className="truncate max-w-[200px]">{suggestion.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default AIFollowUpSuggestions;
