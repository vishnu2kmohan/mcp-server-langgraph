/**
 * OnboardingModal Component
 *
 * First-run onboarding modal with workflow template picker.
 * Helps new users choose a template to get started quickly.
 */

import { useState, useMemo } from "react";
import {
  Loader2,
  Sparkles,
  FileCode,
  Bot,
  Server,
  Users,
  X,
  RefreshCw,
} from "lucide-react";

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
}

export interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (template: WorkflowTemplate | null) => void;
  templates: WorkflowTemplate[];
  isLoading: boolean;
  error: string | null;
  onRetry?: () => void;
}

const categoryIcons: Record<string, React.ReactNode> = {
  conversational: <Bot className="w-5 h-5" />,
  agent: <Server className="w-5 h-5" />,
  pipeline: <FileCode className="w-5 h-5" />,
  collaboration: <Users className="w-5 h-5" />,
  default: <Sparkles className="w-5 h-5" />,
};

const getCategoryIcon = (category: string) => {
  return categoryIcons[category] || categoryIcons.default;
};

export function OnboardingModal({
  isOpen,
  onClose,
  onSelectTemplate,
  templates,
  isLoading,
  error,
  onRetry,
}: OnboardingModalProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  // Get unique categories from templates
  const categories = useMemo(() => {
    const cats = new Set(templates.map((t) => t.category));
    return ["all", ...Array.from(cats)];
  }, [templates]);

  // Filter templates by selected category
  const filteredTemplates = useMemo(() => {
    if (selectedCategory === "all") {
      return templates;
    }
    return templates.filter((t) => t.category === selectedCategory);
  }, [templates, selectedCategory]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <h2
                id="onboarding-title"
                className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2"
              >
                <Sparkles className="w-6 h-6 text-primary-500" />
                Welcome to Agent Studio
              </h2>
              <p className="mt-1 text-gray-600 dark:text-gray-400">
                Choose a template to get started, or start from scratch
              </p>
            </div>
            <button
              onClick={onClose}
              aria-label="Close"
              className="p-2 text-gray-400 dark:text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Category Filters */}
        {!isLoading && !error && templates.length > 0 && (
          <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700 flex gap-2 overflow-x-auto">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                aria-label={cat === "all" ? "All categories" : cat}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === cat
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
                }`}
              >
                {cat === "all"
                  ? "All"
                  : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Loading State */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2
                data-testid="loading-spinner"
                className="w-8 h-8 animate-spin text-primary-500"
              />
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                Loading templates...
              </p>
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-error-600 dark:text-error-400 mb-4">{error}</p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
              )}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && templates.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
              <FileCode className="w-12 h-12 mb-4 opacity-50" />
              <p>No templates available</p>
            </div>
          )}

          {/* Template Grid */}
          {!isLoading && !error && filteredTemplates.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredTemplates.map((template) => (
                <button
                  key={template.id}
                  onClick={() => onSelectTemplate(template)}
                  className="flex items-start gap-4 p-4 text-left rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/10 transition-all group"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-600 dark:text-gray-400 group-hover:bg-primary-100 group-hover:text-primary-600 dark:group-hover:bg-primary-900/30 dark:group-hover:text-primary-400 transition-colors">
                    {getCategoryIcon(template.category)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-primary-600 dark:group-hover:text-primary-400">
                      {template.name}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                      {template.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                        {template.category}
                      </span>
                      {template.tags.slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between bg-gray-50 dark:bg-gray-800/50">
          <button
            onClick={() => onSelectTemplate(null)}
            aria-label="Start from scratch"
            className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <FileCode className="w-4 h-4" />
            Start from scratch
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}
