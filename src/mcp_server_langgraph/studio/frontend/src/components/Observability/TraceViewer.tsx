/**
 * TraceViewer Component
 *
 * Visualizes distributed traces with span timelines and details.
 * Used for debugging LLM workflows and API calls.
 */

import { useState, useMemo } from "react";
import { ExternalLink, Search, Loader2 } from "lucide-react";
import type { Trace, Span } from "./types";

import { Button, Input } from "@/components/UI";

export interface TraceViewerProps {
  /** Trace data to display */
  trace: Trace | null;
  /** Whether trace data is loading */
  isLoading?: boolean;
  /** Optional URL to view trace in Grafana */
  grafanaUrl?: string;
}

/**
 * TraceViewer component for visualizing distributed traces.
 *
 * @example
 * ```tsx
 * <TraceViewer
 *   trace={traceData}
 *   grafanaUrl={`https://grafana.example.com/explore?traceId=${traceId}`}
 * />
 * ```
 */
export function TraceViewer({
  trace,
  isLoading = false,
  grafanaUrl,
}: TraceViewerProps) {
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Filter spans based on search query
  const filteredSpans = useMemo(() => {
    if (!trace) return [];
    if (!searchQuery.trim()) return trace.spans;

    return trace.spans.filter((span) =>
      span.name.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [trace, searchQuery]);

  // Calculate timeline scale
  const timelineScale = useMemo(() => {
    if (!trace || trace.durationMs === 0) return 1;
    return 100 / trace.durationMs; // percentage per millisecond
  }, [trace]);

  if (isLoading) {
    return (
      <div
        data-testid="trace-loading"
        className="flex items-center justify-center h-64"
      >
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="flex items-center justify-center h-64 text-neutral-500 dark:text-neutral-400">
        No trace data available
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
            Trace: {trace.traceId}
          </h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Total Duration: {trace.durationMs}ms | {trace.spans.length} spans
          </p>
        </div>

        <div className="flex items-center gap-4">
          {grafanaUrl && (
            <a
              href={grafanaUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 text-sm text-primary-600 hover:text-primary-800 dark:text-primary-400"
              aria-label="View in Grafana"
            >
              <ExternalLink className="w-4 h-4" />
              View in Grafana
            </a>
          )}
        </div>
      </div>
      {/* Search */}
      <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 dark:text-neutral-400" />
          <Input
            className="pl-9 pr-3 py-2 text-neutral-900 dark:text-white text-sm"
            placeholder="Search spans..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Timeline */}
        <div className="flex-1 overflow-auto p-4">
          {filteredSpans.length === 0 ? (
            <div className="text-center text-neutral-500 dark:text-neutral-400 py-8">
              No spans found matching your search
            </div>
          ) : (
            <ul role="list" className="space-y-1">
              {filteredSpans.map((span) => (
                <SpanRow
                  key={span.spanId}
                  span={span}
                  trace={trace}
                  timelineScale={timelineScale}
                  isSelected={selectedSpan?.spanId === span.spanId}
                  onClick={() => setSelectedSpan(span)}
                />
              ))}
            </ul>
          )}
        </div>

        {/* Details Panel */}
        {selectedSpan && (
          <SpanDetails
            span={selectedSpan}
            onClose={() => setSelectedSpan(null)}
          />
        )}
      </div>
    </div>
  );
}

interface SpanRowProps {
  span: Span;
  trace: Trace;
  timelineScale: number;
  isSelected: boolean;
  onClick: () => void;
}

function SpanRow({
  span,
  trace,
  timelineScale,
  isSelected,
  onClick,
}: SpanRowProps) {
  const barOffset = (span.startTime - trace.startTime) * timelineScale;
  const barWidth = Math.max(span.durationMs * timelineScale, 2);
  const isError = span.status === "error";

  return (
    <li
      role="listitem"
      data-testid={`span-row-${span.spanId}`}
      onClick={onClick}
      className={`flex items-center gap-4 p-2 rounded cursor-pointer transition-colors ${
        isSelected
          ? "bg-primary-50 dark:bg-primary-900/20"
          : "hover:bg-neutral-50 dark:hover:bg-neutral-800"
      } ${span.depth > 0 ? "ml-4" : ""}`}
    >
      {/* Status indicator */}
      <div
        data-testid={`span-status-${span.spanId}`}
        className={`w-2 h-2 rounded-full flex-shrink-0 ${
          isError ? "bg-error-500" : "bg-success-500"
        }`}
      />

      {/* Span name */}
      <div className="flex-shrink-0 w-48 truncate text-sm text-neutral-900 dark:text-white">
        {span.name}
      </div>

      {/* Timeline bar */}
      <div className="flex-1 h-6 bg-neutral-100 dark:bg-neutral-700 rounded relative">
        <div
          data-testid={`span-bar-${span.spanId}`}
          className={`absolute h-full rounded ${
            isError ? "bg-error-400" : "bg-primary-400"
          }`}
          style={{
            left: `${barOffset}%`,
            width: `${barWidth}%`,
          }}
        />
      </div>

      {/* Duration */}
      <div className="flex-shrink-0 w-20 text-right text-sm text-neutral-500 dark:text-neutral-400">
        {span.durationMs}ms
      </div>
    </li>
  );
}

interface SpanDetailsProps {
  span: Span;
  onClose: () => void;
}

function SpanDetails({ span, onClose }: SpanDetailsProps) {
  const isError = span.status === "error";

  return (
    <div
      data-testid="span-details"
      className="w-80 border-l border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 overflow-auto"
    >
      {/* Header */}
      <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-neutral-900 dark:text-white">
            {span.name}
          </h3>
          <Button
            className="text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-200"
            onClick={onClose}
            aria-label="Close details"
          >
            ×
          </Button>
        </div>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          Duration: {span.durationMs}ms
        </p>
      </div>
      {/* Error Message */}
      {isError && span.errorMessage && (
        <div className="p-4 bg-error-50 dark:bg-error-900/20 border-b border-error-100 dark:border-error-800">
          <p className="text-sm font-medium text-error-800 dark:text-error-200">
            Error
          </p>
          <p className="text-sm text-error-600 dark:text-error-300 mt-1">
            {span.errorMessage}
          </p>
        </div>
      )}
      {/* Attributes */}
      <div className="p-4 border-b border-neutral-200 dark:border-neutral-700">
        <h4 className="text-sm font-medium text-neutral-900 dark:text-white mb-2">
          Attributes
        </h4>
        <dl className="space-y-2">
          {Object.entries(span.attributes).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <dt className="text-neutral-500 dark:text-neutral-400">{key}</dt>
              <dd className="text-neutral-900 dark:text-white font-mono">
                {String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
      {/* Events */}
      {span.events.length > 0 && (
        <div className="p-4">
          <h4 className="text-sm font-medium text-neutral-900 dark:text-white mb-2">
            Events
          </h4>
          <ul className="space-y-2">
            {span.events.map((event, index) => (
              <li key={index} className="text-sm">
                <span className="text-neutral-900 dark:text-white">
                  {event.name}
                </span>
                <span className="text-neutral-500 dark:text-neutral-400 ml-2 text-xs">
                  {new Date(event.timestamp).toISOString()}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default TraceViewer;
