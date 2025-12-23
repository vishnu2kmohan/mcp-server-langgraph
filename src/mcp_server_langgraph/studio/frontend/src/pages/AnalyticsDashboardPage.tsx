/**
 * AnalyticsDashboardPage
 *
 * Sprint 4 - Phase 3.3: HEART Metrics Analytics Dashboard
 * Sprint 4 - Phase 6.6: AI-Generated HEART Insights Integration
 *
 * Visual dashboard for HEART metrics (Happiness, Engagement, Adoption,
 * Retention, Task Success). Admin-only access.
 *
 * Features:
 * - Overview cards for 5 HEART dimensions
 * - Overall health score display
 * - Time range selector (7d/30d/90d)
 * - AI-generated insights panel with anomalies, trends, and predictions
 * - Loading and error states
 *
 * Refactored: Now uses useHeartDashboard hook for data management
 */

import React from "react";
import { useHeartDashboard } from "../hooks/useHeartDashboard";
import {
  AIInsightsPanel,
  DimensionCard,
  OverallHealthScore,
  TimeRangeSelector,
} from "../components/Analytics";

// =============================================================================
// Main Component
// =============================================================================

export function AnalyticsDashboardPage(): React.ReactElement {
  const {
    loading,
    error,
    data,
    dimensions,
    overallScore,
    timeRange,
    setTimeRange,
    dataPointCount,
  } = useHeartDashboard();

  return (
    <main
      className="analytics-dashboard-page"
      aria-labelledby="analytics-title"
    >
      {/* Header */}
      <header className="analytics-header">
        <h1 id="analytics-title">Analytics Dashboard</h1>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </header>

      {/* Loading state */}
      {loading && (
        <div
          className="analytics-loading"
          data-testid="analytics-loading"
          role="status"
          aria-live="polite"
        >
          <span className="loading-spinner" aria-hidden="true">
            ⏳
          </span>
          <span>Loading analytics...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div
          className="analytics-error"
          data-testid="analytics-error"
          role="alert"
        >
          <span className="error-icon" aria-hidden="true">
            ⚠️
          </span>
          <span>Failed to load analytics: {error}</span>
        </div>
      )}

      {/* Content */}
      {!loading && !error && (
        <div className="analytics-content">
          {/* Overall Health Score */}
          <section className="analytics-overview">
            <OverallHealthScore score={overallScore} />
          </section>

          {/* HEART Dimension Cards */}
          <section
            className="analytics-dimensions"
            aria-label="HEART Dimensions"
          >
            {dimensions.map((dim) => (
              <DimensionCard
                key={dim.dimension}
                dimension={dim.dimension}
                score={dim.score}
                hasData={dim.samples > 0}
              />
            ))}
          </section>

          {/* AI-Generated Insights (Phase 6.6) */}
          <section className="analytics-insights" aria-label="AI Insights">
            <AIInsightsPanel
              className="ai-insights-section"
              pollingIntervalMs={60000}
            />
          </section>

          {/* Data info footer */}
          {data && (
            <footer className="analytics-footer">
              <p className="data-info">
                Based on {dataPointCount.toLocaleString()} data points
              </p>
            </footer>
          )}
        </div>
      )}
    </main>
  );
}

export default AnalyticsDashboardPage;
