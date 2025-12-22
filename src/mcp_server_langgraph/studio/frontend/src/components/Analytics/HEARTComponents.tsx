/**
 * HEART Dashboard Components
 *
 * Sprint 4 - Phase 3.3: HEART Metrics Dashboard
 *
 * Extracted sub-components for the HEART analytics dashboard:
 * - DimensionCard: Display individual HEART dimension metrics
 * - OverallHealthScore: Aggregate health score visualization
 * - TimeRangeSelector: Time period selector for dashboard
 *
 * @example
 * ```tsx
 * <DimensionCard dimension="happiness" score={85} hasData />
 * <OverallHealthScore score={78} />
 * <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
 * ```
 */

import React from "react";
import type { HeartDimension } from "../../analytics/gsm";

// =============================================================================
// Types
// =============================================================================

export type TimeRange = "7d" | "30d" | "90d";

export interface DimensionCardProps {
  /** The HEART dimension to display */
  dimension: HeartDimension;
  /** Score value (0-100) */
  score: number;
  /** Whether data is available for display */
  hasData: boolean;
}

export interface OverallHealthScoreProps {
  /** Overall health score (0-100) */
  score: number;
}

export interface TimeRangeSelectorProps {
  /** Currently selected time range */
  value: TimeRange;
  /** Callback when time range changes */
  onChange: (range: TimeRange) => void;
}

// =============================================================================
// Constants
// =============================================================================

const DIMENSION_LABELS: Record<HeartDimension, string> = {
  happiness: "Happiness",
  engagement: "Engagement",
  adoption: "Adoption",
  retention: "Retention",
  task_success: "Task Success",
};

const DIMENSION_ICONS: Record<HeartDimension, string> = {
  happiness: "😊",
  engagement: "🔥",
  adoption: "📈",
  retention: "🔄",
  task_success: "✅",
};

const DIMENSION_COLORS: Record<HeartDimension, string> = {
  happiness: "#22c55e",
  engagement: "#f97316",
  adoption: "#3b82f6",
  retention: "#8b5cf6",
  task_success: "#10b981",
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get color based on score value
 */
// eslint-disable-next-line react-refresh/only-export-components
export function getScoreColor(score: number): string {
  if (score >= 80) return "#22c55e"; // green
  if (score >= 60) return "#eab308"; // yellow
  if (score >= 40) return "#f97316"; // orange
  return "#ef4444"; // red
}

// =============================================================================
// DimensionCard Component
// =============================================================================

/**
 * Display an individual HEART dimension with icon, label, and score
 */
export function DimensionCard({
  dimension,
  score,
  hasData,
}: DimensionCardProps): React.ReactElement {
  const label = DIMENSION_LABELS[dimension];
  const icon = DIMENSION_ICONS[dimension];
  const color = DIMENSION_COLORS[dimension];

  return (
    <article
      role="region"
      aria-label={label}
      className="dimension-card"
      style={{ borderLeftColor: color }}
    >
      <div className="dimension-header">
        <span className="dimension-icon" aria-hidden="true">
          {icon}
        </span>
        <h3 className="dimension-title">{label}</h3>
      </div>
      <div className="dimension-body">
        {hasData ? (
          <span
            className="dimension-score"
            style={{ color: getScoreColor(score) }}
          >
            {score}
          </span>
        ) : (
          <span className="dimension-no-data">No data</span>
        )}
      </div>
    </article>
  );
}

// =============================================================================
// OverallHealthScore Component
// =============================================================================

/**
 * Display the overall health score with a circular visualization
 */
export function OverallHealthScore({
  score,
}: OverallHealthScoreProps): React.ReactElement {
  return (
    <div
      className="overall-health"
      data-testid="overall-health-score"
      role="region"
      aria-label="Overall Health Score"
    >
      <h3>Overall Health</h3>
      <div
        className="health-score-circle"
        style={{ borderColor: getScoreColor(score) }}
      >
        <span className="health-score-value">{score}</span>
      </div>
    </div>
  );
}

// =============================================================================
// TimeRangeSelector Component
// =============================================================================

/**
 * Dropdown selector for dashboard time range
 */
export function TimeRangeSelector({
  value,
  onChange,
}: TimeRangeSelectorProps): React.ReactElement {
  return (
    <label className="time-range-selector">
      <span className="sr-only">Time range</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as TimeRange)}
        aria-label="Time range"
        className="time-range-select"
      >
        <option value="7d">Last 7 days</option>
        <option value="30d">Last 30 days</option>
        <option value="90d">Last 90 days</option>
      </select>
    </label>
  );
}
