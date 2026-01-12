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

import { Button } from "@/components/UI";

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
          "bg-neutral-50 dark:bg-neutral-900",
          "text-neutral-500 dark:text-neutral-400",
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
          "bg-neutral-50 dark:bg-neutral-900",
          className,
        )}
      >
        <header className="px-6 py-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
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
          "bg-neutral-50 dark:bg-neutral-900",
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
        "bg-neutral-50 dark:bg-neutral-900",
        compact && "text-sm",
        className,
      )}
    >
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FolderKanban className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <div>
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
                {project?.name || "Project"}
              </h2>
              {project?.description && (
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
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
                  : "bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
              }`}
            >
              {project?.status || "unknown"}
            </span>
            <Button
              variant="secondary"
              className="p-2 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700 rounded-lg"
              onClick={() => refetch()}
              title="Refresh"
            >
              <RefreshCw size={16} />
            </Button>
          </div>
        </div>
      </header>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Project Info */}
          <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
            <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
              Project Info
            </h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <User
                  size={16}
                  className="text-neutral-400 dark:text-neutral-400"
                />
                <span className="text-neutral-600 dark:text-neutral-400">
                  Owner:
                </span>
                <span className="text-neutral-900 dark:text-neutral-100">
                  {project?.ownerName || project?.ownerId || "Unknown"}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar
                  size={16}
                  className="text-neutral-400 dark:text-neutral-400"
                />
                <span className="text-neutral-600 dark:text-neutral-400">
                  Created:
                </span>
                <span className="text-neutral-900 dark:text-neutral-100">
                  {formatDate(project?.createdAt)}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar
                  size={16}
                  className="text-neutral-400 dark:text-neutral-400"
                />
                <span className="text-neutral-600 dark:text-neutral-400">
                  Updated:
                </span>
                <span className="text-neutral-900 dark:text-neutral-100">
                  {formatDate(project?.updatedAt)}
                </span>
              </div>
            </div>
          </div>

          {/* Resource Cards */}
          <div>
            <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
              Resources
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {resourceLinks.map((resource) => (
                <Button
                  key={resource.label}
                  onClick={() => navigate(resource.path)}
                  className={cn(
                    "p-4 rounded-lg border border-neutral-200 dark:border-neutral-700",
                    "bg-white dark:bg-neutral-800 hover:shadow-md transition-shadow",
                    "text-left",
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={cn("p-2 rounded-lg", resource.bgColor)}>
                      <resource.icon size={20} className={resource.color} />
                    </div>
                    <ExternalLink
                      size={14}
                      className="text-neutral-400 dark:text-neutral-400"
                    />
                  </div>
                  <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                    {resource.count}
                  </div>
                  <div className="text-sm text-neutral-600 dark:text-neutral-400">
                    {resource.label}
                  </div>
                </Button>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
            <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
              Quick Actions
            </h3>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="primary"
                className="flex px-3 py-2 text-sm bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/30"
                onClick={() => navigate(`/studio/chat?project=${projectId}`)}
              >
                <MessageSquare size={16} />
                New Session
              </Button>
              <Button
                className="flex px-3 py-2 text-sm bg-insight-50 text-insight-700 dark:bg-insight-900/20 dark:text-insight-400 rounded-lg hover:bg-insight-100 dark:hover:bg-insight-900/30"
                onClick={() =>
                  navigate(`/studio/workflows?project=${projectId}`)
                }
              >
                <GitBranch size={16} />
                Create Workflow
              </Button>
              <Button
                variant="secondary"
                className="flex px-3 py-2 text-sm bg-neutral-50 text-neutral-700 dark:text-neutral-200 dark:bg-neutral-700 dark:text-neutral-300 rounded-lg hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-600"
                onClick={() => navigate(`/studio/projects/${projectId}`)}
              >
                <ExternalLink size={16} />
                Full View
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProjectDocument;
