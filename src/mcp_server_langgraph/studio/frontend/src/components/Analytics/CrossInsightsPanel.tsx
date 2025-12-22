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
    return { level: "high", color: "text-green-600", testId: "confidence-high" };
  } else if (confidence >= 0.6) {
    return { level: "medium", color: "text-yellow-600", testId: "confidence-medium" };
  }
  return { level: "low", color: "text-red-600", testId: "confidence-low" };
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
    personaResult.assigned_persona !== personaResult.detected_persona;

  // Check for disclosure upgrade
  const hasDisclosureUpgrade =
    hasDisclosureResult &&
    disclosureResult.current_level !== disclosureResult.recommended_level;

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            aria-label="Toggle insights panel"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
            <Lightbulb className="w-5 h-5 text-yellow-500" />
            <h3 role="heading" aria-level={3} className="font-semibold text-sm">
              AI Insights
            </h3>
          </button>

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
          <button
            onClick={onDismiss}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Dismiss insights panel"
          >
            <X className="w-4 h-4" />
          </button>
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
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            <span className="ml-2 text-sm text-gray-500">
              Analyzing patterns...
            </span>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !hasContent && (
          <div className="py-6 text-center text-gray-500 text-sm">
            No insights available
          </div>
        )}

        {/* Content when not loading */}
        {!isLoading && hasContent && (
          <div className="p-4 space-y-4">
            {/* Persona mismatch warning */}
            {hasPersonaMismatch && personaResult && (
              <div className="flex items-start gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                    Persona mismatch detected
                  </p>
                  <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                    Assigned: <span className="font-medium">{personaResult.assigned_persona}</span>
                    {" → "}
                    Detected: <span className="font-medium">{personaResult.detected_persona}</span>
                  </p>
                  {personaResult.recommendation && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                      {personaResult.recommendation}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Disclosure level upgrade */}
            {hasDisclosureUpgrade && disclosureResult && (
              <div className="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <ArrowUpCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    Level upgrade recommended
                  </p>
                  <p className="text-xs text-blue-700 dark:text-blue-300 mt-1">
                    Current: <span className="font-medium">{disclosureResult.current_level}</span>
                    {" → "}
                    Recommended: <span className="font-medium">{disclosureResult.recommended_level}</span>
                  </p>
                  {disclosureResult.personalized_message && (
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                      {disclosureResult.personalized_message}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Cross insights list */}
            {hasInsights && (
              <div>
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                  Cross-Service Insights
                </h4>
                <ul role="list" className="space-y-2">
                  {crossInsights.map((insight, index) => (
                    <li
                      key={index}
                      className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300"
                    >
                      <Sparkles className="w-4 h-4 text-purple-500 flex-shrink-0 mt-0.5" />
                      <span>{insight}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* UI Adaptations from persona */}
            {personaResult?.ui_adaptations && personaResult.ui_adaptations.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                  Recommended Adaptations
                </h4>
                <div className="flex flex-wrap gap-2">
                  {personaResult.ui_adaptations.map((adaptation, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200"
                    >
                      <span className="font-medium">{adaptation.feature}</span>
                      <span className="mx-1">→</span>
                      <span>{adaptation.action}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Features to unlock from disclosure */}
            {disclosureResult?.unlock_features && disclosureResult.unlock_features.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                  Features to Unlock
                </h4>
                <div className="flex flex-wrap gap-2">
                  {disclosureResult.unlock_features.map((feature, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200"
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
