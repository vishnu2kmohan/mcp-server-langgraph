/**
 * AgentApprovalDialog Component
 *
 * Modal dialog for approving or rejecting agent HITL requests.
 *
 * Features:
 * - Display agent request details (confidence, proposed action)
 * - Confidence gauge visualization
 * - Approve/reject with optional reason
 * - Low confidence warning
 * - Loading states
 * - Keyboard accessibility
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useReducedMotion } from "motion/react";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import { cn } from "../../utils/cn";
import {
  X,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  FileText,
  Lightbulb,
  TrendingDown,
  Shield,
  History,
  ThumbsUp,
  ThumbsDown,
} from "lucide-react";
import type { AgentApprovalRequestCamelCase } from "../../types/hitl";
import { useRiskAssessment, useDecisionHistory } from "../../hooks";

import { Button, Textarea } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

// Re-export camelCase type for external consumers (ADR-0091 Phase 10)
export type { AgentApprovalRequestCamelCase } from "../../types/hitl";

export interface AgentApprovalDialogProps {
  /** The approval request to display (camelCase per ADR-0091) */
  request: AgentApprovalRequestCamelCase;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when request is approved (camelCase per ADR-0091) */
  onApprove: (data: {
    requestId: string;
    approvedBy: string;
    reason?: string;
  }) => void;
  /** Callback when request is rejected (camelCase per ADR-0091) */
  onReject: (data: {
    requestId: string;
    rejectedBy: string;
    reason?: string;
  }) => void;
  /** Loading state for approval */
  isApproving?: boolean;
  /** Loading state for rejection */
  isRejecting?: boolean;
  /** Error message */
  error?: string | null;
  /** Current user email for attribution */
  currentUser?: string;
  /** Enable AI-powered HITL Intelligence (Sprint 6) */
  enableAI?: boolean;
  /** User ID for AI context */
  userId?: string;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get confidence color based on value
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "bg-success-9";
  if (confidence >= 0.7) return "bg-primary-9";
  if (confidence >= 0.5) return "bg-warning-9";
  return "bg-error-9";
}

/**
 * Get trigger reason explanation
 */
function getTriggerExplanation(
  triggerReason: string,
  confidence: number,
  threshold: number,
): string {
  switch (triggerReason) {
    case "low_confidence":
      return `The agent's confidence (${Math.round(confidence * 100)}%) is below your threshold (${Math.round(threshold * 100)}%). This may indicate uncertainty in the result.`;
    case "destructive_action":
      return "This action may modify or delete data. Your confirmation is required before proceeding.";
    case "external_api":
      return "This action will send data to an external service. Please review before allowing.";
    case "high_cost":
      return "This operation may incur significant costs. Please confirm.";
    case "policy_required":
      return "Your organization requires human approval for this type of action.";
    default:
      return "Human review is required for this action.";
  }
}

/**
 * Format number with commas
 */
