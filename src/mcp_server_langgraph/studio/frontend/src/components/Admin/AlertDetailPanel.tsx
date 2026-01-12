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
      return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400";
    case "warning":
      return "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400";
    default:
      return "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-400";
  }
}

/**
 * Get state badge styling
 */
function getStateStyle(state: Alert["state"]): string {
  switch (state) {
    case "firing":
      return "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400";
    case "resolved":
      return "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400";
    default:
      return "bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-400";
  }
}

/**
 * Get risk level badge color
 */
function getRiskColor(risk: RiskLevel): string {
  switch (risk) {
    case "low":
      return "bg-success-500";
    case "medium":
      return "bg-warning-500";
    case "high":
      return "bg-error-500";
    default:
      return "bg-neutral-500";
  }
}

/**
 * Get status icon for remediation
 */
function getStatusIcon(status: RemediationRequest["status"]) {
  switch (status) {
    case "pending":
      return <Clock className="w-4 h-4 text-warning-500" />;
    case "approved":
      return <CheckCircle className="w-4 h-4 text-success-500" />;
    case "rejected":
      return <XCircle className="w-4 h-4 text-error-500" />;
    case "executing":
      return <Play className="w-4 h-4 text-primary-500 animate-pulse" />;
    case "completed":
      return <CheckCircle className="w-4 h-4 text-success-500" />;
    case "failed":
      return <Ban className="w-4 h-4 text-error-500" />;
    default:
      return (
        <Clock className="w-4 h-4 text-neutral-500 dark:text-neutral-400" />
      );
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
    <div className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg">
      {/* Step Header */}
      <div className="flex items-center gap-3 mb-2">
        <span
          data-testid={`step-number-${step.stepNumber}`}
          className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-500 text-white text-sm font-medium"
        >
          {step.stepNumber}
        </span>
        <span className="font-medium text-neutral-900 dark:text-white">
          {step.action.charAt(0).toUpperCase() + step.action.slice(1)}
        </span>
        <span
          data-testid={`step-risk-${step.stepNumber}`}
          className={`text-xs px-2 py-0.5 rounded-full ${getRiskColor(step.riskLevel)} text-white`}
        >
          {step.riskLevel}
        </span>
        {remediation && (
          <span
            data-testid={`step-status-${step.stepNumber}`}
            className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400"
          >
            {getStatusIcon(remediation.status)}
            {remediation.status.charAt(0).toUpperCase() +
              remediation.status.slice(1)}
          </span>
        )}
      </div>
      {/* Description */}
      <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
        {step.description}
      </p>
      {/* Command */}
      {step.command && (
        <pre className="text-xs bg-neutral-100 dark:bg-neutral-800 p-2 rounded mb-3 overflow-x-auto">
          <code>{step.command}</code>
        </pre>
      )}
      {/* Action Buttons */}
      {isPending && remediation && (
        <div className="flex gap-2">
          <Button
            variant="success"
            className="flex px-3 py-1.5 text-sm bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400 rounded-lg hover:bg-success-200 dark:hover:bg-success-900/50"
            data-testid={`approve-step-${step.stepNumber}`}
            onClick={() => onApprove(remediation.remediationId)}
          >
            <CheckCircle className="w-4 h-4" />
            Approve
          </Button>
          <Button
            variant="danger"
            className="flex px-3 py-1.5 text-sm bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200 dark:hover:bg-error-900/50"
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
  // Empty state
  if (!alert) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-neutral-500 dark:text-neutral-400 p-8">
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
      <div className="flex items-start justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex-1">
          {/* Alert Name and Badges */}
          <div className="flex items-center gap-2 mb-2">
            <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
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
          <p className="text-neutral-600 dark:text-neutral-400 mb-2">
            {alert.message}
          </p>

          {/* Labels */}
          <div className="flex flex-wrap gap-2 mb-2">
            {Object.entries(alert.labels).map(([key, value]) => (
              <span
                key={key}
                className="text-xs px-2 py-0.5 bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 rounded"
              >
                {value}
              </span>
            ))}
          </div>

          {/* Started Time */}
          <div
            data-testid="alert-started"
            className="text-xs text-neutral-500 dark:text-neutral-400"
          >
            Started: {formatRelativeTime(alert.startedAt)}
          </div>
        </div>

        {/* Close Button */}
        <Button
          variant="secondary"
          className="p-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800 rounded-lg"
          data-testid="close-detail-panel"
          onClick={onClose}
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
            <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
          </div>
        )}

        {/* Error State */}
        {recommendationError && (
          <div className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4">
            <p className="text-error-700 dark:text-error-400">
              Failed to generate recommendation: {recommendationError}
            </p>
            <Button
              className="mt-2 text-sm text-error-600 dark:text-error-400 underline"
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
              <h3 className="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                Root Cause Analysis
              </h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-lg">
                {recommendation.rootCauseAnalysis}
              </p>
            </section>

            {/* Risk Assessment */}
            <section>
              <h3 className="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                Risk Assessment
              </h3>
              <div className="bg-neutral-50 dark:bg-neutral-800/50 p-3 rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-neutral-600 dark:text-neutral-400">
                    Overall Risk:
                  </span>
                  <span
                    data-testid="overall-risk"
                    className={`text-xs px-2 py-0.5 rounded-full text-white ${getRiskColor(
                      recommendation.riskAssessment.overallRisk,
                    )}`}
                  >
                    {recommendation.riskAssessment.overallRisk}
                  </span>
                </div>
                <div>
                  <span className="text-sm text-neutral-600 dark:text-neutral-400">
                    Impact:{" "}
                  </span>
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">
                    {recommendation.riskAssessment.impactAnalysis}
                  </span>
                </div>
                <div>
                  <span className="text-sm text-neutral-600 dark:text-neutral-400">
                    Rollback:{" "}
                  </span>
                  <code className="text-xs bg-neutral-100 dark:bg-neutral-700 px-1 py-0.5 rounded">
                    {recommendation.riskAssessment.rollbackPlan}
                  </code>
                </div>
              </div>
            </section>

            {/* Remediation Steps */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-neutral-900 dark:text-white">
                  Remediation Steps
                </h3>
                <Button
                  size="sm"
                  className="flex text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                  data-testid="regenerate-recommendation"
                  onClick={onRegenerate}
                  disabled={isRegenerating}
                >
                  <RefreshCw
                    className={`w-3 h-3 ${isRegenerating ? "animate-spin" : ""}`}
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
                <h3 className="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  Runbook
                </h3>
                <a
                  data-testid="runbook-link"
                  href={recommendation.runbookReference}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 hover:underline"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Runbook
                </a>
              </section>
            )}

            {/* Model Info */}
            <div className="text-xs text-neutral-500 dark:text-neutral-400 pt-4 border-t border-neutral-200 dark:border-neutral-700">
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
