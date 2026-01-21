/**
 * WorkflowsListPage
 *
 * List view for workflow management with grid/table views.
 * Provides browsing, search, filtering, and CRUD operations.
 * The visual builder (canvas) is accessed via /workflows/builder or /workflows/:id.
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import {
  GitBranch,
  Plus,
  RefreshCw,
  Trash2,
  ExternalLink,
  Network,
  Cable,
  LayoutGrid,
  List,
} from "lucide-react";
import { ArrowUp, ArrowDown } from "lucide-react";
import { useListWorkflowsQuery, useDeleteWorkflowMutation } from "../api";
// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { SearchInput } from "../components/UI/SearchInput";
import { SortDropdown, type SortOrder } from "../components/UI/SortDropdown";
import { Checkbox } from "../components/UI/Checkbox";
import {
  SegmentedControl,
  SegmentedControlItem,
} from "../components/UI/SegmentedControl";
import { CursorPagination } from "../components/UI/CursorPagination";
import { SkeletonList } from "../components/UI/Skeleton";
import { Button } from "../components/UI/Button";
import { ErrorState } from "../components/UI/ErrorState";
import { ConfirmDialog } from "../components/UI/ConfirmDialog";
import { AIEmptyState } from "../components/EmptyState/AIEmptyState";
import type { WorkflowSummaryCamelCase } from "../types/api";

// Sort options for workflows
const SORT_OPTIONS = [
  { value: "name", label: "Name" },
  { value: "created_at", label: "Created Date" },
  { value: "updated_at", label: "Updated Date" },
  { value: "node_count", label: "Nodes" },
  { value: "edge_count", label: "Edges" },
];

/**
 * SortableTableHeader - Clickable table header for sorting
 */
interface SortableHeaderProps {
  label: string;
  field: string;
  currentSortBy: string;
  currentSortOrder: SortOrder;
  onSort: (field: string, order: SortOrder) => void;
  align?: "left" | "center" | "right";
}

function SortableHeader({
  label,
  field,
  currentSortBy,
  currentSortOrder,
  onSort,
  align = "left",
}: SortableHeaderProps) {
  const isActive = currentSortBy === field;

  const handleClick = () => {
    // Toggle order if already sorting by this field, otherwise default to desc
    const newOrder: SortOrder =
      isActive && currentSortOrder === "desc" ? "asc" : "desc";
    onSort(field, newOrder);
  };

  const alignClass =
    align === "center"
      ? "justify-center"
      : align === "right"
        ? "justify-end"
        : "justify-start";

  return (
    <th
      className={`px-4 py-3 text-${align} text-xs font-medium text-neutral-11 uppercase tracking-wider cursor-pointer hover:bg-neutral-a6 transition-colors select-none`}
      onClick={handleClick}
    >
      <div className={`flex items-center gap-1 ${alignClass}`}>
        <span>{label}</span>
        {isActive &&
          (currentSortOrder === "asc" ? (
            <ArrowUp className="w-3 h-3 text-primary-9" />
          ) : (
            <ArrowDown className="w-3 h-3 text-primary-9" />
          ))}
      </div>
    </th>
  );
}

