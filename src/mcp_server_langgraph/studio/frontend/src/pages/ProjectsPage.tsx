/**
 * ProjectsPage
 *
 * Project management page for the Unified Workspace Paradigm.
 * Displays list of projects with their child resource counts
 * and provides CRUD operations using RTK Query.
 */

import { useState } from "react";
import { useNavigate } from "react-router";
import {
  FolderKanban,
  Plus,
  RefreshCw,
  Trash2,
  ExternalLink,
  GitBranch,
  MessageSquare,
  Plug,
  X,
  LayoutGrid,
  List,
  User,
} from "lucide-react";
import { ArrowUp, ArrowDown } from "lucide-react";
import {
  useListProjectsQuery,
  useCreateProjectMutation,
  useDeleteProjectMutation,
} from "../api";
// Direct imports to avoid Rollup circular dependency warnings
import { SearchInput } from "../components/UI/SearchInput";
import { PagePagination } from "../components/UI/Pagination";
import { SortDropdown, type SortOrder } from "../components/UI/SortDropdown";
import { StatusFilter } from "../components/UI/StatusFilter";
import { Checkbox } from "../components/UI/Checkbox";
import {
  SegmentedControl,
  SegmentedControlItem,
} from "../components/UI/SegmentedControl";
import { SkeletonList } from "../components/UI/Skeleton";
import { Button } from "../components/UI/Button";
import { Input } from "../components/UI/Input";
import { Textarea } from "../components/UI/Textarea";
import { ErrorState } from "../components/UI/ErrorState";
import { ConfirmDialog } from "../components/UI/ConfirmDialog";
import { AIEmptyState } from "../components/EmptyState/AIEmptyState";

// Sort options for projects
const SORT_OPTIONS = [
  { value: "name", label: "Name" },
  { value: "created_at", label: "Created Date" },
  { value: "updated_at", label: "Updated Date" },
  { value: "session_count", label: "Sessions" },
  { value: "workflow_count", label: "Workflows" },
  { value: "connection_count", label: "Connections" },
];

// Status options for filtering
const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
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

