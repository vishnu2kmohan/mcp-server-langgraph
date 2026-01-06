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
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "warning":
      return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
  }
}

/**
 * Get state badge styling
 */
function getStateStyle(state: Alert["state"]): string {
  switch (state) {
    case "firing":
      return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    case "resolved":
      return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
  }
}

/**
 * Get risk level badge color
 */
function getRiskColor(risk: RiskLevel): string {
  switch (risk) {
    case "low":
      return "bg-green-500";
    case "medium":
      return "bg-yellow-500";
    case "high":
      return "bg-red-500";
    default:
      return "bg-gray-500";
  }
}

/**
 * Get status icon for remediation
 */
function getStatusIcon(status: RemediationRequest["status"]) {
  switch (status) {
    case "pending":
      return <Clock className="w-4 h-4 text-yellow-500" />;
    case "approved":
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case "rejected":
      return <XCircle className="w-4 h-4 text-red-500" />;
    case "executing":
      return <Play className="w-4 h-4 text-blue-500 animate-pulse" />;
    case "completed":
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case "failed":
      return <Ban className="w-4 h-4 text-red-500" />;
    default:
      return <Clock className="w-4 h-4 text-gray-500" />;
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
    <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      {/* Step Header */}
      <div className="flex items-center gap-3 mb-2">
        <span
          data-testid={`step-number-${step.stepNumber}`}
          className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500 text-white text-sm font-medium"
        >
          {step.stepNumber}
        </span>
        <span className="font-medium text-gray-900 dark:text-white">
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
            className="flex items-center gap-1 text-xs text-gray-500"
          >
            {getStatusIcon(remediation.status)}
            {remediation.status.charAt(0).toUpperCase() +
              remediation.status.slice(1)}
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
        {step.description}
      </p>

      {/* Command */}
      {step.command && (
        <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded mb-3 overflow-x-auto">
          <code>{step.command}</code>
        </pre>
      )}

      {/* Action Buttons */}
      {isPending && remediation && (
        <div className="flex gap-2">
          <button
            data-testid={`approve-step-${step.stepNumber}`}
            onClick={() => onApprove(remediation.remediationId)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            Approve
          </button>
          <button
            data-testid={`reject-step-${step.stepNumber}`}
            onClick={() => onReject(remediation.remediationId)}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
          >
            <XCircle className="w-4 h-4" />
            Reject
          </button>
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
      <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400 p-8">
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
      <div className="flex items-start justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex-1">
          {/* Alert Name and Badges */}
          <div className="flex items-center gap-2 mb-2">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
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
          <p className="text-gray-600 dark:text-gray-400 mb-2">
            {alert.message}
          </p>

          {/* Labels */}
          <div className="flex flex-wrap gap-2 mb-2">
            {Object.entries(alert.labels).map(([key, value]) => (
              <span
                key={key}
                className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded"
              >
                {value}
              </span>
            ))}
          </div>

          {/* Started Time */}
          <div
            data-testid="alert-started"
            className="text-xs text-gray-500 dark:text-gray-500"
          >
            Started: {formatRelativeTime(alert.startedAt)}
          </div>
        </div>

        {/* Close Button */}
        <button
          data-testid="close-detail-panel"
          onClick={onClose}
          className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Loading State */}
        {isLoadingRecommendation && (
          <div
            data-testid="recommendation-loading"
            className="flex items-center justify-center py-12"
          >
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        )}

        {/* Error State */}
        {recommendationError && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-700 dark:text-red-400">
              Failed to generate recommendation: {recommendationError}
            </p>
            <button
              onClick={onRegenerate}
              className="mt-2 text-sm text-red-600 dark:text-red-400 underline"
            >
              Try again
            </button>
          </div>
        )}

        {/* Recommendation Content */}
        {recommendation && !isLoadingRecommendation && (
          <>
            {/* Root Cause Analysis */}
            <section>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                Root Cause Analysis
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg">
                {recommendation.rootCauseAnalysis}
              </p>
            </section>

            {/* Risk Assessment */}
            <section>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                Risk Assessment
              </h3>
              <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
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
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Impact:{" "}
                  </span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {recommendation.riskAssessment.impactAnalysis}
                  </span>
                </div>
                <div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Rollback:{" "}
                  </span>
                  <code className="text-xs bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">
                    {recommendation.riskAssessment.rollbackPlan}
                  </code>
                </div>
              </div>
            </section>

            {/* Remediation Steps */}
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Remediation Steps
                </h3>
                <button
                  data-testid="regenerate-recommendation"
                  onClick={onRegenerate}
                  disabled={isRegenerating}
                  className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RefreshCw
                    className={`w-3 h-3 ${isRegenerating ? "animate-spin" : ""}`}
                  />
                  Regenerate
                </button>
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
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Runbook
                </h3>
                <a
                  data-testid="runbook-link"
                  href={recommendation.runbookReference}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Runbook
                </a>
              </section>
            )}

            {/* Model Info */}
            <div className="text-xs text-gray-500 dark:text-gray-500 pt-4 border-t border-gray-200 dark:border-gray-700">
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
