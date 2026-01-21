/**
 * CrossInsightsPanel Component
 *
 * Displays AI-generated cross-insights from batch composite analysis.
 * Shows persona analysis, disclosure recommendations, and confidence indicators.
 *
 * Features:
 * - Cross-insights list with visual bullets
 * - Persona mismatch warnings
 * - Disclosure level upgrade recommendations
 * - Confidence indicator with color coding
 * - Collapsible panel
 * - Dismissible with callback
 * - Loading and empty states
 *
 * @example
 * ```tsx
 * <CrossInsightsPanel
 *   crossInsights={["Insight 1", "Insight 2"]}
 *   personaResult={personaAnalysis}
 *   disclosureResult={disclosureAnalysis}
 *   confidence={0.84}
 *   isLoading={false}
 * />
 * ```
 */

import { useState } from "react";
import { useReducedMotion } from "motion/react";
import {
  Lightbulb,
  ChevronDown,
  ChevronRight,
  X,
  Loader2,
  ArrowUpCircle,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import type {
  PersonaAnalysisResult,
  DisclosureAnalysisResult,
} from "../../hooks/useBatchCompositeAnalysis";

import { Button } from "@/components/UI";
import { cn } from "../../utils/cn";

/**
 * Props for CrossInsightsPanel
 */
export interface CrossInsightsPanelProps {
  /** Array of cross-service insights */
  crossInsights: string[];
  /** Persona analysis result (null if not available) */
  personaResult: PersonaAnalysisResult | null;
  /** Disclosure analysis result (null if not available) */
  disclosureResult: DisclosureAnalysisResult | null;
  /** Overall confidence score (0-1) */
  confidence: number;
  /** Whether the analysis is loading */
  isLoading: boolean;
  /** Hide the panel when there are no insights */
  hideWhenEmpty?: boolean;
  /** Start collapsed */
  defaultCollapsed?: boolean;
  /** Callback when panel is dismissed */
  onDismiss?: () => void;
}

/**
 * Get confidence level and color based on score
 */
function getConfidenceLevel(confidence: number): {
  level: "high" | "medium" | "low";
  color: string;
  testId: string;
} {
  if (confidence >= 0.8) {
    return {
      level: "high",
      color: "text-success-10",
      testId: "confidence-high",
    };
  } else if (confidence >= 0.6) {
    return {
      level: "medium",
      color: "text-warning-9",
      testId: "confidence-medium",
    };
  }
  return { level: "low", color: "text-error-10", testId: "confidence-low" };
}

/**
 * CrossInsightsPanel displays AI-generated insights from batch composite analysis.
 */
export function CrossInsightsPanel({
  crossInsights,
  personaResult,
  disclosureResult,
  confidence,
  isLoading,
  hideWhenEmpty = false,
  defaultCollapsed = false,
  onDismiss,
}: CrossInsightsPanelProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Check if there's anything to display
  const hasInsights = crossInsights.length > 0;
  const hasPersonaResult = personaResult !== null;
  const hasDisclosureResult = disclosureResult !== null;
  const hasContent = hasInsights || hasPersonaResult || hasDisclosureResult;

  // Hide completely if empty and hideWhenEmpty is true
  if (!isLoading && !hasContent && hideWhenEmpty) {
    return null;
  }

  const confidenceInfo = getConfidenceLevel(confidence);
  const confidencePercent = Math.round(confidence * 100);

  // Check for persona mismatch
  const hasPersonaMismatch =
    hasPersonaResult &&
    personaResult.assignedPersona !== personaResult.detectedPersona;

  // Check for disclosure upgrade
  const hasDisclosureUpgrade =
    hasDisclosureResult &&
    disclosureResult.currentLevel !== disclosureResult.recommendedLevel;

  return (
    <div className="bg-neutral-1 border border-neutral-5 rounded-lg shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            className="flex text-neutral-11 hover:text-neutral-12 dark:hover:text-neutral-12"
            onClick={() => setIsCollapsed(!isCollapsed)}
            aria-label="Toggle insights panel">
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
            <Lightbulb className="w-5 h-5 text-warning-9" />
            <h3 role="heading" aria-level={3} className="font-semibold text-sm">
              AI Insights
            </h3>
          </Button>

          {/* Confidence indicator */}
          {!isLoading && confidence > 0 && (
            <span
              className={`ml-2 text-xs font-medium ${confidenceInfo.color}`}
              data-testid={confidenceInfo.testId}
              aria-label={`Confidence score: ${confidencePercent}%`}
            >
              {confidencePercent}%
            </span>
          )}
        </div>

        {/* Dismiss button */}
        {onDismiss && (
          <Button size="icon" variant="ghost"
            className="text-neutral-9 hover:text-neutral-11"
            onClick={onDismiss}
            aria-label="Dismiss insights panel"
          >
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>
      {/* Content */}
      {!isCollapsed && (
        <div className="transition-all duration-200">
          {/* Loading state */}
          {isLoading && (
            <div
              className="flex items-center justify-center py-8"
              data-testid="insights-loading"
            >
              <Loader2 className={cn("w-6 h-6 text-primary-9", !prefersReducedMotion && "animate-spin")} />
              <span className="ml-2 text-sm text-neutral-10">
                Analyzing patterns...
              </span>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !hasContent && (
            <div className="py-6 text-center text-neutral-10 text-sm">
              No insights available
            </div>
          )}

          {/* Content when not loading */}
          {!isLoading && hasContent && (
            <div className="p-4 space-y-4">
              {/* Persona mismatch warning */}
              {hasPersonaMismatch && personaResult && (
                <div className="flex items-start gap-3 p-3 bg-warning-3 bg-warning-3 rounded-lg border border-warning-6 dark:border-warning-11">
                  <AlertTriangle className="w-5 h-5 text-warning-9 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-warning-11 dark:text-warning-6">
                      Persona mismatch detected
                    </p>
                    <p className="text-xs text-warning-10 dark:text-warning-6 mt-1">
                      Assigned:{" "}
                      <span className="font-medium">
                        {personaResult.assignedPersona}
                      </span>
                      {" → "}
                      Detected:{" "}
                      <span className="font-medium">
                        {personaResult.detectedPersona}
                      </span>
                    </p>
                    {personaResult.recommendation && (
                      <p className="text-xs text-warning-9 dark:text-warning-9 mt-1">
                        {personaResult.recommendation}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Disclosure level upgrade */}
              {hasDisclosureUpgrade && disclosureResult && (
                <div className="flex items-start gap-3 p-3 bg-primary-1 dark:bg-primary-a3 rounded-lg border border-primary-4 dark:border-primary-11">
                  <ArrowUpCircle className="w-5 h-5 text-primary-9 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-primary-11 dark:text-primary-4">
                      Level upgrade recommended
                    </p>
                    <p className="text-xs text-primary-11 dark:text-primary-5 mt-1">
                      Current:{" "}
                      <span className="font-medium">
                        {disclosureResult.currentLevel}
                      </span>
                      {" → "}
                      Recommended:{" "}
                      <span className="font-medium">
                        {disclosureResult.recommendedLevel}
                      </span>
                    </p>
                    {disclosureResult.personalizedMessage && (
                      <p className="text-xs text-primary-10 dark:text-primary-7 mt-1">
                        {disclosureResult.personalizedMessage}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Cross insights list */}
              {hasInsights && (
                <div>
                  <h4 className="text-xs font-medium text-neutral-10 uppercase tracking-wide mb-2">
                    Cross-Service Insights
                  </h4>
                  <ul role="list" className="space-y-2">
                    {crossInsights.map((insight, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm text-neutral-11"
                      >
                        <Sparkles className="w-4 h-4 text-insight-9 flex-shrink-0 mt-0.5" />
                        <span>{insight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* UI Adaptations from persona */}
              {personaResult?.uiAdaptations &&
                personaResult.uiAdaptations.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-neutral-10 uppercase tracking-wide mb-2">
                      Recommended Adaptations
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {personaResult.uiAdaptations.map((adaptation, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-success-3 bg-success-4 text-success-11 dark:text-success-4"
                        >
                          <span className="font-medium">
                            {adaptation.feature}
                          </span>
                          <span className="mx-1">→</span>
                          <span>{adaptation.action}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

              {/* Features to unlock from disclosure */}
              {disclosureResult?.unlockFeatures &&
                disclosureResult.unlockFeatures.length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-neutral-10 uppercase tracking-wide mb-2">
                      Features to Unlock
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {disclosureResult.unlockFeatures.map((feature, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-insight-2 dark:bg-insight-a4 text-insight-11 dark:text-insight-4"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CrossInsightsPanel;
