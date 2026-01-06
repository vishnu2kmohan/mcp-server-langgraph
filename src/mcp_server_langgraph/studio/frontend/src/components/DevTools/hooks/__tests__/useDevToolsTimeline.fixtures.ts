/**
 * useDevToolsTimeline Test Fixtures
 *
 * Shared utilities and fixtures for useDevToolsTimeline test shards.
 */

import type { TimelineEvent, TimelineEventType } from "../useDevToolsTimeline";

// =============================================================================
// EVENT FACTORIES
// =============================================================================

export function createEvent(
  type: TimelineEventType,
  timestamp: number,
  data: Record<string, unknown> = {},
): TimelineEvent {
  return {
    id: `${type}-${timestamp}`,
    type,
    timestamp,
    relativeTime: timestamp,
    source: type,
    data,
  };
}

// =============================================================================
// OTEL TRACE/SPAN ID GENERATORS
// =============================================================================

export function generateTraceId(): string {
  return Array.from({ length: 32 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join("");
}

export function generateSpanId(): string {
  return Array.from({ length: 16 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join("");
}

// Re-export types
export type { TimelineEvent, TimelineEventType };
