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

import { useReducedMotion } from "motion/react";
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
import { cn } from "../../utils/cn";
import type { AIRecommendation, RiskLevel } from "../../types/api";

import { Button } from "@/components/UI";

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

function LoadingSkeleton({
  prefersReducedMotion,
}: {
  prefersReducedMotion: boolean | null;
}) {
  return (
    <div
      data-testid="recommendation-skeleton"
      className={cn("space-y-4", !prefersReducedMotion && "animate-pulse")}
    >
      <div className="h-4 bg-neutral-3 rounded w-1/3" />
      <div className="h-16 bg-neutral-3 rounded" />
      <div className="h-4 bg-neutral-3 rounded w-1/4" />
      <div className="space-y-2">
        <div className="h-12 bg-neutral-3 rounded" />
        <div className="h-12 bg-neutral-3 rounded" />
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
      className="p-3 border border-neutral-5 rounded-lg"
    >
      <div className="flex items-center gap-2 mb-2">
        {/* Step Number */}
        <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary-9 text-neutral-12 text-xs font-medium">
          {step.stepNumber}
        </span>

        {/* Action */}
        <span className="font-medium text-neutral-12 text-sm">
          {step.action.charAt(0).toUpperCase() + step.action.slice(1)}
        </span>

        {/* Risk Level */}
        <span
          data-testid={`step-${step.stepNumber}-risk`}
          className={`text-xs px-1.5 py-0.5 rounded ${getRiskBgColor(
            step.riskLevel,
          )} text-neutral-12`}
        >
          {step.riskLevel}
        </span>

        {/* Requires Approval */}
        {step.requiresApproval && (
          <span
            data-testid={`requires-approval-${step.stepNumber}`}
            className="flex items-center gap-1 text-xs text-grafana-10 dark:text-grafana-5"
          >
            <ShieldCheck className="w-3 h-3" />
            Approval required
          </span>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-neutral-11 mb-2">{step.description}</p>

      {/* Command */}
      {step.command ? (
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-neutral-9" />
          <code className="text-xs bg-neutral-2 px-2 py-1 rounded font-mono">
            {step.command}
          </code>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-xs text-neutral-10 italic">
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
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="ai-recommendation-card"
        className="bg-neutral-1 border border-neutral-5 rounded-lg p-4"
      >
        <LoadingSkeleton prefersReducedMotion={prefersReducedMotion} />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="ai-recommendation-card"
        className="bg-neutral-1 border border-error-4 dark:border-error-11 rounded-lg p-4"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-error-9 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-error-11 dark:text-error-7">{error}</p>
            <Button
              variant="primary"
              className="mt-2 text-sm text-error-10 dark:text-error-7 underline hover:no-underline"
              data-testid="retry-button"
              onClick={onRegenerate}
            >
              Retry
            </Button>
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
        className="bg-neutral-1 border border-neutral-5 rounded-lg p-4"
      >
        <div className="flex flex-col items-center justify-center py-8 text-neutral-10">
          <Bot className="w-10 h-10 mb-2 opacity-50" />
          <p>No recommendation available</p>
          <Button
            variant="primary"
            className="mt-2 text-sm text-primary-10 dark:text-primary-7 underline hover:no-underline"
            onClick={onRegenerate}
          >
            Generate recommendation
          </Button>
        </div>
      </div>
    );
  }

  const stale = isStale(recommendation.generatedAt, staleThresholdMs);

  return (
    <div
      data-testid="ai-recommendation-card"
      className="bg-neutral-1 border border-neutral-5 rounded-lg"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-insight-9" />
          <h3 className="font-medium text-neutral-12">AI Recommendation</h3>
          <span className="text-xs text-neutral-10">
            via {recommendation.modelUsed}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="min-h-[44px] min-w-[44px] flex items-center gap-1 text-xs text-primary-10 dark:text-primary-7 hover:text-primary-11 dark:hover:text-primary-5"
          data-testid="regenerate-button"
          onClick={onRegenerate}
          disabled={isRegenerating}
        >
          {isRegenerating ? (
            <RefreshCw
              data-testid="regenerate-loading"
              className={cn("w-3 h-3", !prefersReducedMotion && "animate-spin")}
            />
          ) : (
            <RefreshCw className="w-3 h-3" />
          )}
          Regenerate
        </Button>
      </div>
      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Root Cause Analysis */}
        <section>
          <h4 className="text-sm font-medium text-neutral-12 mb-2">
            Root Cause Analysis
          </h4>
          <p className="text-sm text-neutral-11 bg-neutral-1 p-3 rounded-lg">
            {recommendation.rootCauseAnalysis}
          </p>
        </section>

        {/* Remediation Steps */}
        <section>
          <h4 className="text-sm font-medium text-neutral-12 mb-2">
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
          <h4 className="text-sm font-medium text-neutral-12 mb-2">
            Risk Assessment
          </h4>
          <div className="bg-neutral-1 p-3 rounded-lg space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-neutral-11">Overall Risk:</span>
              <span
                data-testid="overall-risk-badge"
                className={`text-xs px-2 py-0.5 rounded-full text-neutral-12 ${getRiskBgColor(
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

        {/* Runbook Link */}
        {recommendation.runbookReference && (
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
        )}
      </div>
      {/* Footer */}
      <div className="flex items-center gap-2 px-4 py-2 border-t border-neutral-5 bg-neutral-1 text-xs text-neutral-10">
        <Clock className="w-3 h-3" />
        <span data-testid="generated-at">
          Generated {formatRelativeTime(recommendation.generatedAt)}
        </span>
        {stale && (
          <span
            data-testid="stale-indicator"
            className="flex items-center gap-1 text-grafana-9"
          >
            <AlertTriangle className="w-3 h-3" />
            Stale - consider regenerating
          </span>
        )}
      </div>
    </div>
  );
}
