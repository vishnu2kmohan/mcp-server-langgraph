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

import { useState, useEffect, useCallback } from "react";
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
} from "lucide-react";
import type { AIExplanation } from "../../types/hitl";

// =============================================================================
// Types
// =============================================================================

export interface AgentApprovalRequest {
  request_id: string;
  session_id: string;
  task_id: string;
  agent_name: string;
  confidence: number;
  threshold: number;
  proposed_action: string;
  trigger_reason: string;
  context: {
    tokens_used?: number;
    time_elapsed_seconds?: number;
    artifacts?: string[];
    [key: string]: unknown;
  };
  requested_at: string;
  /** AI-generated explanation for HITL dialog (Phase 1 AI-Native Enhancement) */
  ai_explanation?: AIExplanation;
}

export interface AgentApprovalDialogProps {
  /** The approval request to display */
  request: AgentApprovalRequest;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when request is approved */
  onApprove: (data: {
    request_id: string;
    approved_by: string;
    reason?: string;
  }) => void;
  /** Callback when request is rejected */
  onReject: (data: {
    request_id: string;
    rejected_by: string;
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
function getTriggerExplanation(triggerReason: string, confidence: number, threshold: number): string {
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
}: AgentApprovalDialogProps) {
  const [reason, setReason] = useState("");

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
    [isOpen, onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Handle approve
  const handleApprove = () => {
    onApprove({
      request_id: request.request_id,
      approved_by: currentUser,
      reason: reason.trim() || undefined,
    });
  };

  // Handle reject
  const handleReject = () => {
    onReject({
      request_id: request.request_id,
      rejected_by: currentUser,
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
                <p className="text-sm text-amber-600 dark:text-amber-400/80">
                  {getTriggerExplanation(
                    request.trigger_reason,
                    request.confidence,
                    request.threshold
                  )}
                </p>
              </div>
            </div>
          )}

          {/* AI Explanation Section (AI-Native HITL Enhancement Phase 1) */}
          {request.ai_explanation && (
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
                  {request.ai_explanation.why_uncertain}
                </p>

                {/* What Could Go Wrong */}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    What could go wrong:
                  </p>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">
                    {request.ai_explanation.what_could_go_wrong}
                  </p>
                </div>

                {/* Safer Alternatives */}
                {request.ai_explanation.safer_alternatives &&
                  request.ai_explanation.safer_alternatives.length > 0 && (
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                        <Lightbulb className="w-3.5 h-3.5 text-green-500" />
                        Safer alternatives:
                      </p>
                      <ul className="mt-1 space-y-1.5">
                        {request.ai_explanation.safer_alternatives.map(
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
                                Trade-off: {alt.trade_off}
                              </span>
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                {/* Confidence Factors */}
                {request.ai_explanation.confidence_factors &&
                  request.ai_explanation.confidence_factors.length > 0 && (
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1">
                        <TrendingDown className="w-3.5 h-3.5 text-red-500" />
                        Confidence factors:
                      </p>
                      <ul className="mt-1 space-y-1">
                        {request.ai_explanation.confidence_factors.map(
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
                          )
                        )}
                      </ul>
                    </div>
                  )}
              </div>
            </details>
          )}

          {/* Agent Info */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 dark:text-white">
                Agent: {request.agent_name}
              </span>
            </div>

            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Proposed Action:
              </span>
              <p className="text-sm text-gray-900 dark:text-white mt-1 p-2 bg-gray-100 dark:bg-gray-700 rounded">
                {request.proposed_action}
              </p>
            </div>
          </div>

          {/* Context Details */}
          {(request.context.tokens_used ||
            request.context.time_elapsed_seconds ||
            request.context.artifacts) && (
            <div className="space-y-2 text-sm">
              {request.context.tokens_used && (
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <FileText className="w-4 h-4" />
                  <span>
                    Tokens used: {formatNumber(request.context.tokens_used)}
                  </span>
                </div>
              )}
              {request.context.time_elapsed_seconds && (
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span>Time elapsed: {request.context.time_elapsed_seconds}s</span>
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
              data-testid="reason-input"
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
