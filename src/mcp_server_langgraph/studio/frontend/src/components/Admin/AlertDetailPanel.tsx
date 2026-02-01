/**
 * AlertDetailPanel Component
 *
 * Detail view for infrastructure alerts with AI recommendations and remediation actions.
 *
 * Features:
 * - Alert metadata display
 * - AI recommendation display with root cause analysis
 * - Remediation steps with approve/reject buttons
 * - Risk assessment visualization
 * - Regenerate recommendation button
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useReducedMotion } from "motion/react";
import {
  X,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ExternalLink,
  CheckCircle,
  XCircle,
  Play,
  Clock,
  Ban,
} from "lucide-react";
import { cn } from "../../utils/cn";
import type { Alert } from "../../store/slices/alertSlice";
import type {
  AIRecommendation,
  RemediationRequest,
  RiskLevel,
} from "../../types/api";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface AlertDetailPanelProps {
  /** The selected alert to display */
  alert: Alert | null;
  /** AI recommendation for the alert */
  recommendation: AIRecommendation | null;
  /** List of pending remediation requests */
  pendingRemediations: RemediationRequest[];
  /** Callback when a remediation is approved */
  onApprove: (remediationId: string) => void;
  /** Callback when a remediation is rejected */
  onReject: (remediationId: string) => void;
  /** Callback to regenerate recommendation */
  onRegenerate: () => void;
  /** Callback to close the panel */
  onClose: () => void;
  /** Loading state for recommendation */
  isLoadingRecommendation?: boolean;
  /** Error message for recommendation */
  recommendationError?: string | null;
  /** Loading state for regeneration */
  isRegenerating?: boolean;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get severity badge styling
 */
function getSeverityStyle(severity: Alert["severity"]): string {
  switch (severity) {
    case "critical":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "warning":
      return "bg-warning-3 text-warning-10 dark:bg-warning-a4 dark:text-warning-9";
    default:
      return "bg-neutral-2 text-neutral-11";
  }
}

/**
 * Get state badge styling
 */
function getStateStyle(state: Alert["state"]): string {
  switch (state) {
    case "firing":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "resolved":
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    default:
      return "bg-neutral-2 text-neutral-11";
  }
}

/**
 * Get risk level badge color
 */
function getRiskColor(risk: RiskLevel): string {
  switch (risk) {
    case "low":
      return "bg-success-9";
    case "medium":
      return "bg-warning-9";
    case "high":
      return "bg-error-9";
    default:
      return "bg-neutral-5";
  }
}

/**
 * Get status icon for remediation
 */
function getStatusIcon(status: RemediationRequest["status"]) {
  switch (status) {
    case "pending":
      return <Clock className="w-4 h-4 text-warning-9" />;
    case "approved":
      return <CheckCircle className="w-4 h-4 text-success-9" />;
    case "rejected":
      return <XCircle className="w-4 h-4 text-error-9" />;
    case "executing":
      return <Play className="w-4 h-4 text-primary-9" />;
    case "completed":
      return <CheckCircle className="w-4 h-4 text-success-9" />;
    case "failed":
      return <Ban className="w-4 h-4 text-error-9" />;
    default:
      return <Clock className="w-4 h-4 text-neutral-10" />;
  }
}

/**
 * Format relative time from ISO date string
 */
function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

// =============================================================================
// Sub-Components
// =============================================================================

interface RemediationStepCardProps {
  step: AIRecommendation["remediationSteps"][number];
  remediation?: RemediationRequest;
  onApprove: (remediationId: string) => void;
  onReject: (remediationId: string) => void;
}

