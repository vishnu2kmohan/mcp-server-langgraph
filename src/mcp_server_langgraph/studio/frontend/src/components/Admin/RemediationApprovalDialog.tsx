/**
 * RemediationApprovalDialog Component
 *
 * Modal dialog for approving or rejecting remediation actions.
 *
 * Features:
 * - Display remediation details
 * - Approve/reject with optional reason
 * - Risk level warning for high-risk actions
 * - Loading states
 * - Keyboard accessibility
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useState, useEffect, useCallback } from "react";
import {
  X,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Info,
} from "lucide-react";
import type {
  RemediationRequest,
  AIRecommendation,
  ApproveRemediationRequest,
  RejectRemediationRequest,
  RiskLevel,
} from "../../types/api";

// =============================================================================
// Constants
// =============================================================================

/**
 * Structured rejection reasons for AI learning.
 * Maps to RejectionReason enum in backend.
 */
export const REJECTION_REASONS = [
  {
    value: "too_risky",
    label: "Too Risky",
    description: "Command or action is too dangerous",
  },
  {
    value: "incorrect_diagnosis",
    label: "Incorrect Diagnosis",
    description: "Root cause analysis is wrong",
  },
  {
    value: "wrong_command",
    label: "Wrong Command",
    description: "Command syntax or path is incorrect",
  },
  {
    value: "incomplete_steps",
    label: "Incomplete Steps",
    description: "Missing important steps",
  },
  {
    value: "not_relevant",
    label: "Not Relevant",
    description: "Doesn't apply to this alert",
  },
  {
    value: "prefer_manual",
    label: "Prefer Manual",
    description: "Want to handle manually",
  },
  {
    value: "other",
    label: "Other",
    description: "Other reason (specify below)",
  },
] as const;

export type RejectionReasonValue = (typeof REJECTION_REASONS)[number]["value"];

// =============================================================================
// Types
// =============================================================================

