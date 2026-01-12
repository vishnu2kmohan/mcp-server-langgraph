/**
 * HelpPanel Component
 *
 * Contextual help panel that provides tips and documentation links.
 * Context-aware based on current page/feature being used.
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import {
  X,
  Search,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  HelpCircle,
  Lightbulb,
  BookOpen,
} from "lucide-react";

import { Button, Input } from "@/components/UI";

export interface HelpTip {
  id: string;
  content: string;
  icon: string;
  details?: string;
}

export interface HelpArticle {
  id: string;
  title: string;
  url: string;
  description: string;
}

export interface HelpPanelProps {
  isOpen: boolean;
  contextId: string;
  tips: HelpTip[];
  articles: HelpArticle[];
  onClose: () => void;
  contextTitle?: string;
}

export function HelpPanel({
  isOpen,
  tips,
  articles,
  onClose,
  contextTitle,
}: HelpPanelProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTips, setExpandedTips] = useState<Set<string>>(new Set());

  // Filter tips and articles by search query
  const filteredTips = useMemo(() => {
    if (!searchQuery) return tips;
    const query = searchQuery.toLowerCase();
    return tips.filter(
      (tip) =>
        tip.content.toLowerCase().includes(query) ||
        tip.details?.toLowerCase().includes(query),
    );
  }, [tips, searchQuery]);

  const filteredArticles = useMemo(() => {
    if (!searchQuery) return articles;
    const query = searchQuery.toLowerCase();
    return articles.filter(
      (article) =>
        article.title.toLowerCase().includes(query) ||
        article.description.toLowerCase().includes(query),
    );
  }, [articles, searchQuery]);

  const hasNoResults =
    searchQuery && filteredTips.length === 0 && filteredArticles.length === 0;

  const toggleTipExpanded = useCallback((tipId: string) => {
    setExpandedTips((prev) => {
      const next = new Set(prev);
      if (next.has(tipId)) {
        next.delete(tipId);
      } else {
        next.add(tipId);
      }
      return next;
    });
  }, []);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return (
    <aside
      role="complementary"
      aria-label="Contextual help panel"
      className="fixed right-0 top-0 bottom-0 w-80 bg-white dark:bg-neutral-800 border-l border-neutral-200 dark:border-neutral-700 shadow-xl z-[50] flex flex-col"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-primary-500" />
          <h2 className="font-semibold text-neutral-900 dark:text-neutral-100">
            {contextTitle || "Help"}
          </h2>
        </div>
        <Button
          className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300 rounded"
          onClick={onClose}
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>
      {/* Search */}
      <div className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 dark:text-neutral-400" />
          <Input
            className="pl-9 pr-4 py-2 bg-neutral-100 border-0 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-500 dark:placeholder-neutral-400 focus:ring-primary-500"
            type="search"
            role="searchbox"
            placeholder="Search help..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* No Results */}
        {hasNoResults && (
          <div className="px-4 py-8 text-center text-neutral-500 dark:text-neutral-400">
            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No results found</p>
          </div>
        )}

        {/* Tips Section */}
        {filteredTips.length > 0 && (
          <div className="p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
              <Lightbulb className="w-4 h-4 text-warning-500" />
              Tips
            </h3>
            <div className="space-y-2">
              {filteredTips.map((tip) => (
                <div
                  key={tip.id}
                  className="p-3 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg"
                >
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    {tip.content}
                  </p>
                  {tip.details && (
                    <>
                      <Button
                        size="sm"
                        className="flex mt-2 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700"
                        onClick={() => toggleTipExpanded(tip.id)}
                        aria-label="More"
                      >
                        {expandedTips.has(tip.id) ? (
                          <>
                            <ChevronUp className="w-3 h-3" />
                            Less
                          </>
                        ) : (
                          <>
                            <ChevronDown className="w-3 h-3" />
                            More
                          </>
                        )}
                      </Button>
                      {expandedTips.has(tip.id) && (
                        <p className="mt-2 text-xs text-neutral-600 dark:text-neutral-400">
                          {tip.details}
                        </p>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Articles Section */}
        {filteredArticles.length > 0 && (
          <div className="p-4 border-t border-neutral-200 dark:border-neutral-700">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
              <BookOpen className="w-4 h-4 text-primary-500" />
              Documentation
            </h3>
            <div className="space-y-2">
              {filteredArticles.map((article) => (
                <a
                  key={article.id}
                  href={article.url}
                  aria-label={article.title}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-3 p-3 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 group-hover:text-primary-600 dark:group-hover:text-primary-400">
                      {article.title}
                    </h4>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                      {article.description}
                    </p>
                  </div>
                  <ExternalLink className="w-4 h-4 text-neutral-400 dark:text-neutral-400 group-hover:text-primary-500 flex-shrink-0 mt-0.5" />
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default HelpPanel;