function formatNumber(num: number): string {
  return num.toLocaleString();
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * Get risk level color
 */
function getRiskLevelColor(level: string): string {
  switch (level) {
    case "low":
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    case "medium":
      return "bg-warning-3 text-warning-11 dark:bg-warning-a4 dark:text-warning-9";
    case "high":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "critical":
      return "bg-error-4 text-error-12 dark:bg-error-a6 dark:text-error-9";
    default:
      return "bg-neutral-2 text-neutral-12";
  }
}

export function AgentApprovalDialog({
  request,
  isOpen,
  onClose,
  onApprove,
  onReject,
  isApproving = false,
  isRejecting = false,
  error = null,
  currentUser = "unknown",
  enableAI = false,
  userId = "",
}: AgentApprovalDialogProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  const [reason, setReason] = useState("");

  // Focus trap for WCAG 2.1 AA compliance (Sprint 5.2)
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, isOpen);

  // Sprint 6: HITL Intelligence hooks (camelCase per ADR-0091)
  const {
    riskScore,
    riskLevel,
    riskFactors,
    mitigations,
    recommendation,
    explanation: riskExplanation,
    isLoading: riskLoading,
  } = useRiskAssessment({
    userId,
    requestId: request.requestId,
    actionType: request.triggerReason,
    parameters: { proposedAction: request.proposedAction },
    enabled: enableAI && isOpen,
  });

  const {
    similarDecisions,
    approvalRate,
    totalSimilar,
    suggestedAction,
    isLoading: historyLoading,
  } = useDecisionHistory({
    userId,
    actionType: request.triggerReason,
    enabled: enableAI && isOpen,
  });

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setReason("");
    }
  }, [isOpen]);

  // Handle Escape key
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    },
    [isOpen, onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Handle approve (camelCase per ADR-0091)
  const handleApprove = () => {
    onApprove({
      requestId: request.requestId,
      approvedBy: currentUser,
      reason: reason.trim() || undefined,
    });
  };

  // Handle reject (camelCase per ADR-0091)
  const handleReject = () => {
    onReject({
      requestId: request.requestId,
      rejectedBy: currentUser,
      reason: reason.trim() || undefined,
    });
  };

  if (!isOpen) {
    return null;
  }

  const isLowConfidence = request.confidence < request.threshold;
  const isLoading = isApproving || isRejecting;
  const confidencePercent = Math.round(request.confidence * 100);
  const thresholdPercent = Math.round(request.threshold * 100);

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-a6"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Dialog */}
      <div className="relative bg-neutral-1 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-5">
          <h2 className="text-lg font-semibold text-neutral-12 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-warning-9" />
            Agent Decision Requires Approval
          </h2>
          <Button size="icon"
            variant="secondary"
            className="p-2 text-neutral-10 hover:text-neutral-11 hover:bg-neutral-2 rounded-lg"
            data-testid="close-dialog"
            onClick={onClose}
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Error Message */}
          {error && (
            <div className="bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg p-3 text-error-11 dark:text-error-7">
              {error}
            </div>
          )}

          {/* Confidence Gauge */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-neutral-11">
                Confidence
              </span>
              <div className="flex items-center gap-2">
                <span
                  data-testid="confidence-score"
                  className="text-sm font-bold"
                >
                  {confidencePercent}%
                </span>
                <span className="text-sm text-neutral-10">
                  / Threshold:{" "}
                  <span data-testid="confidence-threshold">
                    {thresholdPercent}%
                  </span>
                </span>
              </div>
            </div>
            <div className="h-2 w-full bg-neutral-3 rounded-full overflow-hidden">
              <div
                data-testid="confidence-gauge"
                className={`h-full transition-all ${getConfidenceColor(request.confidence)}`}
                style={{ '--progress': `${confidencePercent}%` } as React.CSSProperties}
              />
            </div>
          </div>

          {/* Low Confidence Warning */}
          {isLowConfidence && (
            <div
              data-testid="low-confidence-warning"
              className="flex items-start gap-3 bg-warning-3 bg-warning-3 border border-warning-6 dark:border-warning-11 rounded-lg p-3"
            >
              <AlertTriangle className="w-5 h-5 text-warning-9 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-warning-10 dark:text-warning-9">
                  Low Confidence
                </p>
                <p
                  data-testid="trigger-explanation"
                  className="text-sm text-warning-9 dark:text-warning-a9"
                >
                  {getTriggerExplanation(
                    request.triggerReason,
                    request.confidence,
                    request.threshold,
                  )}
                </p>
              </div>
            </div>
          )}

          {/* AI Explanation Section (AI-Native HITL Enhancement Phase 1) */}
          {/* Uses camelCase properties per ADR-0091 */}
          {request.aiExplanation && (
            <details
              data-testid="ai-explanation-section"
              className="bg-primary-1 dark:bg-primary-a3 border border-primary-4 dark:border-primary-11 rounded-lg overflow-hidden"
            >
              <summary className="cursor-pointer p-3 font-medium text-primary-11 dark:text-primary-7 hover:bg-primary-3 dark:hover:bg-primary-a4 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" />
                Why is the agent uncertain?
              </summary>
              <div className="p-3 pt-0 space-y-3 text-sm">
                {/* Why Uncertain */}
                <p className="text-neutral-11">
                  {request.aiExplanation.whyUncertain}
                </p>

                {/* What Could Go Wrong */}
                <div>
                  <p className="font-medium text-neutral-12 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-warning-9" />
                    What could go wrong:
                  </p>
                  <p className="text-neutral-11 mt-1">
                    {request.aiExplanation.whatCouldGoWrong}
                  </p>
                </div>

                {/* Safer Alternatives */}
                {request.aiExplanation.saferAlternatives &&
                  request.aiExplanation.saferAlternatives.length > 0 && (
                    <div>
                      <p className="font-medium text-neutral-12 flex items-center gap-1">
                        <Lightbulb className="w-3.5 h-3.5 text-success-9" />
                        Safer alternatives:
                      </p>
                      <ul className="mt-1 space-y-1.5">
                        {request.aiExplanation.saferAlternatives.map(
                          (alt, index) => (
                            <li
                              key={index}
                              className="text-neutral-11 pl-4 border-l-2 border-success-5 dark:border-success-11"
                            >
                              <span className="font-medium text-neutral-12">
                                {alt.action}
                              </span>
                              <span className="text-success-10 dark:text-success-7 ml-1">
                                ({Math.round(alt.confidence * 100)}%)
                              </span>
                              <span className="text-neutral-10 block text-xs">
                                Trade-off: {alt.tradeOff}
                              </span>
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}

                {/* Confidence Factors */}
                {request.aiExplanation.confidenceFactors &&
                  request.aiExplanation.confidenceFactors.length > 0 && (
                    <div>
                      <p className="font-medium text-neutral-12 flex items-center gap-1">
                        <TrendingDown className="w-3.5 h-3.5 text-error-9" />
                        Confidence factors:
                      </p>
                      <ul className="mt-1 space-y-1">
                        {request.aiExplanation.confidenceFactors.map(
                          (factor, index) => (
                            <li
                              key={index}
                              className="text-neutral-11 text-xs"
                            >
                              <span
                                className={`font-mono ${
                                  factor.weight < 0
                                    ? "text-error-10 dark:text-error-7"
                                    : "text-success-10 dark:text-success-7"
                                }`}
                              >
                                {factor.weight > 0 ? "+" : ""}
                                {(factor.weight * 100).toFixed(0)}%
                              </span>
                              <span className="mx-1">—</span>
                              {factor.evidence}
                            </li>
                          ),
                        )}
                      </ul>
                    </div>
                  )}
              </div>
            </details>
          )}

          {/* Sprint 6: Risk Assessment Panel */}
          {enableAI && (
            <div
              data-testid="hitl-risk-assessment"
              className="bg-insight-1 dark:bg-insight-a3 border border-insight-4 dark:border-insight-11 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-insight-12 dark:text-insight-2 flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  AI Risk Assessment
                </h3>
                {riskLoading && (
                  <Loader2 className={cn("w-4 h-4 text-insight-9", !prefersReducedMotion && "animate-spin")} />
                )}
              </div>

              {!riskLoading && riskScore !== null && (
                <>
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-sm text-insight-10 dark:text-insight-9">
                        Risk Score
                      </span>
                      <p
                        data-testid="risk-score"
                        className="text-lg font-bold text-insight-12 dark:text-insight-2"
                      >
                        {Math.round((riskScore || 0) * 100)}%
                      </p>
                    </div>
                    <span
                      data-testid="risk-level"
                      className={`px-2 py-1 rounded text-xs font-medium ${getRiskLevelColor(riskLevel || "")}`}
                    >
                      {riskLevel?.toUpperCase() || "UNKNOWN"}
                    </span>
                  </div>

                  {/* Risk Factors */}
                  {riskFactors && riskFactors.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-insight-11 dark:text-insight-4">
                        Risk Factors:
                      </p>
                      <ul className="space-y-1">
                        {riskFactors.map((factor, index) => (
                          <li
                            key={index}
                            className="text-xs text-insight-11 dark:text-insight-5 flex items-center gap-2"
                          >
                            <span className="font-mono text-insight-9">
                              {Math.round((factor.weight || 0) * 100)}%
                            </span>
                            <span>{factor.description || factor.factor}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Mitigations */}
                  {mitigations && mitigations.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-insight-11 dark:text-insight-4">
                        Suggested Mitigations:
                      </p>
                      <ul className="space-y-1">
                        {mitigations.map((mitigation, index) => (
                          <li
                            key={index}
                            className="text-xs text-insight-11 dark:text-insight-5 pl-3"
                          >
                            • {mitigation}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* AI Recommendation */}
                  {recommendation && (
                    <div
                      data-testid="ai-recommendation"
                      className="mt-2 p-2 bg-insight-2 dark:bg-insight-a5 rounded text-sm"
                    >
                      <span className="font-medium text-insight-11 dark:text-insight-4">
                        AI Recommendation:{" "}
                      </span>
                      <span className="text-insight-11 dark:text-insight-5 capitalize">
                        {recommendation}
                      </span>
                      {riskExplanation && (
                        <p className="text-xs text-insight-10 dark:text-insight-9 mt-1">
                          {riskExplanation}
                        </p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Sprint 6: Decision History Panel */}
          {enableAI && (
            <div
              data-testid="hitl-decision-history"
              className="bg-primary-2 dark:bg-primary-3 border border-primary-4 dark:border-primary-12 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-primary-12 dark:text-primary-3 flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Similar Decisions
                </h3>
                {historyLoading && (
                  <Loader2 className={cn("w-4 h-4 text-primary-9", !prefersReducedMotion && "animate-spin")} />
                )}
              </div>

              {!historyLoading && totalSimilar !== null && (
                <>
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-sm text-primary-10 dark:text-primary-7">
                        {totalSimilar} similar decisions found
                      </span>
                    </div>
                    <div>
                      <span className="text-sm text-primary-10 dark:text-primary-7">
                        Approval Rate
                      </span>
                      <p
                        data-testid="approval-rate"
                        className="text-lg font-bold text-primary-12 dark:text-primary-3"
                      >
                        {Math.round((approvalRate || 0) * 100)}%
                      </p>
                    </div>
                  </div>

                  {/* Recent Similar Decisions */}
                  {similarDecisions && similarDecisions.length > 0 && (
                    <div className="space-y-2">
                      {similarDecisions.slice(0, 2).map((decision, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-2 text-xs text-primary-11 dark:text-primary-5 p-2 bg-primary-3 dark:bg-primary-4 rounded"
                        >
                          {decision.decision === "approved" ? (
                            <ThumbsUp className="w-3 h-3 text-success-9" />
                          ) : (
                            <ThumbsDown className="w-3 h-3 text-error-9" />
                          )}
                          <span className="capitalize">
                            {decision.decision}
                          </span>
                          <span className="text-primary-9">
                            by {decision.decided_by}
                          </span>
                          {decision.reasoning && (
                            <span className="truncate text-primary-10 dark:text-primary-7">
                              — {decision.reasoning}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Suggested Action */}
                  {suggestedAction && (
                    <div
                      data-testid="suggested-action"
                      className="mt-2 p-2 bg-primary-3 dark:bg-primary-4 rounded text-sm"
                    >
                      <span className="font-medium text-primary-12 dark:text-primary-4">
                        Based on history:{" "}
                      </span>
                      <span className="text-primary-11 dark:text-primary-5 capitalize">
                        {suggestedAction}
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Agent Info */}
          <div className="bg-neutral-1 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span
                data-testid="agent-name"
                className="font-medium text-neutral-12"
              >
                Agent: {request.agentName}
              </span>
            </div>

            <div>
              <span className="text-sm text-neutral-10">
                Proposed Action:
              </span>
              <p
                data-testid="proposed-action"
                className="text-sm text-neutral-12 mt-1 p-2 bg-neutral-2 rounded"
              >
                {request.proposedAction}
              </p>
            </div>
          </div>

          {/* Context Details */}
          {(request.context.tokensUsed ||
            request.context.timeElapsedSeconds ||
            request.context.artifacts) && (
            <div className="space-y-2 text-sm">
              {request.context.tokensUsed && (
                <div className="flex items-center gap-2 text-neutral-11">
                  <FileText className="w-4 h-4" />
                  <span>
                    Tokens used: {formatNumber(request.context.tokensUsed)}
                  </span>
                </div>
              )}
              {request.context.timeElapsedSeconds && (
                <div className="flex items-center gap-2 text-neutral-11">
                  <Clock className="w-4 h-4" />
                  <span>
                    Time elapsed: {request.context.timeElapsedSeconds}s
                  </span>
                </div>
              )}
              {request.context.artifacts &&
                request.context.artifacts.length > 0 && (
                  <div className="flex items-start gap-2 text-neutral-11">
                    <FileText className="w-4 h-4 mt-0.5" />
                    <div>
                      <span>Artifacts: </span>
                      {request.context.artifacts.map((artifact) => (
                        <span
                          key={artifact}
                          className="inline-block bg-neutral-2 px-1.5 py-0.5 rounded text-xs mr-1"
                        >
                          {artifact}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          )}

          {/* Reason Input */}
          <div>
            <label
              htmlFor="reason-input"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Reason{" "}
              <span className="text-neutral-10">
                (optional)
              </span>
            </label>
            <Textarea
              className="px-3 py-2 text-sm text-neutral-12 placeholder-neutral-9 focus:ring-primary-7"
              id="reason-input"
              data-testid="approval-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter a reason for your decision..."
              rows={2}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-neutral-5 bg-neutral-1">
          <Button
            variant="danger"
            className="flex px-4 py-2 text-sm text-error-11 dark:text-error-7 bg-error-3 bg-error-4 rounded-lg hover:bg-error-4 dark:hover:bg-error-a6"
            data-testid="reject-button"
            onClick={handleReject}
            disabled={isLoading}
          >
            {isRejecting ? (
              <Loader2
                data-testid="reject-loading"
                className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
              />
            ) : (
              <XCircle className="w-4 h-4" />
            )}
            Reject
          </Button>
          <Button
            variant="success"
            className="flex px-4 py-2 text-sm text-neutral-12 bg-success-10 rounded-lg hover:bg-success-11"
            data-testid="approve-button"
            onClick={handleApprove}
            disabled={isLoading}
          >
            {isApproving ? (
              <Loader2
                data-testid="approve-loading"
                className={cn("w-4 h-4", !prefersReducedMotion && "animate-spin")}
              />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Approve
          </Button>
        </div>
      </div>
    </div>
  );
}