export interface RemediationApprovalDialogProps {
  /** The remediation request to approve/reject */
  remediation: RemediationRequest;
  /** The associated AI recommendation */
  recommendation: AIRecommendation;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Callback when remediation is approved */
  onApprove: (data: ApproveRemediationRequest) => void;
  /** Callback when remediation is rejected */
  onReject: (data: RejectRemediationRequest) => void;
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
 * Get risk level badge color
 */
function getRiskColor(risk: RiskLevel): string {
  switch (risk) {
    case "low":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    case "medium":
      return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
    case "high":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
  }
}

/**
 * Get severity badge color
 */
function getSeverityColor(severity: RemediationRequest["severity"]): string {
  switch (severity) {
    case "critical":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "warning":
      return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
  }
}

// =============================================================================
// Main Component
// =============================================================================

export function RemediationApprovalDialog({
  remediation,
  recommendation,
  isOpen,
  onClose,
  onApprove,
  onReject,
  isApproving = false,
  isRejecting = false,
  error = null,
  currentUser = "unknown",
}: RemediationApprovalDialogProps) {
  const [reason, setReason] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [selectedRejectionReason, setSelectedRejectionReason] =
    useState<RejectionReasonValue | null>(null);
  const [rejectionDetail, setRejectionDetail] = useState("");

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setReason("");
      setValidationError(null);
      setSelectedRejectionReason(null);
      setRejectionDetail("");
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

  // Handle approve
  const handleApprove = () => {
    setValidationError(null);
    onApprove({
      remediation_id: remediation.remediation_id,
      approved_by: currentUser,
      reason: reason.trim() || undefined,
    });
  };

  // Handle reject
  const handleReject = () => {
    // Validate structured rejection reason is selected
    if (!selectedRejectionReason) {
      setValidationError("Please select a rejection reason");
      return;
    }

    // Validate detail is provided when "other" is selected
    if (selectedRejectionReason === "other" && !rejectionDetail.trim()) {
      setValidationError("Please provide details for your reason");
      return;
    }

    setValidationError(null);
    onReject({
      remediation_id: remediation.remediation_id,
      rejected_by: currentUser,
      reason: selectedRejectionReason,
      reason_detail:
        selectedRejectionReason === "other"
          ? rejectionDetail.trim()
          : undefined,
    });
  };

  if (!isOpen) {
    return null;
  }

  const isHighRisk = remediation.risk_level === "high";
  const isLoading = isApproving || isRejecting;

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
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Approve Remediation
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

          {/* Alert Info */}
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 dark:text-white">
              {remediation.alert_name}
            </span>
            <span
              data-testid="severity-badge"
              className={`text-xs px-2 py-0.5 rounded-full ${getSeverityColor(
                remediation.severity,
              )}`}
            >
              {remediation.severity}
            </span>
          </div>

          {/* Step Info */}
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span
                data-testid="step-number"
                className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500 text-white text-sm font-medium"
              >
                {remediation.step_number}
              </span>
              <span className="font-medium text-gray-900 dark:text-white">
                {remediation.action.charAt(0).toUpperCase() +
                  remediation.action.slice(1)}
              </span>
              <span
                data-testid="risk-level"
                className={`text-xs px-2 py-0.5 rounded-full ${getRiskColor(
                  remediation.risk_level,
                )}`}
              >
                {remediation.risk_level}
              </span>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400">
              {remediation.description}
            </p>

            {remediation.command && (
              <pre className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded overflow-x-auto">
                <code>{remediation.command}</code>
              </pre>
            )}
          </div>

          {/* High Risk Warning */}
          {isHighRisk && (
            <div
              data-testid="high-risk-warning"
              className="flex items-start gap-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3"
            >
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-red-700 dark:text-red-400">
                  High Risk Action
                </p>
                <p className="text-sm text-red-600 dark:text-red-400/80">
                  This action has been flagged as high risk. Please review
                  carefully before approving.
                </p>
              </div>
            </div>
          )}

          {/* Impact Analysis */}
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Impact:</strong>{" "}
                  {recommendation.risk_assessment.impact_analysis}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Rollback:</strong>{" "}
                  <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">
                    {recommendation.risk_assessment.rollback_plan}
                  </code>
                </p>
              </div>
            </div>
          </div>

          {/* Structured Rejection Reasons */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Rejection Reason{" "}
              <span className="text-gray-500">(required for rejection)</span>
            </label>
            <div
              data-testid="rejection-reason-select"
              className="space-y-2"
              role="radiogroup"
              aria-label="Select rejection reason"
            >
              {REJECTION_REASONS.map((reasonOption) => (
                <label
                  key={reasonOption.value}
                  className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedRejectionReason === reasonOption.value
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                  }`}
                >
                  <input
                    type="radio"
                    name="rejection-reason"
                    data-testid={`rejection-reason-${reasonOption.value}`}
                    value={reasonOption.value}
                    checked={selectedRejectionReason === reasonOption.value}
                    onChange={() => {
                      setSelectedRejectionReason(reasonOption.value);
                      if (validationError) setValidationError(null);
                    }}
                    className="mt-1"
                  />
                  <div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {reasonOption.label}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {reasonOption.description}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Detail input for "other" reason */}
          {selectedRejectionReason === "other" && (
            <div>
              <label
                htmlFor="rejection-detail-input"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Please provide details
              </label>
              <textarea
                id="rejection-detail-input"
                data-testid="rejection-detail-input"
                value={rejectionDetail}
                onChange={(e) => {
                  setRejectionDetail(e.target.value);
                  if (validationError) setValidationError(null);
                }}
                placeholder="Describe your reason for rejection..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          )}

          {/* Optional Reason/Notes Input */}
          <div>
            <label
              htmlFor="reason-input"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Additional Notes <span className="text-gray-500">(optional)</span>
            </label>
            <textarea
              id="reason-input"
              data-testid="reason-input"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (validationError) setValidationError(null);
              }}
              placeholder="Enter additional notes for approval or rejection..."
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {validationError && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                {validationError}
              </p>
            )}
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
