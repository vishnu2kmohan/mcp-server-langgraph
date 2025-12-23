/**
 * useDevToolsWebSocketBridge Hook
 *
 * Bridges all WebSocket events to the unified timeline.
 * Converts OTEL spans, alerts, metrics, and logs into timeline events.
 */
import { useCallback, useMemo } from "react";
import type { TimelineEvent, TimelineEventType } from "./useDevToolsTimeline";

// =============================================================================
// Types
// =============================================================================

export interface TraceSpan {
  span_id: string;
  trace_id: string;
  parent_span_id?: string | null;
  name: string;
  start_time: number;
  duration_ms: number;
  status: string;
  service_name: string;
  attributes?: Record<string, unknown>;
}

export interface AlertData {
  id: string;
  name: string;
  state: string;
  severity: string;
  service: string;
  message: string;
  started_at: string;
  resolved_at?: string;
  generator_url?: string;
}

export interface MetricData {
  name: string;
  value: number;
  timestamp?: number;
  labels?: Record<string, string>;
}

export interface LogData {
  id: string;
  timestamp: string;
  level: string;
  service: string;
  message: string;
  trace_id?: string;
  span_id?: string;
  attributes?: Record<string, unknown>;
}

export interface LangGraphNodeData {
  id: string;
  name: string;
  type: string;
  status: string;
  startTime?: number;
  endTime?: number;
  duration?: number;
  output?: string;
}

export interface UseDevToolsWebSocketBridgeOptions {
  /** Whether the bridge is enabled */
  enabled: boolean;
  /** Function to register events with the timeline */
  registerEvent: (event: TimelineEvent) => void;
}

export interface UseDevToolsWebSocketBridgeReturn {
  /** Handle incoming trace span */
  handleTraceSpan: (span: TraceSpan) => void;
  /** Handle incoming alert */
  handleAlert: (alert: AlertData) => void;
  /** Handle incoming metric */
  handleMetric: (metric: MetricData) => void;
  /** Handle incoming log */
  handleLog: (log: LogData) => void;
  /** Handle incoming LangGraph node event */
  handleLangGraphNode: (node: LangGraphNodeData) => void;
}

// =============================================================================
// Mapping Functions
// =============================================================================

let eventCounter = 0;

function generateEventId(): string {
  return `evt-${Date.now()}-${++eventCounter}`;
}

/**
 * Map OTEL trace span to timeline event
 */
export function mapTraceSpanToEvent(span: TraceSpan): TimelineEvent {
  const timestamp = span.start_time;
  return {
    id: generateEventId(),
    type: "otel_span" as TimelineEventType,
    timestamp,
    relativeTime: 0, // Will be calculated by timeline context
    source: span.service_name || "otel",
    data: span as unknown as Record<string, unknown>,
  };
}

/**
 * Map alert to timeline event
 */
export function mapAlertToEvent(alert: AlertData): TimelineEvent {
  const timestamp = new Date(alert.started_at).getTime();

  return {
    id: generateEventId(),
    type: "alert" as TimelineEventType,
    timestamp,
    relativeTime: 0, // Will be calculated by timeline context
    source: alert.service || "alerts",
    data: alert as unknown as Record<string, unknown>,
  };
}

/**
 * Map metric snapshot to timeline event
 */
export function mapMetricToEvent(metric: MetricData): TimelineEvent {
  const timestamp = metric.timestamp ?? Date.now();

  return {
    id: generateEventId(),
    type: "metric" as TimelineEventType,
    timestamp,
    relativeTime: 0, // Will be calculated by timeline context
    source: "metrics",
    data: metric as unknown as Record<string, unknown>,
  };
}

/**
 * Map log entry to timeline event
 */
export function mapLogToEvent(log: LogData): TimelineEvent {
  const timestamp = new Date(log.timestamp).getTime();

  return {
    id: generateEventId(),
    type: "console" as TimelineEventType,
    timestamp,
    relativeTime: 0, // Will be calculated by timeline context
    source: log.service || "logs",
    data: log as unknown as Record<string, unknown>,
  };
}

/**
 * Map LangGraph node to timeline event for time-travel debugging
 */
export function mapLangGraphNodeToEvent(node: LangGraphNodeData): TimelineEvent {
  const timestamp = node.startTime ?? Date.now();

  return {
    id: generateEventId(),
    type: "langgraph_node" as TimelineEventType,
    timestamp,
    relativeTime: 0, // Will be calculated by timeline context
    source: "langgraph",
    data: node as unknown as Record<string, unknown>,
  };
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDevToolsWebSocketBridge(
  options: UseDevToolsWebSocketBridgeOptions,
): UseDevToolsWebSocketBridgeReturn {
  const { enabled, registerEvent } = options;

  /**
   * Handle incoming trace span
   */
  const handleTraceSpan = useCallback(
    (span: TraceSpan) => {
      if (!enabled) return;
      const event = mapTraceSpanToEvent(span);
      registerEvent(event);
    },
    [enabled, registerEvent],
  );

  /**
   * Handle incoming alert
   */
  const handleAlert = useCallback(
    (alert: AlertData) => {
      if (!enabled) return;
      const event = mapAlertToEvent(alert);
      registerEvent(event);
    },
    [enabled, registerEvent],
  );

  /**
   * Handle incoming metric
   */
  const handleMetric = useCallback(
    (metric: MetricData) => {
      if (!enabled) return;
      const event = mapMetricToEvent(metric);
      registerEvent(event);
    },
    [enabled, registerEvent],
  );

  /**
   * Handle incoming log
   */
  const handleLog = useCallback(
    (log: LogData) => {
      if (!enabled) return;
      const event = mapLogToEvent(log);
      registerEvent(event);
    },
    [enabled, registerEvent],
  );

  /**
   * Handle incoming LangGraph node event
   */
  const handleLangGraphNode = useCallback(
    (node: LangGraphNodeData) => {
      if (!enabled) return;
      const event = mapLangGraphNodeToEvent(node);
      registerEvent(event);
    },
    [enabled, registerEvent],
  );

  return useMemo(
    () => ({
      handleTraceSpan,
      handleAlert,
      handleMetric,
      handleLog,
      handleLangGraphNode,
    }),
    [handleTraceSpan, handleAlert, handleMetric, handleLog, handleLangGraphNode],
  );
}

export default useDevToolsWebSocketBridge;
