/**
 * ConfidenceIndicator Component
 *
 * Displays AI response confidence score with visual indicators.
 * Helps users understand how confident the AI is in its response.
 */

import { AlertTriangle } from "lucide-react";

export interface ConfidenceIndicatorProps {
  /** Confidence score (0-1) */
  score: number;
  /** Compact mode - only shows visual indicator without text */
  compact?: boolean;
}

/**
 * Get confidence level category
 */
function getConfidenceLevel(score: number): "high" | "medium" | "low" {
  if (score >= 0.8) return "high";
  if (score >= 0.6) return "medium";
  return "low";
}

/**
 * Get color class based on confidence level
 */
function getColorClass(level: "high" | "medium" | "low"): string {
  switch (level) {
    case "high":
      return "text-success-600";
    case "medium":
      return "text-warning-600";
    case "low":
      return "text-error-600";
  }
}

/**
 * Clamp score to valid range [0, 1]
 */
function clampScore(score: number): number {
  return Math.max(0, Math.min(1, score));
}

/**
 * ConfidenceIndicator component for displaying AI response confidence.
 *
 * @example
 * ```tsx
 * // In a chat message
 * <ChatMessage>
 *   <MessageContent>{content}</MessageContent>
 *   <ConfidenceIndicator score={0.92} />
 * </ChatMessage>
 *
 * // Compact mode
 * <ConfidenceIndicator score={0.85} compact />
 * ```
 */
export function ConfidenceIndicator({
  score,
  compact = false,
}: ConfidenceIndicatorProps) {
  const clampedScore = clampScore(score);
  const percentage = Math.round(clampedScore * 100);
  const level = getConfidenceLevel(clampedScore);
  const colorClass = getColorClass(level);
  const showWarning = clampedScore < 0.7;

  const ariaLabel = `AI confidence: ${percentage}%, ${level} confidence`;

  if (compact) {
    return (
      <div
        data-testid="confidence-indicator"
        className={`inline-flex items-center ${colorClass}`}
        title={`Confidence: ${percentage}%`}
        aria-label={ariaLabel}
      >
        <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
          <circle cx="6" cy="6" r="5" opacity="0.2" />
          <circle cx="6" cy="6" r="3" />
        </svg>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2">
      <div
        data-testid="confidence-indicator"
        className={`inline-flex items-center gap-1 text-sm ${colorClass}`}
        aria-label={ariaLabel}
      >
        <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
          <circle cx="6" cy="6" r="5" opacity="0.2" />
          <circle cx="6" cy="6" r="3" />
        </svg>
        <span>{percentage}%</span>
      </div>

      {showWarning && (
        <div className="inline-flex items-center gap-1 px-2 py-0.5 bg-warning-50 dark:bg-warning-900/20 text-warning-700 dark:text-warning-300 rounded text-xs">
          <AlertTriangle
            data-testid="warning-icon"
            className="w-3 h-3"
            aria-hidden="true"
          />
          <span>Low confidence - verify this information</span>
        </div>
      )}
    </div>
  );
}

export default ConfidenceIndicator;
