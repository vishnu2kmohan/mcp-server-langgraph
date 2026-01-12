/**
 * SharedWorkflowsList
 *
 * Displays workflows that have been shared with the current user.
 * Part of Bob's standard user journey - viewing and executing
 * workflows shared by other users.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
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
  Lock,
  Edit3,
} from "lucide-react";
import { authenticatedFetch } from "../../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../../utils/intendedRoute";

import { Button, Input, Select } from "@/components/UI";

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
  onEdit?: (workflowId: string) => void;
}

export function SharedWorkflowsList({
  onView,
  onExecute,
  onEdit,
}: SharedWorkflowsListProps) {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<SharedWorkflow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [searchText, setSearchText] = useState("");
  const [permissionFilter, setPermissionFilter] = useState("");
  const [sharedByFilter, setSharedByFilter] = useState("");

  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  const fetchSharedWorkflows = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        "/api/v1/workflows/shared-with-me",
        {
          onAuthFailure: handleAuthFailure,
        },
      );

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
  }, [handleAuthFailure]);

  useEffect(() => {
    fetchSharedWorkflows();
  }, [fetchSharedWorkflows]);

  const getPermissionBadgeStyle = (permission: string) => {
    switch (permission) {
      case "editor":
        return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
      case "executor":
        return "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400";
      case "viewer":
      default:
        return "bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300";
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

  const canEdit = (permission: string) => {
    return permission === "editor";
  };

  const isViewOnly = (permission: string) => {
    return permission === "viewer";
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
    <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
      {/* Header */}
      <div className="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Share2 className="text-primary-500" size={24} />
            <div>
              <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
                Shared With Me
              </h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                Workflows shared by other users
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="flex px-3 py-1.5 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 rounded-lg hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
            onClick={fetchSharedWorkflows}
            aria-label="Refresh"
          >
            <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
            Refresh
          </Button>
        </div>
      </div>
      {/* Filters - only show when we have workflows */}
      {!isLoading && !error && workflows.length > 0 && (
        <div className="px-6 py-3 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900">
          <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative flex-1 min-w-[200px]">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
                size={16}
              />
              <Input
                className="pl-9 pr-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search workflows..."
              />
            </div>

            {/* Permission Filter */}
            <Select
              className="px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100"
              value={permissionFilter}
              onChange={(e) => setPermissionFilter(e.target.value)}
              aria-label="Filter by permission"
            >
              <option value="">All Permissions</option>
              <option value="viewer">Viewer</option>
              <option value="executor">Executor</option>
              <option value="editor">Editor</option>
            </Select>

            {/* Shared By Filter */}
            <Select
              className="px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100"
              value={sharedByFilter}
              onChange={(e) => setSharedByFilter(e.target.value)}
              aria-label="Filter by shared by"
            >
              <option value="">All Users</option>
              {uniqueSharedByUsers.map((user) => (
                <option key={user} value={user}>
                  {user}
                </option>
              ))}
            </Select>

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <Button
                variant="secondary"
                className="flex .5 px-3 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded-lg"
                onClick={clearFilters}
                aria-label="Clear filters"
              >
                <X size={14} />
                Clear filters
              </Button>
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
              className="animate-spin text-primary-500"
            />
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertCircle size={48} className="text-error-500 mb-4" />
            <p className="text-error-600 dark:text-error-400 mb-4">{error}</p>
            <Button
              variant="danger"
              className="px-4 py-2 bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200"
              onClick={fetchSharedWorkflows}
              aria-label="Retry"
            >
              Retry
            </Button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && workflows.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Inbox
              size={48}
              className="text-neutral-400 dark:text-neutral-400 mb-4"
            />
            <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
              No workflows shared with you
            </h3>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
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
              <Search
                size={48}
                className="text-neutral-400 dark:text-neutral-400 mb-4"
              />
              <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
                No workflows match your filters
              </h3>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
                Try adjusting your search or filter criteria.
              </p>
              <Button
                variant="primary"
                className="px-4 py-2 text-sm bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 rounded-lg hover:bg-primary-200"
                onClick={clearFilters}
              >
                Clear filters
              </Button>
            </div>
          )}

        {/* Workflow List */}
        {!isLoading && !error && filteredWorkflows.length > 0 && (
          <div className="space-y-4">
            {filteredWorkflows.map((workflow) => (
              <div
                key={workflow.id}
                className={`flex items-center justify-between p-4 bg-neutral-50 dark:bg-neutral-900 rounded-lg border ${
                  isViewOnly(workflow.permission)
                    ? "border-warning-200 dark:border-warning-800"
                    : "border-neutral-200 dark:border-neutral-700"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    {/* Lock icon for view-only workflows */}
                    {isViewOnly(workflow.permission) && (
                      <Lock
                        size={14}
                        className="text-warning-600 dark:text-warning-400 flex-shrink-0"
                        data-testid={`lock-icon-${workflow.id}`}
                      />
                    )}
                    <h3 className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
                      {workflow.name}
                    </h3>
                    {/* Show "View Only" badge for viewer permission, otherwise show permission level */}
                    {isViewOnly(workflow.permission) ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400 flex items-center gap-1">
                        View Only
                      </span>
                    ) : (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${getPermissionBadgeStyle(workflow.permission)}`}
                      >
                        {workflow.permission.charAt(0).toUpperCase() +
                          workflow.permission.slice(1)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate mb-1">
                    {workflow.description}
                  </p>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400">
                    Shared by {workflow.shared_by} on{" "}
                    {formatDate(workflow.shared_at)}
                  </p>
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="secondary"
                    className="flex .5 px-3 py-1.5 text-sm bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded-lg hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600"
                    onClick={() => onView?.(workflow.id)}
                    aria-label="View"
                  >
                    <Eye size={14} />
                    View
                  </Button>
                  {/* Edit button - disabled for viewer, enabled for editor */}
                  <Button
                    className="flex .5 px-3 py-1.5 text-sm rounded-lg"
                    onClick={() =>
                      canEdit(workflow.permission) && onEdit?.(workflow.id)
                    }
                    disabled={!canEdit(workflow.permission)}
                    aria-label="Edit"
                    title={
                      canEdit(workflow.permission)
                        ? "Edit workflow"
                        : "Shared with you as read-only"
                    }
                  >
                    <Edit3 size={14} />
                    Edit
                  </Button>
                  {canExecute(workflow.permission) && (
                    <Button
                      variant="success"
                      className="flex .5 px-3 py-1.5 text-sm bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400 rounded-lg hover:bg-success-200 dark:hover:bg-success-900/50"
                      onClick={() => onExecute?.(workflow.id)}
                      aria-label="Execute"
                    >
                      <Play size={14} />
                      Execute
                    </Button>
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
