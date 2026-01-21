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
import { useReducedMotion } from "motion/react";
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
  if (confidence >= 0.9) return "text-success-10 dark:text-success-7";
  if (confidence >= 0.7) return "text-primary-10 dark:text-primary-7";
  if (confidence >= 0.5) return "text-warning-9 dark:text-warning-9";
  return "text-error-10 dark:text-error-7";
}

/**
 * Get confidence background color
 */
function getConfidenceBgColor(confidence: number): string {
  if (confidence >= 0.9) return "bg-success-9";
  if (confidence >= 0.7) return "bg-primary-9";
  if (confidence >= 0.5) return "bg-warning-9";
  return "bg-error-9";
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

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
          "border border-dashed border-neutral-5 rounded-lg",
          className,
        )}
      >
        <CheckCircle
          className="w-12 h-12 text-success-9 mb-4"
          aria-hidden="true"
        />
        <p className="text-neutral-11">
          No pending approvals
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="batch-approval-panel"
      className={cn(
        "flex flex-col border border-neutral-5 rounded-lg",
        className,
      )}
      role="region"
      aria-label="Batch approval panel"
    >
      {/* Header with select all and actions */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5 bg-neutral-1">
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
            <span className="text-sm text-neutral-10">
              {selectedCount} selected
            </span>
          )}
        </div>

        {/* Batch action buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            type="button"
            data-testid="batch-approve-btn"
            onClick={handleBatchApprove}
            disabled={selectedCount === 0 || isLoading}
            aria-label="Approve selected"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium",
              "bg-success-10 text-neutral-12 hover:bg-success-11",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors",
            )}>
            {isApproving ? (
              <Loader2
                className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
                data-testid="batch-approve-loading"
              />
            ) : (
              <CheckCircle className="w-4 h-4" aria-hidden="true" />
            )}
            Approve selected
          </Button>
          <Button
            variant="primary"
            type="button"
            data-testid="batch-reject-btn"
            onClick={handleBatchReject}
            disabled={selectedCount === 0 || isLoading}
            aria-label="Reject selected"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium",
              "bg-error-10 text-neutral-12 hover:bg-error-11",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors",
            )}>
            {isRejecting ? (
              <Loader2
                className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
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
      <div className="p-4 border-b border-neutral-5">
        <Input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Common reason for all (optional)"
          disabled={isLoading}
          className={cn(
            "w-full px-3 py-2 rounded border",
            "border-neutral-5",
            "bg-neutral-1",
            "text-neutral-12",
            "placeholder-neutral-9",
            "focus:ring-2 focus:ring-primary-7 focus:border-primary-9",
            "disabled:opacity-50",
          )}
        />
      </div>
      {/* Approval list */}
      <div className="divide-y divide-neutral-5 dark:divide-neutral-6 max-h-96 overflow-y-auto">
        {approvals.map((approval) => {
          const isSelected = selectedIds.has(approval.requestId);
          const confidencePercent = Math.round(approval.confidence * 100);

          return (
            <div
              key={approval.requestId}
              className={cn(
                "flex items-center gap-4 p-4",
                "hover:bg-neutral-a6",
                isSelected && "bg-primary-1 dark:bg-primary-a3",
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
                <div className="w-full h-1.5 bg-neutral-3 rounded-full mt-1">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      getConfidenceBgColor(approval.confidence),
                    )}
                    style={{ '--progress': `${confidencePercent}%` } as React.CSSProperties}
                  />
                </div>
              </div>
              {/* Agent info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-neutral-12">
                    {approval.agentName}
                  </span>
                  {approval.confidence < approval.threshold && (
                    <AlertTriangle
                      className="w-4 h-4 text-warning-9"
                      aria-hidden="true"
                    />
                  )}
                </div>
                <p className="text-sm text-neutral-11 truncate">
                  {approval.proposedAction}
                </p>
              </div>
              {/* Trigger reason badge */}
              <span
                className={cn(
                  "px-2 py-0.5 text-xs font-medium rounded",
                  "bg-neutral-2 text-neutral-11",
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
