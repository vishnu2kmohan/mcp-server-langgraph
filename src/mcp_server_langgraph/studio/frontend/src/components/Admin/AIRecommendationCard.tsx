/**
 * AIRecommendationCard Component
 *
 * Display card for AI-generated alert recommendations.
 *
 * Features:
 * - Root cause analysis display
 * - Remediation steps list
 * - Risk assessment badge
 * - Regenerate button
 * - Cache freshness indicator
 * - Runbook link
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import {
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Clock,
  Bot,
  ShieldCheck,
  Terminal,
  AlertCircle,
} from "lucide-react";
import type { AIRecommendation, RiskLevel } from "../../types/api";

// =============================================================================
// Types
// =============================================================================

export interface AIRecommendationCardProps {
  /** The AI recommendation to display */
  recommendation: AIRecommendation | null;
  /** Callback to regenerate recommendation */
  onRegenerate: () => void;
  /** Loading state */
  isLoading?: boolean;
  /** Regenerating state */
  isRegenerating?: boolean;
  /** Error message */
  error?: string | null;
  /** Stale threshold in milliseconds (default: 1 hour) */
  staleThresholdMs?: number;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_STALE_THRESHOLD_MS = 60 * 60 * 1000; // 1 hour

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get risk level badge color (background)
 */
function getRiskBgColor(risk: RiskLevel): string {
  switch (risk) {
    case "low":
      return "bg-success-500";
    case "medium":
      return "bg-warning-500";
    case "high":
      return "bg-error-500";
    default:
      return "bg-gray-500";
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

/**
 * Check if recommendation is stale
 */
function isStale(generatedAt: string, thresholdMs: number): boolean {
  const date = new Date(generatedAt);
  const now = new Date();
  return now.getTime() - date.getTime() > thresholdMs;
}

// =============================================================================
// Sub-Components
// =============================================================================

function LoadingSkeleton() {
  return (
    <div
      data-testid="recommendation-skeleton"
      className="animate-pulse space-y-4"
    >
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
      <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded" />
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
      <div className="space-y-2">
        <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    </div>
  );
}

interface StepCardProps {
  step: AIRecommendation["remediationSteps"][0];
}

function StepCard({ step }: StepCardProps) {
  return (
    <div
      data-testid={`step-${step.stepNumber}`}
      className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg"
    >
      <div className="flex items-center gap-2 mb-2">
        {/* Step Number */}
        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary-500 text-white text-xs font-medium">
          {step.stepNumber}
        </span>

        {/* Action */}
        <span className="font-medium text-gray-900 dark:text-white text-sm">
          {step.action.charAt(0).toUpperCase() + step.action.slice(1)}
        </span>

        {/* Risk Level */}
        <span
          data-testid={`step-${step.stepNumber}-risk`}
          className={`text-xs px-1.5 py-0.5 rounded ${getRiskBgColor(
            step.riskLevel,
          )} text-white`}
        >
          {step.riskLevel}
        </span>

        {/* Requires Approval */}
        {step.requiresApproval && (
          <span
            data-testid={`requires-approval-${step.stepNumber}`}
            className="flex items-center gap-1 text-xs text-grafana-600 dark:text-grafana-400"
          >
            <ShieldCheck className="w-3 h-3" />
            Approval required
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
        {step.description}
      </p>

      {/* Command */}
      {step.command ? (
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-gray-400 dark:text-gray-400" />
          <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded font-mono">
            {step.command}
          </code>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 italic">
          <Terminal className="w-4 h-4" />
          Manual step - no command
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AIRecommendationCard({
  recommendation,
  onRegenerate,
  isLoading = false,
  isRegenerating = false,
  error = null,
  staleThresholdMs = DEFAULT_STALE_THRESHOLD_MS,
}: AIRecommendationCardProps) {
  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="ai-recommendation-card"
        className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
      >
        <LoadingSkeleton />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="ai-recommendation-card"
        className="bg-white dark:bg-gray-900 border border-error-200 dark:border-error-800 rounded-lg p-4"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-error-700 dark:text-error-400">{error}</p>
            <button
              data-testid="retry-button"
              onClick={onRegenerate}
              className="mt-2 text-sm text-error-600 dark:text-error-400 underline hover:no-underline"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!recommendation) {
    return (
      <div
        data-testid="ai-recommendation-card"
        className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
      >
        <div className="flex flex-col items-center justify-center py-8 text-gray-500 dark:text-gray-400">
          <Bot className="w-10 h-10 mb-2 opacity-50" />
          <p>No recommendation available</p>
          <button
            onClick={onRegenerate}
            className="mt-2 text-sm text-primary-600 dark:text-primary-400 underline hover:no-underline"
          >
            Generate recommendation
          </button>
        </div>
      </div>
    );
  }

  const stale = isStale(recommendation.generatedAt, staleThresholdMs);

  return (
    <div
      data-testid="ai-recommendation-card"
      className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-insight-500" />
          <h3 className="font-medium text-gray-900 dark:text-white">
            AI Recommendation
          </h3>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            via {recommendation.modelUsed}
          </span>
        </div>
        <button
          data-testid="regenerate-button"
          onClick={onRegenerate}
          disabled={isRegenerating}
          className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRegenerating ? (
            <RefreshCw
              data-testid="regenerate-loading"
              className="w-3 h-3 animate-spin"
            />
          ) : (
            <RefreshCw className="w-3 h-3" />
          )}
          Regenerate
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Root Cause Analysis */}
        <section>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Root Cause Analysis
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg">
            {recommendation.rootCauseAnalysis}
          </p>
        </section>

        {/* Remediation Steps */}
        <section>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Remediation Steps
          </h4>
          <div className="space-y-2">
            {recommendation.remediationSteps.map((step) => (
              <StepCard key={step.stepNumber} step={step} />
            ))}
          </div>
        </section>

        {/* Risk Assessment */}
        <section>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Risk Assessment
          </h4>
          <div className="bg-gray-50 dark:bg-gray-800/50 p-3 rounded-lg space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Overall Risk:
              </span>
              <span
                data-testid="overall-risk-badge"
                className={`text-xs px-2 py-0.5 rounded-full text-white ${getRiskBgColor(
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

        {/* Runbook Link */}
        {recommendation.runbookReference && (
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
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30 text-xs text-gray-500 dark:text-gray-400">
        <Clock className="w-3 h-3" />
        <span data-testid="generated-at">
          Generated {formatRelativeTime(recommendation.generatedAt)}
        </span>
        {stale && (
          <span
            data-testid="stale-indicator"
            className="flex items-center gap-1 text-grafana-500"
          >
            <AlertTriangle className="w-3 h-3" />
            Stale - consider regenerating
          </span>
        )}
      </div>
    </div>
  );
}
