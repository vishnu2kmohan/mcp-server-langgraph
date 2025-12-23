/**
 * useDevToolsWebSocketBridge Hook Tests
 *
 * TDD tests for bridging WebSocket events to the unified timeline.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";

import {
  useDevToolsWebSocketBridge,
  mapTraceSpanToEvent,
  mapAlertToEvent,
  mapMetricToEvent,
  mapLogToEvent,
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
      expect((warningEvent.data as Record<string, unknown>).level).toBe("warning");
    });
  });

  describe("hook integration", () => {
    it("should return registerEvent function", () => {
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
