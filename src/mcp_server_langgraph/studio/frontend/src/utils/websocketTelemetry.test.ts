/**
 * WebSocket Telemetry Tests
 *
 * Tests for the WebSocket telemetry tracking module.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  WebSocketTelemetry,
  websocketTelemetry,
  reportWebSocketMetrics,
} from "./websocketTelemetry";
import { createInitialReconnectionMetrics } from "../types/websocket-metrics";
import type { ReconnectionMetrics } from "../types/websocket-metrics";

describe("WebSocketTelemetry", () => {
  let telemetry: WebSocketTelemetry;

  beforeEach(() => {
    telemetry = new WebSocketTelemetry({ debug: false });
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("trackReconnectionMetrics", () => {
    it("should track metrics for an endpoint", () => {
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;
      metrics.totalReconnections = 3;

      telemetry.trackReconnectionMetrics("notifications", metrics);

      const tracked = telemetry.getEndpointMetrics("notifications");
      expect(tracked).not.toBeNull();
      expect(tracked?.totalAttempts).toBe(5);
      expect(tracked?.totalReconnections).toBe(3);
    });

    it("should update existing endpoint metrics", () => {
      const metrics1 = createInitialReconnectionMetrics();
      metrics1.totalAttempts = 2;

      telemetry.trackReconnectionMetrics("notifications", metrics1);

      const metrics2 = createInitialReconnectionMetrics();
      metrics2.totalAttempts = 7;

      telemetry.trackReconnectionMetrics("notifications", metrics2);

      const tracked = telemetry.getEndpointMetrics("notifications");
      expect(tracked?.totalAttempts).toBe(7);
    });

    it("should track multiple endpoints independently", () => {
      const metrics1 = createInitialReconnectionMetrics();
      metrics1.totalAttempts = 3;

      const metrics2 = createInitialReconnectionMetrics();
      metrics2.totalAttempts = 5;

      telemetry.trackReconnectionMetrics("notifications", metrics1);
      telemetry.trackReconnectionMetrics("traces", metrics2);

      expect(telemetry.getEndpointMetrics("notifications")?.totalAttempts).toBe(
        3,
      );
      expect(telemetry.getEndpointMetrics("traces")?.totalAttempts).toBe(5);
    });
  });

  describe("removeEndpoint", () => {
    it("should remove tracked endpoint", () => {
      const metrics = createInitialReconnectionMetrics();
      telemetry.trackReconnectionMetrics("notifications", metrics);

      expect(telemetry.getEndpointMetrics("notifications")).not.toBeNull();

      telemetry.removeEndpoint("notifications");

      expect(telemetry.getEndpointMetrics("notifications")).toBeNull();
    });
  });

  describe("getAggregatedMetrics", () => {
    it("should return empty metrics when no connections", () => {
      const aggregated = telemetry.getAggregatedMetrics();

      expect(aggregated.totalConnections).toBe(0);
      expect(aggregated.totalReconnectionAttempts).toBe(0);
      expect(aggregated.totalSuccessfulReconnections).toBe(0);
      expect(aggregated.avgSuccessRate).toBeNull();
    });

    it("should aggregate metrics across multiple connections", () => {
      const metrics1: ReconnectionMetrics = {
        ...createInitialReconnectionMetrics(),
        totalAttempts: 10,
        totalReconnections: 8,
        successRate: 80,
        failuresByReason: {
          ...createInitialReconnectionMetrics().failuresByReason,
          network_error: 2,
        },
      };

      const metrics2: ReconnectionMetrics = {
        ...createInitialReconnectionMetrics(),
        totalAttempts: 5,
        totalReconnections: 5,
        successRate: 100,
        failuresByReason: {
          ...createInitialReconnectionMetrics().failuresByReason,
          network_error: 0,
        },
      };

      telemetry.trackReconnectionMetrics("notifications", metrics1);
      telemetry.trackReconnectionMetrics("traces", metrics2);

      const aggregated = telemetry.getAggregatedMetrics();

      expect(aggregated.totalConnections).toBe(2);
      expect(aggregated.totalReconnectionAttempts).toBe(15);
      expect(aggregated.totalSuccessfulReconnections).toBe(13);
      expect(aggregated.avgSuccessRate).toBe(90); // (80 + 100) / 2 = 90
      expect(aggregated.failuresByReason.network_error).toBe(2);
    });

    it("should include per-endpoint breakdown", () => {
      const metrics = createInitialReconnectionMetrics();
      metrics.totalAttempts = 5;

      telemetry.trackReconnectionMetrics("notifications", metrics);

      const aggregated = telemetry.getAggregatedMetrics();

      expect(aggregated.byEndpoint.notifications).toBeDefined();
      expect(aggregated.byEndpoint.notifications.totalAttempts).toBe(5);
    });
  });

  describe("getConnections", () => {
    it("should return all tracked connections", () => {
      telemetry.trackReconnectionMetrics(
        "notifications",
        createInitialReconnectionMetrics(),
      );
      telemetry.trackReconnectionMetrics(
        "traces",
        createInitialReconnectionMetrics(),
      );

      const connections = telemetry.getConnections();

      expect(connections.length).toBe(2);
      expect(connections.map((c) => c.endpointId).sort()).toEqual([
        "notifications",
        "traces",
      ]);
    });

    it("should include lastUpdated timestamp", () => {
      const before = Date.now();
      telemetry.trackReconnectionMetrics(
        "notifications",
        createInitialReconnectionMetrics(),
      );
      const after = Date.now();

      const connections = telemetry.getConnections();
      const conn = connections[0];

      expect(conn.lastUpdated).toBeGreaterThanOrEqual(before);
      expect(conn.lastUpdated).toBeLessThanOrEqual(after);
    });
  });

  describe("getExportPayload", () => {
    it("should return complete export payload", () => {
      telemetry.trackReconnectionMetrics(
        "notifications",
        createInitialReconnectionMetrics(),
      );

      const payload = telemetry.getExportPayload();

      expect(payload.metrics).toBeDefined();
      expect(payload.connections).toBeDefined();
      expect(payload.metadata.timestamp).toBeDefined();
      expect(payload.exportedAt).toBeDefined();
    });
  });

  describe("toJSON", () => {
    it("should return valid JSON string", () => {
      telemetry.trackReconnectionMetrics(
        "notifications",
        createInitialReconnectionMetrics(),
      );

      const json = telemetry.toJSON();
      const parsed = JSON.parse(json);

      expect(parsed.metrics).toBeDefined();
      expect(parsed.connections).toBeDefined();
    });
  });

  describe("flush", () => {
    it("should call exporter with payload", async () => {
      const exporter = vi.fn().mockResolvedValue(undefined);
      const telemetryWithExporter = new WebSocketTelemetry({ exporter });

      telemetryWithExporter.trackReconnectionMetrics(
        "notifications",
        createInitialReconnectionMetrics(),
      );

      await telemetryWithExporter.flush();

      expect(exporter).toHaveBeenCalledTimes(1);
      expect(exporter).toHaveBeenCalledWith(
        expect.objectContaining({
          metrics: expect.any(Object),
          connections: expect.any(Array),
        }),
      );
    });

    it("should do nothing if no exporter configured", async () => {
      // Should not throw
      await telemetry.flush();
    });
  });

  describe("reset", () => {
    it("should clear all tracked connections", () => {
      telemetry.trackReconnectionMetrics(
        "notifications",
        createInitialReconnectionMetrics(),
      );
      telemetry.trackReconnectionMetrics(
        "traces",
        createInitialReconnectionMetrics(),
      );

      expect(telemetry.getConnections().length).toBe(2);

      telemetry.reset();

      expect(telemetry.getConnections().length).toBe(0);
    });
  });
});

describe("websocketTelemetry singleton", () => {
  afterEach(() => {
    websocketTelemetry.reset();
  });

  it("should be available as a singleton", () => {
    expect(websocketTelemetry).toBeDefined();
    expect(websocketTelemetry).toBeInstanceOf(WebSocketTelemetry);
  });
});

describe("reportWebSocketMetrics helper", () => {
  afterEach(() => {
    websocketTelemetry.reset();
  });

  it("should track metrics via the singleton", () => {
    const metrics = createInitialReconnectionMetrics();
    metrics.totalAttempts = 10;

    reportWebSocketMetrics("test-endpoint", metrics);

    const tracked = websocketTelemetry.getEndpointMetrics("test-endpoint");
    expect(tracked?.totalAttempts).toBe(10);
  });
});
