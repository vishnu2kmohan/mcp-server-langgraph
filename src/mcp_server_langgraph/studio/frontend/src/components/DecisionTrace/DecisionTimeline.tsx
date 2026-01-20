/**
 * DecisionTimeline Component
 *
 * Displays a chronological timeline of decision traces for context graphs.
 * Shows the "WHY" behind agent decisions with confidence scores and outcomes.
 *
 * Reference: ADR-0101 Context Graphs
 */

import { useMemo } from "react";
import type {
  DecisionTraceSummary,
  DecisionType,
} from "../../types/contextGraph";

export interface DecisionTimelineProps {
  /** List of decision traces to display */
  traces: DecisionTraceSummary[];
  /** Loading state indicator */
  isLoading?: boolean;
  /** Filter by specific decision type */
  filterType?: DecisionType;
  /** Optional className for container */
  className?: string;
}

/**
 * Format timestamp to readable time
 */
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return timestamp;
  }
}

/**
 * Get CSS class for decision type badge
 * Uses semantic color tokens per design system
 */
function getDecisionTypeClass(type: DecisionType): string {
  const baseClass = "px-2 py-0.5 rounded text-xs font-medium";
  switch (type) {
    case "routing":
      return `${baseClass} bg-primary-3 text-primary-11 dark:bg-primary-12 dark:text-primary-4`;
    case "tool_selection":
      return `${baseClass} bg-insight-2 text-insight-11 dark:bg-insight-12 dark:text-insight-4`;
    case "skill_selection":
      return `${baseClass} bg-success-3 text-success-11 dark:bg-success-12 dark:text-success-4`;
    case "model_selection":
      return `${baseClass} bg-grafana-2 text-grafana-11 dark:bg-grafana-12 dark:text-grafana-3`;
    case "approval":
      return `${baseClass} bg-warning-3 text-warning-11 dark:bg-warning-12 dark:text-warning-6`;
    case "exception":
      return `${baseClass} bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-4`;
    default:
      return `${baseClass} bg-neutral-2 text-neutral-12`;
  }
}

/**
 * Get confidence color based on value
 * Uses semantic color tokens
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return "text-success-10 dark:text-success-7";
  if (confidence >= 0.7) return "text-warning-9 dark:text-warning-9";
  return "text-error-10 dark:text-error-7";
}

/**
 * Loading skeleton for timeline items
 */
function TimelineSkeleton() {
  return (
    <div className="animate-pulse" data-testid="timeline-skeleton">
      <div className="flex items-start gap-3 p-3">
        <div className="w-3 h-3 rounded-full bg-neutral-3 mt-1.5" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-neutral-3 rounded w-24" />
          <div className="h-3 bg-neutral-3 rounded w-48" />
          <div className="h-3 bg-neutral-3 rounded w-16" />
        </div>
      </div>
    </div>
  );
}

/**
 * Empty state component
 */
function TimelineEmpty() {
  return (
    <div
      data-testid="timeline-empty"
      className="flex flex-col items-center justify-center py-8 text-neutral-10"
    >
      <svg
        className="w-12 h-12 mb-3 text-neutral-9"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
        />
      </svg>
      <p className="text-sm">No decision traces found</p>
    </div>
  );
}

/**
 * Outcome indicator component
 */
function OutcomeIndicator({
  outcome,
}: {
  outcome: DecisionTraceSummary["outcome"];
}) {
  if (outcome === "success") {
    return (
      <span
        data-testid="outcome-success"
        className="inline-flex items-center text-success-10 dark:text-success-7"
        title="Success"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  if (outcome === "failure") {
    return (
      <span
        data-testid="outcome-failure"
        className="inline-flex items-center text-error-10 dark:text-error-7"
        title="Failure"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }

  // Pending or null
  return (
    <span
      data-testid="outcome-pending"
      className="inline-flex items-center text-warning-9 dark:text-warning-9"
      title="Pending"
    >
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
          clipRule="evenodd"
        />
      </svg>
    </span>
  );
}

/**
 * Single timeline item component
 */
function TimelineItem({ trace }: { trace: DecisionTraceSummary }) {
  const confidencePercent = Math.round(trace.confidence * 100);

  return (
    <li
      data-testid="timeline-item"
      className="relative flex items-start gap-3 pb-4 last:pb-0"
      role="listitem"
    >
      {/* Timeline connector line */}
      <div className="absolute left-1.5 top-3 bottom-0 w-px bg-neutral-3 last:hidden" />

      {/* Timeline dot */}
      <div className="relative z-10 w-3 h-3 rounded-full bg-primary-9 mt-1.5 ring-2 ring-neutral-1" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={getDecisionTypeClass(trace.decisionType)}>
            {trace.decisionType}
          </span>
          <span className="text-xs text-neutral-10">
            {formatTime(trace.timestamp)}
          </span>
          <OutcomeIndicator outcome={trace.outcome} />
        </div>

        <p className="mt-1 text-sm text-neutral-12 truncate">
          {trace.chosenAction}
        </p>

        <p className={`text-xs mt-0.5 ${getConfidenceColor(trace.confidence)}`}>
          {confidencePercent}%
        </p>
      </div>
    </li>
  );
}

/**
 * Decision Timeline Component
 *
 * Displays a chronological timeline of decision traces showing
 * the reasoning behind agent decisions.
 */
export function DecisionTimeline({
  traces,
  isLoading = false,
  filterType,
  className = "",
}: DecisionTimelineProps) {
  // Filter traces if filterType is specified
  const filteredTraces = useMemo(() => {
    if (!filterType) return traces;
    return traces.filter((t) => t.decisionType === filterType);
  }, [traces, filterType]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="decision-timeline"
        className={`decision-timeline ${className}`}
      >
        <div data-testid="timeline-loading">
          {[1, 2, 3].map((i) => (
            <TimelineSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (filteredTraces.length === 0) {
    return (
      <div
        data-testid="decision-timeline"
        className={`decision-timeline ${className}`}
      >
        <TimelineEmpty />
      </div>
    );
  }

  return (
    <div
      data-testid="decision-timeline"
      className={`decision-timeline ${className}`}
    >
      <ul role="list" aria-label="Decision timeline" className="space-y-1 p-2">
        {filteredTraces.map((trace) => (
          <TimelineItem key={trace.traceId} trace={trace} />
        ))}
      </ul>
    </div>
  );
}

export default DecisionTimeline;
