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
      className="fixed inset-0 z-60 flex items-center justify-center bg-neutral-a7"
    >
      <div className="bg-neutral-2 border border-neutral-6 rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col backdrop-blur-sm">
        {/* Header */}
        <div className="px-6 py-5 border-b border-neutral-6">
          <div className="flex items-center justify-between">
            <div>
              <h2
                id="onboarding-title"
                className="text-2xl font-bold text-neutral-12 flex items-center gap-2"
              >
                <Sparkles className="w-6 h-6 text-primary-9" />
                Welcome to Agent Studio
              </h2>
              <p className="mt-1 text-neutral-11">
                Choose a template to get started, or start from scratch
              </p>
            </div>
            <Button
              size="icon"
              variant="secondary"
              className="p-2 rounded-lg text-neutral-9 hover:text-neutral-11 hover:bg-neutral-3"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Category Filters */}
        {!isLoading && !error && templates.length > 0 && (
          <div className="px-6 py-3 border-b border-neutral-6 flex gap-2 overflow-x-auto">
            {categories.map((cat) => (
              <Button
                variant="primary"
                className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                  selectedCategory === cat
                    ? "bg-primary-3 text-primary-11"
                    : "bg-neutral-3 text-neutral-11 hover:bg-neutral-4"
                }`}
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
                className="w-8 h-8 animate-spin text-primary-9"
              />
              <p className="mt-4 text-neutral-11">Loading templates...</p>
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <p className="text-error-11 mb-4">{error}</p>
              {onRetry && (
                <Button
                  variant="primary"
                  className="flex gap-2 px-4 py-2 bg-primary-9 text-neutral-12 rounded-lg hover:bg-primary-10"
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
            <div className="flex flex-col items-center justify-center py-12 text-neutral-9">
              <FileCode className="w-12 h-12 mb-4 opacity-50" />
              <p>No templates available</p>
            </div>
          )}

          {/* Template Grid */}
          {!isLoading && !error && filteredTemplates.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredTemplates.map((template) => (
                <Button
                  variant="secondary"
                  className="flex items-start gap-3 p-4 text-left rounded-lg border-2 border-neutral-6 bg-neutral-3 hover:border-primary-7 hover:bg-neutral-4 group transition-colors"
                  key={template.id}
                  onClick={() => onSelectTemplate(template)}
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-neutral-4 flex items-center justify-center text-neutral-11 group-hover:bg-primary-3 group-hover:text-primary-11 transition-colors">
                    {getCategoryIcon(template.category)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-neutral-12 group-hover:text-primary-11">
                      {template.name}
                    </h3>
                    <p className="text-sm text-neutral-11 mt-1 line-clamp-2">
                      {template.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 text-xs rounded-full bg-neutral-4 text-neutral-11">
                        {template.category}
                      </span>
                      {template.tags.slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 text-xs rounded-full bg-neutral-4 text-neutral-11"
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
        <div className="px-6 py-4 border-t border-neutral-6 flex items-center justify-between bg-neutral-2">
          <Button
            variant="secondary"
            className="flex gap-2 px-4 py-2 text-neutral-11 hover:bg-neutral-4 rounded-lg"
            onClick={() => onSelectTemplate(null)}
            aria-label="Start from scratch"
          >
            <FileCode className="w-4 h-4" />
            Start from scratch
          </Button>
          <Button
            variant="secondary"
            className="px-4 py-2 text-neutral-9 hover:text-neutral-11"
            onClick={onClose}
          >
            Skip for now
          </Button>
        </div>
      </div>
    </div>
  );
}
