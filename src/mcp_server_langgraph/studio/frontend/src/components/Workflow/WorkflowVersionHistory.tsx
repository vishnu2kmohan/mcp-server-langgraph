/**
 * WorkflowVersionHistory Component
 *
 * Displays version history for a workflow with support for:
 * - Viewing all versions with commit messages
 * - Selecting versions for preview
 * - Restoring previous versions
 * - Viewing telemetry metadata (prompt version/model)
 * - Comparing versions (diff view)
 *
 * Plan: greedy-wiggling-marshmallow.md, Phase 3
 * ADR: adr-0089-prompt-architecture-centralization.md
 */

import { useState, useCallback } from "react";
import {
  History,
  Loader2,
  AlertCircle,
  RotateCcw,
  GitCompare,
  Check,
} from "lucide-react";

import {
  useGetWorkflowVersionsQuery,
  useRestoreWorkflowVersionMutation,
} from "../../api";
import type { WorkflowVersion } from "../../types";
import { cn } from "../../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface WorkflowVersionHistoryProps {
  /** Workflow ID to show versions for */
  workflowId: string;
  /** Currently active version ID */
  currentVersionId?: string;
  /** Callback when a version is selected for preview */
  onVersionSelect?: (version: WorkflowVersion) => void;
  /** Enable diff comparison mode */
  enableDiff?: boolean;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function WorkflowVersionHistory({
  workflowId,
  currentVersionId,
  onVersionSelect,
  enableDiff = false,
  className,
}: WorkflowVersionHistoryProps) {
  // State
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    null,
  );
  const [compareVersionIds, setCompareVersionIds] = useState<string[]>([]);

  // Fetch versions
  const {
    data: versions,
    isLoading,
    error,
  } = useGetWorkflowVersionsQuery(workflowId);

  // Restore mutation
  const [restoreVersion, { isLoading: isRestoring }] =
    useRestoreWorkflowVersionMutation();

  // Handle version selection
  const handleVersionClick = useCallback(
    (version: WorkflowVersion) => {
      setSelectedVersionId(version.id);
      onVersionSelect?.(version);
    },
    [onVersionSelect],
  );

  // Handle restore
  const handleRestore = useCallback(
    async (versionId: string) => {
      try {
        await restoreVersion({ workflowId, versionId }).unwrap();
      } catch (err) {
        console.error("Failed to restore version:", err);
      }
    },
    [workflowId, restoreVersion],
  );

  // Handle checkbox for comparison
  const handleCheckboxChange = useCallback((versionId: string) => {
    setCompareVersionIds((prev) => {
      if (prev.includes(versionId)) {
        return prev.filter((id) => id !== versionId);
      }
      // Only allow 2 versions for comparison
      if (prev.length >= 2) {
        return [prev[1], versionId];
      }
      return [...prev, versionId];
    });
  }, []);

  // Format date
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="version-history-panel"
        className={cn(
          "flex items-center justify-center h-48",
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <Loader2
          data-testid="loading-spinner"
          size={24}
          className="animate-spin text-gray-400"
        />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="version-history-panel"
        className={cn(
          "flex flex-col items-center justify-center h-48 gap-2",
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <AlertCircle size={24} className="text-red-500" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Failed to load versions
        </p>
      </div>
    );
  }

  // Empty state
  if (!versions || versions.length === 0) {
    return (
      <div
        data-testid="version-history-panel"
        className={cn(
          "flex flex-col items-center justify-center h-48 gap-2",
          "bg-white dark:bg-gray-900",
          className,
        )}
      >
        <History size={24} className="text-gray-400" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No versions yet
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="version-history-panel"
      className={cn("flex flex-col bg-white dark:bg-gray-900", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          data-testid="version-history-button"
          className="flex items-center gap-2 text-left"
        >
          <History size={16} className="text-gray-500" />
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
            Version History
          </h3>
        </button>

        {/* Compare button (when 2 versions selected) */}
        {enableDiff && compareVersionIds.length === 2 && (
          <button
            type="button"
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
          >
            <GitCompare size={12} />
            Compare
          </button>
        )}
      </div>

      {/* Version list */}
      <div className="flex-1 overflow-y-auto">
        <ul className="divide-y divide-gray-100 dark:divide-gray-800">
          {versions.map((version) => {
            const isCurrent = version.id === currentVersionId;
            const isSelected = version.id === selectedVersionId;

            return (
              <li
                key={version.id}
                data-testid={`version-item-${version.id}`}
                data-selected={isSelected}
                onClick={() => handleVersionClick(version)}
                className={cn(
                  "px-4 py-3 cursor-pointer transition-colors",
                  isSelected
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : "hover:bg-gray-50 dark:hover:bg-gray-800",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Version number and status */}
                    <div className="flex items-center gap-2">
                      {enableDiff && (
                        <input
                          type="checkbox"
                          data-testid={`version-checkbox-${version.id}`}
                          checked={compareVersionIds.includes(version.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleCheckboxChange(version.id);
                          }}
                          className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      )}
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        v{version.version_number}
                      </span>
                      {isCurrent && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">
                          <Check size={10} />
                          Current
                        </span>
                      )}
                    </div>

                    {/* Commit message */}
                    {version.commit_message && (
                      <p className="mt-0.5 text-sm text-gray-700 dark:text-gray-300 truncate">
                        {version.commit_message}
                      </p>
                    )}

                    {/* Meta info */}
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>{version.created_by}</span>
                      <span>-</span>
                      <span>{formatDate(version.created_at)}</span>
                    </div>

                    {/* Telemetry info */}
                    {(version.prompt_version || version.prompt_model) && (
                      <div className="mt-1 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                        {version.prompt_version && (
                          <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
                            {version.prompt_version}
                          </span>
                        )}
                        {version.prompt_model && (
                          <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
                            {version.prompt_model}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Restore button (for non-current versions) */}
                  {!isCurrent && (
                    <button
                      type="button"
                      data-testid={`restore-button-${version.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRestore(version.id);
                      }}
                      disabled={isRestoring}
                      className={cn(
                        "flex items-center gap-1 px-2 py-1 text-xs font-medium rounded",
                        "text-gray-600 dark:text-gray-400",
                        "hover:bg-gray-100 dark:hover:bg-gray-700",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                      )}
                    >
                      <RotateCcw size={12} />
                      Restore
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

export default WorkflowVersionHistory;
