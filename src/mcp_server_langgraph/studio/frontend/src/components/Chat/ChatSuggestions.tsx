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
            className="h-10 w-40 bg-neutral-3 rounded-lg animate-pulse"
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
      <p className="text-sm text-neutral-10 mb-2">{title}</p>
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
                className="bg-neutral-1 border border-neutral-5 rounded-lg text-neutral-11 hover:bg-neutral-1 hover:border-primary-5 dark:hover:border-primary-10 focus:ring-primary-a6"
                type="button"
                onClick={() => onSelect(suggestion.text)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    onSelect(suggestion.text);
                  }
                }}
              >
                <Icon size={compact ? 14 : 16} className="text-neutral-9" />
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
