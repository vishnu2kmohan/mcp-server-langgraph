/**
 * WorkflowsTab Component
 *
 * Project workflows tab with list display, create/remove operations,
 * and bulk selection with BulkActionBar.
 */

import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router";
import { Plus, GitBranch, Trash2, X, Search } from "lucide-react";
import { BulkActionBar } from "../UI/BulkActionBar";
import { authenticatedFetch } from "../../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../../utils/intendedRoute";

import { Button, Input, Select, Checkbox } from "@/components/UI";

// ============================================================================
// Sort Types
// ============================================================================

type SortField = "name" | "createdAt";
type SortOrder = "asc" | "desc";

// ============================================================================
// Types
// ============================================================================

export interface WorkflowRef {
  id: string;
  name: string;
  createdAt: string | null;
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
      <div
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Enter" && onClose()}
        role="button"
        tabIndex={0}
        aria-label="Close dialog"
      />
      <div className="relative bg-neutral-1 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-5">
          <h3 className="text-lg font-medium text-neutral-12">
            {title}
          </h3>
          <Button size="icon" variant="ghost"
            className="p-1 text-neutral-10 hover:text-neutral-11"
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </Button>
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
            className="block text-sm font-medium text-neutral-11 mb-1"
          >
            Workflow Name
          </label>
          <Input
            className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
            id="workflow-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter workflow name"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            className="px-4 py-2 text-sm text-neutral-11 hover:bg-neutral-2 rounded-lg"
            type="button"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            className="px-4 py-2 text-sm bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
            type="submit"
            disabled={!name.trim()}
          >
            Create
          </Button>
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

  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Search and sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("createdAt");
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
      if (sortBy === "createdAt") {
        if (!a.createdAt && !b.createdAt) return 0;
        if (!a.createdAt) return 1; // a (null) goes after b
        if (!b.createdAt) return -1; // b (null) goes after a
      }

      let compareVal = 0;
      switch (sortBy) {
        case "name":
          compareVal = a.name.localeCompare(b.name);
          break;
        case "createdAt":
        default:
          compareVal =
            new Date(a.createdAt!).getTime() - new Date(b.createdAt!).getTime();
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
    const response = await authenticatedFetch(
      `/api/v1/projects/${projectId}/workflows?workflow_id=${workflowId}&workflow_name=${encodeURIComponent(name)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        onAuthFailure: handleAuthFailure,
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
    const response = await authenticatedFetch(
      `/api/v1/projects/${projectId}/workflows/${workflowId}`,
      {
        method: "DELETE",
        onAuthFailure: handleAuthFailure,
      },
    );
    if (response.ok) {
      onRefresh();
    }
  };

  // Bulk selection handlers
  const handleSelectWorkflow = (workflowId: string) => {
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
    const deletePromises = Array.from(selectedWorkflows).map(
      async (workflowId) => {
        const response = await authenticatedFetch(
          `/api/v1/projects/${projectId}/workflows/${workflowId}`,
          {
            method: "DELETE",
            onAuthFailure: handleAuthFailure,
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
          <h2 className="text-lg font-medium text-neutral-12">
            Workflows
          </h2>
          {filteredWorkflows.length > 0 && (
            <Checkbox
              checked={
                selectedWorkflows.size === filteredWorkflows.length &&
                filteredWorkflows.length > 0
              }
              onChange={handleSelectAll}
              label="Select All"
              size="sm"
            />
          )}
        </div>
        <Button
          variant="primary"
          className="flex px-3 py-1.5 bg-primary-10 text-neutral-12 text-sm rounded-lg hover:bg-primary-11"
          onClick={() => setShowDialog(true)}
        >
          <Plus className="w-4 h-4" />
          New Workflow
        </Button>
      </div>
      {/* Search and Sort Controls */}
      {workflows.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-9" />
            <Input
              className="pl-10 pr-4 py-2 text-neutral-12 focus:ring-primary-7"
              placeholder="Search workflows..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Select
            size="lg"
            className="px-4 py-2 text-neutral-12 focus:ring-primary-7"
            aria-label="Sort by"
            value={sortBy}
            onChange={handleSortChange}
          >
            <option value="createdAt">Date Created</option>
            <option value="name">Name</option>
          </Select>
        </div>
      )}
      {/* Empty search results */}
      {filteredWorkflows.length === 0 &&
        searchQuery &&
        workflows.length > 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-neutral-10">
            <Search className="w-12 h-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">
              No workflows match your search
            </p>
            <p className="text-sm mt-2">Try adjusting your search terms</p>
          </div>
        )}
      {workflows.length === 0 ? (
        <div className="text-center py-12 text-neutral-10">
          No workflows yet. Create a workflow to automate your AI tasks.
        </div>
      ) : filteredWorkflows.length > 0 ? (
        <div className="space-y-2">
          {filteredWorkflows.map((workflow) => (
            <div
              key={workflow.id}
              className="flex items-center gap-3 p-4 bg-neutral-1 border border-neutral-5 rounded-lg hover:shadow-sm cursor-pointer"
              onClick={() => navigate(`/studio/workflows?id=${workflow.id}`)}
            >
              <Checkbox
                checked={selectedWorkflows.has(workflow.id)}
                onChange={() => handleSelectWorkflow(workflow.id)}
                onClick={(e) => e.stopPropagation()}
                size="sm"
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-neutral-12">
                  {workflow.name}
                </div>
                {workflow.createdAt && (
                  <div className="text-sm text-neutral-10">
                    Created {new Date(workflow.createdAt).toLocaleDateString()}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="danger"
                  className="p-1.5 text-neutral-9 hover:text-error-9 hover:bg-error-1 dark:hover:bg-error-a3 rounded"
                  aria-label="Remove workflow"
                  onClick={(e) => handleRemoveWorkflow(workflow.id, e)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
                <GitBranch className="w-5 h-5 text-neutral-9" />
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
