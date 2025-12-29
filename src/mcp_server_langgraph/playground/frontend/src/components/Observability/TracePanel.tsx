/**
 * TracePanel Component
 *
 * Displays OpenTelemetry traces in a list format.
 */

import React from 'react';
import type { TraceInfo } from '../../api/types';

export interface TracePanelProps {
  traces: TraceInfo[];
  isLoading?: boolean;
  onTraceSelect?: (traceId: string) => void;
}

function formatDuration(ms: number | undefined): string {
  if (ms === undefined) return '--';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString();
}

export function TracePanel({
  traces,
  isLoading = false,
  onTraceSelect,
}: TracePanelProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        <div className="animate-pulse">Loading traces...</div>
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        No traces yet
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200 dark:divide-dark-border">
      {traces.map((trace) => (
        <button
          key={trace.traceId}
          onClick={() => onTraceSelect?.(trace.traceId)}
          className="w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-dark-surfaceHover transition-colors"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-gray-900 dark:text-dark-text truncate">
              {trace.traceId.slice(0, 16)}...
            </span>
            <span className="text-sm text-gray-500 dark:text-dark-textMuted">
              {formatDuration(trace.totalDurationMs)}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-400">{trace.spans.length} spans</span>
            <span className="text-xs text-gray-400">{formatTime(trace.startTime)}</span>
          </div>
        </button>
      ))}
    </div>
  );
}
