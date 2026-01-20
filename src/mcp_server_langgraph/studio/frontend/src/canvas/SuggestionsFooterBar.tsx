/**
 * SuggestionsFooterBar Component
 *
 * A collapsible footer bar for AI suggestions in the canvas panel.
 * Replaces the floating CanvasShortcutsMenu with a non-intrusive footer.
 *
 * Design System Compliance:
 * - Radix color scale (neutral, primary, insight)
 * - 32px minimum touch targets
 * - Smooth transitions
 * - ARIA attributes for accessibility
 */

import { useState, useCallback } from "react";
import {
  Sparkles,
  ChevronUp,
  ChevronDown,
  RefreshCw,
  Check,
  X,
  Loader2,
} from "lucide-react";
import type { AISuggestion } from "../types/artifacts";
import { cn } from "../utils/cn";

export interface SuggestionsFooterBarProps {
  /** Array of AI suggestions to display */
  suggestions: AISuggestion[];
  /** Callback when a suggestion is accepted */
  onAccept?: (suggestion: AISuggestion) => void;
  /** Callback when a suggestion is dismissed */
  onDismiss?: (suggestion: AISuggestion) => void;
  /** Callback when refresh is requested */
  onRefresh?: () => void;
  /** Whether suggestions are loading */
  isLoading?: boolean;
  /** Controlled expanded state */
  isExpanded?: boolean;
  /** Callback for controlled toggle */
  onToggle?: () => void;
  /** Additional class names */
  className?: string;
}

export function SuggestionsFooterBar({
  suggestions,
  onAccept,
  onDismiss,
  onRefresh,
  isLoading = false,
  isExpanded: controlledExpanded,
  onToggle,
  className,
}: SuggestionsFooterBarProps) {
  // Support both controlled and uncontrolled mode
  const [internalExpanded, setInternalExpanded] = useState(false);
  const isExpanded = controlledExpanded ?? internalExpanded;

  const handleToggle = useCallback(() => {
    if (onToggle) {
      onToggle();
    } else {
      setInternalExpanded((prev) => !prev);
    }
  }, [onToggle]);

  const handleAccept = useCallback(
    (suggestion: AISuggestion) => {
      onAccept?.(suggestion);
    },
    [onAccept]
  );

  const handleDismiss = useCallback(
    (suggestion: AISuggestion) => {
      onDismiss?.(suggestion);
    },
    [onDismiss]
  );

  const handleRefresh = useCallback(() => {
    onRefresh?.();
  }, [onRefresh]);

  return (
    <div
      data-testid="suggestions-footer-bar"
      className={cn("border-t border-neutral-6 bg-neutral-1", className)}
    >
      {/* Header bar - always visible */}
      <div
        className={cn(
          "w-full h-8 px-3",
          "flex items-center justify-between",
          "text-sm text-neutral-11"
        )}
      >
        {/* Clickable header section */}
        <button
          type="button"
          data-testid="suggestions-header"
          onClick={handleToggle}
          aria-expanded={isExpanded}
          aria-controls="suggestions-content"
          className={cn(
            "flex-1 h-full",
            "flex items-center gap-2",
            "hover:bg-neutral-2",
            "transition-colors duration-150",
            "focus:outline-none focus:ring-2 focus:ring-primary-7 focus:ring-inset",
            "-ml-3 pl-3" // Extend click area to left edge
          )}
        >
          <Sparkles
            data-testid="sparkles-icon"
            className="w-4 h-4 text-insight-11"
          />
          <span className="font-medium">AI Suggestions</span>
          {suggestions.length > 0 && (
            <span
              className={cn(
                "px-1.5 py-0.5 rounded-full",
                "bg-insight-3 text-insight-11",
                "text-xs font-medium"
              )}
            >
              {suggestions.length}
            </span>
          )}
        </button>
        {/* Actions section (not nested in header button) */}
        <div className="flex items-center gap-2">
          {/* Loading spinner */}
          {isLoading && (
            <Loader2
              data-testid="loading-spinner"
              className="w-4 h-4 animate-spin text-neutral-11"
            />
          )}
          {/* Refresh button */}
          <button
            type="button"
            data-testid="refresh-button"
            onClick={(e) => {
              e.stopPropagation();
              handleRefresh();
            }}
            disabled={isLoading}
            className={cn(
              "p-1 rounded",
              "text-neutral-11 hover:text-neutral-11",
              "hover:bg-neutral-3",
              "transition-colors duration-150",
              "min-w-[24px] min-h-[24px]",
              "flex items-center justify-center",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
            aria-label="Refresh suggestions"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          {/* Chevron */}
          {isExpanded ? (
            <ChevronDown
              data-testid="chevron-down-icon"
              className="w-4 h-4 text-neutral-11"
            />
          ) : (
            <ChevronUp
              data-testid="chevron-up-icon"
              className="w-4 h-4 text-neutral-11"
            />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div
          id="suggestions-content"
          data-testid="suggestions-content"
          className={cn(
            "max-h-[200px] overflow-y-auto",
            "border-t border-neutral-6",
            "bg-neutral-2"
          )}
        >
          {suggestions.length === 0 ? (
            <div className="p-4 text-center text-sm text-neutral-11">
              No suggestions available
            </div>
          ) : (
            <div className="p-2 space-y-1">
              {suggestions.map((suggestion) => (
                <SuggestionItem
                  key={suggestion.id}
                  suggestion={suggestion}
                  onAccept={handleAccept}
                  onDismiss={handleDismiss}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// SuggestionItem Component
// =============================================================================

interface SuggestionItemProps {
  suggestion: AISuggestion;
  onAccept: (suggestion: AISuggestion) => void;
  onDismiss: (suggestion: AISuggestion) => void;
}

function SuggestionItem({
  suggestion,
  onAccept,
  onDismiss,
}: SuggestionItemProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3",
        "p-2 rounded-md",
        "bg-neutral-1 hover:bg-neutral-3",
        "transition-colors duration-150"
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-neutral-12 truncate">
          {suggestion.label}
        </div>
        <div className="text-xs text-neutral-11 truncate">
          {suggestion.description}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          data-testid={`accept-${suggestion.id}`}
          onClick={() => onAccept(suggestion)}
          className={cn(
            "p-1 rounded",
            "text-success-11 hover:bg-success-3",
            "transition-colors duration-150",
            "min-w-7 min-h-7",
            "flex items-center justify-center"
          )}
          aria-label={`Accept ${suggestion.label}`}
        >
          <Check className="w-4 h-4" />
        </button>
        <button
          type="button"
          data-testid={`dismiss-${suggestion.id}`}
          onClick={() => onDismiss(suggestion)}
          className={cn(
            "p-1 rounded",
            "text-neutral-11 hover:text-neutral-11 hover:bg-neutral-4",
            "transition-colors duration-150",
            "min-w-7 min-h-7",
            "flex items-center justify-center"
          )}
          aria-label={`Dismiss ${suggestion.label}`}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default SuggestionsFooterBar;
