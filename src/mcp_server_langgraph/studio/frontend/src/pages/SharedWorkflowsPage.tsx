/**
 * SharedWorkflowsPage Component
 *
 * Read-only view of workflows shared with the current user.
 * Accessible to all personas (admin, developer, user).
 *
 * HEART Metrics:
 * - Adoption: Provides value to standard users with shared resources
 * - Engagement: Browse and learn from shared workflows
 * - Task Success: View workflow details without editing
 */

import { useState, useMemo } from "react";
import { useNavigate } from "react-router";
import {
  GitBranch,
  Eye,
  User as UserIcon,
  Calendar,
  Loader2,
  Search,
} from "lucide-react";
import { useGetSharedWorkflowsQuery } from "../api";

interface SharedWorkflow {
  id: string;
  name: string;
  description?: string;
  owner: string;
  sharedWith: string[];
  createdAt: string;
}

type SortField = "name" | "createdAt" | "owner";
type SortOrder = "asc" | "desc";

export function SharedWorkflowsPage() {
  const navigate = useNavigate();
  const { data: workflows, isLoading, error } = useGetSharedWorkflowsQuery();

  // Search and sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("createdAt");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Filter and sort workflows
  const filteredWorkflows = useMemo(() => {
    const workflowList = workflows as SharedWorkflow[] | undefined;
    if (!workflowList) return [];

    // Filter by search query
    let result = workflowList;
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = workflowList.filter(
        (w) =>
          w.name.toLowerCase().includes(query) ||
          (w.description && w.description.toLowerCase().includes(query)) ||
          w.owner.toLowerCase().includes(query),
      );
    }

    // Sort
    result = [...result].sort((a, b) => {
      let compareVal = 0;
      switch (sortBy) {
        case "name":
          compareVal = a.name.localeCompare(b.name);
          break;
        case "owner":
          compareVal = a.owner.localeCompare(b.owner);
          break;
        case "createdAt":
        default:
          compareVal =
            new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
      }
      return sortOrder === "asc" ? compareVal : -compareVal;
    });

    return result;
  }, [workflows, searchQuery, sortBy, sortOrder]);

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center h-full"
        data-testid="loading-indicator"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
        <p className="text-lg">Failed to load shared workflows</p>
        <p className="text-sm">Please try again later</p>
      </div>
    );
  }

  const handleViewWorkflow = (workflowId: string) => {
    // Navigate to read-only workflow view
    navigate(`/studio/workflows/${workflowId}?readonly=true`);
  };

  // Handle sort change
  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value as SortField;
    if (value === sortBy) {
      // Toggle order if same field selected
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(value);
      setSortOrder("asc");
    }
  };

  const workflowList = workflows as SharedWorkflow[] | undefined;
  if (!workflowList || workflowList.length === 0) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          Shared Workflows
        </h1>
        <div className="flex flex-col items-center justify-center py-16 text-gray-500 dark:text-gray-400">
          <GitBranch className="w-16 h-16 mb-4 opacity-50" />
          <p className="text-lg font-medium">No shared workflows</p>
          <p className="text-sm mt-2">
            When team members share workflows with you, they will appear here.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Shared Workflows
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Workflows shared with you by team members (read-only access)
        </p>
      </div>

      {/* Search and Sort Controls */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search workflows..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <select
          aria-label="Sort by"
          value={sortBy}
          onChange={handleSortChange}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
        >
          <option value="createdAt">Date Created</option>
          <option value="name">Name</option>
          <option value="owner">Owner</option>
        </select>
      </div>

      {/* Empty search results */}
      {filteredWorkflows.length === 0 && searchQuery && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500 dark:text-gray-400">
          <Search className="w-12 h-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">No workflows match your search</p>
          <p className="text-sm mt-2">Try adjusting your search terms</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredWorkflows.map((workflow) => (
          <div
            key={workflow.id}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <GitBranch className="w-5 h-5 text-blue-500" />
                <h3 className="font-medium text-gray-900 dark:text-white">
                  {workflow.name}
                </h3>
              </div>
              <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded">
                Read-only
              </span>
            </div>

            {workflow.description && (
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-2">
                {workflow.description}
              </p>
            )}

            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 mb-4">
              <div className="flex items-center gap-1">
                <UserIcon className="w-3 h-3" />
                <span>Owner: {workflow.owner}</span>
              </div>
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{new Date(workflow.createdAt).toLocaleDateString()}</span>
              </div>
            </div>

            <button
              onClick={() => handleViewWorkflow(workflow.id)}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
            >
              <Eye className="w-4 h-4" />
              View
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
