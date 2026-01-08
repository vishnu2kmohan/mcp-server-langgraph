/**
 * ResourceBrowser Component
 *
 * Browse and view aggregated resources from all connected MCP servers.
 * Supports the MCP Protocol 2025-11-25 capability aggregation feature.
 */

import { useState, useMemo } from "react";
import { useListAggregatedResourcesQuery } from "../../api";
import { Badge } from "../UI/Badge";
import { Card } from "../UI/Card";

export interface ResourceBrowserProps {
  /** Optional filter by server name */
  serverFilter?: string;
  /** Callback when view button is clicked */
  onView?: (qualifiedName: string) => void;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * ResourceBrowser component for browsing aggregated resources
 */
export function ResourceBrowser({
  serverFilter,
  onView,
}: ResourceBrowserProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const { data, isLoading, error } =
    useListAggregatedResourcesQuery(serverFilter);

  // Filter resources by search term
  const filteredResources = useMemo(() => {
    if (!data?.resources) return [];

    const term = searchTerm.toLowerCase();
    if (!term) return data.resources;

    return data.resources.filter(
      (resource) =>
        resource.qualifiedName.toLowerCase().includes(term) ||
        resource.uri.toLowerCase().includes(term) ||
        resource.name.toLowerCase().includes(term) ||
        (resource.description?.toLowerCase().includes(term) ?? false) ||
        resource.serverName.toLowerCase().includes(term),
    );
  }, [data?.resources, searchTerm]);

  const handleView = (qualifiedName: string) => {
    onView?.(qualifiedName);
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
        Failed to load resources. Please try again.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Search input */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search resources..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={cn(
            "w-full px-4 py-2 rounded-lg border",
            "border-gray-300 dark:border-gray-600",
            "bg-white dark:bg-gray-800",
            "text-gray-900 dark:text-gray-100",
            "placeholder-gray-500 dark:placeholder-gray-400",
            "focus:outline-none focus:ring-2 focus:ring-brand-primary",
          )}
        />
        <svg
          className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-400"
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

      {/* Resource list */}
      <div className="flex flex-col gap-2">
        {filteredResources.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            No resources found
          </div>
        ) : (
          filteredResources.map((resource) => (
            <Card
              key={resource.qualifiedName}
              variant="default"
              padding="sm"
              className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                {/* Resource info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-sm font-medium text-gray-900 dark:text-gray-100">
                      {resource.qualifiedName}
                    </span>
                    <Badge variant="outline" size="sm">
                      {resource.serverName}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                    {resource.uri}
                  </p>
                  {resource.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-1">
                      {resource.description}
                    </p>
                  )}
                  {resource.mimeType && (
                    <Badge variant="default" size="sm" className="mt-1">
                      {resource.mimeType}
                    </Badge>
                  )}
                </div>

                {/* View button */}
                <button
                  type="button"
                  onClick={() => handleView(resource.qualifiedName)}
                  className={cn(
                    "shrink-0 px-3 py-1.5 text-sm font-medium rounded-md",
                    "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 dark:bg-gray-700 dark:text-gray-200",
                    "hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600",
                    "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2",
                    "transition-colors",
                  )}
                >
                  View
                </button>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
