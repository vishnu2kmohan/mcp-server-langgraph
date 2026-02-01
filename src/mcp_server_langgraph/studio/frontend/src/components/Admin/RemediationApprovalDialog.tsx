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
import { useReducedMotion } from "motion/react";
import {
  X,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Info,
} from "lucide-react";
import { cn } from "../../utils/cn";
import type {
  RemediationRequest,
  AIRecommendation,
  ApproveRemediationRequest,
  RejectRemediationRequest,
  RiskLevel,
} from "../../types/api";

import { Button, Textarea, RadioGroup, Radio } from "@/components/UI";

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
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    case "medium":
      return "bg-warning-3 text-warning-10 dark:bg-warning-a4 dark:text-warning-9";
    case "high":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    default:
      return "bg-neutral-2 text-neutral-11";
  }
}

/**
 * Get severity badge color
 */
function getSeverityColor(severity: RemediationRequest["severity"]): string {
  switch (severity) {
    case "critical":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "warning":
      return "bg-warning-3 text-warning-10 dark:bg-warning-a4 dark:text-warning-9";
    default:
      return "bg-neutral-2 text-neutral-11";
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

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
      remediationId: remediation.remediationId,
      approvedBy: currentUser,
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
      remediationId: remediation.remediationId,
      rejectedBy: currentUser,
      reason: selectedRejectionReason,
      reasonDetail:
        selectedRejectionReason === "other"
          ? rejectionDetail.trim()
          : undefined,
    });
  };

  if (!isOpen) {
    return null;
  }

  const isHighRisk = remediation.riskLevel === "high";
  const isLoading = isApproving || isRejecting;

  return (
    <div
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
          <h2 className="text-lg font-semibold text-neutral-12">
            Approve Remediation
          </h2>
          <Button
            size="icon"
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

          {/* Alert Info */}
          <div className="flex items-center gap-2">
            <span className="font-medium text-neutral-12">
              {remediation.alertName}
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
          <div className="bg-neutral-1 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span
                data-testid="step-number"
                className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-9 text-neutral-12 text-sm font-medium"
              >
                {remediation.stepNumber}
              </span>
              <span className="font-medium text-neutral-12">
                {remediation.action.charAt(0).toUpperCase() +
                  remediation.action.slice(1)}
              </span>
              <span
                data-testid="risk-level"
                className={`text-xs px-2 py-0.5 rounded-full ${getRiskColor(
                  remediation.riskLevel,
                )}`}
              >
                {remediation.riskLevel}
              </span>
            </div>

            <p className="text-sm text-neutral-11">{remediation.description}</p>

            {remediation.command && (
              <pre className="text-xs bg-neutral-2 p-2 rounded overflow-x-auto">
                <code>{remediation.command}</code>
              </pre>
            )}
          </div>

          {/* High Risk Warning */}
          {isHighRisk && (
            <div
              data-testid="high-risk-warning"
              className="flex items-start gap-3 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg p-3"
            >
              <AlertTriangle className="w-5 h-5 text-error-9 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-error-11 dark:text-error-7">
                  High Risk Action
                </p>
                <p className="text-sm text-error-10 dark:text-error-a9">
                  This action has been flagged as high risk. Please review
                  carefully before approving.
                </p>
              </div>
            </div>
          )}

          {/* Impact Analysis */}
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-neutral-9 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-neutral-11">
                  <strong>Impact:</strong>{" "}
                  {recommendation.riskAssessment.impactAnalysis}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-neutral-9 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-neutral-11">
                  <strong>Rollback:</strong>{" "}
                  <code className="text-xs bg-neutral-2 px-1 py-0.5 rounded">
                    {recommendation.riskAssessment.rollbackPlan}
                  </code>
                </p>
              </div>
            </div>
          </div>

          {/* Structured Rejection Reasons */}
          <div>
            <label className="block text-sm font-medium text-neutral-11 mb-2">
              Rejection Reason{" "}
              <span className="text-neutral-10">(required for rejection)</span>
            </label>
            <RadioGroup
              name="rejection-reason"
              value={selectedRejectionReason ?? ""}
              onChange={(value) => {
                setSelectedRejectionReason(value as RejectionReasonValue);
                if (validationError) setValidationError(null);
              }}
              variant="card"
              aria-label="Select rejection reason"
              data-testid="rejection-reason-select"
            >
              {REJECTION_REASONS.map((reasonOption) => (
                <Radio
                  key={reasonOption.value}
                  value={reasonOption.value}
                  label={reasonOption.label}
                  description={reasonOption.description}
                  data-testid={`rejection-reason-${reasonOption.value}`}
                />
              ))}
            </RadioGroup>
          </div>

          {/* Detail input for "other" reason */}
          {selectedRejectionReason === "other" && (
            <div>
              <label
                htmlFor="rejection-detail-input"
                className="block text-sm font-medium text-neutral-11 mb-1"
              >
                Please provide details
              </label>
              <Textarea
                className="px-3 py-2 text-sm text-neutral-12 placeholder-neutral-9 focus:ring-primary-7"
                id="rejection-detail-input"
                data-testid="rejection-detail-input"
                value={rejectionDetail}
                onChange={(e) => {
                  setRejectionDetail(e.target.value);
                  if (validationError) setValidationError(null);
                }}
                placeholder="Describe your reason for rejection..."
                rows={2}
              />
            </div>
          )}

          {/* Optional Reason/Notes Input */}
          <div>
            <label
              htmlFor="reason-input"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Additional Notes{" "}
              <span className="text-neutral-10">(optional)</span>
            </label>
            <Textarea
              className="px-3 py-2 text-sm text-neutral-12 placeholder-neutral-9 focus:ring-primary-7"
              id="reason-input"
              data-testid="reason-input"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (validationError) setValidationError(null);
              }}
              placeholder="Enter additional notes for approval or rejection..."
              rows={2}
            />
            {validationError && (
              <p className="mt-1 text-sm text-error-10 dark:text-error-7">
                {validationError}
              </p>
            )}
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
                className={cn(
                  "w-4 h-4",
                  !prefersReducedMotion && "animate-spin",
                )}
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
                className={cn(
                  "w-4 h-4",
                  !prefersReducedMotion && "animate-spin",
                )}
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
