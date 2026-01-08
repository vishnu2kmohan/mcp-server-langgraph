/**
 * ProjectDocument Component
 *
 * A project document component for use within the MainDock.
 * Displays project details, child resources, and quick actions.
 *
 * Features:
 * - Project info (name, description, status, owner)
 * - Resource counts (sessions, workflows, connections)
 * - Quick navigation to child resources
 * - Compact mode for docked tabs
 */

import { useNavigate } from "react-router";
import {
  FolderKanban,
  MessageSquare,
  GitBranch,
  Plug,
  User,
  Calendar,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { useGetProjectQuery } from "../../api";
import { Skeleton, SkeletonCard, ErrorState } from "../UI";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface ProjectDocumentProps {
  /** Project ID to display */
  projectId: string;
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function ProjectDocument({
  projectId,
  compact = false,
  className,
}: ProjectDocumentProps) {
  const navigate = useNavigate();

  // Fetch project data
  const {
    data: project,
    isLoading,
    isError,
    error,
    refetch,
  } = useGetProjectQuery(projectId, { skip: !projectId });

  // Empty state
  if (!projectId) {
    return (
      <div
        data-testid="project-document"
        className={cn(
          "flex flex-col items-center justify-center h-full",
          "bg-gray-50 dark:bg-gray-900",
          "text-gray-500 dark:text-gray-400",
          compact && "text-sm",
          className,
        )}
      >
        <FolderKanban size={64} className="mb-4 opacity-50" />
        <h2 className="text-xl font-semibold mb-2">No project selected</h2>
        <p className="text-sm">Select or create a project to get started.</p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="project-document"
        className={cn(
          "flex flex-col h-full",
          "bg-gray-50 dark:bg-gray-900",
          className,
        )}
      >
        <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <Skeleton className="h-6 w-1/3 mb-2" />
          <Skeleton className="h-4 w-1/2" />
        </header>
        <div className="p-6 space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div
        data-testid="project-document"
        className={cn(
          "flex flex-col h-full",
          "bg-gray-50 dark:bg-gray-900",
          className,
        )}
      >
        <ErrorState
          title="Failed to load project"
          message={
            (error as { message?: string })?.message ||
            "Unable to fetch project data."
          }
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const resourceLinks = [
    {
      icon: MessageSquare,
      label: "Sessions",
      count: project?.sessionCount ?? 0,
      path: `/studio/chat?project=${projectId}`,
      color: "text-primary-600 dark:text-primary-400",
      bgColor: "bg-primary-50 dark:bg-primary-900/20",
    },
    {
      icon: GitBranch,
      label: "Workflows",
      count: project?.workflowCount ?? 0,
      path: `/studio/workflows?project=${projectId}`,
      color: "text-insight-600 dark:text-insight-400",
      bgColor: "bg-insight-50 dark:bg-insight-900/20",
    },
    {
      icon: Plug,
      label: "Connections",
      count: project?.connectionCount ?? 0,
      path: `/studio/connections/mcp?project=${projectId}`,
      color: "text-success-600 dark:text-success-400",
      bgColor: "bg-success-50 dark:bg-success-900/20",
    },
  ];

  return (
    <div
      data-testid="project-document"
      className={cn(
        "flex flex-col h-full",
        "bg-gray-50 dark:bg-gray-900",
        compact && "text-sm",
        className,
      )}
    >
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FolderKanban className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {project?.name || "Project"}
              </h2>
              {project?.description && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {project.description}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-1 text-xs rounded-full ${
                project?.status === "active"
                  ? "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
              }`}
            >
              {project?.status || "unknown"}
            </span>
            <button
              onClick={() => refetch()}
              className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg"
              title="Refresh"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Project Info */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Project Info
            </h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <User size={16} className="text-gray-400 dark:text-gray-400" />
                <span className="text-gray-600 dark:text-gray-400">Owner:</span>
                <span className="text-gray-900 dark:text-gray-100">
                  {project?.ownerName || project?.ownerId || "Unknown"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar
                  size={16}
                  className="text-gray-400 dark:text-gray-400"
                />
                <span className="text-gray-600 dark:text-gray-400">
                  Created:
                </span>
                <span className="text-gray-900 dark:text-gray-100">
                  {formatDate(project?.createdAt)}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar
                  size={16}
                  className="text-gray-400 dark:text-gray-400"
                />
                <span className="text-gray-600 dark:text-gray-400">
                  Updated:
                </span>
                <span className="text-gray-900 dark:text-gray-100">
                  {formatDate(project?.updatedAt)}
                </span>
              </div>
            </div>
          </div>

          {/* Resource Cards */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Resources
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {resourceLinks.map((resource) => (
                <button
                  key={resource.label}
                  onClick={() => navigate(resource.path)}
                  className={cn(
                    "p-4 rounded-lg border border-gray-200 dark:border-gray-700",
                    "bg-white dark:bg-gray-800 hover:shadow-md transition-shadow",
                    "text-left",
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={cn("p-2 rounded-lg", resource.bgColor)}>
                      <resource.icon size={20} className={resource.color} />
                    </div>
                    <ExternalLink
                      size={14}
                      className="text-gray-400 dark:text-gray-400"
                    />
                  </div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {resource.count}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {resource.label}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => navigate(`/studio/chat?project=${projectId}`)}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/30"
              >
                <MessageSquare size={16} />
                New Session
              </button>
              <button
                onClick={() =>
                  navigate(`/studio/workflows?project=${projectId}`)
                }
                className="flex items-center gap-2 px-3 py-2 text-sm bg-insight-50 text-insight-700 dark:bg-insight-900/20 dark:text-insight-400 rounded-lg hover:bg-insight-100 dark:hover:bg-insight-900/30"
              >
                <GitBranch size={16} />
                Create Workflow
              </button>
              <button
                onClick={() => navigate(`/studio/projects/${projectId}`)}
                className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-50 text-gray-700 dark:text-gray-200 dark:bg-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-600"
              >
                <ExternalLink size={16} />
                Full View
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectDocument;
