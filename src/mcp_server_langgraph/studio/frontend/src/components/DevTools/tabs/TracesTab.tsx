/**
 * TracesTab Component
 *
 * OTEL distributed traces waterfall view.
 * Displays trace list with filtering and detailed span visualization.
 *
 * Uses shared OTEL components:
 * - OTELStatusBadge for span status indicators
 * - OTELDetailsPanel for expanded attributes
 * - HumanTimestamp for relative time display
 * - useLGTMIntegration for Grafana/Tempo links
 *
 * Design System Compliance:
 * - Uses CVA for toolbar button variants
 * - Uses Motion.dev for button press feedback and dropdown animations
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import { useState, useMemo, useCallback } from "react";
import {
  Search,
  Filter,
  ExternalLink,
  ChevronRight,
  Clock,
  X,
} from "lucide-react";

import { motion, useReducedMotion, AnimatePresence } from "motion/react";
import { cva } from "class-variance-authority";
import { buttonVariants as motionButtonVariants, dropdownVariants } from "@/design-system/micro-interactions";
import { cn } from "../../../utils/cn";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { getIndentClass } from '@/utils/indent';
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";

// Shared OTEL components
import { HumanTimestamp, OTELStatusBadge, OTELDetailsPanel } from "../components";
import { useLGTMIntegration } from "../hooks/useLGTMIntegration";

import { Button, Input } from "@/components/UI";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Filter dropdown trigger button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const traceFilterButtonVariants = cva(
  "flex px-2 py-1.5 text-sm border rounded transition-colors",
  {
    variants: {
      open: {
        true: "bg-primary-2 border-primary-7 text-primary-11",
        false: "bg-neutral-1 border-neutral-5 hover:bg-neutral-2 text-neutral-11",
      },
    },
    defaultVariants: {
      open: false,
    },
  },
);

/**
 * Filter dropdown option button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const traceFilterOptionVariants = cva(
  "block w-full px-3 py-1.5 text-left text-sm transition-colors",
  {
    variants: {
      selected: {
        true: "bg-primary-3 text-primary-11",
        false: "hover:bg-neutral-2 text-neutral-11",
      },
    },
    defaultVariants: {
      selected: false,
    },
  },
);

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

/**
 * Get background color for span bar based on status.
 * Uses semantic colors from design system.
 */
function getStatusColor(status: "ok" | "error" | "unset"): string {
  switch (status) {
    case "ok":
      return "bg-success-9";
    case "error":
      return "bg-error-9";
    default:
      return "bg-neutral-4";
  }
}

/**
 * Get background color for duration bar based on relative duration.
 * Uses semantic colors: error for slow, warning for medium, primary for fast.
 */
