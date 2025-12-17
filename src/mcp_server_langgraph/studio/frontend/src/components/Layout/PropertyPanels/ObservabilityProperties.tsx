/**
 * ObservabilityProperties Component
 *
 * Property panel for observability, showing trace/log
 * statistics and quick metrics overview.
 */

import { useGetMetricsQuery } from "../../../api";
import type { TabState } from "../../../store/slices/workspaceSlice";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

// =============================================================================
// Types
// =============================================================================

export interface ObservabilityPropertiesProps {
  tab: TabState;
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function ObservabilityProperties({
  tab: _tab,
  isSectionExpanded,
  onToggleSection,
}: ObservabilityPropertiesProps) {
  const { data: metrics, isLoading } = useGetMetricsQuery();

  if (isLoading) {
    return (
      <div className="p-4 text-xs text-gray-500 dark:text-gray-400">
        Loading metrics...
      </div>
    );
  }

  const formatDuration = (ms?: number) => {
    if (ms === undefined) return "N/A";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatPercent = (value?: number) => {
    if (value === undefined) return "0%";
    return `${value.toFixed(1)}%`;
  };

  // Calculate derived metrics
  const requestsTotal = metrics?.requests_total ?? 0;
  const errorsTotal = metrics?.errors_total ?? 0;
  const successRate =
    requestsTotal > 0
      ? ((requestsTotal - errorsTotal) / requestsTotal) * 100
      : 100;
  const errorRate = requestsTotal > 0 ? (errorsTotal / requestsTotal) * 100 : 0;

  return (
    <div data-testid="observability-properties">
      <PropertySection
        id="metrics-overview"
        title="Overview"
        isExpanded={isSectionExpanded("metrics-overview")}
        onToggle={() => onToggleSection("metrics-overview")}
      >
        <PropertyRow
          label="Total Requests"
          value={requestsTotal.toLocaleString()}
        />
        <PropertyRow label="Success Rate" value={formatPercent(successRate)} />
        <PropertyRow label="Error Rate" value={formatPercent(errorRate)} />
      </PropertySection>

      <PropertySection
        id="latency-info"
        title="Latency"
        isExpanded={isSectionExpanded("latency-info")}
        onToggle={() => onToggleSection("latency-info")}
      >
        <PropertyRow
          label="Average"
          value={formatDuration(metrics?.avg_latency_ms)}
        />
        <PropertyRow
          label="P99"
          value={formatDuration(metrics?.p99_latency_ms)}
        />
      </PropertySection>

      <PropertySection
        id="resources-info"
        title="Resources"
        isExpanded={isSectionExpanded("resources-info")}
        onToggle={() => onToggleSection("resources-info")}
      >
        <PropertyRow
          label="Active Sessions"
          value={metrics?.active_sessions ?? 0}
        />
        <PropertyRow
          label="Tokens Used"
          value={metrics?.tokens_used?.toLocaleString() ?? "0"}
        />
      </PropertySection>

      <PropertySection
        id="time-range"
        title="Time Range"
        isExpanded={isSectionExpanded("time-range")}
        onToggle={() => onToggleSection("time-range")}
      >
        <PropertyRow label="View" value="Last 24 hours" />
        <PropertyRow label="Refresh" value="Auto (30s)" />
      </PropertySection>
    </div>
  );
}

export default ObservabilityProperties;
