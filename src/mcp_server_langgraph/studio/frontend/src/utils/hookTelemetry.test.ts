/**
 * Hook Telemetry Utilities Tests
 *
 * TDD tests for standardized telemetry helpers for hook degradation,
 * retry, and fallback tracking.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useHookTelemetry, createHookTelemetry } from "./hookTelemetry";

// Mock devLogger
vi.mock("./devLogger", () => ({
  devLogger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    withPrefix: vi.fn(() => ({
      debug: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    })),
  },
}));

import { devLogger } from "./devLogger";

describe("hookTelemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("createHookTelemetry", () => {
    it("should create telemetry instance with hook name prefix", () => {
      createHookTelemetry("TestHook");

      expect(devLogger.withPrefix).toHaveBeenCalledWith("[TestHook]");
    });

    it("should return telemetry methods", () => {
      const telemetry = createHookTelemetry("TestHook");

      expect(typeof telemetry.logDegradation).toBe("function");
      expect(typeof telemetry.logRetry).toBe("function");
      expect(typeof telemetry.logBackoff).toBe("function");
      expect(typeof telemetry.logFallback).toBe("function");
      expect(typeof telemetry.logError).toBe("function");
      expect(typeof telemetry.getEvents).toBe("function");
    });
  });

  describe("logDegradation", () => {
    it("should log degradation with reason and context", () => {
      const telemetry = createHookTelemetry("TestHook");
      const mockLogger = (devLogger.withPrefix as ReturnType<typeof vi.fn>).mock
        .results[0].value;

      telemetry.logDegradation("missing_session_id", {
        inputLength: 10,
      });

      expect(mockLogger.debug).toHaveBeenCalledWith(
        "Graceful degradation",
        expect.objectContaining({
          reason: "missing_session_id",
          inputLength: 10,
        }),
      );
    });

    it("should track degradation events", () => {
      const telemetry = createHookTelemetry("TestHook");

      telemetry.logDegradation("api_error", { status: 500 });

      const events = telemetry.getEvents();
      expect(events).toHaveLength(1);
      expect(events[0]).toMatchObject({
        type: "degradation",
        reason: "api_error",
        context: { status: 500 },
      });
    });
  });

  describe("logRetry", () => {
    it("should log retry attempt with attempt number", () => {
      const telemetry = createHookTelemetry("TestHook");
      const mockLogger = (devLogger.withPrefix as ReturnType<typeof vi.fn>).mock
        .results[0].value;

      telemetry.logRetry(2, 3, new Error("Network error"));

      expect(mockLogger.warn).toHaveBeenCalledWith(
        "Retry attempt 2/3",
        expect.objectContaining({
          attempt: 2,
          maxAttempts: 3,
          error: "Network error",
        }),
      );
    });

    it("should track retry events", () => {
      const telemetry = createHookTelemetry("TestHook");

      telemetry.logRetry(1, 3, new Error("Timeout"));

      const events = telemetry.getEvents();
      expect(events).toHaveLength(1);
      expect(events[0]).toMatchObject({
        type: "retry",
        metrics: {
          attempt: 1,
          maxAttempts: 3,
        },
      });
    });
  });

  describe("logBackoff", () => {
    it("should log backoff with delay", () => {
      const telemetry = createHookTelemetry("TestHook");
      const mockLogger = (devLogger.withPrefix as ReturnType<typeof vi.fn>).mock
        .results[0].value;

      telemetry.logBackoff(2, 2000);

      expect(mockLogger.debug).toHaveBeenCalledWith(
        "Exponential backoff",
        expect.objectContaining({
          attempt: 2,
          delayMs: 2000,
        }),
      );
    });
  });

  describe("logFallback", () => {
    it("should log fallback usage", () => {
      const telemetry = createHookTelemetry("TestHook");
      const mockLogger = (devLogger.withPrefix as ReturnType<typeof vi.fn>).mock
        .results[0].value;

      telemetry.logFallback("cache_stale", { cachedValue: "test" });

      expect(mockLogger.debug).toHaveBeenCalledWith(
        "Using fallback",
        expect.objectContaining({
          reason: "cache_stale",
          fallback: { cachedValue: "test" },
        }),
      );
    });

    it("should track fallback events", () => {
      const telemetry = createHookTelemetry("TestHook");

      telemetry.logFallback("api_unavailable", { default: true });

      const events = telemetry.getEvents();
      expect(events).toHaveLength(1);
      expect(events[0].type).toBe("fallback");
    });
  });

  describe("logError", () => {
    it("should log errors with context", () => {
      const telemetry = createHookTelemetry("TestHook");
      const mockLogger = (devLogger.withPrefix as ReturnType<typeof vi.fn>).mock
        .results[0].value;

      const error = new Error("Connection failed");
      telemetry.logError(error, { endpoint: "/api/test" });

      expect(mockLogger.error).toHaveBeenCalledWith(
        "Error occurred",
        expect.objectContaining({
          error: "Connection failed",
          endpoint: "/api/test",
        }),
      );
    });

    it("should handle non-Error objects", () => {
      const telemetry = createHookTelemetry("TestHook");
      const mockLogger = (devLogger.withPrefix as ReturnType<typeof vi.fn>).mock
        .results[0].value;

      telemetry.logError("string error", {});

      expect(mockLogger.error).toHaveBeenCalledWith(
        "Error occurred",
        expect.objectContaining({
          error: "string error",
        }),
      );
    });
  });

  describe("getEvents", () => {
    it("should return all tracked events", () => {
      const telemetry = createHookTelemetry("TestHook");

      telemetry.logDegradation("network_error", {});
      telemetry.logRetry(1, 3, new Error("Failed"));
      telemetry.logFallback("default", {});

      const events = telemetry.getEvents();
      expect(events).toHaveLength(3);
      expect(events.map((e) => e.type)).toEqual([
        "degradation",
        "retry",
        "fallback",
      ]);
    });

    it("should limit events to maxEvents", () => {
      const telemetry = createHookTelemetry("TestHook", { maxEvents: 2 });

      telemetry.logDegradation("error1", {});
      telemetry.logDegradation("error2", {});
      telemetry.logDegradation("error3", {});

      const events = telemetry.getEvents();
      expect(events).toHaveLength(2);
      // Should keep most recent events
      expect(events[0].reason).toBe("error2");
      expect(events[1].reason).toBe("error3");
    });
  });

  describe("useHookTelemetry hook", () => {
    it("should create stable telemetry instance", () => {
      const { result, rerender } = renderHook(() =>
        useHookTelemetry("StableHook"),
      );

      const firstInstance = result.current;
      rerender();
      const secondInstance = result.current;

      expect(firstInstance).toBe(secondInstance);
    });

    it("should provide all telemetry methods", () => {
      const { result } = renderHook(() => useHookTelemetry("TestHook"));

      expect(typeof result.current.logDegradation).toBe("function");
      expect(typeof result.current.logRetry).toBe("function");
      expect(typeof result.current.logBackoff).toBe("function");
      expect(typeof result.current.logFallback).toBe("function");
      expect(typeof result.current.logError).toBe("function");
    });
  });

  describe("event timestamps", () => {
    it("should include timestamp in events", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      const telemetry = createHookTelemetry("TestHook");
      telemetry.logDegradation("test", {});

      const events = telemetry.getEvents();
      expect(events[0].timestamp).toBeGreaterThanOrEqual(now);

      vi.useRealTimers();
    });
  });
});
