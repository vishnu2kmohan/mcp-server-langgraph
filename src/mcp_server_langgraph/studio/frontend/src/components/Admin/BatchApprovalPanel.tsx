/**
 * BatchApprovalPanel Component
 *
 * Panel for batch approving or rejecting multiple agent HITL requests.
 *
 * Features:
 * - Display multiple pending approval requests
 * - Select/deselect individual requests
 * - Select all / deselect all
 * - Batch approve selected requests
 * - Batch reject selected requests
 * - Common reason input
 * - Loading states
 * - Accessibility support
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { useState, useMemo, useCallback } from "react";
import { CheckCircle, XCircle, Loader2, AlertTriangle } from "lucide-react";
import { cn } from "../../utils/cn";
import type { AgentApprovalRequestCamelCase } from "../../types/hitl";

import { Button, Checkbox, Input } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

// Use camelCase type per ADR-0091
export type ApprovalRequest = AgentApprovalRequestCamelCase;

export interface BatchApprovalPanelProps {
  /** List of pending approval requests */
  approvals: ApprovalRequest[];
  /** Callback when batch approve is clicked */
  onBatchApprove: (requestIds: string[], reason?: string) => Promise<void>;
  /** Callback when batch reject is clicked */
  onBatchReject: (requestIds: string[], reason?: string) => Promise<void>;
  /** Current user for attribution */
  currentUser?: string;
  /** Loading state for approval */
  isApproving?: boolean;
  /** Loading state for rejection */
  isRejecting?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get confidence color based on value
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "text-success-600 dark:text-success-400";
  if (confidence >= 0.7) return "text-primary-600 dark:text-primary-400";
  if (confidence >= 0.5) return "text-warning-600 dark:text-warning-400";
  return "text-error-600 dark:text-error-400";
}

/**
 * Get confidence background color
 */
function getConfidenceBgColor(confidence: number): string {
  if (confidence >= 0.9) return "bg-success-500";
  if (confidence >= 0.7) return "bg-primary-500";
  if (confidence >= 0.5) return "bg-warning-500";
  return "bg-error-500";
}

// =============================================================================
// Component
// =============================================================================

