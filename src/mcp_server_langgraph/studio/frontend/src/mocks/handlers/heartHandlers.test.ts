/**
 * HEART Metrics MSW Handlers Tests
 *
 * TDD tests for MSW handlers that mock HEART metrics API endpoints.
 * These handlers prevent "unhandled request" warnings during tests.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../server";
import {
  heartHandlers,
  createHeartEventHandler,
  createHeartBatchHandler,
} from "./heartHandlers";

describe("heartHandlers", () => {
  beforeEach(() => {
    // Add our handlers to the global server
    server.use(...heartHandlers);
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("handler exports", () => {
    it("should export heartHandlers array", () => {
      expect(Array.isArray(heartHandlers)).toBe(true);
      expect(heartHandlers.length).toBeGreaterThan(0);
    });

    it("should export createHeartEventHandler factory", () => {
      expect(typeof createHeartEventHandler).toBe("function");
    });

    it("should export createHeartBatchHandler factory", () => {
      expect(typeof createHeartBatchHandler).toBe("function");
    });
  });

  describe("POST /api/v1/metrics/heart/event", () => {
    it("should accept valid HEART event", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "engagement",
          feature: "chat",
          action: "send",
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.event_id).toBeDefined();
    });

    it("should accept happiness event with NPS score", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "happiness",
          npsScore: 9,
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });

    it("should accept session_start event", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "session_start",
          session_id: Date.now(),
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });

    it("should accept session_end event", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "session_end",
          session_id: Date.now(),
          session_duration: 30000,
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });

    it("should accept task_success event", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "task_success",
          task_id: "create_workflow",
          success: true,
          duration_ms: 5000,
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });

    it("should accept retention event", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "retention",
          days_since_last_visit: 3,
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });

    it("should accept adoption event", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "adoption",
          step: "template_selection",
          stepIndex: 2,
          completed: true,
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });

    it("should include persona context in response", async () => {
      const response = await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: "engagement",
          persona: "alice-builder",
          username: "alice",
          feature: "workflow",
          action: "create",
          timestamp: Date.now(),
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.persona_received).toBe("alice-builder");
    });
  });

  describe("POST /api/v1/metrics/heart/batch", () => {
    it("should accept batch of events", async () => {
      const events = [
        {
          event_type: "engagement",
          payload: { feature: "chat", action: "send" },
          timestamp: Date.now(),
        },
        {
          event_type: "engagement",
          payload: { feature: "chat", action: "receive" },
          timestamp: Date.now(),
        },
        {
          event_type: "engagement",
          payload: { feature: "workflow", action: "view" },
          timestamp: Date.now(),
        },
      ];

      const response = await fetch("/api/v1/metrics/heart/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events,
          session_duration: 60000,
        }),
      });

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.events_received).toBe(3);
      expect(data.batch_id).toBeDefined();
    });

    it("should handle empty batch gracefully", async () => {
      const response = await fetch("/api/v1/metrics/heart/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events: [],
          session_duration: 0,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
      expect(data.events_received).toBe(0);
    });

    it("should include session duration in response", async () => {
      const response = await fetch("/api/v1/metrics/heart/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events: [
            {
              event_type: "signal",
              payload: { signal_id: "test" },
              timestamp: Date.now(),
            },
          ],
          session_duration: 120000,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.session_duration_received).toBe(120000);
    });

    it("should handle large batches", async () => {
      const events = Array.from({ length: 50 }, (_, i) => ({
        event_type: "engagement",
        payload: { feature: "test", action: `action_${i}` },
        timestamp: Date.now(),
      }));

      const response = await fetch("/api/v1/metrics/heart/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events,
          session_duration: 300000,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.events_received).toBe(50);
    });
  });

  describe("custom handler factories", () => {
    it("should allow custom event handler with callback", async () => {
      let capturedBody: unknown = null;

      const customHandler = createHeartEventHandler((body) => {
        capturedBody = body;
        return { custom: true };
      });

      server.use(customHandler);

      await fetch("/api/v1/metrics/heart/event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_type: "test", data: "custom" }),
      });

      expect(capturedBody).toEqual({ event_type: "test", data: "custom" });
    });

    it("should allow custom batch handler with callback", async () => {
      let capturedEvents: unknown[] = [];

      const customHandler = createHeartBatchHandler(
        (events, sessionDuration) => {
          capturedEvents = events;
          return { processed: events.length, duration: sessionDuration };
        },
      );

      server.use(customHandler);

      const testEvents = [
        { event_type: "a", payload: {}, timestamp: 1 },
        { event_type: "b", payload: {}, timestamp: 2 },
      ];

      const response = await fetch("/api/v1/metrics/heart/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ events: testEvents, session_duration: 5000 }),
      });

      const data = await response.json();
      expect(capturedEvents).toHaveLength(2);
      expect(data.processed).toBe(2);
      expect(data.duration).toBe(5000);
    });
  });
});
