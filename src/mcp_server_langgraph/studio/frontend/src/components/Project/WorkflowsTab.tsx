/**
 * WorkflowsTab Component
 *
 * Project workflows tab with list display, create/remove operations,
 * and bulk selection with BulkActionBar.
 */

import { useState, useMemo } from "react";
import { useNavigate } from "react-router";
import { Plus, GitBranch, Trash2, X, Search } from "lucide-react";
import { BulkActionBar } from "../UI/BulkActionBar";
import { getAuthToken } from "../../utils/storage";

// ============================================================================
// Sort Types
// ============================================================================

type SortField = "name" | "created_at";
type SortOrder = "asc" | "desc";

// ============================================================================
// Types
// ============================================================================

export interface WorkflowRef {
  id: string;
  name: string;
  created_at: string | null;
}

export interface WorkflowsTabProps {
  workflows: WorkflowRef[];
  projectId: string;
  onRefresh: () => void;
}

// ============================================================================
// Dialog Components
// ============================================================================

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

function Dialog({ isOpen, onClose, title, children }: DialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

interface CreateWorkflowDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string) => void;
}

function CreateWorkflowDialog({
  isOpen,
  onClose,
  onSubmit,
}: CreateWorkflowDialogProps) {
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onSubmit(name.trim());
      setName("");
      onClose();
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Create New Workflow">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label
            htmlFor="workflow-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Workflow Name
          </label>
          <input
            id="workflow-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter workflow name"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim()}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Create
          </button>
        </div>
      </form>
    </Dialog>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function WorkflowsTab({
  workflows,
  projectId,
  onRefresh,
}: WorkflowsTabProps) {
  const navigate = useNavigate();
  const [showDialog, setShowDialog] = useState(false);
  const [selectedWorkflows, setSelectedWorkflows] = useState<Set<string>>(
    new Set(),
  );

  // Search and sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Filter and sort workflows
  const filteredWorkflows = useMemo(() => {
    let result = [...workflows];

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter((w) => w.name.toLowerCase().includes(query));
    }

    // Sort
    result.sort((a, b) => {
      // Handle null dates - always put them at the end
      if (sortBy === "created_at") {
        if (!a.created_at && !b.created_at) return 0;
        if (!a.created_at) return 1; // a (null) goes after b
        if (!b.created_at) return -1; // b (null) goes after a
      }

      let compareVal = 0;
      switch (sortBy) {
        case "name":
          compareVal = a.name.localeCompare(b.name);
          break;
        case "created_at":
        default:
          compareVal =
            new Date(a.created_at!).getTime() -
            new Date(b.created_at!).getTime();
          break;
      }
      return sortOrder === "asc" ? compareVal : -compareVal;
    });

    return result;
  }, [workflows, searchQuery, sortBy, sortOrder]);

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

  const handleCreateWorkflow = async (name: string) => {
    const workflowId = crypto.randomUUID();
    const token = getAuthToken();
    const response = await fetch(
      `/api/v1/projects/${projectId}/workflows?workflow_id=${workflowId}&workflow_name=${encodeURIComponent(name)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
      },
    );
    if (response.ok) {
      onRefresh();
    }
  };

  const handleRemoveWorkflow = async (
    workflowId: string,
    e: React.MouseEvent,
  ) => {
    e.stopPropagation(); // Prevent navigation
    const token = getAuthToken();
    const response = await fetch(
      `/api/v1/projects/${projectId}/workflows/${workflowId}`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
      },
    );
    if (response.ok) {
      onRefresh();
    }
  };

  // Bulk selection handlers
  const handleSelectWorkflow = (workflowId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent navigation
    setSelectedWorkflows((prev) => {
      const next = new Set(prev);
      if (next.has(workflowId)) {
        next.delete(workflowId);
      } else {
        next.add(workflowId);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedWorkflows.size === filteredWorkflows.length) {
      setSelectedWorkflows(new Set());
    } else {
      setSelectedWorkflows(new Set(filteredWorkflows.map((w) => w.id)));
    }
  };

  const handleClearSelection = () => {
    setSelectedWorkflows(new Set());
  };

  const handleBulkDelete = async () => {
    // Delete each selected workflow
    const token = getAuthToken();
    const deletePromises = Array.from(selectedWorkflows).map(
      async (workflowId) => {
        const response = await fetch(
          `/api/v1/projects/${projectId}/workflows/${workflowId}`,
          {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            credentials: "include",
          },
        );
        return response.ok;
      },
    );
    await Promise.all(deletePromises);
    setSelectedWorkflows(new Set());
    onRefresh();
  };

  return (
    <div>
      <CreateWorkflowDialog
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
        onSubmit={handleCreateWorkflow}
      />
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Workflows
          </h2>
          {filteredWorkflows.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 cursor-pointer">
              <input
                type="checkbox"
                checked={
                  selectedWorkflows.size === filteredWorkflows.length &&
                  filteredWorkflows.length > 0
                }
                onChange={handleSelectAll}
                aria-label="Select all workflows"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Select All
            </label>
          )}
        </div>
        <button
          onClick={() => setShowDialog(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          New Workflow
        </button>
      </div>

      {/* Search and Sort Controls */}
      {workflows.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
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
            <option value="created_at">Date Created</option>
            <option value="name">Name</option>
          </select>
        </div>
      )}

      {/* Empty search results */}
      {filteredWorkflows.length === 0 &&
        searchQuery &&
        workflows.length > 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500 dark:text-gray-400">
            <Search className="w-12 h-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">
              No workflows match your search
            </p>
            <p className="text-sm mt-2">Try adjusting your search terms</p>
          </div>
        )}
      {workflows.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No workflows yet. Create a workflow to automate your AI tasks.
        </div>
      ) : filteredWorkflows.length > 0 ? (
        <div className="space-y-2">
          {filteredWorkflows.map((workflow) => (
            <div
              key={workflow.id}
              className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-sm cursor-pointer"
              onClick={() => navigate(`/studio/workflows?id=${workflow.id}`)}
            >
              <input
                type="checkbox"
                checked={selectedWorkflows.has(workflow.id)}
                onChange={() => {}}
                onClick={(e) => handleSelectWorkflow(workflow.id, e)}
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 flex-shrink-0"
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {workflow.name}
                </div>
                {workflow.created_at && (
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Created {new Date(workflow.created_at).toLocaleDateString()}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  aria-label="Remove workflow"
                  onClick={(e) => handleRemoveWorkflow(workflow.id, e)}
                  className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <GitBranch className="w-5 h-5 text-gray-400" />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Bulk Action Bar */}
      <BulkActionBar
        selectedCount={selectedWorkflows.size}
        onClearSelection={handleClearSelection}
        onDelete={handleBulkDelete}
      />
    </div>
  );
}

export default WorkflowsTab;