export function ProjectsPage() {
  const navigate = useNavigate();

  // Search state
  const [searchQuery, setSearchQuery] = useState("");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  // Sort state
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Status filter state
  const [statusFilter, setStatusFilter] = useState("");

  // View mode state (grid or table)
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  // RTK Query hooks - pass all filter/sort/pagination parameters
  const {
    data: projectsResponse,
    isLoading,
    isFetching,
    error: fetchError,
    refetch,
  } = useListProjectsQuery({
    search: searchQuery || undefined,
    page: currentPage,
    per_page: perPage,
    sort_by: sortBy || undefined,
    sort_order: sortOrder,
    status: statusFilter || undefined,
  });

  const [createProject, { isLoading: isCreating }] = useCreateProjectMutation();
  const [deleteProject] = useDeleteProjectMutation();

  // Create dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [mutationError, setMutationError] = useState<string | null>(null);

  // Delete dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<{
    id: string;
    name: string;
  } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Bulk selection state (for table view)
  const [selectedProjects, setSelectedProjects] = useState<Set<string>>(
    new Set(),
  );
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);

  // Combine fetch and mutation errors
  // Extract a meaningful error message from fetchError
  const fetchErrorMessage = fetchError
    ? "status" in fetchError && fetchError.status === "FETCH_ERROR"
      ? "Unable to connect to the server. Please check your network connection."
      : "Failed to load projects"
    : null;
  const error = mutationError || fetchErrorMessage;

  const handleRefresh = () => {
    setMutationError(null);
    refetch();
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    setMutationError(null);
    try {
      await createProject({
        name: newProjectName.trim(),
        description: newProjectDescription.trim() || undefined,
      }).unwrap();

      // Reset form and close dialog
      setNewProjectName("");
      setNewProjectDescription("");
      setShowCreateDialog(false);
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to create project",
      );
    }
  };

  const handleDeleteProject = (projectId: string, projectName: string) => {
    // Open the styled confirmation dialog instead of native confirm()
    setProjectToDelete({ id: projectId, name: projectName });
    setShowDeleteDialog(true);
  };

  const confirmDeleteProject = async () => {
    if (!projectToDelete) return;

    setIsDeleting(true);
    setMutationError(null);
    try {
      await deleteProject(projectToDelete.id).unwrap();
      setShowDeleteDialog(false);
      setProjectToDelete(null);
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to delete project",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelDeleteProject = () => {
    setShowDeleteDialog(false);
    setProjectToDelete(null);
  };

  // Bulk selection handlers
  const handleSelectAll = () => {
    if (selectedProjects.size === projects.length) {
      // Deselect all
      setSelectedProjects(new Set());
    } else {
      // Select all
      setSelectedProjects(new Set(projects.map((p) => p.id)));
    }
  };

  const handleSelectProject = (projectId: string) => {
    setSelectedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
  };

  const handleBulkDelete = () => {
    if (selectedProjects.size > 0) {
      setShowBulkDeleteDialog(true);
    }
  };

  const confirmBulkDeleteProjects = async () => {
    setIsDeleting(true);
    setMutationError(null);
    try {
      // Delete all selected projects sequentially
      for (const projectId of selectedProjects) {
        await deleteProject(projectId).unwrap();
      }
      setShowBulkDeleteDialog(false);
      setSelectedProjects(new Set());
    } catch (err) {
      setMutationError(
        err instanceof Error ? err.message : "Failed to delete projects",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const cancelBulkDeleteProjects = () => {
    setShowBulkDeleteDialog(false);
  };

  const handleOpenProject = (projectId: string) => {
    navigate(`/studio/projects/${projectId}`);
  };

  // Derive data from query result
  const projects = projectsResponse?.items ?? [];
  const total = projectsResponse?.total ?? 0;
  // snake_case from API response types
  const totalPages = projectsResponse?.total_pages ?? 1;

  // Handler for sort changes
  const handleSortChange = (field: string, order: SortOrder) => {
    setSortBy(field);
    setSortOrder(order);
    setCurrentPage(1); // Reset to first page on sort change
  };

  // Handler for status filter changes
  const handleStatusChange = (status: string | null) => {
    setStatusFilter(status ?? "");
    setCurrentPage(1); // Reset to first page on filter change
  };

  // Handler for search changes (from SearchInput)
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    setCurrentPage(1); // Reset to first page on search
  };

  // Handler for page changes
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  // Handler for per page changes
  const handlePerPageChange = (newPerPage: number) => {
    setPerPage(newPerPage);
    setCurrentPage(1); // Reset to first page
  };

  // Loading state - only show on initial load
  if (isLoading && !projectsResponse) {
    return (
      <div className="h-full p-6 bg-neutral-1">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-neutral-12">
            Projects
          </h1>
          <p className="text-sm text-neutral-11">
            Loading your projects...
          </p>
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
          title="Failed to load projects"
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
            <FolderKanban className="w-6 h-6 text-primary-11" />
            <h1 className="text-xl font-semibold text-neutral-12">
              Projects
            </h1>
            <span className="text-sm text-neutral-11">
              ({total})
            </span>
          </div>
          <div className="flex items-center gap-3">
            {/* Search input with debouncing */}
            <SearchInput
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search projects..."
              isLoading={isFetching}
              debounceMs={300}
            />
            {/* Status filter dropdown (replaces FilterChips) */}
            <StatusFilter
              options={STATUS_OPTIONS}
              value={statusFilter || null}
              onChange={handleStatusChange}
              allLabel="All Statuses"
              ariaLabel="Filter by status"
            />
            {/* Sort dropdown */}
            <SortDropdown
              options={SORT_OPTIONS}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onChange={handleSortChange}
              ariaLabel="Sort projects"
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
              aria-label="Refresh projects"
            >
              <RefreshCw
                className={`w-5 h-5 ${isFetching ? "animate-spin" : ""}`}
              />
            </Button>
            {/* Create button - primary action */}
            <Button
              variant="primary"
              onClick={() => setShowCreateDialog(true)}
            >
              <Plus className="w-4 h-4" />
              Create Project
            </Button>
          </div>
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {projects.length === 0 ? (
          // Empty state - AI-enhanced (Sprint 3 Migration)
          <AIEmptyState
            context="projects"
            onAction={() => setShowCreateDialog(true)}
            actionLabel="Create Project"
          />
        ) : (
          <>
            {viewMode === "grid" ? (
              /* Grid View */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {projects.map((project) => (
                  <div
                    key={project.id}
                    className="bg-neutral-1 border border-neutral-5 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    {/* Project header */}
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-medium text-neutral-12">
                          {project.name}
                        </h3>
                        {project.description && (
                          <p className="text-sm text-neutral-11 mt-1">
                            {project.description}
                          </p>
                        )}
                      </div>
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full ${
                          project.status === "active"
                            ? "bg-success-3 text-success-11"
                            : "bg-neutral-2 text-neutral-11"
                        }`}
                      >
                        {project.status}
                      </span>
                    </div>

                    {/* Owner info */}
                    <div className="flex items-center gap-1.5 text-xs text-neutral-11 mb-3">
                      <User className="w-3.5 h-3.5" />
                      <span>{project.owner_name || project.owner_id}</span>
                    </div>

                    {/* Resource counts */}
                    <div className="flex items-center gap-4 text-sm text-neutral-11 mb-4">
                      <div className="flex items-center gap-1" title="Sessions">
                        <MessageSquare className="w-4 h-4" />
                        <span>{project.session_count} sessions</span>
                      </div>
                      <div
                        className="flex items-center gap-1"
                        title="Workflows"
                      >
                        <GitBranch className="w-4 h-4" />
                        <span>{project.workflow_count} workflows</span>
                      </div>
                      <div
                        className="flex items-center gap-1"
                        title="Connections"
                      >
                        <Plug className="w-4 h-4" />
                        <span>{project.connection_count}</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-between pt-3 border-t border-neutral-5">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenProject(project.id)}
                        aria-label="Open project"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() =>
                          handleDeleteProject(project.id, project.name)
                        }
                        aria-label="Delete project"
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
                {selectedProjects.size > 0 && (
                  <div className="px-4 py-2 bg-primary-2 border-b border-primary-5 flex items-center justify-between">
                    <span className="text-sm text-primary-11">
                      {selectedProjects.size} project
                      {selectedProjects.size > 1 ? "s" : ""} selected
                    </span>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={handleBulkDelete}
                    >
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
                            projects.length > 0 &&
                            selectedProjects.size === projects.length
                          }
                          onChange={handleSelectAll}
                          aria-label="Select all projects"
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
                      <th className="px-4 py-3 text-left text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Owner
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-neutral-11 uppercase tracking-wider">
                        Status
                      </th>
                      <SortableHeader
                        label="Sessions"
                        field="session_count"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                        align="center"
                      />
                      <SortableHeader
                        label="Workflows"
                        field="workflow_count"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                        align="center"
                      />
                      <SortableHeader
                        label="Connections"
                        field="connection_count"
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
                    {projects.map((project) => (
                      <tr
                        key={project.id}
                        className={`hover:bg-neutral-a6 transition-colors ${
                          selectedProjects.has(project.id)
                            ? "bg-primary-1"
                            : ""
                        }`}
                      >
                        {/* Row checkbox */}
                        <td className="px-4 py-3 w-10">
                          <Checkbox
                            checked={selectedProjects.has(project.id)}
                            onChange={() => handleSelectProject(project.id)}
                            aria-label={`Select ${project.name}`}
                            size="sm"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-medium text-neutral-12">
                              {project.name}
                            </div>
                            {project.description && (
                              <div className="text-sm text-neutral-11 truncate max-w-xs">
                                {project.description}
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-neutral-11">
                          <div className="flex items-center gap-1.5">
                            <User className="w-4 h-4" />
                            <span className="truncate max-w-[120px]">
                              {project.owner_name || project.owner_id}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                              project.status === "active"
                                ? "bg-success-3 text-success-11"
                                : "bg-neutral-2 text-neutral-11"
                            }`}
                          >
                            {project.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          <div className="flex items-center justify-center gap-1">
                            <MessageSquare className="w-4 h-4" />
                            {project.session_count}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          <div className="flex items-center justify-center gap-1">
                            <GitBranch className="w-4 h-4" />
                            {project.workflow_count}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          <div className="flex items-center justify-center gap-1">
                            <Plug className="w-4 h-4" />
                            {project.connection_count}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-neutral-11">
                          {project.updated_at
                            ? new Date(project.updated_at).toLocaleDateString()
                            : "-"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleOpenProject(project.id)}
                              aria-label="Open project"
                              title="Open"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                handleDeleteProject(project.id, project.name)
                              }
                              aria-label="Delete project"
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

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-6">
                <PagePagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                  totalItems={total}
                  perPage={perPage}
                  onPerPageChange={handlePerPageChange}
                  isLoading={isFetching}
                />
              </div>
            )}
          </>
        )}
      </div>
      {/* Create Project Dialog */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-neutral-a6 flex items-center justify-center z-60">
          <div className="bg-neutral-1 rounded-lg shadow-xl w-full max-w-md mx-4">
            {/* Dialog header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-5">
              <h2 className="text-lg font-semibold text-neutral-12">
                Create New Project
              </h2>
              <Button
                className="p-1 text-neutral-9 hover:text-neutral-11"
                onClick={() => setShowCreateDialog(false)}
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Dialog body */}
            <div className="px-6 py-4">
              <div className="mb-4">
                <label
                  htmlFor="projectName"
                  className="block text-sm font-medium text-neutral-11 mb-1"
                >
                  Project Name
                </label>
                <Input
                  className="px-3 py-2 text-neutral-12 focus:ring-primary-7"
                  id="projectName"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="My Project"
                  autoFocus
                />
              </div>
              <div>
                <label
                  htmlFor="projectDescription"
                  className="block text-sm font-medium text-neutral-11 mb-1"
                >
                  Description (optional)
                </label>
                <Textarea
                  className="px-3 py-2 text-neutral-12 focus:ring-primary-7 resize-none"
                  id="projectDescription"
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  placeholder="Describe your project..."
                  rows={3}
                />
              </div>
            </div>

            {/* Dialog footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-5">
              <Button
                variant="secondary"
                onClick={() => setShowCreateDialog(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || isCreating}
              >
                {isCreating ? "Creating..." : "Create"}
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Delete Project Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onClose={cancelDeleteProject}
        onConfirm={confirmDeleteProject}
        title="Delete Project"
        message={`Are you sure you want to delete "${projectToDelete?.name}"? This action cannot be undone and will remove all associated sessions and workflows.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={isDeleting}
      />
      {/* Bulk Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showBulkDeleteDialog}
        onClose={cancelBulkDeleteProjects}
        onConfirm={confirmBulkDeleteProjects}
        title="Delete Selected Projects"
        message={`Are you sure you want to delete ${selectedProjects.size} project${selectedProjects.size > 1 ? "s" : ""}? This action cannot be undone and will remove all associated sessions and workflows.`}
        confirmText={`Delete ${selectedProjects.size} Project${selectedProjects.size > 1 ? "s" : ""}`}
        cancelText="Cancel"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </div>
  );
}
