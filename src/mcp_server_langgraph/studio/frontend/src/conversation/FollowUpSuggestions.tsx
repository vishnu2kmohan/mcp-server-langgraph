/**
 * FollowUpSuggestions - Phase 2
 *
 * AI-generated follow-up suggestion chips with
 * keyboard navigation and loading states.
 */
import { useState, useRef, useCallback } from "react";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface Suggestion {
  id: string;
  text: string;
  type: "follow-up" | "action";
}

export interface FollowUpSuggestionsProps {
  suggestions: Suggestion[];
  onSelect: (suggestion: Suggestion) => void;
  isLoading?: boolean;
  animate?: boolean;
  maxSuggestions?: number;
  className?: string;
}

// =============================================================================
// Loading Skeleton
// =============================================================================

function SuggestionsSkeleton() {
  return (
    <div
      data-testid="suggestions-skeleton"
      className="flex gap-2 py-2"
      role="status"
      aria-label="Loading suggestions"
    >
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-8 w-32 bg-neutral-3 rounded-full animate-pulse"
        />
      ))}
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

export function FollowUpSuggestions({
  suggestions,
  onSelect,
  isLoading = false,
  animate = false,
  maxSuggestions,
  className,
}: FollowUpSuggestionsProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const chipsRef = useRef<(HTMLButtonElement | null)[]>([]);

  // Limit displayed suggestions
  const displayedSuggestions = maxSuggestions
    ? suggestions.slice(0, maxSuggestions)
    : suggestions;

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number, suggestion: Suggestion) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onSelect(suggestion);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        const nextIndex = (index + 1) % displayedSuggestions.length;
        chipsRef.current[nextIndex]?.focus();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prevIndex =
          index === 0 ? displayedSuggestions.length - 1 : index - 1;
        chipsRef.current[prevIndex]?.focus();
      }
    },
    [displayedSuggestions.length, onSelect],
  );

  // Loading state
  if (isLoading) {
    return <SuggestionsSkeleton />;
  }

  // Don't render if no suggestions
  if (suggestions.length === 0) {
    return null;
  }

  return (
    <nav
      data-testid="follow-up-suggestions"
      role="navigation"
      aria-label="Follow-up suggestions"
      className={cn(
        "flex flex-wrap gap-2 py-2 px-4",
        animate && "animate-in fade-in-0 slide-in-from-bottom-2 duration-300",
        className,
      )}
    >
      {displayedSuggestions.map((suggestion, index) => {
        const isHovered = hoveredId === suggestion.id;

        return (
          <Button variant="ghost"
            key={suggestion.id}
            ref={(el) => {
              chipsRef.current[index] = el;
            }}
            data-testid="suggestion-chip"
            type="button"
            tabIndex={0}
            onClick={() => onSelect(suggestion)}
            onKeyDown={(e) => handleKeyDown(e, index, suggestion)}
            onMouseEnter={() => setHoveredId(suggestion.id)}
            onMouseLeave={() => setHoveredId(null)}
            aria-label={`Suggestion: ${suggestion.text}`}
            className={cn(
              "inline-flex items-center px-3 py-1.5",
              "text-sm rounded-full",
              "border transition-all",
              suggestion.type,
              isHovered && "hover",
              suggestion.type === "action"
                ? cn(
                    "action",
                    "bg-primary-1 dark:bg-primary-a3",
                    "border-primary-4 dark:border-primary-11",
                    "text-primary-11 dark:text-primary-5",
                    "hover:bg-primary-3 dark:hover:bg-primary-a4",
                  )
                : cn(
                    "follow-up",
                    "bg-neutral-1",
                    "border-neutral-5",
                    "text-neutral-11",
                    "hover:bg-neutral-2",
                  ),
            )}
          >
            {suggestion.text}
          </Button>
        );
      })}
    </nav>
  );
}
