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

import { Button } from "@/components/UI";

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
    <div className="border-b border-neutral-3 last:border-b-0">
      <button
        type="button"
        className="flex items-center w-full p-2 bg-transparent border-none cursor-pointer font-semibold text-sm text-neutral-12 hover:bg-neutral-2 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="mr-2">{isOpen ? "▼" : "▶"}</span>
        {title}
      </button>
      {isOpen && <div className="py-2 px-2 pl-6">{children}</div>}
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
    <div className="flex justify-between py-1 text-xs">
      <span className="text-neutral-10">{label}</span>
      <span className="font-medium text-neutral-12">{value}</span>
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
    <div className="fixed bottom-4 right-4 w-80 max-h-[400px] overflow-auto bg-neutral-1 border border-neutral-5 rounded-lg shadow-lg z-dropdown font-sans">
      {/* Header */}
      <div className="p-3 border-b border-neutral-3 flex justify-between items-center">
        <span className="font-semibold text-sm text-neutral-12">
          Telemetry Viewer
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            Export
          </Button>
          <Button variant="outline" size="sm" onClick={handleReset}>
            Reset
          </Button>
        </div>
      </div>
      {/* Metrics */}
      <div className="p-2">
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
      <div className="p-3 border-t border-neutral-3 text-center">
        <Button variant="outline" size="sm" className="w-full" onClick={refresh}>
          Refresh Metrics
        </Button>
      </div>
    </div>
  );
}
