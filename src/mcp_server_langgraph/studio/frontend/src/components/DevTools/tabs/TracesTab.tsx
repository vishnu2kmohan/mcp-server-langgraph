/**
 * TracesTab Component
 *
 * OTEL distributed traces waterfall view.
 * Displays trace list with filtering and detailed span visualization.
 */
import { useState, useMemo, useCallback } from "react";
import {
  Search,
  Filter,
  ExternalLink,
  ChevronRight,
  Clock,
  AlertCircle,
  CheckCircle,
  Circle,
  X,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";

// =============================================================================
// Types
// =============================================================================

export interface TraceListItem {
  traceId: string;
  name: string;
  startTime: number;
  durationMs: number;
  spanCount: number;
  serviceName?: string;
  status: "ok" | "error" | "unset";
}

export interface TraceSpan {
  spanId: string;
  traceId: string;
  parentSpanId: string | null;
  name: string;
  startTime: number;
  durationMs: number;
  status: "ok" | "error" | "unset";
  serviceName?: string;
  depth: number;
  attributes: Record<string, unknown>;
  errorMessage?: string;
}

export interface TracesTabProps {
  /** Trace list data */
  traces?: TraceListItem[];
  /** Span data for waterfall */
  spans?: TraceSpan[];
  /** Currently selected trace ID */
  selectedTraceId?: string;
  /** Grafana URL for deep linking */
  grafanaUrl?: string;
  /** Loading state */
  isLoading?: boolean;
  /** Error message */
  error?: string;
  /** Callback when trace selected */
  onTraceSelect?: (traceId: string | null) => void;
  /** Callback when span selected */
  onSpanSelect?: (spanId: string | null) => void;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatDuration(ms: number): string {
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function getStatusIcon(status: "ok" | "error" | "unset") {
  switch (status) {
    case "ok":
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "error":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Circle className="h-4 w-4 text-gray-400" />;
  }
}

/**
 * Get background color for span bar based on status.
 * Used in waterfall view to visually indicate span status.
 */
function getStatusColor(status: "ok" | "error" | "unset"): string {
  switch (status) {
    case "ok":
      return "bg-green-500";
    case "error":
      return "bg-red-500";
    default:
      return "bg-gray-400";
  }
}

function getDurationColor(durationMs: number, totalMs: number): string {
  const ratio = durationMs / totalMs;
  if (ratio > 0.5) return "bg-red-500";
  if (ratio > 0.25) return "bg-yellow-500";
  return "bg-blue-500";
}

// =============================================================================
// Sub-Components
// =============================================================================

interface SpanRowProps {
  span: TraceSpan;
  totalDuration: number;
  traceStartTime: number;
  isSelected: boolean;
  onClick: () => void;
}

function SpanRow({
  span,
  totalDuration,
  traceStartTime,
  isSelected,
  onClick,
}: SpanRowProps) {
  const leftOffset =
    totalDuration > 0
      ? ((span.startTime - traceStartTime) / totalDuration) * 100
      : 0;
  const width = totalDuration > 0 ? (span.durationMs / totalDuration) * 100 : 0;

  return (
    <div
      className={cn(
        "flex items-center gap-2 py-1 px-2 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer border-b border-gray-100 dark:border-gray-800",
        isSelected && "bg-blue-50 dark:bg-blue-900/20",
      )}
      onClick={onClick}
      data-span-id={span.spanId}
    >
      {/* Span name with depth indentation */}
      <div
        className="flex items-center gap-1 min-w-[200px] max-w-[300px] truncate text-sm"
        style={{ paddingLeft: `${span.depth * 16}px` }}
      >
        {getStatusIcon(span.status)}
        <span className="truncate">{span.name}</span>
      </div>

      {/* Service name */}
      <div className="text-xs text-gray-500 dark:text-gray-400 min-w-[100px] truncate">
        {span.serviceName || "-"}
      </div>

      {/* Duration */}
      <div className="text-xs text-gray-500 dark:text-gray-400 min-w-[60px]">
        {formatDuration(span.durationMs)}
      </div>

      {/* Timing bar with status-based coloring */}
      <div className="flex-1 relative h-4 bg-gray-100 dark:bg-gray-800 rounded">
        <div
          data-testid="span-timing-bar"
          data-status={span.status}
          className={cn(
            "absolute h-full rounded",
            // Use status color for error spans, duration color otherwise
            span.status === "error"
              ? getStatusColor(span.status)
              : getDurationColor(span.durationMs, totalDuration),
          )}
          style={{
            left: `${Math.max(0, leftOffset)}%`,
            width: `${Math.max(1, width)}%`,
          }}
        />
      </div>
    </div>
  );
}

interface SpanDetailsProps {
  span: TraceSpan;
  onClose: () => void;
}

function SpanDetails({ span, onClose }: SpanDetailsProps) {
  return (
    <div
      data-testid="span-details"
      className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">{span.name}</h3>
        <button
          type="button"
          onClick={onClose}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-gray-500 dark:text-gray-400">Span ID</dt>
        <dd className="font-mono text-xs">{span.spanId}</dd>

        <dt className="text-gray-500 dark:text-gray-400">Service</dt>
        <dd>{span.serviceName || "-"}</dd>

        <dt className="text-gray-500 dark:text-gray-400">Duration</dt>
        <dd>{formatDuration(span.durationMs)}</dd>

        <dt className="text-gray-500 dark:text-gray-400">Status</dt>
        <dd className="flex items-center gap-1">
          {getStatusIcon(span.status)}
          {span.status}
        </dd>

        {span.errorMessage && (
          <>
            <dt className="text-gray-500 dark:text-gray-400">Error</dt>
            <dd className="text-red-500">{span.errorMessage}</dd>
          </>
        )}
      </dl>

      {Object.keys(span.attributes).length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium mb-2">Attributes</h4>
          <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded overflow-auto max-h-40">
            {JSON.stringify(span.attributes, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function TracesTab({
  traces = [],
  spans = [],
  selectedTraceId,
  grafanaUrl,
  isLoading = false,
  error,
  onTraceSelect,
  onSpanSelect,
  className,
}: TracesTabProps): React.ReactElement {
  const timeline = useTimelineContext();
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "ok" | "error">(
    "all",
  );
  const [serviceFilter, setServiceFilter] = useState<string>("all");
  const [localSelectedTraceId, setLocalSelectedTraceId] = useState<
    string | null
  >(selectedTraceId ?? null);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const [showStatusMenu, setShowStatusMenu] = useState(false);
  const [showServiceMenu, setShowServiceMenu] = useState(false);

  // Filter traces based on timeline time window
  const filteredByTimeline = useMemo(() => {
    if (!timeline.timeWindow) return traces;

    return traces.filter((trace) => {
      const traceEnd = trace.startTime + trace.durationMs;
      return (
        trace.startTime <= timeline.timeWindow!.end &&
        traceEnd >= timeline.timeWindow!.start
      );
    });
  }, [traces, timeline.timeWindow]);

  // Apply search and status filters
  const filteredTraces = useMemo(() => {
    return filteredByTimeline.filter((trace) => {
      // Search filter
      if (searchTerm) {
        const lowerSearch = searchTerm.toLowerCase();
        if (
          !trace.name.toLowerCase().includes(lowerSearch) &&
          !trace.traceId.toLowerCase().includes(lowerSearch) &&
          !trace.serviceName?.toLowerCase().includes(lowerSearch)
        ) {
          return false;
        }
      }

      // Status filter
      if (statusFilter !== "all" && trace.status !== statusFilter) {
        return false;
      }

      // Service filter
      if (serviceFilter !== "all" && trace.serviceName !== serviceFilter) {
        return false;
      }

      return true;
    });
  }, [filteredByTimeline, searchTerm, statusFilter, serviceFilter]);

  // Get unique services for filter
  const services = useMemo(() => {
    const uniqueServices = new Set(
      traces.map((t) => t.serviceName).filter(Boolean),
    );
    return Array.from(uniqueServices) as string[];
  }, [traces]);

  // Get spans for selected trace
  const selectedTraceSpans = useMemo(() => {
    const traceId = selectedTraceId ?? localSelectedTraceId;
    if (!traceId) return [];
    return spans
      .filter((s) => s.traceId === traceId)
      .sort((a, b) => a.startTime - b.startTime);
  }, [spans, selectedTraceId, localSelectedTraceId]);

  // Get selected trace data
  const selectedTrace = useMemo(() => {
    const traceId = selectedTraceId ?? localSelectedTraceId;
    return traces.find((t) => t.traceId === traceId);
  }, [traces, selectedTraceId, localSelectedTraceId]);

  // Get selected span
  const selectedSpan = useMemo(() => {
    if (!selectedSpanId) return null;
    return spans.find((s) => s.spanId === selectedSpanId) ?? null;
  }, [spans, selectedSpanId]);

  // Handlers
  const handleTraceSelect = useCallback(
    (traceId: string) => {
      setLocalSelectedTraceId(traceId);
      setSelectedSpanId(null);
      onTraceSelect?.(traceId);
    },
    [onTraceSelect],
  );

  const handleSpanSelect = useCallback(
    (spanId: string) => {
      setSelectedSpanId(spanId);
      onSpanSelect?.(spanId);
    },
    [onSpanSelect],
  );

  const handleOpenGrafana = useCallback(() => {
    const traceId = selectedTraceId ?? localSelectedTraceId;
    if (grafanaUrl && traceId) {
      window.open(`${grafanaUrl}?traceId=${traceId}`, "_blank");
    }
  }, [grafanaUrl, selectedTraceId, localSelectedTraceId]);

  const handleClearTrace = useCallback(() => {
    setLocalSelectedTraceId(null);
    setSelectedSpanId(null);
    onTraceSelect?.(null);
  }, [onTraceSelect]);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="traces-tab"
        className={cn("flex items-center justify-center h-full", className)}
      >
        <div className="text-gray-500 dark:text-gray-400">
          Loading traces...
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="traces-tab"
        className={cn("flex items-center justify-center h-full", className)}
      >
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div
      data-testid="traces-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 p-2 border-b border-gray-200 dark:border-gray-700">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search traces..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border rounded bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
          />
        </div>

        {/* Service filter */}
        <div className="relative">
          <button
            type="button"
            className="flex items-center gap-1 px-2 py-1.5 text-sm border rounded bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
            onClick={() => setShowServiceMenu(!showServiceMenu)}
            aria-label="Service"
          >
            <Filter className="h-4 w-4" />
            Service: {serviceFilter === "all" ? "All" : serviceFilter}
          </button>
          {showServiceMenu && (
            <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border rounded shadow-lg z-10 min-w-[120px]">
              <button
                type="button"
                role="option"
                className="block w-full px-3 py-1 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => {
                  setServiceFilter("all");
                  setShowServiceMenu(false);
                }}
              >
                All
              </button>
              {services.map((service) => (
                <button
                  key={service}
                  type="button"
                  role="option"
                  className="block w-full px-3 py-1 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => {
                    setServiceFilter(service);
                    setShowServiceMenu(false);
                  }}
                >
                  {service}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Status filter */}
        <div className="relative">
          <button
            type="button"
            className="flex items-center gap-1 px-2 py-1.5 text-sm border rounded bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
            onClick={() => setShowStatusMenu(!showStatusMenu)}
            aria-label="Status"
          >
            Status: {statusFilter}
          </button>
          {showStatusMenu && (
            <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 border rounded shadow-lg z-10 min-w-[100px]">
              <button
                type="button"
                role="option"
                aria-label="All"
                className="block w-full px-3 py-1 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => {
                  setStatusFilter("all");
                  setShowStatusMenu(false);
                }}
              >
                All
              </button>
              <button
                type="button"
                role="option"
                aria-label="ok"
                className="block w-full px-3 py-1 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => {
                  setStatusFilter("ok");
                  setShowStatusMenu(false);
                }}
              >
                OK
              </button>
              <button
                type="button"
                role="option"
                aria-label="error"
                className="block w-full px-3 py-1 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => {
                  setStatusFilter("error");
                  setShowStatusMenu(false);
                }}
              >
                Error
              </button>
            </div>
          )}
        </div>

        {/* Grafana link */}
        {grafanaUrl && (selectedTraceId ?? localSelectedTraceId) && (
          <button
            type="button"
            className="flex items-center gap-1 px-2 py-1.5 text-sm border rounded bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 ml-auto"
            onClick={handleOpenGrafana}
            aria-label="View in Grafana"
          >
            <ExternalLink className="h-4 w-4" />
            View in Grafana
          </button>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        {/* Trace list or waterfall */}
        {(selectedTraceId ?? localSelectedTraceId) ? (
          <div className="flex flex-col h-full">
            {/* Selected trace header */}
            <div className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
              <button
                type="button"
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                onClick={handleClearTrace}
                aria-label="Back to list"
              >
                <ChevronRight className="h-4 w-4 rotate-180" />
              </button>
              <span className="font-medium">{selectedTrace?.name}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {selectedTrace?.traceId.slice(0, 8)}...
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {formatDuration(selectedTrace?.durationMs ?? 0)}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {selectedTrace?.spanCount} spans
              </span>
            </div>

            {/* Waterfall view */}
            <div data-testid="trace-waterfall" className="flex-1 overflow-auto">
              {/* Timeline header */}
              <div className="sticky top-0 z-10 flex items-center gap-2 py-1 px-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <div className="min-w-[200px] max-w-[300px]">Span</div>
                <div className="min-w-[100px]">Service</div>
                <div className="min-w-[60px]">Duration</div>
                <div className="flex-1">Timeline</div>
              </div>

              {/* Span rows */}
              {selectedTraceSpans.map((span) => (
                <SpanRow
                  key={span.spanId}
                  span={span}
                  totalDuration={selectedTrace?.durationMs ?? 1}
                  traceStartTime={selectedTrace?.startTime ?? 0}
                  isSelected={selectedSpanId === span.spanId}
                  onClick={() => handleSpanSelect(span.spanId)}
                />
              ))}
            </div>

            {/* Span details */}
            {selectedSpan && (
              <SpanDetails
                span={selectedSpan}
                onClose={() => setSelectedSpanId(null)}
              />
            )}
          </div>
        ) : (
          // Trace list
          <div>
            {filteredTraces.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-full text-center text-gray-500 dark:text-gray-400 p-8">
                <Clock className="h-12 w-12 mb-4 opacity-50" />
                <p>No traces found</p>
                {searchTerm && (
                  <p className="text-sm mt-2">
                    Try adjusting your search or filters
                  </p>
                )}
              </div>
            ) : (
              filteredTraces.map((trace) => (
                <div
                  key={trace.traceId}
                  data-trace
                  data-status={trace.status}
                  className={cn(
                    "flex items-center gap-4 p-3 border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer",
                    trace.status === "error" && "bg-red-50 dark:bg-red-900/10",
                  )}
                  onClick={() => handleTraceSelect(trace.traceId)}
                >
                  {getStatusIcon(trace.status)}

                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{trace.name}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {trace.traceId.slice(0, 16)}...
                      {trace.serviceName && ` • ${trace.serviceName}`}
                    </div>
                  </div>

                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {formatDuration(trace.durationMs)}
                  </div>

                  <div className="text-xs text-gray-400">
                    {trace.spanCount} spans
                  </div>

                  <ChevronRight className="h-4 w-4 text-gray-400" />
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default TracesTab;
