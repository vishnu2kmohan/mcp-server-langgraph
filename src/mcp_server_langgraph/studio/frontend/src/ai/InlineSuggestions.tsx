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

import { Button } from "@/components/UI";

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
  if (confidence >= 0.9) return "text-success-10 dark:text-success-7";
  if (confidence >= 0.7) return "text-warning-9 dark:text-warning-9";
  return "text-neutral-10";
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
          "bg-neutral-1",
          "border border-neutral-5",
          "text-sm text-neutral-10",
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
          "bg-neutral-1",
          "border border-neutral-5",
          "text-sm text-neutral-10",
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
      <div className="flex items-center gap-2 text-xs text-neutral-10 mb-1">
        <Sparkles size={12} />
        <span>AI Suggestions</span>
      </div>
      {suggestions.map((suggestion) => (
        <div
          key={suggestion.id}
          className={cn(
            "flex items-start gap-3 p-3 rounded-lg",
            "bg-neutral-1",
            "border border-neutral-5",
            "hover:border-primary-5 dark:hover:border-primary-11",
            "transition-colors",
          )}
        >
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5 text-primary-9">
            {getSuggestionIcon(suggestion.type)}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {/* Type badge */}
              <span
                className={cn(
                  "px-1.5 py-0.5 rounded text-xs font-medium",
                  "bg-neutral-2",
                  "text-neutral-11",
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
            <p className="text-sm text-neutral-11">
              {suggestion.content}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 flex-shrink-0">
            <Button
              variant="primary"
              type="button"
              aria-label="Accept suggestion"
              onClick={() => onAccept(suggestion)}
              className={cn(
                "h-6 w-6 min-h-6 min-w-6 p-1 rounded",
                "text-success-10 hover:bg-success-3 dark:hover:bg-success-a4",
                "transition-colors",
              )}>
              <Check size={16} />
            </Button>
            <Button
              variant="secondary"
              type="button"
              aria-label="Dismiss suggestion"
              onClick={() => onDismiss(suggestion)}
              className={cn(
                "h-6 w-6 min-h-6 min-w-6 p-1 rounded",
                "text-neutral-9 hover:text-error-9 hover:bg-error-3 dark:hover:bg-error-a4",
                "transition-colors",
              )}>
              <X size={16} />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