export function BatchApprovalPanel({
  approvals,
  onBatchApprove,
  onBatchReject,
  isApproving = false,
  isRejecting = false,
  className,
}: BatchApprovalPanelProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [reason, setReason] = useState("");

  const isLoading = isApproving || isRejecting;
  const hasApprovals = approvals.length > 0;
  const selectedCount = selectedIds.size;
  const allSelected = hasApprovals && selectedCount === approvals.length;

  // Memoized selected IDs array
  const selectedArray = useMemo(() => Array.from(selectedIds), [selectedIds]);

  // Toggle individual selection
  const handleToggleSelect = useCallback((requestId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(requestId)) {
        next.delete(requestId);
      } else {
        next.add(requestId);
      }
      return next;
    });
  }, []);

  // Toggle select all
  const handleToggleSelectAll = useCallback(() => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(approvals.map((a) => a.requestId)));
    }
  }, [allSelected, approvals]);

  // Handle batch approve
  const handleBatchApprove = useCallback(async () => {
    if (selectedCount === 0) return;
    await onBatchApprove(selectedArray, reason || undefined);
    setSelectedIds(new Set());
    setReason("");
  }, [selectedCount, selectedArray, reason, onBatchApprove]);

  // Handle batch reject
  const handleBatchReject = useCallback(async () => {
    if (selectedCount === 0) return;
    await onBatchReject(selectedArray, reason || undefined);
    setSelectedIds(new Set());
    setReason("");
  }, [selectedCount, selectedArray, reason, onBatchReject]);

  // Empty state
  if (!hasApprovals) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center p-8 text-center",
          "border border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg",
          className,
        )}
      >
        <CheckCircle
          className="w-12 h-12 text-success-500 mb-4"
          aria-hidden="true"
        />
        <p className="text-neutral-600 dark:text-neutral-400">
          No pending approvals
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="batch-approval-panel"
      className={cn(
        "flex flex-col border border-neutral-200 dark:border-neutral-700 rounded-lg",
        className,
      )}
      role="region"
      aria-label="Batch approval panel"
    >
      {/* Header with select all and actions */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
        {/* Select all */}
        <div className="flex items-center gap-3">
          <Checkbox
            data-testid="select-all"
            checked={allSelected}
            onChange={handleToggleSelectAll}
            disabled={isLoading}
            label="Select all"
            size="sm"
          />
          {selectedCount > 0 && (
            <span className="text-sm text-neutral-500 dark:text-neutral-400">
              {selectedCount} selected
            </span>
          )}
        </div>

        {/* Batch action buttons */}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            data-testid="batch-approve-btn"
            onClick={handleBatchApprove}
            disabled={selectedCount === 0 || isLoading}
            aria-label="Approve selected"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium",
              "bg-success-600 text-white hover:bg-success-700",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors",
            )}
          >
            {isApproving ? (
              <Loader2
                className="w-4 h-4 animate-spin"
                data-testid="batch-approve-loading"
              />
            ) : (
              <CheckCircle className="w-4 h-4" aria-hidden="true" />
            )}
            Approve selected
          </Button>
          <Button
            type="button"
            data-testid="batch-reject-btn"
            onClick={handleBatchReject}
            disabled={selectedCount === 0 || isLoading}
            aria-label="Reject selected"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium",
              "bg-error-600 text-white hover:bg-error-700",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors",
            )}
          >
            {isRejecting ? (
              <Loader2
                className="w-4 h-4 animate-spin"
                data-testid="batch-reject-loading"
              />
            ) : (
              <XCircle className="w-4 h-4" aria-hidden="true" />
            )}
            Reject selected
          </Button>
        </div>
      </div>
      {/* Common reason input */}
      <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
        <Input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Common reason for all (optional)"
          disabled={isLoading}
          className={cn(
            "w-full px-3 py-2 rounded border",
            "border-neutral-300 dark:border-neutral-600",
            "bg-white dark:bg-neutral-800",
            "text-neutral-900 dark:text-neutral-100",
            "placeholder-neutral-400 dark:placeholder-neutral-500",
            "focus:ring-2 focus:ring-primary-500 focus:border-primary-500",
            "disabled:opacity-50",
          )}
        />
      </div>
      {/* Approval list */}
      <div className="divide-y divide-neutral-200 dark:divide-neutral-700 max-h-96 overflow-y-auto">
        {approvals.map((approval) => {
          const isSelected = selectedIds.has(approval.requestId);
          const confidencePercent = Math.round(approval.confidence * 100);

          return (
            <div
              key={approval.requestId}
              className={cn(
                "flex items-center gap-4 p-4",
                "hover:bg-neutral-50 dark:hover:bg-neutral-800/50",
                isSelected && "bg-primary-50 dark:bg-primary-900/20",
              )}
            >
              {/* Checkbox */}
              <Checkbox
                data-testid={`select-request-${approval.requestId}`}
                checked={isSelected}
                onChange={() => handleToggleSelect(approval.requestId)}
                disabled={isLoading}
                aria-label={`Select ${approval.agentName}`}
                size="sm"
              />
              {/* Confidence indicator */}
              <div className="flex flex-col items-center w-12">
                <span
                  className={cn(
                    "text-sm font-bold",
                    getConfidenceColor(approval.confidence),
                  )}
                >
                  {confidencePercent}%
                </span>
                <div className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full mt-1">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      getConfidenceBgColor(approval.confidence),
                    )}
                    style={{ width: `${confidencePercent}%` }}
                  />
                </div>
              </div>
              {/* Agent info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-neutral-900 dark:text-white">
                    {approval.agentName}
                  </span>
                  {approval.confidence < approval.threshold && (
                    <AlertTriangle
                      className="w-4 h-4 text-warning-500"
                      aria-hidden="true"
                    />
                  )}
                </div>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate">
                  {approval.proposedAction}
                </p>
              </div>
              {/* Trigger reason badge */}
              <span
                className={cn(
                  "px-2 py-0.5 text-xs font-medium rounded",
                  "bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300",
                )}
              >
                {approval.triggerReason.replace(/_/g, " ")}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
