/**
 * WebSocket Metrics Types Tests
 *
 * Tests for the reconnection metrics types and utility functions.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  createInitialReconnectionMetrics,
  classifyCloseCode,
  calculateSuccessRate,
  calculateAvgDuration,
  type ReconnectionMetrics,
  type ReconnectionFailureReason,
} from "./websocket-metrics";

describe("websocket-metrics", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("createInitialReconnectionMetrics", () => {
    it("should create metrics with zero counts", () => {
      const metrics = createInitialReconnectionMetrics();

      expect(metrics.totalReconnections).toBe(0);
      expect(metrics.totalAttempts).toBe(0);
      expect(metrics.consecutiveFailures).toBe(0);
    });

    it("should create metrics with null timestamps", () => {
      const metrics = createInitialReconnectionMetrics();

      expect(metrics.lastReconnectionTime).toBeNull();
      expect(metrics.lastDisconnectionTime).toBeNull();
    });

    it("should create metrics with null derived values", () => {
      const metrics = createInitialReconnectionMetrics();

      expect(metrics.avgReconnectionDurationMs).toBeNull();
      expect(metrics.successRate).toBeNull();
    });

    it("should create metrics with zero failure counts for all reasons", () => {
      const metrics = createInitialReconnectionMetrics();

      const reasons: ReconnectionFailureReason[] = [
        "max_attempts_exceeded",
        "token_expired",
        "token_refresh_failed",
        "network_error",
        "server_error",
        "invalid_url",
        "manual_disconnect",
        "unknown",
      ];

      for (const reason of reasons) {
        expect(metrics.failuresByReason[reason]).toBe(0);
      }
    });

    it("should create metrics with empty recent attempts array", () => {
      const metrics = createInitialReconnectionMetrics();

      expect(metrics.recentAttempts).toEqual([]);
    });

    it("should create metrics with zero total reconnection time", () => {
      const metrics = createInitialReconnectionMetrics();

      expect(metrics.totalReconnectionTimeMs).toBe(0);
    });
  });

  describe("classifyCloseCode", () => {
    it("should classify code 1000 as manual_disconnect", () => {
      expect(classifyCloseCode(1000)).toBe("manual_disconnect");
    });

    it("should classify code 1001 as manual_disconnect", () => {
      expect(classifyCloseCode(1001)).toBe("manual_disconnect");
    });

    it("should classify code 1006 as network_error", () => {
      expect(classifyCloseCode(1006)).toBe("network_error");
    });

    it("should classify code 1015 as network_error", () => {
      expect(classifyCloseCode(1015)).toBe("network_error");
    });

    it("should classify code 4009 as protocol_version_mismatch", () => {
      expect(classifyCloseCode(4009)).toBe("protocol_version_mismatch");
    });

    it("should classify code 4010 as token_expired", () => {
      expect(classifyCloseCode(4010)).toBe("token_expired");
    });

    it("should classify protocol errors as server_error", () => {
      expect(classifyCloseCode(1002)).toBe("server_error");
      expect(classifyCloseCode(1003)).toBe("server_error");
      expect(classifyCloseCode(1007)).toBe("server_error");
      expect(classifyCloseCode(1008)).toBe("server_error");
      expect(classifyCloseCode(1009)).toBe("server_error");
      expect(classifyCloseCode(1010)).toBe("server_error");
      expect(classifyCloseCode(1011)).toBe("server_error");
    });

    it("should classify unknown codes as unknown", () => {
      expect(classifyCloseCode(9999)).toBe("unknown");
      expect(classifyCloseCode(4000)).toBe("unknown");
      expect(classifyCloseCode(5000)).toBe("unknown");
    });
  });

  describe("calculateSuccessRate", () => {
    it("should return null for zero attempts", () => {
      expect(calculateSuccessRate(0, 0)).toBeNull();
    });

    it("should return 100 for all successful attempts", () => {
      expect(calculateSuccessRate(5, 5)).toBe(100);
    });

    it("should return 0 for no successful attempts", () => {
      expect(calculateSuccessRate(0, 5)).toBe(0);
    });

    it("should calculate correct percentage", () => {
      expect(calculateSuccessRate(3, 4)).toBe(75);
      expect(calculateSuccessRate(1, 2)).toBe(50);
      expect(calculateSuccessRate(1, 3)).toBe(33);
    });

    it("should round to nearest integer", () => {
      expect(calculateSuccessRate(2, 3)).toBe(67); // 66.66... rounds to 67
    });
  });

  describe("calculateAvgDuration", () => {
    it("should return null for zero reconnections", () => {
      expect(calculateAvgDuration(1000, 0)).toBeNull();
    });

    it("should calculate correct average", () => {
      expect(calculateAvgDuration(3000, 3)).toBe(1000);
      expect(calculateAvgDuration(5000, 2)).toBe(2500);
    });

    it("should round to nearest integer", () => {
      expect(calculateAvgDuration(1000, 3)).toBe(333);
    });
  });

  describe("ReconnectionMetrics type structure", () => {
    it("should allow creating valid metrics object", () => {
      const metrics: ReconnectionMetrics = {
        totalReconnections: 5,
        totalAttempts: 7,
        consecutiveFailures: 0,
        lastReconnectionTime: Date.now(),
        lastDisconnectionTime: Date.now() - 1000,
        avgReconnectionDurationMs: 500,
        totalReconnectionTimeMs: 2500,
        failuresByReason: {
          max_attempts_exceeded: 1,
          token_expired: 1,
          token_refresh_failed: 0,
          network_error: 0,
          server_error: 0,
          invalid_url: 0,
          manual_disconnect: 0,
          unknown: 0,
        },
        successRate: 71,
        recentAttempts: [
          {
            timestamp: Date.now(),
            attemptNumber: 1,
            succeeded: true,
            durationMs: 500,
            failureReason: null,
            triggerCloseCode: 1006,
          },
        ],
      };

      expect(metrics.totalReconnections).toBe(5);
      expect(metrics.recentAttempts).toHaveLength(1);
    });
  });
});
