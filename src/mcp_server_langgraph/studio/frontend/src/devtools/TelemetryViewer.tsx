/**
 * TelemetryViewer Component
 *
 * Development tools panel for viewing session telemetry metrics.
 * Only visible in development mode.
 *
 * Usage:
 * ```tsx
 * // In your app layout (dev mode only)
 * {import.meta.env.DEV && <TelemetryViewer />}
 * ```
 */
import { useState, useCallback, useMemo } from "react";
import { useSessionTelemetry } from "../contexts/TelemetryContext";
import { isDevMode } from "../utils/devLogger";

// =============================================================================
// Types
// =============================================================================

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

// =============================================================================
// Collapsible Section Component
// =============================================================================

function CollapsibleSection({
  title,
  children,
  defaultOpen = true,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="telemetry-section">
      <button
        className="telemetry-section-header"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: "flex",
          alignItems: "center",
          width: "100%",
          padding: "8px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          fontWeight: 600,
          fontSize: "14px",
          color: "#333",
        }}
      >
        <span style={{ marginRight: "8px" }}>{isOpen ? "▼" : "▶"}</span>
        {title}
      </button>
      {isOpen && <div style={{ padding: "8px 8px 8px 24px" }}>{children}</div>}
    </div>
  );
}

// =============================================================================
// Metric Row Component
// =============================================================================

function MetricRow({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "4px 0",
        fontSize: "12px",
      }}
    >
      <span style={{ color: "#666" }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function TelemetryViewer() {
  const telemetry = useSessionTelemetry();
  const [, setRefreshKey] = useState(0);

  // Get current metrics
  const metrics = useMemo(() => telemetry.getMetrics(), [telemetry]);

  // Force re-render to update metrics
  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  // Reset all metrics
  const handleReset = useCallback(() => {
    telemetry.reset();
    refresh();
  }, [telemetry, refresh]);

  // Export metrics as JSON
  const handleExport = useCallback(() => {
    const json = telemetry.toJSON();
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `telemetry-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [telemetry]);

  // Don't render in production
  if (!isDevMode()) {
    return null;
  }

  return (
    <div
      className="telemetry-viewer"
      style={{
        position: "fixed",
        bottom: 16,
        right: 16,
        width: 320,
        maxHeight: 400,
        overflow: "auto",
        background: "#fff",
        border: "1px solid #ddd",
        borderRadius: 8,
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        zIndex: 9999,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid #eee",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: "14px" }}>
          Telemetry Viewer
        </span>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleExport}
            style={{
              padding: "4px 8px",
              fontSize: "11px",
              cursor: "pointer",
              border: "1px solid #ddd",
              borderRadius: 4,
              background: "#f5f5f5",
            }}
          >
            Export
          </button>
          <button
            onClick={handleReset}
            style={{
              padding: "4px 8px",
              fontSize: "11px",
              cursor: "pointer",
              border: "1px solid #ddd",
              borderRadius: 4,
              background: "#f5f5f5",
            }}
          >
            Reset
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div style={{ padding: "8px" }}>
        {/* Session Creations */}
        <CollapsibleSection title="Session Creations">
          <MetricRow label="Total" value={metrics.sessionCreations.total} />
          <MetricRow
            label="Successful"
            value={metrics.sessionCreations.successful}
          />
          <MetricRow label="Failed" value={metrics.sessionCreations.failed} />
          <MetricRow
            label="Success Rate"
            value={`${(metrics.sessionCreations.successRate * 100).toFixed(1)}%`}
          />
          <MetricRow
            label="Avg Duration"
            value={`${metrics.sessionCreations.avgDurationMs.toFixed(0)}ms`}
          />
          {metrics.sessionCreations.lastError && (
            <MetricRow
              label="Last Error"
              value={metrics.sessionCreations.lastError}
            />
          )}
        </CollapsibleSection>

        {/* Revalidations */}
        <CollapsibleSection title="Revalidations">
          <MetricRow label="Total" value={metrics.revalidations.total} />
          <MetricRow label="Executed" value={metrics.revalidations.executed} />
          <MetricRow
            label="Debounced"
            value={metrics.revalidations.debounced}
          />
          <MetricRow
            label="Avg Duration"
            value={`${metrics.revalidations.avgDurationMs.toFixed(0)}ms`}
          />
          {Object.entries(metrics.revalidations.byTrigger).map(
            ([trigger, count]) => (
              <MetricRow key={trigger} label={`By ${trigger}`} value={count} />
            ),
          )}
        </CollapsibleSection>

        {/* Syncs */}
        <CollapsibleSection title="Syncs">
          <MetricRow label="Total" value={metrics.syncs.total} />
          <MetricRow label="Executed" value={metrics.syncs.executed} />
          <MetricRow label="Skipped" value={metrics.syncs.skipped} />
          <MetricRow
            label="Avg Duration"
            value={`${metrics.syncs.avgDurationMs.toFixed(0)}ms`}
          />
          <MetricRow
            label="Avg Messages"
            value={metrics.syncs.avgMessageCount.toFixed(1)}
          />
        </CollapsibleSection>
      </div>

      {/* Refresh Button */}
      <div
        style={{
          padding: "8px 16px",
          borderTop: "1px solid #eee",
          textAlign: "center",
        }}
      >
        <button
          onClick={refresh}
          style={{
            padding: "6px 16px",
            fontSize: "12px",
            cursor: "pointer",
            border: "1px solid #ddd",
            borderRadius: 4,
            background: "#f5f5f5",
            width: "100%",
          }}
        >
          Refresh Metrics
        </button>
      </div>
    </div>
  );
}
