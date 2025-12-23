/**
 * useDevToolsWebSocketBridge Hook Tests
 *
 * TDD tests for bridging WebSocket events to the unified timeline.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import {
  useDevToolsWebSocketBridge,
  mapTraceSpanToEvent,
  mapAlertToEvent,
  mapMetricToEvent,
  mapLogToEvent,
  mapLangGraphNodeToEvent,
} from "./useDevToolsWebSocketBridge";

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsWebSocketBridge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("mapTraceSpanToEvent", () => {
    it("should map OTEL span to timeline event", () => {
      const span = {
        span_id: "span-123",
        trace_id: "trace-456",
        name: "api.request",
        start_time: 1700000000000,
        duration_ms: 150,
        status: "ok",
        service_name: "api-gateway",
      };

      const event = mapTraceSpanToEvent(span);

      expect(event.type).toBe("otel_span");
      expect(event.timestamp).toBe(span.start_time);
      expect(event.data).toEqual(span);
    });

    it("should generate unique id for span event", () => {
      const span1 = {
        span_id: "span-123",
        trace_id: "trace-456",
        name: "api.request",
        start_time: 1700000000000,
        duration_ms: 150,
        status: "ok",
        service_name: "api-gateway",
      };

      const span2 = {
        span_id: "span-789",
        trace_id: "trace-456",
        name: "db.query",
        start_time: 1700000000100,
        duration_ms: 50,
        status: "ok",
        service_name: "db-service",
      };

      const event1 = mapTraceSpanToEvent(span1);
      const event2 = mapTraceSpanToEvent(span2);

      expect(event1.id).not.toBe(event2.id);
    });
  });

  describe("mapAlertToEvent", () => {
    it("should map alert to timeline event", () => {
      const alert = {
        id: "alert-123",
        name: "HighErrorRate",
        state: "firing",
        severity: "critical",
        service: "api-gateway",
        message: "Error rate exceeded threshold",
        started_at: "2024-01-01T12:00:00Z",
      };

      const event = mapAlertToEvent(alert);

      expect(event.type).toBe("alert");
      expect(event.timestamp).toBe(new Date(alert.started_at).getTime());
      expect(event.data).toEqual(alert);
    });

    it("should include severity in data for priority determination", () => {
      const alert = {
        id: "alert-123",
        name: "HighErrorRate",
        state: "firing",
        severity: "critical",
        service: "api-gateway",
        message: "Error rate exceeded threshold",
        started_at: "2024-01-01T12:00:00Z",
      };

      const event = mapAlertToEvent(alert);

      // Severity is stored in data for priority determination
      expect((event.data as Record<string, unknown>).severity).toBe("critical");
    });
  });

  describe("mapMetricToEvent", () => {
    it("should map metric snapshot to timeline event", () => {
      const metric = {
        name: "requests_per_minute",
        value: 1500,
        timestamp: 1700000000000,
      };

      const event = mapMetricToEvent(metric);

      expect(event.type).toBe("metric");
      expect(event.timestamp).toBe(metric.timestamp);
      expect(event.data).toEqual(metric);
    });

    it("should use current time if timestamp not provided", () => {
      const metric = {
        name: "requests_per_minute",
        value: 1500,
      };

      const before = Date.now();
      const event = mapMetricToEvent(metric);
      const after = Date.now();

      expect(event.timestamp).toBeGreaterThanOrEqual(before);
      expect(event.timestamp).toBeLessThanOrEqual(after);
    });
  });

  describe("mapLogToEvent", () => {
    it("should map log entry to timeline event", () => {
      const log = {
        id: "log-123",
        timestamp: "2024-01-01T12:00:00Z",
        level: "error",
        service: "api-gateway",
        message: "Connection timeout",
        trace_id: "trace-456",
      };

      const event = mapLogToEvent(log);

      expect(event.type).toBe("console");
      expect(event.timestamp).toBe(new Date(log.timestamp).getTime());
      expect(event.data).toEqual(log);
    });

    it("should preserve log level in data", () => {
      const errorLog = {
        id: "log-1",
        timestamp: "2024-01-01T12:00:00Z",
        level: "error",
        service: "api",
        message: "Error",
      };

      const warningLog = {
        id: "log-2",
        timestamp: "2024-01-01T12:00:00Z",
        level: "warning",
        service: "api",
        message: "Warning",
      };

      const errorEvent = mapLogToEvent(errorLog);
      const warningEvent = mapLogToEvent(warningLog);

      // Log level is preserved in data
      expect((errorEvent.data as Record<string, unknown>).level).toBe("error");
      expect((warningEvent.data as Record<string, unknown>).level).toBe(
        "warning",
      );
    });
  });

  describe("mapLangGraphNodeToEvent", () => {
    it("should map LangGraph node to timeline event with langgraph_node type", () => {
      const now = Date.now();
      const node = {
        id: "node-123",
        name: "AgentNode",
        type: "agent" as const,
        status: "completed" as const,
        startTime: now - 1000,
        endTime: now,
        duration: 1000,
      };

      const event = mapLangGraphNodeToEvent(node);

      expect(event.type).toBe("langgraph_node");
      expect(event.timestamp).toBe(node.startTime);
      expect(event.data).toEqual(node);
    });

    it("should use current time if startTime not provided", () => {
      const node = {
        id: "node-123",
        name: "ToolNode",
        type: "tool" as const,
        status: "running" as const,
        duration: 500,
      };

      const before = Date.now();
      const event = mapLangGraphNodeToEvent(node);
      const after = Date.now();

      expect(event.timestamp).toBeGreaterThanOrEqual(before);
      expect(event.timestamp).toBeLessThanOrEqual(after);
    });

    it("should preserve node status and type in data", () => {
      const node = {
        id: "node-456",
        name: "ConditionalNode",
        type: "conditional" as const,
        status: "error" as const,
        startTime: Date.now() - 500,
        duration: 500,
      };

      const event = mapLangGraphNodeToEvent(node);

      expect((event.data as Record<string, unknown>).status).toBe("error");
      expect((event.data as Record<string, unknown>).type).toBe("conditional");
    });

    it("should set source to langgraph", () => {
      const node = {
        id: "node-789",
        name: "StartNode",
        type: "start" as const,
        status: "completed" as const,
        startTime: Date.now(),
      };

      const event = mapLangGraphNodeToEvent(node);

      expect(event.source).toBe("langgraph");
    });

    it("should generate unique id for each node event", () => {
      const node1 = {
        id: "node-1",
        name: "Node1",
        type: "agent" as const,
        status: "completed" as const,
        startTime: Date.now(),
      };

      const node2 = {
        id: "node-2",
        name: "Node2",
        type: "tool" as const,
        status: "completed" as const,
        startTime: Date.now() + 100,
      };

      const event1 = mapLangGraphNodeToEvent(node1);
      const event2 = mapLangGraphNodeToEvent(node2);

      expect(event1.id).not.toBe(event2.id);
    });
  });

  describe("hook integration", () => {
    it("should return all handler functions including handleLangGraphNode", () => {
      const mockRegisterEvent = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsWebSocketBridge({
          enabled: true,
          registerEvent: mockRegisterEvent,
        }),
      );

      expect(result.current.handleTraceSpan).toBeDefined();
      expect(result.current.handleAlert).toBeDefined();
      expect(result.current.handleMetric).toBeDefined();
      expect(result.current.handleLog).toBeDefined();
      expect(result.current.handleLangGraphNode).toBeDefined();
    });

    it("should call registerEvent when handling trace span", () => {
      const mockRegisterEvent = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsWebSocketBridge({
          enabled: true,
          registerEvent: mockRegisterEvent,
        }),
      );

      act(() => {
        result.current.handleTraceSpan({
          span_id: "span-123",
          trace_id: "trace-456",
          name: "api.request",
          start_time: 1700000000000,
          duration_ms: 150,
          status: "ok",
          service_name: "api-gateway",
        });
      });

      expect(mockRegisterEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "otel_span",
        }),
      );
    });

    it("should call registerEvent when handling alert", () => {
      const mockRegisterEvent = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsWebSocketBridge({
          enabled: true,
          registerEvent: mockRegisterEvent,
        }),
      );

      act(() => {
        result.current.handleAlert({
          id: "alert-123",
          name: "HighErrorRate",
          state: "firing",
          severity: "critical",
          service: "api-gateway",
          message: "Error rate exceeded threshold",
          started_at: "2024-01-01T12:00:00Z",
        });
      });

      expect(mockRegisterEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "alert",
        }),
      );
    });

    it("should call registerEvent when handling LangGraph node", () => {
      const mockRegisterEvent = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsWebSocketBridge({
          enabled: true,
          registerEvent: mockRegisterEvent,
        }),
      );

      const now = Date.now();
      act(() => {
        result.current.handleLangGraphNode({
          id: "node-123",
          name: "AgentNode",
          type: "agent",
          status: "completed",
          startTime: now - 1000,
          endTime: now,
          duration: 1000,
        });
      });

      expect(mockRegisterEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "langgraph_node",
          timestamp: now - 1000,
        }),
      );
    });

    it("should not call registerEvent for LangGraph nodes when disabled", () => {
      const mockRegisterEvent = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsWebSocketBridge({
          enabled: false,
          registerEvent: mockRegisterEvent,
        }),
      );

      act(() => {
        result.current.handleLangGraphNode({
          id: "node-123",
          name: "AgentNode",
          type: "agent",
          status: "completed",
          startTime: Date.now(),
        });
      });

      expect(mockRegisterEvent).not.toHaveBeenCalled();
    });

    it("should not call registerEvent when disabled", () => {
      const mockRegisterEvent = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsWebSocketBridge({
          enabled: false,
          registerEvent: mockRegisterEvent,
        }),
      );

      act(() => {
        result.current.handleTraceSpan({
          span_id: "span-123",
          trace_id: "trace-456",
          name: "api.request",
          start_time: 1700000000000,
          duration_ms: 150,
          status: "ok",
          service_name: "api-gateway",
        });
      });

      expect(mockRegisterEvent).not.toHaveBeenCalled();
    });
  });
});
