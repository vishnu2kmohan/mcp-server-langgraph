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

import { Button, Input, Select } from "@/components/UI";

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
  isSelected: _isSelected,
  onClick,
}: {
  template: PlanTemplate;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      variant="primary"
      className="w-full text-left p-4 rounded-lg border"
      type="button"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-neutral-12">{template.name}</h4>
        <span className="text-xs px-2 py-1 rounded-full bg-neutral-2 text-neutral-11">
          {template.orchestrator}
        </span>
      </div>
      <p className="text-sm text-neutral-11 mb-3 line-clamp-2">
        {template.description}
      </p>
      <div className="flex items-center justify-between text-xs text-neutral-10">
        <span>{template.useCount} uses</span>
        <span>{Math.round(template.successRate * 100)}% success</span>
      </div>
      {template.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {template.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs px-1.5 py-0.5 rounded bg-neutral-2 text-neutral-11"
            >
              {tag}
            </span>
          ))}
          {template.tags.length > 3 && (
            <span className="text-xs text-neutral-9">
              +{template.tags.length - 3}
            </span>
          )}
        </div>
      )}
    </Button>
  );
}

function LoadingIndicator() {
  return (
    <div role="status" className="flex items-center justify-center p-8">
      <Loader2 className="w-6 h-6 animate-spin text-primary-9" />
      <span className="sr-only">Loading templates...</span>
    </div>
  );
}

function EmptyState({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <div className="text-center p-8">
      <Search className="w-12 h-12 mx-auto text-neutral-9 mb-4" />
      <p className="text-neutral-11 mb-4">No templates found</p>
      <Button
        variant="secondary"
        className="text-primary-9 hover:text-primary-10 text-sm"
        type="button"
        onClick={onClearFilters}
      >
        Clear filters
      </Button>
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
      <AlertCircle className="w-12 h-12 mx-auto text-error-7 mb-4" />
      <p className="text-error-10 dark:text-error-7 mb-4">{message}</p>
      {onRetry && (
        <Button
          variant="danger"
          className="px-4 py-2 bg-error-3 bg-error-4 text-error-10 dark:text-error-7 rounded-lg text-sm hover:bg-error-4 dark:hover:bg-error-a6"
          type="button"
          onClick={onRetry}
        >
          Retry
        </Button>
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
    <div className="bg-neutral-1 rounded-lg shadow-sm border border-neutral-5">
      {/* Search Header */}
      <div className="p-4 border-b border-neutral-5">
        <div className="flex items-center gap-4 mb-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-9" />
            <Input
              className="pl-10 pr-4 py-2 text-sm text-neutral-12 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
              type="search"
              role="searchbox"
              aria-label="Search templates"
              placeholder="Search templates..."
              value={query}
              onChange={handleQueryChange}
              disabled={isLoading}
            />
          </div>

          {/* Orchestrator Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-neutral-9" />
            <Select
              className="px-3 py-2 text-sm text-neutral-12 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
              id="orchestrator-filter"
              aria-label="Orchestrator"
              value={orchestrator}
              onChange={handleOrchestratorChange}
              disabled={isLoading}
            >
              {ORCHESTRATOR_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <SortAsc className="w-4 h-4 text-neutral-9" />
            <Select
              className="px-3 py-2 text-sm text-neutral-12 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
              id="sort-by"
              aria-label="Sort by"
              value={sortBy}
              onChange={handleSortChange}
              disabled={isLoading}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {/* Tag Chips */}
        {allTags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <Tag className="w-4 h-4 text-neutral-9" />
            {allTags.map((tag) => (
              <Button
                variant="primary"
                size="sm"
                className="px-2 py-1 text-xs rounded-full border"
                key={tag}
                type="button"
                onClick={() => handleTagToggle(tag)}
                disabled={isLoading}
              >
                {tag}
              </Button>
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
