/**
 * TraceViewer Component
 *
 * Visualizes distributed traces with span timelines and details.
 * Used for debugging LLM workflows and API calls.
 */

import { useState, useMemo } from "react";
import { ExternalLink, Search, Loader2 } from "lucide-react";
import type { Trace, Span } from "./types";

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
    if (!trace || trace.duration_ms === 0) return 1;
    return 100 / trace.duration_ms; // percentage per millisecond
  }, [trace]);

  if (isLoading) {
    return (
      <div
        data-testid="trace-loading"
        className="flex items-center justify-center h-64"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        No trace data available
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Trace: {trace.trace_id}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Total Duration: {trace.duration_ms}ms | {trace.spans.length} spans
          </p>
        </div>

        <div className="flex items-center gap-4">
          {grafanaUrl && (
            <a
              href={grafanaUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
              aria-label="View in Grafana"
            >
              <ExternalLink className="w-4 h-4" />
              View in Grafana
            </a>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search spans..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          />
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Timeline */}
        <div className="flex-1 overflow-auto p-4">
          {filteredSpans.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 py-8">
              No spans found matching your search
            </div>
          ) : (
            <ul role="list" className="space-y-1">
              {filteredSpans.map((span) => (
                <SpanRow
                  key={span.span_id}
                  span={span}
                  trace={trace}
                  timelineScale={timelineScale}
                  isSelected={selectedSpan?.span_id === span.span_id}
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
  const barOffset = (span.start_time - trace.start_time) * timelineScale;
  const barWidth = Math.max(span.duration_ms * timelineScale, 2);
  const isError = span.status === "error";

  return (
    <li
      role="listitem"
      data-testid={`span-row-${span.span_id}`}
      onClick={onClick}
      className={`flex items-center gap-4 p-2 rounded cursor-pointer transition-colors ${
        isSelected
          ? "bg-blue-50 dark:bg-blue-900/20"
          : "hover:bg-gray-50 dark:hover:bg-gray-800"
      } ${span.depth > 0 ? "ml-4" : ""}`}
    >
      {/* Status indicator */}
      <div
        data-testid={`span-status-${span.span_id}`}
        className={`w-2 h-2 rounded-full flex-shrink-0 ${
          isError ? "bg-red-500" : "bg-green-500"
        }`}
      />

      {/* Span name */}
      <div className="flex-shrink-0 w-48 truncate text-sm text-gray-900 dark:text-white">
        {span.name}
      </div>

      {/* Timeline bar */}
      <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-700 rounded relative">
        <div
          data-testid={`span-bar-${span.span_id}`}
          className={`absolute h-full rounded ${
            isError ? "bg-red-400" : "bg-blue-400"
          }`}
          style={{
            left: `${barOffset}%`,
            width: `${barWidth}%`,
          }}
        />
      </div>

      {/* Duration */}
      <div className="flex-shrink-0 w-20 text-right text-sm text-gray-500 dark:text-gray-400">
        {span.duration_ms}ms
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
      className="w-80 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-auto"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {span.name}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            aria-label="Close details"
          >
            ×
          </button>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Duration: {span.duration_ms}ms
        </p>
      </div>

      {/* Error Message */}
      {isError && span.error_message && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border-b border-red-100 dark:border-red-800">
          <p className="text-sm font-medium text-red-800 dark:text-red-200">
            Error
          </p>
          <p className="text-sm text-red-600 dark:text-red-300 mt-1">
            {span.error_message}
          </p>
        </div>
      )}

      {/* Attributes */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
          Attributes
        </h4>
        <dl className="space-y-2">
          {Object.entries(span.attributes).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <dt className="text-gray-500 dark:text-gray-400">{key}</dt>
              <dd className="text-gray-900 dark:text-white font-mono">
                {String(value)}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Events */}
      {span.events.length > 0 && (
        <div className="p-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Events
          </h4>
          <ul className="space-y-2">
            {span.events.map((event, index) => (
              <li key={index} className="text-sm">
                <span className="text-gray-900 dark:text-white">
                  {event.name}
                </span>
                <span className="text-gray-500 dark:text-gray-400 ml-2 text-xs">
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
