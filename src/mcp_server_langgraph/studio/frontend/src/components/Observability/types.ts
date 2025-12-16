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
  span_id: string;
  /** Human-readable span name */
  name: string;
  /** Start time in milliseconds since epoch */
  start_time: number;
  /** Duration in milliseconds */
  duration_ms: number;
  /** Span status */
  status: "ok" | "error" | "unset";
  /** Depth in the span hierarchy (0 = root) */
  depth: number;
  /** Span attributes (key-value pairs) */
  attributes: Record<string, unknown>;
  /** Span events */
  events: SpanEvent[];
  /** Error message if status is error */
  error_message?: string;
  /** Parent span ID (if not root) */
  parent_span_id?: string;
}

/**
 * Complete trace containing multiple spans
 */
export interface Trace {
  /** Unique trace identifier */
  trace_id: string;
  /** All spans in this trace */
  spans: Span[];
  /** Trace start time in milliseconds since epoch */
  start_time: number;
  /** Trace end time in milliseconds since epoch */
  end_time: number;
  /** Total trace duration in milliseconds */
  duration_ms: number;
  /** Service name */
  service_name?: string;
}
