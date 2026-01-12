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
import { HelpCircle, Search, X, Loader2, BookOpen, Zap } from "lucide-react";
import { cn } from "../utils/cn";
import { useContextualHelp } from "../hooks/useUXIntelligence";

import { Button, Input } from "@/components/UI";

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
  onQuickAction?: (action: {
    id: string;
    label: string;
    action: string;
  }) => void;
}

// =============================================================================
// Utility
// =============================================================================

function getCategoryColor(category: string): string {
  switch (category) {
    case "basics":
      return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
    case "productivity":
      return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
    case "compliance":
      return "bg-insight-100 text-insight-700 dark:bg-insight-900/30 dark:text-insight-400";
    default:
      return "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-400";
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
          "rounded-lg border border-neutral-200 dark:border-neutral-700",
          "bg-white dark:bg-neutral-900 p-4",
          className,
        )}
      >
        <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
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
        "rounded-lg border border-neutral-200 dark:border-neutral-700",
        "bg-white dark:bg-neutral-900 flex flex-col",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-neutral-200 dark:border-neutral-700">
        <HelpCircle size={18} className="text-primary-500" />
        <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
          Help
        </h3>
      </div>
      {/* Search */}
      <div className="p-3 border-b border-neutral-200 dark:border-neutral-700">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
          />
          <Input
            placeholder="Search help topics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              "w-full pl-9 pr-9 py-2 rounded-lg",
              "bg-neutral-50 dark:bg-neutral-800",
              "border border-neutral-200 dark:border-neutral-700",
              "text-sm text-neutral-900 dark:text-neutral-100",
              "placeholder-neutral-400",
              "focus:outline-none focus:ring-2 focus:ring-primary-500",
            )}
          />
          {searchQuery && (
            <Button
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300"
              type="button"
              aria-label="Clear search"
              onClick={() => setSearchQuery("")}
            >
              <X size={16} />
            </Button>
          )}
        </div>
      </div>
      {/* AI Contextual Help Section (Sprint 6) */}
      {enableAI && !searchQuery && (
        <div
          data-testid="ai-contextual-help-section"
          className="p-3 border-b border-neutral-200 dark:border-neutral-700"
        >
          {/* Quick Actions */}
          {quickActions.length > 0 && (
            <div className="space-y-1">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1.5">
                Quick Actions
              </div>
              <div className="flex flex-wrap gap-1.5">
                {quickActions.map((action, index) => (
                  <Button
                    key={`${action.label}-${index}`}
                    type="button"
                    onClick={() =>
                      onQuickAction?.({
                        id: `action-${index}`,
                        label: action.label,
                        action: action.action,
                      })
                    }
                    className={cn(
                      "inline-flex items-center gap-1 px-2 py-1 rounded text-xs",
                      "bg-neutral-100 dark:bg-neutral-800",
                      "text-neutral-700 dark:text-neutral-300",
                      "hover:bg-primary-100 dark:hover:bg-primary-900/30",
                      "transition-colors",
                    )}
                  >
                    <Zap size={12} />
                    {action.label}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* AI-Suggested Topics */}
          {aiTopics && aiTopics.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                Related Topics
              </div>
              {aiTopics.slice(0, 3).map((topic) => (
                <Button
                  key={topic.id}
                  type="button"
                  onClick={() =>
                    onTopicSelect({
                      id: topic.id,
                      title: topic.title,
                      category: "ai-suggested",
                      content: topic.summary,
                      keywords: [],
                    })
                  }
                  className={cn(
                    "w-full text-left p-2 rounded-lg text-sm",
                    "bg-neutral-50 dark:bg-neutral-800",
                    "hover:bg-primary-50 dark:hover:bg-primary-900/20",
                    "transition-colors",
                  )}
                >
                  <span className="text-neutral-700 dark:text-neutral-300">
                    {topic.title}
                  </span>
                </Button>
              ))}
            </div>
          )}

          {/* Loading state for AI */}
          {aiLoading && (
            <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
              <Loader2 size={12} className="animate-spin" />
              <span>Finding relevant help...</span>
            </div>
          )}
        </div>
      )}
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {topics.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-sm text-neutral-500 dark:text-neutral-400">
            <BookOpen size={24} className="mb-2 opacity-50" />
            <span>No help topics available</span>
          </div>
        ) : filteredTopics.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-sm text-neutral-500 dark:text-neutral-400">
            <Search size={24} className="mb-2 opacity-50" />
            <span>No results found</span>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTopics.map((topic) => (
              <Button
                key={topic.id}
                type="button"
                onClick={() => onTopicSelect(topic)}
                className={cn(
                  "w-full text-left p-3 rounded-lg",
                  "bg-neutral-50 dark:bg-neutral-800",
                  "border border-neutral-100 dark:border-neutral-700",
                  "hover:border-primary-300 dark:hover:border-primary-700",
                  "transition-colors",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
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
                <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2">
                  {topic.content}
                </p>
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