export function WorkflowsListPage() {
  const navigate = useNavigate();

  // Search state
  const [searchQuery, setSearchQuery] = useState("");

  // Cursor pagination state
  const [currentCursor, setCurrentCursor] = useState<string | undefined>();
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);

  // Sort state
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // View mode state (grid or table)
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // RTK Query hooks - pass all filter/sort/pagination parameters
  const {
    data: workflowsResponse,
    isLoading,
    isFetching,
    error: fetchError,
    refetch,
  } = useListWorkflowsQuery({
    search: searchQuery || undefined,
    cursor: currentCursor,
    limit: 20,
    sort_by: sortBy || undefined,
    sort_order: sortOrder,
  });

  const [deleteWorkflow] = useDeleteWorkflowMutation();

  // Mutation error state
  const [mutationError, setMutationError] = useState<string | null>(null);

  // Delete dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [workflowToDelete, setWorkflowToDelete] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Bulk selection state (for table view)
  const [selectedWorkflows, setSelectedWorkflows] = useState<Set<string>>(
    new Set()
  );
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);

  // Combine fetch and mutation errors
  const fetchErrorMessage = fetchError
    ? "status" in fetchError && fetchError.status === "FETCH_ERROR"
      ? "Unable to connect to the server. Please check your network connection."
      : "Failed to load workflows"
    : null;
  const error = mutationError || fetchErrorMessage;

  const handleRefresh = () => {
    setMutationError(null);
    refetch();
  };

  const handleDeleteWorkflow = (workflowId: string, workflowName: string) => {
    setWorkflowToDelete({ id: workflowId, name: workflowName });
    setShowDeleteDialog(true);
  };

  const confirmDeleteWorkflow = async () => {
    if (!workflowToDelete) return;

    setIsDeleting(true);
    setMutationError(null);
    try {
      await deleteWorkflow(workflowToDelete.id).unwrap();
      setShowDeleteDialog(false);
      setWorkflowToDelete(null);
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to delete workflow"
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDeleteWorkflow = () => {
    setShowDeleteDialog(false);
    setWorkflowToDelete(null);
  };

  // Bulk selection handlers
  const handleSelectAll = () => {
    if (selectedWorkflows.size === workflows.length) {
      // Deselect all
      setSelectedWorkflows(new Set());
    } else {
      // Select all
      setSelectedWorkflows(new Set(workflows.map((w) => w.id)));
    }
  };

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

  const handleBulkDelete = () => {
    if (selectedWorkflows.size > 0) {
      setShowBulkDeleteDialog(true);
    }
  };

  const confirmBulkDeleteWorkflows = async () => {
    setIsDeleting(true);
    setMutationError(null);
    try {
      // Delete all selected workflows sequentially
      for (const workflowId of selectedWorkflows) {
        await deleteWorkflow(workflowId).unwrap();
      }
      setShowBulkDeleteDialog(false);
      setSelectedWorkflows(new Set());
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to delete workflows"
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelBulkDeleteWorkflows = () => {
    setShowBulkDeleteDialog(false);
  };

  const handleOpenWorkflow = (workflowId: string) => {
    navigate(`/studio/workflows/${workflowId}`);
  };

  const handleCreateWorkflow = () => {
    navigate("/studio/workflows/builder");
  };

  // Derive data from query result
  const workflows: WorkflowSummaryCamelCase[] = workflowsResponse?.items ?? [];
  const hasNext = workflowsResponse?.hasNext ?? false;
  const hasPrev = cursorHistory.length > 0;

  // Cursor pagination handlers
  const handleNextPage = useCallback(() => {
    if (workflowsResponse?.nextCursor) {
      setCursorHistory((prev) => [...prev, currentCursor ?? ""]);
      setCurrentCursor(workflowsResponse.nextCursor);
    }
  }, [workflowsResponse?.nextCursor, currentCursor]);

  const handlePrevPage = useCallback(() => {
    if (cursorHistory.length > 0) {
      const prevCursor = cursorHistory[cursorHistory.length - 1];
      setCursorHistory((prev) => prev.slice(0, -1));
      setCurrentCursor(prevCursor || undefined);
    }
  }, [cursorHistory]);

  // Handler for sort changes
  const handleSortChange = (field: string, order: SortOrder) => {
    setSortBy(field);
    setSortOrder(order);
    // Reset pagination on sort change
    setCurrentCursor(undefined);
    setCursorHistory([]);
  };

  // Handler for search changes (from SearchInput)
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    // Reset pagination on search
    setCurrentCursor(undefined);
    setCursorHistory([]);
  };

  // Loading state - only show on initial load
  if (isLoading && !workflowsResponse) {
    return (
      <div className="h-full p-6 bg-neutral-1">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-neutral-12">Workflows</h1>
          <p className="text-sm text-neutral-11">Loading your workflows...</p>
        </div>
        <SkeletonList items={5} />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <ErrorState
          title="Failed to load workflows"
          message={error}
          onRetry={handleRefresh}
          variant="fullscreen"
        />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header - Unified toolbar following STYLE.md */}
      <div className="px-6 py-4 border-b border-neutral-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GitBranch className="w-6 h-6 text-primary-11" />
            <h1 className="text-xl font-semibold text-neutral-12">Workflows</h1>
            <span className="text-sm text-neutral-11">
              ({workflowsResponse?.count ?? 0})
            </span>
          </div>
          <div className="flex items-center gap-3">
            {/* Search input with debouncing */}
            <SearchInput
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search workflows..."
              isLoading={isFetching}
              debounceMs={300}
            />
            {/* Sort dropdown */}
            <SortDropdown
              options={SORT_OPTIONS}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onChange={handleSortChange}
              ariaLabel="Sort workflows"
            />
            {/* View mode toggle (SegmentedControl) */}
            <SegmentedControl
              value={viewMode}
              onValueChange={(value) => setViewMode(value as "grid" | "table")}
              aria-label="View mode"
              size="sm"
            >
              <SegmentedControlItem value="grid" aria-label="Grid view">
                <LayoutGrid className="w-4 h-4" />
              </SegmentedControlItem>
              <SegmentedControlItem value="table" aria-label="Table view">
                <List className="w-4 h-4" />
              </SegmentedControlItem>
            </SegmentedControl>
            {/* Refresh button - uses ghost variant for toolbar */}
            <Button
              size="icon"
              variant="ghost"
              onClick={handleRefresh}
              disabled={isFetching}
              title="Refresh"
              aria-label="Refresh workflows"
            >
              <RefreshCw
                className={`w-5 h-5 ${isFetching ? "animate-spin" : ""}`}
              />
            </Button>
            {/* Create button - primary action, navigates to builder */}
            <Button variant="primary" onClick={handleCreateWorkflow}>
              <Plus className="w-4 h-4" />
              Create Workflow
            </Button>
          </div>
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {workflows.length === 0 ? (
          // Empty state - AI-enhanced
          <AIEmptyState
            context="workflows"
            onAction={handleCreateWorkflow}
            actionLabel="Create Workflow"
          />
        ) : (
          <>
            {viewMode === "grid" ? (
              /* Grid View */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {workflows.map((workflow) => (
                  <div
                    key={workflow.id}
                    className="bg-neutral-1 border border-neutral-5 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    {/* Workflow header */}
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-medium text-neutral-12">
                          {workflow.name}
                        </h3>
                        {workflow.description && (
                          <p className="text-sm text-neutral-11 mt-1 line-clamp-2">
                            {workflow.description}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Resource counts */}
                    <div className="flex items-center gap-4 text-sm text-neutral-11 mb-4">
                      <div className="flex items-center gap-1" title="Nodes">
                        <Network className="w-4 h-4" />
                        <span>{workflow.nodeCount} nodes</span>
                      </div>
                      <div className="flex items-center gap-1" title="Edges">
                        <Cable className="w-4 h-4" />
                        <span>{workflow.edgeCount} edges</span>
                      </div>
                    </div>

                    {/* Updated date */}
                    <div className="text-xs text-neutral-10 mb-4">
                      Updated:{" "}
                      {workflow.updatedAt
                        ? new Date(workflow.updatedAt).toLocaleDateString()
                        : "-"}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-between pt-3 border-t border-neutral-5">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenWorkflow(workflow.id)}
                        aria-label="Open workflow"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() =>
                          handleDeleteWorkflow(workflow.id, workflow.name)
                        }
                        aria-label="Delete workflow"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Table View */
              <div className="bg-neutral-1 border border-neutral-5 rounded-lg overflow-hidden">
                {/* Bulk action bar */}
                {selectedWorkflows.size > 0 && (
                  <div className="px-4 py-2 bg-primary-2 border-b border-primary-5 flex items-center justify-between">
                    <span className="text-sm text-primary-11">
                      {selectedWorkflows.size} workflow
                      {selectedWorkflows.size > 1 ? "s" : ""} selected
                    </span>
                    <Button variant="danger" size="sm" onClick={handleBulkDelete}>
                      <Trash2 className="w-4 h-4" />
                      Delete Selected
                    </Button>
                  </div>
                )}
                <table className="w-full">
                  <thead className="bg-neutral-1">
                    <tr>
                      {/* Select all checkbox */}
                      <th className="px-4 py-3 w-10">
                        <Checkbox
                          checked={
                            workflows.length > 0 &&
                            selectedWorkflows.size === workflows.length
                          }
                          onChange={handleSelectAll}
                          aria-label="Select all workflows"
                          size="sm"
                        />
                      </th>
                      <SortableHeader
                        label="Name"
                        field="name"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                      />
                      <SortableHeader
                        label="Nodes"
                        field="node_count"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                        align="center"
                      />
                      <SortableHeader
                        label="Edges"
                        field="edge_count"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                        align="center"
                      />
                      <SortableHeader
                        label="Updated"
                        field="updated_at"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                        align="center"
                      />
                      <th className="px-4 py-3 text-right text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-5 dark:divide-neutral-6">
                    {workflows.map((workflow) => (
                      <tr
                        key={workflow.id}
                        className={`hover:bg-neutral-a6 transition-colors ${
                          selectedWorkflows.has(workflow.id)
                            ? "bg-primary-1"
                            : ""
                        }`}
                      >
                        {/* Row checkbox */}
                        <td className="px-4 py-3 w-10">
                          <Checkbox
                            checked={selectedWorkflows.has(workflow.id)}
                            onChange={() => handleSelectWorkflow(workflow.id)}
                            aria-label={`Select ${workflow.name}`}
                            size="sm"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-medium text-neutral-12">
                              {workflow.name}
                            </div>
                            {workflow.description && (
                              <div className="text-sm text-neutral-11 truncate max-w-xs">
                                {workflow.description}
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          <div className="flex items-center justify-center gap-1">
                            <Network className="w-4 h-4" />
                            {workflow.nodeCount}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          <div className="flex items-center justify-center gap-1">
                            <Cable className="w-4 h-4" />
                            {workflow.edgeCount}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          {workflow.updatedAt
                            ? new Date(workflow.updatedAt).toLocaleDateString()
                            : "-"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleOpenWorkflow(workflow.id)}
                              aria-label="Open workflow"
                              title="Open"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                handleDeleteWorkflow(workflow.id, workflow.name)
                              }
                              aria-label="Delete workflow"
                              title="Delete"
                              className="text-error-11 hover:text-error-11 hover:bg-error-a3"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Cursor Pagination */}
            {(hasNext || hasPrev) && (
              <div className="mt-6">
                <CursorPagination
                  hasNextPage={hasNext}
                  hasPreviousPage={hasPrev}
                  onNextPage={handleNextPage}
                  onPreviousPage={handlePrevPage}
                  isLoading={isFetching}
                  itemCount={workflows.length}
                  totalCount={workflowsResponse?.count}
                />
              </div>
            )}
          </>
        )}
      </div>
      {/* Delete Workflow Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onClose={cancelDeleteWorkflow}
        onConfirm={confirmDeleteWorkflow}
        title="Delete Workflow"
        message={`Are you sure you want to delete "${workflowToDelete?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={isDeleting}
      />
      {/* Bulk Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showBulkDeleteDialog}
        onClose={cancelBulkDeleteWorkflows}
        onConfirm={confirmBulkDeleteWorkflows}
        title="Delete Selected Workflows"
        message={`Are you sure you want to delete ${selectedWorkflows.size} workflow${selectedWorkflows.size > 1 ? "s" : ""}? This action cannot be undone.`}
        confirmText={`Delete ${selectedWorkflows.size} Workflow${selectedWorkflows.size > 1 ? "s" : ""}`}
        cancelText="Cancel"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </div>
  );
}

export default WorkflowsListPage;
