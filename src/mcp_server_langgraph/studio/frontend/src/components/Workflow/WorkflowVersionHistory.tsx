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
import type { WorkflowVersionCamelCase } from "../../types/api";
import { cn } from "../../utils/cn";

import { Button, Checkbox } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface WorkflowVersionHistoryProps {
  /** Workflow ID to show versions for */
  workflowId: string;
  /** Currently active version ID */
  currentVersionId?: string;
  /** Callback when a version is selected for preview */
  onVersionSelect?: (version: WorkflowVersionCamelCase) => void;
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
    (version: WorkflowVersionCamelCase) => {
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
          "bg-neutral-1",
          className,
        )}
      >
        <Loader2
          data-testid="loading-spinner"
          size={24}
          className="animate-spin text-neutral-9"
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
          "bg-neutral-1",
          className,
        )}
      >
        <AlertCircle size={24} className="text-error-9" />
        <p className="text-sm text-neutral-10">Failed to load versions</p>
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
          "bg-neutral-1",
          className,
        )}
      >
        <History size={24} className="text-neutral-9" />
        <p className="text-sm text-neutral-10">No versions yet</p>
      </div>
    );
  }

  return (
    <div
      data-testid="version-history-panel"
      className={cn("flex flex-col bg-neutral-1", className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-5">
        <Button
          variant="primary"
          className="flex text-left"
          type="button"
          data-testid="version-history-button"
        >
          <History size={16} className="text-neutral-10" />
          <h3 className="text-sm font-medium text-neutral-12">
            Version History
          </h3>
        </Button>

        {/* Compare button (when 2 versions selected) */}
        {enableDiff && compareVersionIds.length === 2 && (
          <Button
            variant="primary"
            size="sm"
            className="flex px-2 py-1 text-xs text-primary-10 dark:text-primary-7 hover:bg-primary-1 dark:hover:bg-primary-a3 rounded"
            type="button"
          >
            <GitCompare size={12} />
            Compare
          </Button>
        )}
      </div>
      {/* Version list */}
      <div className="flex-1 overflow-y-auto">
        <ul className="divide-y divide-neutral-5">
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
                    ? "bg-primary-1 dark:bg-primary-a3"
                    : "hover:bg-neutral-1",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Version number and status */}
                    <div className="flex items-center gap-2">
                      {enableDiff && (
                        <Checkbox
                          data-testid={`version-checkbox-${version.id}`}
                          checked={compareVersionIds.includes(version.id)}
                          onChange={() => handleCheckboxChange(version.id)}
                          onClick={(e) => e.stopPropagation()}
                          size="sm"
                        />
                      )}
                      <span className="text-sm font-medium text-neutral-12">
                        v{version.versionNumber}
                      </span>
                      {isCurrent && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-success-3 text-success-11 bg-success-4 dark:text-success-7 rounded">
                          <Check size={10} />
                          Current
                        </span>
                      )}
                    </div>

                    {/* Commit message */}
                    {version.commitMessage && (
                      <p className="mt-0.5 text-sm text-neutral-11 truncate">
                        {version.commitMessage}
                      </p>
                    )}

                    {/* Meta info */}
                    <div className="mt-1 flex items-center gap-2 text-xs text-neutral-10">
                      <span>{version.createdBy}</span>
                      <span>-</span>
                      <span>{formatDate(version.createdAt)}</span>
                    </div>

                    {/* Telemetry info */}
                    {(version.promptVersion || version.promptModel) && (
                      <div className="mt-1 flex items-center gap-2 text-xs text-neutral-9">
                        {version.promptVersion && (
                          <span className="px-1.5 py-0.5 bg-neutral-2 rounded">
                            {version.promptVersion}
                          </span>
                        )}
                        {version.promptModel && (
                          <span className="px-1.5 py-0.5 bg-neutral-2 rounded">
                            {version.promptModel}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Restore button (for non-current versions) */}
                  {!isCurrent && (
                    <Button
                      variant="primary"
                      type="button"
                      data-testid={`restore-button-${version.id}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRestore(version.id);
                      }}
                      disabled={isRestoring}
                      className={cn(
                        "flex items-center gap-1 px-2 py-1 text-xs font-medium rounded",
                        "text-neutral-11",
                        "hover:bg-neutral-2",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                      )}
                    >
                      <RotateCcw size={12} />
                      Restore
                    </Button>
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