function RemediationStepCard({
  step,
  remediation,
  onApprove,
  onReject,
}: RemediationStepCardProps) {
  const isPending = remediation?.status === "pending";

  return (
    <div className="p-4 border border-neutral-5 rounded-lg">
      {/* Step Header */}
      <div className="flex items-center gap-3 mb-2">
        <span
          data-testid={`step-number-${step.stepNumber}`}
          className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-9 text-neutral-12 text-sm font-medium"
        >
          {step.stepNumber}
        </span>
        <span className="font-medium text-neutral-12">
          {step.action.charAt(0).toUpperCase() + step.action.slice(1)}
        </span>
        <span
          data-testid={`step-risk-${step.stepNumber}`}
          className={`text-xs px-2 py-0.5 rounded-full ${getRiskColor(step.riskLevel)} text-neutral-12`}
        >
          {step.riskLevel}
        </span>
        {remediation && (
          <span
            data-testid={`step-status-${step.stepNumber}`}
            className="flex items-center gap-1 text-xs text-neutral-10"
          >
            {getStatusIcon(remediation.status)}
            {remediation.status.charAt(0).toUpperCase() +
              remediation.status.slice(1)}
          </span>
        )}
      </div>
      {/* Description */}
      <p className="text-sm text-neutral-11 mb-2">{step.description}</p>
      {/* Command */}
      {step.command && (
        <pre className="text-xs bg-neutral-2 p-2 rounded mb-3 overflow-x-auto">
          <code>{step.command}</code>
        </pre>
      )}
      {/* Action Buttons */}
      {isPending && remediation && (
        <div className="flex gap-2">
          <Button
            variant="success"
            className="min-h-[44px] flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg"
            data-testid={`approve-step-${step.stepNumber}`}
            onClick={() => onApprove(remediation.remediationId)}
          >
            <CheckCircle className="w-4 h-4" />
            Approve
          </Button>
          <Button
            variant="danger"
            className="min-h-[44px] flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg"
            data-testid={`reject-step-${step.stepNumber}`}
            onClick={() => onReject(remediation.remediationId)}
          >
            <XCircle className="w-4 h-4" />
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AlertDetailPanel({
  alert,
  recommendation,
  pendingRemediations,
  onApprove,
  onReject,
  onRegenerate,
  onClose,
  isLoadingRecommendation = false,
  recommendationError = null,
  isRegenerating = false,
}: AlertDetailPanelProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Empty state
  if (!alert) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-neutral-10 p-8">
        <AlertTriangle className="w-12 h-12 mb-4 opacity-50" />
        <p className="text-lg">Select an alert to view details</p>
      </div>
    );
  }

  // Find remediation for each step
  const getRemediationForStep = (stepNumber: number) =>
    pendingRemediations.find((r) => r.stepNumber === stepNumber);

  return (
    <div
      data-testid="alert-detail-panel"
      className="flex flex-col h-full overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-neutral-5">
        <div className="flex-1">
          {/* Alert Name and Badges */}
          <div className="flex items-center gap-2 mb-2">
            <h2 className="text-xl font-semibold text-neutral-12">
              {alert.name}
            </h2>
            <span
              data-testid="alert-severity"
              className={`text-xs px-2 py-0.5 rounded-full ${getSeverityStyle(
                alert.severity,
              )}`}
            >
              {alert.severity}
            </span>
            <span
              data-testid="alert-state"
              className={`text-xs px-2 py-0.5 rounded-full ${getStateStyle(
                alert.state,
              )}`}
            >
              {alert.state.charAt(0).toUpperCase() + alert.state.slice(1)}
            </span>
          </div>

          {/* Message */}
          <p className="text-neutral-11 mb-2">{alert.message}</p>

          {/* Labels */}
          <div className="flex flex-wrap gap-2 mb-2">
            {Object.entries(alert.labels).map(([key, value]) => (
              <span
                key={key}
                className="text-xs px-2 py-0.5 bg-neutral-2 text-neutral-11 rounded"
              >
                {value}
              </span>
            ))}
          </div>

          {/* Started Time */}
          <div data-testid="alert-started" className="text-xs text-neutral-10">
            Started: {formatRelativeTime(alert.startedAt)}
          </div>
        </div>

        {/* Close Button */}
        <Button
          size="icon"
          variant="ghost"
          className="min-h-[44px] min-w-[44px] p-2 text-neutral-10 hover:text-neutral-11 hover:bg-neutral-2 rounded-lg"
          data-testid="close-detail-panel"
          onClick={onClose}
          aria-label="Close detail panel"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Loading State */}
        {isLoadingRecommendation && (
          <div
            data-testid="recommendation-loading"
            className="flex items-center justify-center py-12"
          >
            <Loader2
              className={cn(
                "w-8 h-8 text-primary-9",
                !prefersReducedMotion && "animate-spin",
              )}
            />
          </div>
        )}

        {/* Error State */}
        {recommendationError && (
          <div className="bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg p-4">
            <p className="text-error-11 dark:text-error-7">
              Failed to generate recommendation: {recommendationError}
            </p>
            <Button
              variant="primary"
              className="mt-2 text-sm text-error-10 dark:text-error-7 underline"
              onClick={onRegenerate}
            >
              Try again
            </Button>
          </div>
        )}

        {/* Recommendation Content */}
        {recommendation && !isLoadingRecommendation && (
          <>
            {/* Root Cause Analysis */}
            <section>
              <h3 className="text-sm font-medium text-neutral-12 mb-2">
                Root Cause Analysis
              </h3>
              <p className="text-sm text-neutral-11 bg-neutral-1 p-3 rounded-lg">
                {recommendation.rootCauseAnalysis}
              </p>
            </section>

            {/* Risk Assessment */}
            <section>
              <h3 className="text-sm font-medium text-neutral-12 mb-2">
                Risk Assessment
              </h3>
              <div className="bg-neutral-1 p-3 rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-neutral-11">Overall Risk:</span>
                  <span
                    data-testid="overall-risk"
                    className={`text-xs px-2 py-0.5 rounded-full text-neutral-12 ${getRiskColor(
                      recommendation.riskAssessment.overallRisk,
                    )}`}
                  >
                    {recommendation.riskAssessment.overallRisk}
                  </span>
                </div>
                <div>
                  <span className="text-sm text-neutral-11">Impact: </span>
                  <span className="text-sm text-neutral-11">
                    {recommendation.riskAssessment.impactAnalysis}
                  </span>
                </div>
                <div>
                  <span className="text-sm text-neutral-11">Rollback: </span>
                  <code className="text-xs bg-neutral-2 px-1 py-0.5 rounded">
                    {recommendation.riskAssessment.rollbackPlan}
                  </code>
                </div>
              </div>
            </section>

            {/* Remediation Steps */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-neutral-12">
                  Remediation Steps
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="min-h-[44px] min-w-[44px] flex items-center gap-1 text-xs text-primary-10 dark:text-primary-7 hover:text-primary-11 dark:hover:text-primary-5"
                  data-testid="regenerate-recommendation"
                  onClick={onRegenerate}
                  disabled={isRegenerating}
                >
                  <RefreshCw
                    className={cn(
                      "w-3 h-3",
                      isRegenerating && !prefersReducedMotion && "animate-spin",
                    )}
                  />
                  Regenerate
                </Button>
              </div>
              <div className="space-y-3">
                {recommendation.remediationSteps.map((step) => (
                  <RemediationStepCard
                    key={step.stepNumber}
                    step={step}
                    remediation={getRemediationForStep(step.stepNumber)}
                    onApprove={onApprove}
                    onReject={onReject}
                  />
                ))}
              </div>
            </section>

            {/* Runbook Reference */}
            {recommendation.runbookReference && (
              <section>
                <h3 className="text-sm font-medium text-neutral-12 mb-2">
                  Runbook
                </h3>
                <a
                  data-testid="runbook-link"
                  href={recommendation.runbookReference}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-primary-10 dark:text-primary-7 hover:underline"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Runbook
                </a>
              </section>
            )}

            {/* Model Info */}
            <div className="text-xs text-neutral-10 pt-4 border-t border-neutral-5">
              <span>
                Generated by {recommendation.modelUsed} •{" "}
                {formatRelativeTime(recommendation.generatedAt)}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
