/**
 * HelpPane Component
 *
 * Phase 6: Help & Accessibility
 * Searchable help pane with topic browsing.
 *
 * Features:
 * - Full-text search across topics
 * - Category-based organization
 * - Topic selection callback
 * - AI-powered contextual help (Sprint 6)
 */

import { useState, useMemo } from "react";
import { HelpCircle, Search, X, Loader2, BookOpen, Sparkles, Zap } from "lucide-react";
import { cn } from "../utils/cn";
import { useContextualHelp } from "../hooks/useUXIntelligence";

// =============================================================================
// Types
// =============================================================================

export interface HelpTopic {
  id: string;
  title: string;
  category: string;
  content: string;
  keywords: string[];
}

export interface HelpPaneProps {
  topics: HelpTopic[];
  onTopicSelect: (topic: HelpTopic) => void;
  isLoading?: boolean;
  className?: string;
  /** Enable AI-powered contextual help (Sprint 6) */
  enableAI?: boolean;
  /** Current page for contextual suggestions */
  currentPage?: string;
  /** Current feature being used */
  currentFeature?: string;
  /** Callback for quick action click */
  onQuickAction?: (action: { id: string; label: string; action: string }) => void;
}

// =============================================================================
// Utility
// =============================================================================

function getCategoryColor(category: string): string {
  switch (category) {
    case "basics":
      return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
    case "productivity":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "compliance":
      return "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
  }
}

// =============================================================================
// Component
// =============================================================================

export function HelpPane({
  topics,
  onTopicSelect,
  isLoading = false,
  className,
  enableAI = false,
  currentPage,
  currentFeature,
  onQuickAction,
}: HelpPaneProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // AI Contextual Help (Sprint 6)
  const {
    helpTopics: aiTopics,
    quickActions,
    isLoading: aiLoading,
  } = useContextualHelp({
    userId: "",
    currentPage: currentPage ?? "",
    activeFeature: currentFeature ?? "",
    enabled: enableAI,
  });

  // Filter topics based on search
  const filteredTopics = useMemo(() => {
    if (!searchQuery.trim()) return topics;

    const query = searchQuery.toLowerCase();
    return topics.filter(
      (topic) =>
        topic.title.toLowerCase().includes(query) ||
        topic.content.toLowerCase().includes(query) ||
        topic.keywords.some((kw) => kw.toLowerCase().includes(query)),
    );
  }, [topics, searchQuery]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="help-pane"
        className={cn(
          "rounded-lg border border-gray-200 dark:border-gray-700",
          "bg-white dark:bg-gray-900 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 size={16} className="animate-spin" />
          <span>Loading help topics...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="help-pane"
      className={cn(
        "rounded-lg border border-gray-200 dark:border-gray-700",
        "bg-white dark:bg-gray-900 flex flex-col",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
        <HelpCircle size={18} className="text-primary-500" />
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Help</h3>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search help topics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              "w-full pl-9 pr-9 py-2 rounded-lg",
              "bg-gray-50 dark:bg-gray-800",
              "border border-gray-200 dark:border-gray-700",
              "text-sm text-gray-900 dark:text-gray-100",
              "placeholder-gray-400",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
            )}
          />
          {searchQuery && (
            <button
              type="button"
              aria-label="Clear search"
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* AI Contextual Help Section (Sprint 6) */}
      {enableAI && !searchQuery && (
        <div
          data-testid="ai-contextual-help-section"
          className="p-3 border-b border-gray-200 dark:border-gray-700"
        >
          {/* Quick Actions */}
          {quickActions.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                Quick Actions
              </div>
              <div className="flex flex-wrap gap-1.5">
                {quickActions.map((action, index) => (
                  <button
                    key={`${action.label}-${index}`}
                    type="button"
                    onClick={() => onQuickAction?.({ id: `action-${index}`, label: action.label, action: action.action })}
                    className={cn(
                      "inline-flex items-center gap-1 px-2 py-1 rounded text-xs",
                      "bg-gray-100 dark:bg-gray-800",
                      "text-gray-700 dark:text-gray-300",
                      "hover:bg-primary-100 dark:hover:bg-primary-900/30",
                      "transition-colors"
                    )}
                  >
                    <Zap size={12} />
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* AI-Suggested Topics */}
          {aiTopics.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Related Topics
              </div>
              {aiTopics.slice(0, 3).map((topic) => (
                <button
                  key={topic.id}
                  type="button"
                  onClick={() => onTopicSelect({
                    id: topic.id,
                    title: topic.title,
                    category: "ai-suggested",
                    content: topic.summary,
                    keywords: [],
                  })}
                  className={cn(
                    "w-full text-left p-2 rounded-lg text-sm",
                    "bg-gray-50 dark:bg-gray-800",
                    "hover:bg-primary-50 dark:hover:bg-primary-900/20",
                    "transition-colors"
                  )}
                >
                  <span className="text-gray-700 dark:text-gray-300">
                    {topic.title}
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Loading state for AI */}
          {aiLoading && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Loader2 size={12} className="animate-spin" />
              <span>Finding relevant help...</span>
            </div>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {topics.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-sm text-gray-500 dark:text-gray-400">
            <BookOpen size={24} className="mb-2 opacity-50" />
            <span>No help topics available</span>
          </div>
        ) : filteredTopics.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-sm text-gray-500 dark:text-gray-400">
            <Search size={24} className="mb-2 opacity-50" />
            <span>No results found</span>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTopics.map((topic) => (
              <button
                key={topic.id}
                type="button"
                onClick={() => onTopicSelect(topic)}
                className={cn(
                  "w-full text-left p-3 rounded-lg",
                  "bg-gray-50 dark:bg-gray-800",
                  "border border-gray-100 dark:border-gray-700",
                  "hover:border-primary-300 dark:hover:border-primary-700",
                  "transition-colors",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {topic.title}
                  </span>
                  <span
                    className={cn(
                      "text-xs px-1.5 py-0.5 rounded",
                      getCategoryColor(topic.category),
                    )}
                  >
                    {topic.category}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                  {topic.content}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
