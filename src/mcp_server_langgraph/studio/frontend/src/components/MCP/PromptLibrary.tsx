/**
 * PromptLibrary Component
 *
 * Browse and test aggregated prompts from all connected MCP servers.
 * Supports the MCP Protocol 2025-11-25 capability aggregation feature.
 */

import { useState, useMemo } from "react";
import { useListAggregatedPromptsQuery } from "../../api";
import { Badge } from "../UI/Badge";
import { Card } from "../UI/Card";

import { Button, Input } from "@/components/UI";

export interface PromptLibraryProps {
  /** Optional filter by server name */
  serverFilter?: string;
  /** Callback when test button is clicked */
  onTest?: (qualifiedName: string) => void;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Chevron icon for expand/collapse
 */
function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={cn("w-4 h-4 transition-transform", expanded && "rotate-180")}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 9l-7 7-7-7"
      />
    </svg>
  );
}

/**
 * PromptLibrary component for browsing and testing aggregated prompts
 */
export function PromptLibrary({ serverFilter, onTest }: PromptLibraryProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedPrompts, setExpandedPrompts] = useState<Set<string>>(
    new Set(),
  );
  const { data, isLoading, error } =
    useListAggregatedPromptsQuery(serverFilter);

  // Filter prompts by search term
  const filteredPrompts = useMemo(() => {
    if (!data?.prompts) return [];

    const term = searchTerm.toLowerCase();
    if (!term) return data.prompts;

    return data.prompts.filter(
      (prompt) =>
        prompt.qualifiedName.toLowerCase().includes(term) ||
        prompt.name.toLowerCase().includes(term) ||
        (prompt.description?.toLowerCase().includes(term) ?? false) ||
        prompt.serverName.toLowerCase().includes(term),
    );
  }, [data?.prompts, searchTerm]);

  const handleTest = (qualifiedName: string) => {
    onTest?.(qualifiedName);
  };

  const toggleExpanded = (qualifiedName: string) => {
    setExpandedPrompts((prev) => {
      const next = new Set(prev);
      if (next.has(qualifiedName)) {
        next.delete(qualifiedName);
      } else {
        next.add(qualifiedName);
      }
      return next;
    });
  };

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center p-8"
        data-testid="loading-spinner"
      >
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-error-500">
        Failed to load prompts. Please try again.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Search input */}
      <div className="relative">
        <Input
          placeholder="Search prompts..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={cn(
            "w-full px-4 py-2 rounded-lg border",
            "border-neutral-300 dark:border-neutral-600",
            "bg-white dark:bg-neutral-800",
            "text-neutral-900 dark:text-neutral-100",
            "placeholder-neutral-500 dark:placeholder-neutral-400",
            "focus:outline-none focus:ring-2 focus:ring-brand-primary",
          )}
        />
        <svg
          className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 dark:text-neutral-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>
      {/* Prompt list */}
      <div className="flex flex-col gap-2">
        {filteredPrompts.length === 0 ? (
          <div className="p-4 text-center text-neutral-500 dark:text-neutral-400">
            No prompts found
          </div>
        ) : (
          filteredPrompts.map((prompt) => {
            const isExpanded = expandedPrompts.has(prompt.qualifiedName);
            return (
              <Card
                key={prompt.qualifiedName}
                variant="default"
                padding="sm"
                className="hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
              >
                <div className="flex flex-col">
                  {/* Header row */}
                  <div className="flex items-start justify-between gap-4">
                    {/* Prompt info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          {prompt.qualifiedName}
                        </span>
                        <Badge variant="outline" size="sm">
                          {prompt.serverName}
                        </Badge>
                      </div>
                      {prompt.description && (
                        <p className="text-sm text-neutral-600 dark:text-neutral-400 line-clamp-2">
                          {prompt.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-neutral-500 dark:text-neutral-400">
                          {prompt.arguments.length} arguments
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {prompt.arguments.length > 0 && (
                        <Button
                          type="button"
                          onClick={() => toggleExpanded(prompt.qualifiedName)}
                          aria-label="Expand"
                          className={cn(
                            "p-1.5 rounded-md",
                            "text-neutral-500 dark:text-neutral-400",
                            "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
                            "focus:outline-none focus:ring-2 focus:ring-brand-primary",
                          )}
                        >
                          <ChevronIcon expanded={isExpanded} />
                        </Button>
                      )}
                      <Button
                        type="button"
                        onClick={() => handleTest(prompt.qualifiedName)}
                        className={cn(
                          "shrink-0 px-3 py-1.5 text-sm font-medium rounded-md",
                          "bg-success-500 text-white",
                          "hover:bg-success-600",
                          "focus:outline-none focus:ring-2 focus:ring-success-500 focus:ring-offset-2",
                          "transition-colors",
                        )}
                      >
                        Test
                      </Button>
                    </div>
                  </div>

                  {/* Expanded arguments */}
                  {isExpanded && prompt.arguments.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
                      <h5 className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase mb-2">
                        Arguments
                      </h5>
                      <div className="space-y-2">
                        {prompt.arguments.map((arg) => (
                          <div
                            key={arg.name}
                            className="flex items-start gap-2 text-sm"
                          >
                            <span className="font-mono text-neutral-900 dark:text-neutral-100">
                              {arg.name}
                            </span>
                            {arg.required && (
                              <Badge variant="error" size="sm">
                                required
                              </Badge>
                            )}
                            {arg.description && (
                              <span className="text-neutral-500 dark:text-neutral-400">
                                - {arg.description}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
