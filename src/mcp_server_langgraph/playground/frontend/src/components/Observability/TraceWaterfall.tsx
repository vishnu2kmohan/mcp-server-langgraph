/**
 * TraceWaterfall Component
 *
 * Displays spans in a Gantt-chart style waterfall visualization.
 */

import React from 'react';
import clsx from 'clsx';
import type { SpanInfo } from '../../api/types';

export interface TraceWaterfallProps {
  spans: SpanInfo[];
  totalDuration: number;
}

function getSpanColor(operationName: string, status: string): string {
  if (status === 'ERROR') return 'bg-error-500';
  if (operationName.includes('llm') || operationName.includes('LLM')) return 'bg-primary-500';
  if (operationName.includes('tool')) return 'bg-success-500';
  if (operationName.includes('agent')) return 'bg-warning-500';
  return 'bg-gray-400';
}

function getSpanOffset(span: SpanInfo, traceStart: Date, totalDuration: number): number {
  if (totalDuration === 0) return 0;
  const spanStart = new Date(span.startTime);
  const offsetMs = spanStart.getTime() - traceStart.getTime();
  return (offsetMs / totalDuration) * 100;
}

function getSpanWidth(span: SpanInfo, totalDuration: number): number {
  if (totalDuration === 0) return 0;
  const duration = span.durationMs || 0;
  return Math.max((duration / totalDuration) * 100, 1); // Minimum 1%
}

export function TraceWaterfall({
  spans,
  totalDuration,
}: TraceWaterfallProps): React.ReactElement {
  if (spans.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        No spans to display
      </div>
    );
  }

  const traceStart = new Date(
    Math.min(...spans.map((s) => new Date(s.startTime).getTime()))
  );

  return (
    <div className="space-y-1 p-2">
      {spans.map((span) => {
        const offset = getSpanOffset(span, traceStart, totalDuration);
        const width = getSpanWidth(span, totalDuration);
        const depth = span.parentSpanId ? 1 : 0;

        return (
          <div
            key={span.spanId}
            className="flex items-center gap-2"
            style={{ paddingLeft: `${depth * 16}px` }}
          >
            {/* Span Info */}
            <div className="w-32 flex-shrink-0">
              <div className="text-sm font-medium text-gray-900 dark:text-dark-text truncate">
                {span.operationName}
              </div>
              <div className="text-xs text-gray-500 dark:text-dark-textMuted">
                {span.durationMs}ms
              </div>
            </div>

            {/* Waterfall Bar */}
            <div className="flex-1 h-6 bg-gray-100 dark:bg-dark-surface rounded relative">
              <div
                className={clsx(
                  'absolute h-full rounded',
                  getSpanColor(span.operationName, span.status)
                )}
                style={{
                  left: `${offset}%`,
                  width: `${width}%`,
                }}
                data-testid="span-bar"
                title={`${span.operationName}: ${span.durationMs}ms`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
