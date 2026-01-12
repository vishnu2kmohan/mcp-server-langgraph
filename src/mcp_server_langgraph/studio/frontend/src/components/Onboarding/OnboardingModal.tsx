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

import { Button } from "@/components/UI";

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
      <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between">
            <div>
              <h2
                id="onboarding-title"
                className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 flex items-center gap-2"
              >
                <Sparkles className="w-6 h-6 text-primary-500" />
                Welcome to Agent Studio
              </h2>
              <p className="mt-1 text-neutral-600 dark:text-neutral-400">
                Choose a template to get started, or start from scratch
              </p>
            </div>
            <Button
              variant="secondary"
              className="p-2 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300 rounded-lg hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Category Filters */}
        {!isLoading && !error && templates.length > 0 && (
          <div className="px-6 py-3 border-b border-neutral-200 dark:border-neutral-700 flex gap-2 overflow-x-auto">
            {categories.map((cat) => (
              <Button
                className="px-3 py-1.5 rounded-full text-sm"
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                aria-label={cat === "all" ? "All categories" : cat}
              >
                {cat === "all"
                  ? "All"
                  : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </Button>
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
              <p className="mt-4 text-neutral-600 dark:text-neutral-400">
                Loading templates...
              </p>
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-error-600 dark:text-error-400 mb-4">{error}</p>
              {onRetry && (
                <Button
                  variant="primary"
                  className="flex px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  onClick={onRetry}
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </Button>
              )}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && templates.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-neutral-500 dark:text-neutral-400">
              <FileCode className="w-12 h-12 mb-4 opacity-50" />
              <p>No templates available</p>
            </div>
          )}

          {/* Template Grid */}
          {!isLoading && !error && filteredTemplates.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredTemplates.map((template) => (
                <Button
                  variant="primary"
                  className="flex items-start p-4 text-left rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-primary-500 dark:hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/10 group"
                  key={template.id}
                  onClick={() => onSelectTemplate(template)}
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-neutral-100 dark:bg-neutral-700 flex items-center justify-center text-neutral-600 dark:text-neutral-400 group-hover:bg-primary-100 group-hover:text-primary-600 dark:group-hover:bg-primary-900/30 dark:group-hover:text-primary-400 transition-colors">
                    {getCategoryIcon(template.category)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-neutral-900 dark:text-neutral-100 group-hover:text-primary-600 dark:group-hover:text-primary-400">
                      {template.name}
                    </h3>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1 line-clamp-2">
                      {template.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 text-xs rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400">
                        {template.category}
                      </span>
                      {template.tags.slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 text-xs rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </Button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between bg-neutral-50 dark:bg-neutral-800/50">
          <Button
            variant="secondary"
            className="flex px-4 py-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded-lg"
            onClick={() => onSelectTemplate(null)}
            aria-label="Start from scratch"
          >
            <FileCode className="w-4 h-4" />
            Start from scratch
          </Button>
          <Button
            className="px-4 py-2 text-neutral-600 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200"
            onClick={onClose}
          >
            Skip for now
          </Button>
        </div>
      </div>
    </div>
  );
}
