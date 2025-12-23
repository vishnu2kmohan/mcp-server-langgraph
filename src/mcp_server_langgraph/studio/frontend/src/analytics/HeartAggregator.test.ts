/**
 * HeartAggregator Tests
 *
 * TDD - Sprint 4 - Phase 3.2: HEART Tracker Enhancement
 *
 * Tests for the extracted HEART event aggregation module:
 * - Event queuing and batching
 * - Auto-flush on interval and max batch size
 * - Batch sending to backend
 * - Statistics and pending event tracking
 * - Session context attachment
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  HeartAggregator,
  type HeartAggregatorConfig as _HeartAggregatorConfig,
} from "./HeartAggregator";

// =============================================================================
// Test Setup
// =============================================================================

describe("HeartAggregator", () => {
  let aggregator: HeartAggregator;
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);
  });

  afterEach(() => {
    if (aggregator) {
      aggregator.destroy();
    }
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Constructor Tests
  // ===========================================================================

  describe("constructor", () => {
    it("creates aggregator with default config", () => {
      aggregator = new HeartAggregator();

      expect(aggregator.getConfig()).toEqual({
        flushIntervalMs: 30000,
        maxBatchSize: 50,
        batchEndpoint: "/api/v1/metrics/heart/batch",
        enabled: true,
      });
    });

    it("accepts custom configuration", () => {
      aggregator = new HeartAggregator({
        flushIntervalMs: 10000,
        maxBatchSize: 25,
        batchEndpoint: "/custom/endpoint",
      });

      expect(aggregator.getConfig().flushIntervalMs).toBe(10000);
      expect(aggregator.getConfig().maxBatchSize).toBe(25);
      expect(aggregator.getConfig().batchEndpoint).toBe("/custom/endpoint");
    });

    it("starts auto-flush timer when enabled", async () => {
      aggregator = new HeartAggregator({ flushIntervalMs: 5000 });
      aggregator.queueEvent("test", { data: 1 });

      // Should not flush immediately
      expect(fetchSpy).not.toHaveBeenCalled();

      // Should flush after interval
      await vi.advanceTimersByTimeAsync(5000);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it("does not start timer when disabled", () => {
      aggregator = new HeartAggregator({ enabled: false });
      aggregator.queueEvent("test", { data: 1 });

      vi.advanceTimersByTime(60000);
      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Event Queuing Tests
  // ===========================================================================

  describe("queueEvent", () => {
    beforeEach(() => {
      aggregator = new HeartAggregator({ flushIntervalMs: 30000 });
    });

    it("queues event with timestamp", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      aggregator.queueEvent("engagement", { feature: "chat" });

      expect(aggregator.getPendingCount()).toBe(1);
      const events = aggregator.getPendingEvents();
      expect(events[0]).toEqual({
        event_type: "engagement",
        payload: { feature: "chat" },
        timestamp: now,
      });
    });

    it("queues multiple events", () => {
      aggregator.queueEvent("engagement", { feature: "chat" });
      aggregator.queueEvent("signal", { signal_id: "click" });
      aggregator.queueEvent("adoption", { step: "welcome" });

      expect(aggregator.getPendingCount()).toBe(3);
    });

    it("does not queue when disabled", () => {
      aggregator = new HeartAggregator({ enabled: false });
      aggregator.queueEvent("test", { data: 1 });

      expect(aggregator.getPendingCount()).toBe(0);
    });

    it("auto-flushes when max batch size reached", async () => {
      aggregator = new HeartAggregator({
        maxBatchSize: 3,
        flushIntervalMs: 60000,
      });

      aggregator.queueEvent("event1", { n: 1 });
      aggregator.queueEvent("event2", { n: 2 });
      expect(fetchSpy).not.toHaveBeenCalled();

      aggregator.queueEvent("event3", { n: 3 }); // Triggers flush

      // Allow async flush to complete
      await vi.advanceTimersByTimeAsync(0);

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(aggregator.getPendingCount()).toBe(0);
    });

    it("includes session context in queued events", () => {
      aggregator.setSessionContext({
        sessionId: "session-123",
        persona: "admin",
        username: "testuser",
      });

      aggregator.queueEvent("test", { data: 1 });

      const events = aggregator.getPendingEvents();
      expect(events[0].payload).toEqual({
        data: 1,
        sessionId: "session-123",
        persona: "admin",
        username: "testuser",
      });
    });
  });

  // ===========================================================================
  // Flush Tests
  // ===========================================================================

  describe("flush", () => {
    beforeEach(() => {
      aggregator = new HeartAggregator();
    });

    it("sends batch to backend endpoint", async () => {
      aggregator.queueEvent("event1", { data: 1 });
      aggregator.queueEvent("event2", { data: 2 });

      await aggregator.flush();

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/v1/metrics/heart/batch",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    it("clears queue after successful flush", async () => {
      aggregator.queueEvent("event1", { data: 1 });
      aggregator.queueEvent("event2", { data: 2 });

      expect(aggregator.getPendingCount()).toBe(2);
      await aggregator.flush();
      expect(aggregator.getPendingCount()).toBe(0);
    });

    it("includes session duration in batch", async () => {
      aggregator.setSessionStartTime(1000);
      vi.setSystemTime(6000); // 5000ms later

      aggregator.queueEvent("test", { data: 1 });
      await aggregator.flush();

      const call = fetchSpy.mock.calls[0];
      const body = JSON.parse(call[1].body);
      expect(body.session_duration).toBe(5000);
    });

    it("does nothing when queue is empty", async () => {
      await aggregator.flush();
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("updates stats on successful flush", async () => {
      aggregator.queueEvent("event1", { data: 1 });
      aggregator.queueEvent("event2", { data: 2 });

      await aggregator.flush();

      const stats = aggregator.getStats();
      expect(stats.totalFlushed).toBe(2);
      expect(stats.flushCount).toBe(1);
    });

    it("handles API errors gracefully", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("Network error"));

      aggregator.queueEvent("event1", { data: 1 });
      await aggregator.flush();

      const stats = aggregator.getStats();
      expect(stats.failedFlushes).toBe(1);
      // Events should be cleared even on failure to prevent infinite retries
      expect(aggregator.getPendingCount()).toBe(0);
    });

    it("handles non-OK responses", async () => {
      fetchSpy.mockResolvedValueOnce({ ok: false, status: 500 });

      aggregator.queueEvent("event1", { data: 1 });
      await aggregator.flush();

      const stats = aggregator.getStats();
      expect(stats.failedFlushes).toBe(1);
    });
  });

  // ===========================================================================
  // Auto-Flush Timer Tests
  // ===========================================================================

  describe("auto-flush timer", () => {
    it("flushes on interval", async () => {
      aggregator = new HeartAggregator({ flushIntervalMs: 5000 });
      aggregator.queueEvent("event1", { data: 1 });

      // Advance time and run only pending timers (not all timers which can loop)
      await vi.advanceTimersByTimeAsync(5000);

      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it("does not flush when queue is empty on interval", async () => {
      aggregator = new HeartAggregator({ flushIntervalMs: 5000 });

      await vi.advanceTimersByTimeAsync(5000);

      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("continues flushing on subsequent intervals", async () => {
      aggregator = new HeartAggregator({ flushIntervalMs: 5000 });

      aggregator.queueEvent("event1", { data: 1 });
      await vi.advanceTimersByTimeAsync(5000);

      aggregator.queueEvent("event2", { data: 2 });
      await vi.advanceTimersByTimeAsync(5000);

      expect(fetchSpy).toHaveBeenCalledTimes(2);
    });

    it("can be paused and resumed", async () => {
      aggregator = new HeartAggregator({ flushIntervalMs: 5000 });

      aggregator.queueEvent("event1", { data: 1 });
      aggregator.pause();

      await vi.advanceTimersByTimeAsync(10000);
      expect(fetchSpy).not.toHaveBeenCalled();

      aggregator.resume();
      await vi.advanceTimersByTimeAsync(5000);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
  });

  // ===========================================================================
  // Session Context Tests
  // ===========================================================================

  describe("session context", () => {
    beforeEach(() => {
      aggregator = new HeartAggregator();
    });

    it("sets session context", () => {
      aggregator.setSessionContext({
        sessionId: "sess-abc",
        persona: "developer",
      });

      const context = aggregator.getSessionContext();
      expect(context).toEqual({
        sessionId: "sess-abc",
        persona: "developer",
      });
    });

    it("merges partial context updates", () => {
      aggregator.setSessionContext({ sessionId: "sess-1" });
      aggregator.setSessionContext({ persona: "admin" });

      const context = aggregator.getSessionContext();
      expect(context).toEqual({
        sessionId: "sess-1",
        persona: "admin",
      });
    });

    it("clears session context", () => {
      aggregator.setSessionContext({ sessionId: "sess-1", persona: "admin" });
      aggregator.clearSessionContext();

      expect(aggregator.getSessionContext()).toEqual({});
    });
  });

  // ===========================================================================
  // Statistics Tests
  // ===========================================================================

  describe("statistics", () => {
    beforeEach(() => {
      aggregator = new HeartAggregator();
    });

    it("tracks total events queued", async () => {
      aggregator.queueEvent("event1", {});
      aggregator.queueEvent("event2", {});
      aggregator.queueEvent("event3", {});

      expect(aggregator.getStats().totalQueued).toBe(3);
    });

    it("tracks total events flushed", async () => {
      aggregator.queueEvent("event1", {});
      aggregator.queueEvent("event2", {});
      await aggregator.flush();

      expect(aggregator.getStats().totalFlushed).toBe(2);
    });

    it("tracks flush count", async () => {
      aggregator.queueEvent("event1", {});
      await aggregator.flush();

      aggregator.queueEvent("event2", {});
      await aggregator.flush();

      expect(aggregator.getStats().flushCount).toBe(2);
    });

    it("tracks failed flushes", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("error"));
      aggregator.queueEvent("event1", {});
      await aggregator.flush();

      expect(aggregator.getStats().failedFlushes).toBe(1);
    });

    it("resets statistics", async () => {
      aggregator.queueEvent("event1", {});
      await aggregator.flush();

      aggregator.resetStats();

      expect(aggregator.getStats()).toEqual({
        totalQueued: 0,
        totalFlushed: 0,
        flushCount: 0,
        failedFlushes: 0,
      });
    });
  });

  // ===========================================================================
  // Enable/Disable Tests
  // ===========================================================================

  describe("enable/disable", () => {
    it("can be disabled after creation", async () => {
      aggregator = new HeartAggregator({ enabled: true });
      await aggregator.disable();

      aggregator.queueEvent("event1", {});
      expect(aggregator.getPendingCount()).toBe(0);

      await vi.advanceTimersByTimeAsync(60000);
      // fetchSpy might have been called once during disable() flush
      const callsAfterDisable = fetchSpy.mock.calls.length;
      await vi.advanceTimersByTimeAsync(30000);
      // No more calls after disable
      expect(fetchSpy.mock.calls.length).toBe(callsAfterDisable);
    });

    it("can be enabled after creation", async () => {
      aggregator = new HeartAggregator({ enabled: false });
      aggregator.enable();

      aggregator.queueEvent("event1", {});
      expect(aggregator.getPendingCount()).toBe(1);

      await vi.advanceTimersByTimeAsync(30000);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it("flushes pending events when disabled", async () => {
      aggregator = new HeartAggregator();
      aggregator.queueEvent("event1", {});
      aggregator.queueEvent("event2", {});

      await aggregator.disable();
      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(aggregator.getPendingCount()).toBe(0);
    });
  });

  // ===========================================================================
  // Destroy Tests
  // ===========================================================================

  describe("destroy", () => {
    it("clears timer and queue", async () => {
      aggregator = new HeartAggregator({ flushIntervalMs: 5000 });
      aggregator.queueEvent("event1", {});

      aggregator.destroy();

      vi.advanceTimersByTime(10000);
      await vi.runAllTimersAsync();
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it("flushes pending events before destroy", async () => {
      aggregator = new HeartAggregator();
      aggregator.queueEvent("event1", {});

      await aggregator.destroy(true); // flush=true

      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
  });

  // ===========================================================================
  // Batch Payload Format Tests
  // ===========================================================================

  describe("batch payload format", () => {
    beforeEach(() => {
      aggregator = new HeartAggregator();
    });

    it("sends events array in correct format", async () => {
      vi.setSystemTime(1000);
      aggregator.queueEvent("engagement", { feature: "chat" });
      vi.setSystemTime(2000);
      aggregator.queueEvent("signal", { signal_id: "click", value: 1 });

      await aggregator.flush();

      const call = fetchSpy.mock.calls[0];
      const body = JSON.parse(call[1].body);

      expect(body.events).toHaveLength(2);
      expect(body.events[0]).toEqual({
        event_type: "engagement",
        payload: { feature: "chat" },
        timestamp: 1000,
      });
      expect(body.events[1]).toEqual({
        event_type: "signal",
        payload: { signal_id: "click", value: 1 },
        timestamp: 2000,
      });
    });
  });
});
