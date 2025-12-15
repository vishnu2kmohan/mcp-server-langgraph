/**
 * SharedWorkflowsList
 *
 * Displays workflows that have been shared with the current user.
 * Part of Bob's standard user journey - viewing and executing
 * workflows shared by other users.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  RefreshCw,
  Eye,
  Play,
  Share2,
  Loader2,
  AlertCircle,
  Inbox,
  Search,
  X,
} from "lucide-react";

interface SharedWorkflow {
  id: string;
  name: string;
  description: string;
  shared_by: string;
  permission: "viewer" | "executor" | "editor";
  shared_at: string;
}

export interface SharedWorkflowsListProps {
  onView?: (workflowId: string) => void;
  onExecute?: (workflowId: string) => void;
}

export function SharedWorkflowsList({
  onView,
  onExecute,
}: SharedWorkflowsListProps) {
  const [workflows, setWorkflows] = useState<SharedWorkflow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [searchText, setSearchText] = useState("");
  const [permissionFilter, setPermissionFilter] = useState("");
  const [sharedByFilter, setSharedByFilter] = useState("");

  const fetchSharedWorkflows = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("auth_token");
      const response = await fetch("/api/v1/workflows/shared", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Failed to fetch shared workflows");
      }

      const data = await response.json();
      setWorkflows(data.workflows || []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch shared workflows",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSharedWorkflows();
  }, [fetchSharedWorkflows]);

  const getPermissionBadgeStyle = (permission: string) => {
    switch (permission) {
      case "editor":
        return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
      case "executor":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
      case "viewer":
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const canExecute = (permission: string) => {
    return permission === "executor" || permission === "editor";
  };

  // Get unique users who shared workflows
  const uniqueSharedByUsers = useMemo(() => {
    const users = new Set(workflows.map((w) => w.shared_by));
    return Array.from(users).sort();
  }, [workflows]);

  // Filter workflows based on search and filter criteria
  const filteredWorkflows = useMemo(() => {
    return workflows.filter((workflow) => {
      // Search filter (name or description)
      if (searchText.trim()) {
        const search = searchText.toLowerCase();
        if (
          !workflow.name.toLowerCase().includes(search) &&
          !workflow.description.toLowerCase().includes(search)
        ) {
          return false;
        }
      }

      // Permission filter
      if (permissionFilter && workflow.permission !== permissionFilter) {
        return false;
      }

      // Shared by filter
      if (sharedByFilter && workflow.shared_by !== sharedByFilter) {
        return false;
      }

      return true;
    });
  }, [workflows, searchText, permissionFilter, sharedByFilter]);

  // Check if any filters are active
  const hasActiveFilters =
    searchText.trim() !== "" ||
    permissionFilter !== "" ||
    sharedByFilter !== "";

  // Clear all filters
  const clearFilters = () => {
    setSearchText("");
    setPermissionFilter("");
    setSharedByFilter("");
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Share2 className="text-blue-500" size={24} />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Shared With Me
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Workflows shared by other users
              </p>
            </div>
          </div>
          <button
            onClick={fetchSharedWorkflows}
            aria-label="Refresh"
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters - only show when we have workflows */}
      {!isLoading && !error && workflows.length > 0 && (
        <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[200px]">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                size={16}
              />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search workflows..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Permission Filter */}
            <select
              value={permissionFilter}
              onChange={(e) => setPermissionFilter(e.target.value)}
              aria-label="Filter by permission"
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="">All Permissions</option>
              <option value="viewer">Viewer</option>
              <option value="executor">Executor</option>
              <option value="editor">Editor</option>
            </select>

            {/* Shared By Filter */}
            <select
              value={sharedByFilter}
              onChange={(e) => setSharedByFilter(e.target.value)}
              aria-label="Filter by shared by"
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="">All Users</option>
              {uniqueSharedByUsers.map((user) => (
                <option key={user} value={user}>
                  {user}
                </option>
              ))}
            </select>

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                aria-label="Clear filters"
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg"
              >
                <X size={14} />
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="p-6">
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2
              data-testid="loading-spinner"
              size={32}
              className="animate-spin text-blue-500"
            />
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertCircle size={48} className="text-red-500 mb-4" />
            <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
            <button
              onClick={fetchSharedWorkflows}
              aria-label="Retry"
              className="px-4 py-2 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg hover:bg-red-200"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && workflows.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Inbox size={48} className="text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No workflows shared with you
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ask a colleague to share a workflow with you to collaborate.
            </p>
          </div>
        )}

        {/* No Matches State (when filters active but no results) */}
        {!isLoading &&
          !error &&
          workflows.length > 0 &&
          filteredWorkflows.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Search size={48} className="text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                No workflows match your filters
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                Try adjusting your search or filter criteria.
              </p>
              <button
                onClick={clearFilters}
                className="px-4 py-2 text-sm bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-lg hover:bg-blue-200"
              >
                Clear filters
              </button>
            </div>
          )}

        {/* Workflow List */}
        {!isLoading && !error && filteredWorkflows.length > 0 && (
          <div className="space-y-4">
            {filteredWorkflows.map((workflow) => (
              <div
                key={workflow.id}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {workflow.name}
                    </h3>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${getPermissionBadgeStyle(workflow.permission)}`}
                    >
                      {workflow.permission.charAt(0).toUpperCase() +
                        workflow.permission.slice(1)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 truncate mb-1">
                    {workflow.description}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">
                    Shared by {workflow.shared_by} on{" "}
                    {formatDate(workflow.shared_at)}
                  </p>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => onView?.(workflow.id)}
                    aria-label="View"
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
                  >
                    <Eye size={14} />
                    View
                  </button>
                  {canExecute(workflow.permission) && (
                    <button
                      onClick={() => onExecute?.(workflow.id)}
                      aria-label="Execute"
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50"
                    >
                      <Play size={14} />
                      Execute
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default SharedWorkflowsList;