function getDurationColor(durationMs: number, totalMs: number): string {
  const ratio = durationMs / totalMs;
  if (ratio > 0.5) return "bg-error-9";
  if (ratio > 0.25) return "bg-warning-9";
  return "bg-primary-9";
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
        "flex items-center gap-2 py-1 px-2 hover:bg-neutral-2 cursor-pointer border-b border-neutral-5",
        isSelected && "bg-primary-1 dark:bg-primary-a3",
      )}
      onClick={onClick}
      data-span-id={span.spanId}
    >
      {/* Span name with depth indentation */}
      <div
        className={cn(
          "flex items-center gap-1 min-w-[200px] max-w-[300px] truncate text-sm",
          getIndentClass(span.depth * 16),
        )}
      >
        <OTELStatusBadge type="span-status" value={span.status} size="sm" />
        <span className="truncate">{span.name}</span>
      </div>

      {/* Service name */}
      <div className="text-xs text-neutral-10 min-w-28 truncate">
        {span.serviceName || "-"}
      </div>

      {/* Duration */}
      <div className="text-xs text-neutral-10 min-w-[60px]">
        {formatDuration(span.durationMs)}
      </div>

      {/* Timing bar with status-based coloring */}
      <div className="flex-1 relative h-4 bg-neutral-2 rounded">
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
  const hasAttributes = Object.keys(span.attributes).length > 0;

  return (
    <div
      data-testid="span-details"
      className="border-t border-neutral-5 p-4 bg-neutral-1"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">{span.name}</h3>
        <Button size="icon"
          variant="secondary"
          className="p-1 hover:bg-neutral-3 rounded"
          type="button"
          onClick={onClose}
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-neutral-10">Span ID</dt>
        <dd className="font-mono text-xs">{span.spanId}</dd>

        <dt className="text-neutral-10">Service</dt>
        <dd>{span.serviceName || "-"}</dd>

        <dt className="text-neutral-10">Duration</dt>
        <dd>{formatDuration(span.durationMs)}</dd>

        <dt className="text-neutral-10">Status</dt>
        <dd className="flex items-center gap-1">
          <OTELStatusBadge type="span-status" value={span.status} size="sm" />
        </dd>

        {span.errorMessage && (
          <>
            <dt className="text-neutral-10">Error</dt>
            <dd className={STATUS_TEXT_COLORS.error}>{span.errorMessage}</dd>
          </>
        )}
      </dl>
      {hasAttributes && (
        <div className="mt-4">
          <OTELDetailsPanel
            data={span.attributes}
            title="Attributes"
          />
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
  isLoading = false,
  error,
  onTraceSelect,
  onSpanSelect,
  className,
}: TracesTabProps): React.ReactElement {
  const prefersReducedMotion = useReducedMotion();
  const timeline = useTimelineContext();
  const lgtm = useLGTMIntegration();
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
    if (traceId) {
      const url = lgtm.getTraceUrl(traceId);
      if (url) {
        window.open(url, "_blank");
      }
    }
  }, [lgtm, selectedTraceId, localSelectedTraceId]);

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
        <div className="text-neutral-10">
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
        <div className={STATUS_TEXT_COLORS.error}>{error}</div>
      </div>
    );
  }

  return (
    <div
      data-testid="traces-tab"
      className={cn("flex flex-col h-full overflow-hidden", className)}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 p-2 border-b border-neutral-5">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-9"
            aria-hidden="true"
          />
          <Input
            className="h-8 pl-8 pr-2 py-1.5 text-sm"
            placeholder="Search traces..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            aria-label="Search traces"
          />
        </div>

        {/* Service filter */}
        <div className="relative">
          <motion.button
            type="button"
            onClick={() => setShowServiceMenu(!showServiceMenu)}
            className={traceFilterButtonVariants({ open: showServiceMenu })}
            aria-label="Service filter"
            aria-expanded={showServiceMenu}
            aria-haspopup="listbox"
            variants={prefersReducedMotion ? undefined : motionButtonVariants}
            initial="rest"
            whileHover="hover"
            whileTap="pressed"
          >
            <Filter className="h-4 w-4 mr-1" />
            Service: {serviceFilter === "all" ? "All" : serviceFilter}
          </motion.button>
          <AnimatePresence>
            {showServiceMenu && (
              <motion.div
                className="absolute top-full left-0 mt-1 bg-neutral-1 border border-neutral-5 rounded shadow-lg z-dropdown min-w-32 overflow-hidden"
                role="listbox"
                aria-label="Service options"
                variants={prefersReducedMotion ? undefined : dropdownVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
              >
                <motion.button
                  type="button"
                  role="option"
                  aria-selected={serviceFilter === "all"}
                  className={traceFilterOptionVariants({ selected: serviceFilter === "all" })}
                  onClick={() => {
                    setServiceFilter("all");
                    setShowServiceMenu(false);
                  }}
                  variants={prefersReducedMotion ? undefined : motionButtonVariants}
                  initial="rest"
                  whileHover="hover"
                  whileTap="pressed"
                >
                  All
                </motion.button>
                {services.map((service) => (
                  <motion.button
                    key={service}
                    type="button"
                    role="option"
                    aria-selected={serviceFilter === service}
                    className={traceFilterOptionVariants({ selected: serviceFilter === service })}
                    onClick={() => {
                      setServiceFilter(service);
                      setShowServiceMenu(false);
                    }}
                    variants={prefersReducedMotion ? undefined : motionButtonVariants}
                    initial="rest"
                    whileHover="hover"
                    whileTap="pressed"
                  >
                    {service}
                  </motion.button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Status filter */}
        <div className="relative">
          <motion.button
            type="button"
            onClick={() => setShowStatusMenu(!showStatusMenu)}
            className={traceFilterButtonVariants({ open: showStatusMenu })}
            aria-label="Status filter"
            aria-expanded={showStatusMenu}
            aria-haspopup="listbox"
            variants={prefersReducedMotion ? undefined : motionButtonVariants}
            initial="rest"
            whileHover="hover"
            whileTap="pressed"
          >
            Status: {statusFilter === "all" ? "All" : statusFilter === "ok" ? "OK" : "Error"}
          </motion.button>
          <AnimatePresence>
            {showStatusMenu && (
              <motion.div
                className="absolute top-full left-0 mt-1 bg-neutral-1 border border-neutral-5 rounded shadow-lg z-dropdown min-w-28 overflow-hidden"
                role="listbox"
                aria-label="Status options"
                variants={prefersReducedMotion ? undefined : dropdownVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
              >
                <motion.button
                  type="button"
                  role="option"
                  aria-selected={statusFilter === "all"}
                  className={traceFilterOptionVariants({ selected: statusFilter === "all" })}
                  onClick={() => {
                    setStatusFilter("all");
                    setShowStatusMenu(false);
                  }}
                  variants={prefersReducedMotion ? undefined : motionButtonVariants}
                  initial="rest"
                  whileHover="hover"
                  whileTap="pressed"
                >
                  All
                </motion.button>
                <motion.button
                  type="button"
                  role="option"
                  aria-selected={statusFilter === "ok"}
                  className={traceFilterOptionVariants({ selected: statusFilter === "ok" })}
                  onClick={() => {
                    setStatusFilter("ok");
                    setShowStatusMenu(false);
                  }}
                  variants={prefersReducedMotion ? undefined : motionButtonVariants}
                  initial="rest"
                  whileHover="hover"
                  whileTap="pressed"
                >
                  OK
                </motion.button>
                <motion.button
                  type="button"
                  role="option"
                  aria-selected={statusFilter === "error"}
                  className={traceFilterOptionVariants({ selected: statusFilter === "error" })}
                  onClick={() => {
                    setStatusFilter("error");
                    setShowStatusMenu(false);
                  }}
                  variants={prefersReducedMotion ? undefined : motionButtonVariants}
                  initial="rest"
                  whileHover="hover"
                  whileTap="pressed"
                >
                  Error
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Grafana/Tempo link */}
        {lgtm.canOpenInTempo && (selectedTraceId ?? localSelectedTraceId) && (
          <Button
            variant="secondary"
            size="sm"
            className="flex px-2 py-1.5 text-sm border rounded bg-neutral-1 border-neutral-5 hover:bg-neutral-1 ml-auto"
            type="button"
            onClick={handleOpenGrafana}
            aria-label="View in Tempo"
          >
            <ExternalLink className="h-4 w-4" />
            View in Tempo
          </Button>
        )}
      </div>
      {/* Main content */}
      <div className="flex-1 overflow-auto">
        {/* Trace list or waterfall */}
        {(selectedTraceId ?? localSelectedTraceId) ? (
          <div className="flex flex-col h-full">
            {/* Selected trace header */}
            <div className="flex items-center gap-2 p-2 bg-neutral-1 border-b border-neutral-5">
              <Button size="icon"
                variant="secondary"
                className="p-1 hover:bg-neutral-3 rounded"
                type="button"
                onClick={handleClearTrace}
                aria-label="Back to list"
              >
                <ChevronRight className="h-4 w-4 rotate-180" />
              </Button>
              <span className="font-medium">{selectedTrace?.name}</span>
              <span className="text-xs text-neutral-10">
                {selectedTrace?.traceId.slice(0, 8)}...
              </span>
              <span className="text-xs text-neutral-10">
                {formatDuration(selectedTrace?.durationMs ?? 0)}
              </span>
              <span className="text-xs text-neutral-10">
                {selectedTrace?.spanCount} spans
              </span>
            </div>

            {/* Waterfall view */}
            <div data-testid="trace-waterfall" className="flex-1 overflow-auto">
              {/* Timeline header */}
              <div className="sticky top-0 z-10 flex items-center gap-2 py-1 px-2 text-xs text-neutral-10 border-b border-neutral-5 bg-neutral-1">
                <div className="min-w-[200px] max-w-[300px]">Span</div>
                <div className="min-w-28">Service</div>
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
              <div className="flex flex-col items-center justify-center min-h-full text-center text-neutral-10 p-8">
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
                    "flex items-center gap-4 p-3 border-b border-neutral-5 hover:bg-neutral-a6 cursor-pointer",
                    trace.status === "error" &&
                      "bg-error-1 dark:bg-error-a2",
                  )}
                  onClick={() => handleTraceSelect(trace.traceId)}
                >
                  <OTELStatusBadge type="span-status" value={trace.status} size="sm" />

                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{trace.name}</div>
                    <div className="text-xs text-neutral-10">
                      {trace.traceId.slice(0, 16)}...
                      {trace.serviceName && ` • ${trace.serviceName}`}
                    </div>
                  </div>

                  <HumanTimestamp timestamp={trace.startTime} format="relative" />

                  <div className="text-sm text-neutral-10">
                    {formatDuration(trace.durationMs)}
                  </div>

                  <div className="text-xs text-neutral-9">
                    {trace.spanCount} spans
                  </div>

                  <ChevronRight className="h-4 w-4 text-neutral-9" />
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
