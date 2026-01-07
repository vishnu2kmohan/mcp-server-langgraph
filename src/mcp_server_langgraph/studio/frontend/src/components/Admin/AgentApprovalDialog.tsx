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
import { useFocusTrap } from "../../hooks/useFocusTrap";
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
  if (confidence >= 0.9) return "bg-green-500";
  if (confidence >= 0.7) return "bg-blue-500";
  if (confidence >= 0.5) return "bg-amber-500";
  return "bg-red-500";
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
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
    case "medium":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
    case "high":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
    case "critical":
      return "bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400";
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
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Agent Decision Requires Approval
          </h2>
          <button
            data-testid="close-dialog"
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Confidence Gauge */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Confidence
              </span>
              <div className="flex items-center gap-2">
                <span
                  data-testid="confidence-score"
                  className="text-sm font-bold"
                >
                  {confidencePercent}%
                </span>
                <span className="text-sm text-gray-500">
                  / Threshold:{" "}
                  <span data-testid="confidence-threshold">
                    {thresholdPercent}%
                  </span>
                </span>
              </div>
            </div>
            <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                data-testid="confidence-gauge"
                className={`h-full transition-all ${getConfidenceColor(request.confidence)}`}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>

          {/* Low Confidence Warning */}
          {isLowConfidence && (
            <div
              data-testid="low-confidence-warning"
              className="flex items-start gap-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3"
            >
              <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-amber-700 dark:text-amber-400">
                  Low Confidence
                </p>
                <p
                  data-testid="trigger-explanation"
                  className="text-sm text-amber-600 dark:text-amber-400/80"
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
              className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden"
            >
              <summary className="cursor-pointer p-3 font-medium text-blue-700 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" />
                Why is the agent uncertain?
              </summary>
              <div className="p-3 pt-0 space-y-3 text-sm">
                {/* Why Uncertain */}
                <p className="text-gray-700 dark:text-gray-300">
                  {request.aiExplanation.whyUncertain}
                </p>

                {/* What Could Go Wrong */}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    What could go wrong:
                  </p>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    {request.aiExplanation.whatCouldGoWrong}
                  </p>
                </div>

                {/* Safer Alternatives */}
                {request.aiExplanation.saferAlternatives &&
                  request.aiExplanation.saferAlternatives.length > 0 && (
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                        <Lightbulb className="w-3.5 h-3.5 text-green-500" />
                        Safer alternatives:
                      </p>
                      <ul className="mt-1 space-y-1.5">
                        {request.aiExplanation.saferAlternatives.map(
                          (alt, index) => (
                            <li
                              key={index}
                              className="text-gray-600 dark:text-gray-400 pl-4 border-l-2 border-green-300 dark:border-green-700"
                            >
                              <span className="font-medium text-gray-800 dark:text-gray-200">
                                {alt.action}
                              </span>
                              <span className="text-green-600 dark:text-green-400 ml-1">
                                ({Math.round(alt.confidence * 100)}%)
                              </span>
                              <span className="text-gray-500 dark:text-gray-500 block text-xs">
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
                      <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                        <TrendingDown className="w-3.5 h-3.5 text-red-500" />
                        Confidence factors:
                      </p>
                      <ul className="mt-1 space-y-1">
                        {request.aiExplanation.confidenceFactors.map(
                          (factor, index) => (
                            <li
                              key={index}
                              className="text-gray-600 dark:text-gray-400 text-xs"
                            >
                              <span
                                className={`font-mono ${
                                  factor.weight < 0
                                    ? "text-red-600 dark:text-red-400"
                                    : "text-green-600 dark:text-green-400"
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
              className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-purple-900 dark:text-purple-100 flex items-center gap-2">
                  <Shield className="w-4 h-4" />
                  AI Risk Assessment
                </h3>
                {riskLoading && (
                  <Loader2 className="w-4 h-4 animate-spin text-purple-500" />
                )}
              </div>

              {!riskLoading && riskScore !== null && (
                <>
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-sm text-purple-600 dark:text-purple-400">
                        Risk Score
                      </span>
                      <p
                        data-testid="risk-score"
                        className="text-lg font-bold text-purple-900 dark:text-purple-100"
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
                      <p className="text-sm font-medium text-purple-800 dark:text-purple-200">
                        Risk Factors:
                      </p>
                      <ul className="space-y-1">
                        {riskFactors.map((factor, index) => (
                          <li
                            key={index}
                            className="text-xs text-purple-700 dark:text-purple-300 flex items-center gap-2"
                          >
                            <span className="font-mono text-purple-500">
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
                      <p className="text-sm font-medium text-purple-800 dark:text-purple-200">
                        Suggested Mitigations:
                      </p>
                      <ul className="space-y-1">
                        {mitigations.map((mitigation, index) => (
                          <li
                            key={index}
                            className="text-xs text-purple-700 dark:text-purple-300 pl-3"
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
                      className="mt-2 p-2 bg-purple-100 dark:bg-purple-900/40 rounded text-sm"
                    >
                      <span className="font-medium text-purple-800 dark:text-purple-200">
                        AI Recommendation:{" "}
                      </span>
                      <span className="text-purple-700 dark:text-purple-300 capitalize">
                        {recommendation}
                      </span>
                      {riskExplanation && (
                        <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
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
              className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-indigo-900 dark:text-indigo-100 flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Similar Decisions
                </h3>
                {historyLoading && (
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
                )}
              </div>

              {!historyLoading && totalSimilar !== null && (
                <>
                  <div className="flex items-center gap-4">
                    <div>
                      <span className="text-sm text-indigo-600 dark:text-indigo-400">
                        {totalSimilar} similar decisions found
                      </span>
                    </div>
                    <div>
                      <span className="text-sm text-indigo-600 dark:text-indigo-400">
                        Approval Rate
                      </span>
                      <p
                        data-testid="approval-rate"
                        className="text-lg font-bold text-indigo-900 dark:text-indigo-100"
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
                          className="flex items-center gap-2 text-xs text-indigo-700 dark:text-indigo-300 p-2 bg-indigo-100 dark:bg-indigo-900/40 rounded"
                        >
                          {decision.decision === "approved" ? (
                            <ThumbsUp className="w-3 h-3 text-green-500" />
                          ) : (
                            <ThumbsDown className="w-3 h-3 text-red-500" />
                          )}
                          <span className="capitalize">
                            {decision.decision}
                          </span>
                          <span className="text-indigo-500">
                            by {decision.decided_by}
                          </span>
                          {decision.reasoning && (
                            <span className="truncate text-indigo-600 dark:text-indigo-400">
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
                      className="mt-2 p-2 bg-indigo-100 dark:bg-indigo-900/40 rounded text-sm"
                    >
                      <span className="font-medium text-indigo-800 dark:text-indigo-200">
                        Based on history:{" "}
                      </span>
                      <span className="text-indigo-700 dark:text-indigo-300 capitalize">
                        {suggestedAction}
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Agent Info */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span
                data-testid="agent-name"
                className="font-medium text-gray-900 dark:text-white"
              >
                Agent: {request.agentName}
              </span>
            </div>

            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Proposed Action:
              </span>
              <p
                data-testid="proposed-action"
                className="text-sm text-gray-900 dark:text-white mt-1 p-2 bg-gray-100 dark:bg-gray-700 rounded"
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
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <FileText className="w-4 h-4" />
                  <span>
                    Tokens used: {formatNumber(request.context.tokensUsed)}
                  </span>
                </div>
              )}
              {request.context.timeElapsedSeconds && (
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span>
                    Time elapsed: {request.context.timeElapsedSeconds}s
                  </span>
                </div>
              )}
              {request.context.artifacts &&
                request.context.artifacts.length > 0 && (
                  <div className="flex items-start gap-2 text-gray-600 dark:text-gray-400">
                    <FileText className="w-4 h-4 mt-0.5" />
                    <div>
                      <span>Artifacts: </span>
                      {request.context.artifacts.map((artifact) => (
                        <span
                          key={artifact}
                          className="inline-block bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-xs mr-1"
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
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Reason <span className="text-gray-500">(optional)</span>
            </label>
            <textarea
              id="reason-input"
              data-testid="approval-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter a reason for your decision..."
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <button
            data-testid="reject-button"
            onClick={handleReject}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRejecting ? (
              <Loader2
                data-testid="reject-loading"
                className="w-4 h-4 animate-spin"
              />
            ) : (
              <XCircle className="w-4 h-4" />
            )}
            Reject
          </button>
          <button
            data-testid="approve-button"
            onClick={handleApprove}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isApproving ? (
              <Loader2
                data-testid="approve-loading"
                className="w-4 h-4 animate-spin"
              />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
