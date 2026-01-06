/**
 * Observability Types
 *
 * Type definitions for trace and span data structures.
 */

/**
 * Span event within a trace span
 */
export interface SpanEvent {
  name: string;
  timestamp: number;
  attributes?: Record<string, unknown>;
}

/**
 * Individual span in a trace
 */
export interface Span {
  /** Unique span identifier */
  spanId: string;
  /** Human-readable span name */
  name: string;
  /** Start time in milliseconds since epoch */
  startTime: number;
  /** Duration in milliseconds */
  durationMs: number;
  /** Span status */
  status: "ok" | "error" | "unset";
  /** Depth in the span hierarchy (0 = root) */
  depth: number;
  /** Span attributes (key-value pairs) */
  attributes: Record<string, unknown>;
  /** Span events */
  events: SpanEvent[];
  /** Error message if status is error */
  errorMessage?: string;
  /** Parent span ID (if not root) */
  parentSpanId?: string;
}

/**
 * Complete trace containing multiple spans
 */
export interface Trace {
  /** Unique trace identifier */
  traceId: string;
  /** All spans in this trace */
  spans: Span[];
  /** Trace start time in milliseconds since epoch */
  startTime: number;
  /** Trace end time in milliseconds since epoch */
  endTime: number;
  /** Total trace duration in milliseconds */
  durationMs: number;
  /** Service name */
  serviceName?: string;
}
