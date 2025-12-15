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
import { SearchInput } from "../components/UI/SearchInput";
import { PagePagination } from "../components/UI/Pagination";
import { SortDropdown, type SortOrder } from "../components/UI/SortDropdown";
import { FilterChips } from "../components/UI/FilterChips";
import { ArrowUp, ArrowDown } from "lucide-react";
import {
  useListProjectsQuery,
  useCreateProjectMutation,
  useDeleteProjectMutation,
} from "../api";
import { SkeletonList, ErrorState, ConfirmDialog } from "../components/UI";

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
  { value: "active", label: "Active", color: "green" },
  { value: "archived", label: "Archived", color: "gray" },
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
      className={`px-4 py-3 text-${align} text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors select-none`}
      onClick={handleClick}
    >
      <div className={`flex items-center gap-1 ${alignClass}`}>
        <span>{label}</span>
        {isActive &&
          (currentSortOrder === "asc" ? (
            <ArrowUp className="w-3 h-3 text-blue-500" />
          ) : (
            <ArrowDown className="w-3 h-3 text-blue-500" />
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
      <div className="h-full p-6 bg-gray-50 dark:bg-gray-900">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Projects
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
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
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FolderKanban className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Projects
            </h1>
            <span className="text-sm text-gray-500 dark:text-gray-400">
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
            {/* Sort dropdown */}
            <SortDropdown
              options={SORT_OPTIONS}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onChange={handleSortChange}
              ariaLabel="Sort projects"
            />
            {/* View mode toggle */}
            <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode("grid")}
                className={`p-2 transition-colors ${
                  viewMode === "grid"
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
                title="Grid view"
                aria-label="Grid view"
                aria-pressed={viewMode === "grid"}
              >
                <LayoutGrid className="w-5 h-5" />
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`p-2 transition-colors ${
                  viewMode === "table"
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
                title="Table view"
                aria-label="Table view"
                aria-pressed={viewMode === "table"}
              >
                <List className="w-5 h-5" />
              </button>
            </div>
            <button
              onClick={handleRefresh}
              disabled={isFetching}
              className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw
                className={`w-5 h-5 ${isFetching ? "animate-spin" : ""}`}
              />
            </button>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Create Project
            </button>
          </div>
        </div>
        {/* Status filter chips */}
        <div className="mt-3">
          <FilterChips
            options={STATUS_OPTIONS}
            value={statusFilter || null}
            onChange={handleStatusChange}
            ariaLabel="Filter projects by status"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {projects.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full text-center">
            <FolderKanban className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No projects yet
            </h2>
            <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md">
              Projects are unified workspaces that contain your sessions,
              workflows, and connections. Create your first project to get
              started.
            </p>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-5 h-5" />
              Create Project
            </button>
          </div>
        ) : (
          <>
            {viewMode === "grid" ? (
              /* Grid View */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {projects.map((project) => (
                  <div
                    key={project.id}
                    className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    {/* Project header */}
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-medium text-gray-900 dark:text-gray-100">
                          {project.name}
                        </h3>
                        {project.description && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {project.description}
                          </p>
                        )}
                      </div>
                      <span
                        className={`px-2 py-0.5 text-xs rounded-full ${
                          project.status === "active"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                        }`}
                      >
                        {project.status}
                      </span>
                    </div>

                    {/* Owner info */}
                    <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 mb-3">
                      <User className="w-3.5 h-3.5" />
                      <span>{project.owner_name || project.owner_id}</span>
                    </div>

                    {/* Resource counts */}
                    <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mb-4">
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
                    <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
                      <button
                        onClick={() => handleOpenProject(project.id)}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                        aria-label="Open project"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open
                      </button>
                      <button
                        onClick={() =>
                          handleDeleteProject(project.id, project.name)
                        }
                        className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                        aria-label="Delete project"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Table View */
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                {/* Bulk action bar */}
                {selectedProjects.size > 0 && (
                  <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 flex items-center justify-between">
                    <span className="text-sm text-blue-700 dark:text-blue-300">
                      {selectedProjects.size} project
                      {selectedProjects.size > 1 ? "s" : ""} selected
                    </span>
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete Selected
                    </button>
                  </div>
                )}
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-900/50">
                    <tr>
                      {/* Select all checkbox */}
                      <th className="px-4 py-3 w-10">
                        <input
                          type="checkbox"
                          checked={
                            projects.length > 0 &&
                            selectedProjects.size === projects.length
                          }
                          onChange={handleSelectAll}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
                          aria-label="Select all projects"
                        />
                      </th>
                      <SortableHeader
                        label="Name"
                        field="name"
                        currentSortBy={sortBy}
                        currentSortOrder={sortOrder}
                        onSort={handleSortChange}
                      />
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Owner
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
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
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {projects.map((project) => (
                      <tr
                        key={project.id}
                        className={`hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                          selectedProjects.has(project.id)
                            ? "bg-blue-50 dark:bg-blue-900/10"
                            : ""
                        }`}
                      >
                        {/* Row checkbox */}
                        <td className="px-4 py-3 w-10">
                          <input
                            type="checkbox"
                            checked={selectedProjects.has(project.id)}
                            onChange={() => handleSelectProject(project.id)}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
                            aria-label={`Select ${project.name}`}
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-medium text-gray-900 dark:text-gray-100">
                              {project.name}
                            </div>
                            {project.description && (
                              <div className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                                {project.description}
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
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
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                                : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                            }`}
                          >
                            {project.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-gray-600 dark:text-gray-400">
                          <div className="flex items-center justify-center gap-1">
                            <MessageSquare className="w-4 h-4" />
                            {project.session_count}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-gray-600 dark:text-gray-400">
                          <div className="flex items-center justify-center gap-1">
                            <GitBranch className="w-4 h-4" />
                            {project.workflow_count}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-gray-600 dark:text-gray-400">
                          <div className="flex items-center justify-center gap-1">
                            <Plug className="w-4 h-4" />
                            {project.connection_count}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center text-sm text-gray-500 dark:text-gray-400">
                          {project.updated_at
                            ? new Date(project.updated_at).toLocaleDateString()
                            : "-"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleOpenProject(project.id)}
                              className="p-1.5 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                              aria-label="Open project"
                              title="Open"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() =>
                                handleDeleteProject(project.id, project.name)
                              }
                              className="p-1.5 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                              aria-label="Delete project"
                              title="Delete"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
            {/* Dialog header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Create New Project
              </h2>
              <button
                onClick={() => setShowCreateDialog(false)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Dialog body */}
            <div className="px-6 py-4">
              <div className="mb-4">
                <label
                  htmlFor="projectName"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Project Name
                </label>
                <input
                  type="text"
                  id="projectName"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="My Project"
                  autoFocus
                />
              </div>
              <div>
                <label
                  htmlFor="projectDescription"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Description (optional)
                </label>
                <textarea
                  id="projectDescription"
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  placeholder="Describe your project..."
                  rows={3}
                />
              </div>
            </div>

            {/* Dialog footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowCreateDialog(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || isCreating}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? "Creating..." : "Create"}
              </button>
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
