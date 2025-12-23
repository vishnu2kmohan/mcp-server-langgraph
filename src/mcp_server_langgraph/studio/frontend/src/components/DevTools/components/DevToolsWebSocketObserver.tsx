/**
 * DevToolsWebSocketObserver Component
 *
 * Bridges WebSocket events to the unified DevTools timeline.
 * Observes trace spans, alerts, and other WebSocket sources,
 * converting them to timeline events.
 *
 * This component should be rendered inside DevToolsTimelineProvider.
 */
import { useEffect, useRef, type ReactNode } from "react";

import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { useDevToolsWebSocketBridge } from "../hooks/useDevToolsWebSocketBridge";
import { useTraceWebSocket } from "../../../hooks/useTraceWebSocket";
import { useAppSelector } from "../../../store/hooks";
import type { Alert } from "../../../store/slices/alertSlice";
import type { RootState } from "../../../store";

// Stable empty array for memoization when alerts slice is missing
const EMPTY_ALERTS: Alert[] = [];

// Safe selector that handles missing alert slice (e.g., in tests)
// Returns stable EMPTY_ALERTS reference to prevent unnecessary re-renders
const selectAlertsSafe = (state: RootState): Alert[] => {
  try {
    return state?.alerts?.alerts ?? EMPTY_ALERTS;
  } catch {
    return EMPTY_ALERTS;
  }
};

// =============================================================================
// Types
// =============================================================================

export interface DevToolsWebSocketObserverProps {
  /** Whether the observer is enabled (default: true) */
  enabled?: boolean;
  /** Child components to render (optional) */
  children?: ReactNode;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Observer component that bridges WebSocket events to the timeline.
 *
 * Renders nothing by itself (or children if provided).
 * Internally observes:
 * - Trace spans from useTraceWebSocket
 * - Alerts from Redux alertSlice
 *
 * @example
 * ```tsx
 * <DevToolsTimelineProvider>
 *   <DevToolsWebSocketObserver />
 *   <DevToolsPanel />
 * </DevToolsTimelineProvider>
 * ```
 */
export function DevToolsWebSocketObserver({
  enabled = true,
  children,
}: DevToolsWebSocketObserverProps): ReactNode {
  const { registerEvent } = useTimelineContext();

  // Get bridge handlers
  // Note: handleLangGraphNode is available but unused until LangGraph
  // node events are dispatched from chat components to Redux
  const {
    handleTraceSpan,
    handleAlert,
    handleLangGraphNode: _handleLangGraphNode,
  } = useDevToolsWebSocketBridge({
    enabled,
    registerEvent,
  });

  // Observe trace spans
  const { spans } = useTraceWebSocket({ autoConnect: enabled });

  // Observe alerts from Redux (with safe fallback for tests)
  const alerts = useAppSelector(selectAlertsSafe);

  // Track processed IDs to avoid duplicates
  const processedSpanIds = useRef<Set<string>>(new Set());
  const processedAlertIds = useRef<Set<string>>(new Set());

  // Process new trace spans
  useEffect(() => {
    if (!enabled) return;

    for (const span of spans) {
      if (!processedSpanIds.current.has(span.spanId)) {
        processedSpanIds.current.add(span.spanId);

        // Convert to bridge format
        handleTraceSpan({
          span_id: span.spanId,
          trace_id: span.traceId,
          parent_span_id: span.parentSpanId,
          name: span.name,
          start_time: new Date(span.startTime).getTime(),
          duration_ms: span.endTime
            ? new Date(span.endTime).getTime() -
              new Date(span.startTime).getTime()
            : 0,
          status: span.status.toLowerCase(),
          service_name: (span.attributes?.service_name as string) || "unknown",
          attributes: span.attributes,
        });
      }
    }
  }, [enabled, spans, handleTraceSpan]);

  // Process new alerts from Redux
  useEffect(() => {
    if (!enabled) return;

    for (const alert of alerts) {
      if (!processedAlertIds.current.has(alert.alert_id)) {
        processedAlertIds.current.add(alert.alert_id);

        handleAlert({
          id: alert.alert_id,
          name: alert.name,
          state: alert.state,
          severity: alert.severity,
          service: (alert as { service?: string }).service || "unknown",
          message: alert.message,
          started_at: alert.started_at,
          resolved_at: (alert as { resolved_at?: string }).resolved_at,
          generator_url: (alert as { generator_url?: string }).generator_url,
        });
      }
    }
  }, [enabled, alerts, handleAlert]);

  // Note: LangGraph node observation requires useStreamingChat which
  // is used in chat components. To integrate LangGraph nodes:
  // 1. Chat components could dispatch LangGraph events to Redux
  // 2. Or a shared context could be used across chat and DevTools
  // For now, this observer handles trace spans and alerts.

  // Render children if provided, otherwise null
  return children ?? null;
}

export default DevToolsWebSocketObserver;
