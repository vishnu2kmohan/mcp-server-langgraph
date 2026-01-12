/**
 * ChatSuggestions Component
 *
 * Displays contextual prompt suggestions to help users start conversations.
 * Similar to ChatGPT/Claude's suggested prompts at the start of a chat.
 */

import {
  Sparkles,
  Code,
  BookOpen,
  Search,
  HelpCircle,
  MessageSquare,
} from "lucide-react";

import { Button } from "@/components/UI";

export interface ChatSuggestion {
  id: string;
  text: string;
  category: string;
  icon?: string;
}

export interface ChatSuggestionsProps {
  /** Array of suggestions to display */
  suggestions: ChatSuggestion[];
  /** Callback when a suggestion is selected */
  onSelect: (text: string) => void;
  /** Whether suggestions are loading */
  isLoading?: boolean;
  /** Whether to show the suggestions (defaults to true) */
  show?: boolean;
  /** Title above suggestions */
  title?: string;
  /** Maximum number of suggestions to show */
  maxItems?: number;
  /** Compact mode for smaller display */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get icon component based on icon name
 */
function getIcon(iconName?: string) {
  switch (iconName) {
    case "code":
      return Code;
    case "book":
      return BookOpen;
    case "search":
      return Search;
    case "help":
      return HelpCircle;
    case "message":
      return MessageSquare;
    default:
      return Sparkles;
  }
}

export function ChatSuggestions({
  suggestions,
  onSelect,
  isLoading = false,
  show = true,
  title = "Try asking",
  maxItems,
  compact = false,
  className = "",
}: ChatSuggestionsProps) {
  // Don't render if hidden
  if (!show) {
    return null;
  }

  // Show loading skeleton
  if (isLoading) {
    return (
      <div
        data-testid="suggestions-loading"
        className="flex flex-wrap gap-2 p-4"
      >
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-10 w-40 bg-neutral-200 dark:bg-neutral-700 rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  // Don't render if no suggestions
  if (suggestions.length === 0) {
    return null;
  }

  // Limit suggestions if maxItems is set
  const displayedSuggestions = maxItems
    ? suggestions.slice(0, maxItems)
    : suggestions;

  return (
    <div className={`px-4 py-3 ${className}`}>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-2">
        {title}
      </p>
      <ul
        role="list"
        className={`flex flex-wrap ${compact ? "gap-2" : "gap-3"} ${className}`}
      >
        {displayedSuggestions.map((suggestion) => {
          const Icon = getIcon(suggestion.icon);
          return (
            <li key={suggestion.id}>
              <Button
                variant="secondary"
                className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 hover:border-primary-300 dark:hover:border-primary-600 focus:ring-primary-500/50"
                type="button"
                onClick={() => onSelect(suggestion.text)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    onSelect(suggestion.text);
                  }
                }}
              >
                <Icon
                  size={compact ? 14 : 16}
                  className="text-neutral-400 dark:text-neutral-400"
                />
                <span>{suggestion.text}</span>
              </Button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default ChatSuggestions;
