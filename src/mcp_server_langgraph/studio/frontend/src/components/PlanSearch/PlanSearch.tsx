/**
 * PlanSearch Component
 *
 * Template search component with semantic search, field filters,
 * and sort options for finding reusable plan templates.
 *
 * Features:
 * - Natural language semantic search
 * - Filter by orchestrator type
 * - Filter by tags
 * - Sort by popularity, success rate, or recency
 */

import { useState, useCallback, useEffect, useRef } from "react";
import {
  Search,
  Filter,
  SortAsc,
  Tag,
  Loader2,
  AlertCircle,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type OrchestratorType = "standard" | "swarm" | "studio" | "ux" | "alert";
export type ThinkingBudget = "none" | "light" | "medium" | "deep";
export type SortOption = "popularity" | "success_rate" | "recent";

export interface PlanTemplate {
  templateId: string;
  name: string;
  description: string;
  orchestrator: OrchestratorType;
  thinkingBudget: ThinkingBudget;
  critiqueRounds: number;
  autoApprove: boolean;
  createdBy: string;
  createdAt: string;
  useCount: number;
  successRate: number;
  tags: string[];
}

export interface SearchParams {
  query?: string;
  orchestrator?: OrchestratorType | "";
  tags?: string[];
  sortBy?: SortOption;
}

export interface PlanSearchProps {
  /** Available templates to display */
  templates: PlanTemplate[];
  /** Callback when search params change */
  onSearch: (params: SearchParams) => void;
  /** Callback when a template is selected */
  onSelect: (template: PlanTemplate) => void;
  /** Whether search is in progress */
  isLoading?: boolean;
  /** Error message to display */
  error?: string;
  /** Callback for retry on error */
  onRetry?: () => void;
  /** ID of currently selected template */
  selectedTemplateId?: string;
}

// =============================================================================
// Constants
// =============================================================================

const ORCHESTRATOR_OPTIONS: { value: OrchestratorType | ""; label: string }[] =
  [
    { value: "", label: "All Orchestrators" },
    { value: "standard", label: "Standard" },
    { value: "swarm", label: "Swarm" },
    { value: "studio", label: "Studio" },
    { value: "ux", label: "UX" },
    { value: "alert", label: "Alert" },
  ];

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "popularity", label: "Popularity" },
  { value: "success_rate", label: "Success Rate" },
  { value: "recent", label: "Recent" },
];

const DEBOUNCE_MS = 300;

// =============================================================================
// Helper Components
// =============================================================================

function TemplateCard({
  template,
  isSelected,
  onClick,
}: {
  template: PlanTemplate;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left p-4 rounded-lg border transition-all ${
        isSelected
          ? "ring-2 ring-primary-500 border-primary-500 bg-primary-50 dark:bg-primary-900/20"
          : "border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 bg-white dark:bg-gray-800"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-gray-900 dark:text-white">
          {template.name}
        </h4>
        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
          {template.orchestrator}
        </span>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
        {template.description}
      </p>

      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>{template.useCount} uses</span>
        <span>{Math.round(template.successRate * 100)}% success</span>
      </div>

      {template.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {template.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
            >
              {tag}
            </span>
          ))}
          {template.tags.length > 3 && (
            <span className="text-xs text-gray-400 dark:text-gray-400">
              +{template.tags.length - 3}
            </span>
          )}
        </div>
      )}
    </button>
  );
}

function LoadingIndicator() {
  return (
    <div role="status" className="flex items-center justify-center p-8">
      <Loader2 className="w-6 h-6 animate-spin text-primary-500" />
      <span className="sr-only">Loading templates...</span>
    </div>
  );
}

function EmptyState({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <div className="text-center p-8">
      <Search className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 dark:text-gray-300 mb-4" />
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        No templates found
      </p>
      <button
        type="button"
        onClick={onClearFilters}
        className="text-primary-500 hover:text-primary-600 text-sm font-medium"
      >
        Clear filters
      </button>
    </div>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="text-center p-8">
      <AlertCircle className="w-12 h-12 mx-auto text-error-400 mb-4" />
      <p className="text-error-600 dark:text-error-400 mb-4">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400 rounded-lg text-sm font-medium hover:bg-error-200 dark:hover:bg-error-900/50"
        >
          Retry
        </button>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function PlanSearch({
  templates,
  onSearch,
  onSelect,
  isLoading = false,
  error,
  onRetry,
  selectedTemplateId,
}: PlanSearchProps) {
  const [query, setQuery] = useState("");
  const [orchestrator, setOrchestrator] = useState<OrchestratorType | "">("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortOption>("popularity");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Collect all unique tags from templates
  const allTags = Array.from(new Set(templates.flatMap((t) => t.tags)));

  // Debounced search callback
  const debouncedSearch = useCallback(
    (params: SearchParams) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        onSearch(params);
      }, DEBOUNCE_MS);
    },
    [onSearch],
  );

  // Immediate search (for non-text inputs)
  const immediateSearch = useCallback(
    (params: SearchParams) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      onSearch(params);
    },
    [onSearch],
  );

  // Handle query input change
  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setQuery(newQuery);
    debouncedSearch({
      query: newQuery,
      orchestrator,
      tags: selectedTags,
      sortBy,
    });
  };

  // Handle orchestrator filter change
  const handleOrchestratorChange = (
    e: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    const newOrchestrator = e.target.value as OrchestratorType | "";
    setOrchestrator(newOrchestrator);
    immediateSearch({
      query,
      orchestrator: newOrchestrator,
      tags: selectedTags,
      sortBy,
    });
  };

  // Handle sort change
  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newSortBy = e.target.value as SortOption;
    setSortBy(newSortBy);
    immediateSearch({
      query,
      orchestrator,
      tags: selectedTags,
      sortBy: newSortBy,
    });
  };

  // Handle tag toggle
  const handleTagToggle = (tag: string) => {
    const newTags = selectedTags.includes(tag)
      ? selectedTags.filter((t) => t !== tag)
      : [...selectedTags, tag];
    setSelectedTags(newTags);
    immediateSearch({
      query,
      orchestrator,
      tags: newTags,
      sortBy,
    });
  };

  // Clear all filters
  const handleClearFilters = () => {
    setQuery("");
    setOrchestrator("");
    setSelectedTags([]);
    setSortBy("popularity");
    immediateSearch({
      query: "",
      orchestrator: "",
      tags: [],
      sortBy: "popularity",
    });
  };

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      {/* Search Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4 mb-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-400" />
            <input
              type="search"
              role="searchbox"
              aria-label="Search templates"
              placeholder="Search templates..."
              value={query}
              onChange={handleQueryChange}
              disabled={isLoading}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {/* Orchestrator Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400 dark:text-gray-400" />
            <select
              id="orchestrator-filter"
              aria-label="Orchestrator"
              value={orchestrator}
              onChange={handleOrchestratorChange}
              disabled={isLoading}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {ORCHESTRATOR_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <SortAsc className="w-4 h-4 text-gray-400 dark:text-gray-400" />
            <select
              id="sort-by"
              aria-label="Sort by"
              value={sortBy}
              onChange={handleSortChange}
              disabled={isLoading}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Tag Chips */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <Tag className="w-4 h-4 text-gray-400 dark:text-gray-400" />
            {allTags.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => handleTagToggle(tag)}
                disabled={isLoading}
                className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                  selectedTags.includes(tag)
                    ? "bg-primary-500 text-white border-primary-500"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-700 dark:border-gray-600 hover:border-primary-300"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results */}
      <div className="p-4">
        {error ? (
          <ErrorState message={error} onRetry={onRetry} />
        ) : isLoading ? (
          <LoadingIndicator />
        ) : templates.length === 0 ? (
          <EmptyState onClearFilters={handleClearFilters} />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {templates.map((template) => (
              <TemplateCard
                key={template.templateId}
                template={template}
                isSelected={template.templateId === selectedTemplateId}
                onClick={() => onSelect(template)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
