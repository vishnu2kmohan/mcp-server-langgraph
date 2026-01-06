/**
 * useDevToolsTimeline Parsing Tests
 *
 * Tests for initialization and event registration:
 * - Initial state
 * - Session start time configuration
 * - Event registration (console, network, state, trace, alert, metric)
 * - Relative time calculation
 * - Chronological ordering
 * - Time range updates
 * - maxEvents limit
 * - Callbacks
 *
 * @see useDevToolsTimeline.fixtures.ts for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import {
  useDevToolsTimeline,
  type TimelineEventType as _TimelineEventType,
} from "../useDevToolsTimeline";
import { createEvent } from "./useDevToolsTimeline.fixtures";

describe("useDevToolsTimeline - Parsing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ===========================================================================
  // INITIALIZATION
  // ===========================================================================

  describe("initialization", () => {
    it("should return initial state with no events", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      expect(result.current.events).toEqual([]);
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.timeRange).toEqual({ start: 0, end: 0 });
    });

    it("should accept session start time", () => {
      const startTime = Date.now();
      const { result } = renderHook(() =>
        useDevToolsTimeline({ sessionStartTime: startTime }),
      );

      expect(result.current.sessionStartTime).toBe(startTime);
    });

    it("should accept initial events", () => {
      const events = [createEvent("console", 100), createEvent("network", 200)];
      const { result } = renderHook(() =>
        useDevToolsTimeline({ initialEvents: events }),
      );

      expect(result.current.events).toHaveLength(2);
    });
  });

  // ===========================================================================
  // EVENT REGISTRATION
  // ===========================================================================

  describe("event registration", () => {
    it("should register a console event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 1000,
          data: { message: "Test log" },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("console");
      expect(result.current.events[0].data).toEqual({ message: "Test log" });
    });

    it("should register a network event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "network",
          timestamp: 1000,
          data: { url: "/api/test", method: "GET" },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("network");
    });

    it("should register a state event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "state",
          timestamp: 1000,
          data: { counter: 5 },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("state");
    });

    it("should register a trace event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "trace",
          timestamp: 1000,
          data: { nodeId: "node-1", nodeName: "agent" },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("trace");
    });

    it("should register an alert event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "alert",
          timestamp: 1000,
          data: { severity: "error", message: "Something failed" },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("alert");
    });

    it("should register a metric event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "metric",
          timestamp: 1000,
          data: { name: "latency", value: 250 },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("metric");
    });

    it("should calculate relative time from session start", () => {
      const sessionStart = 10000;
      const { result } = renderHook(() =>
        useDevToolsTimeline({ sessionStartTime: sessionStart }),
      );

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 15000,
          data: {},
        });
      });

      expect(result.current.events[0].relativeTime).toBe(5000);
    });

    it("should maintain events in chronological order", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: {},
        });
      });
      act(() => {
        result.current.registerEvent({
          type: "network",
          timestamp: 100,
          data: {},
        });
      });
      act(() => {
        result.current.registerEvent({
          type: "state",
          timestamp: 200,
          data: {},
        });
      });

      expect(result.current.events[0].timestamp).toBe(100);
      expect(result.current.events[1].timestamp).toBe(200);
      expect(result.current.events[2].timestamp).toBe(300);
    });

    it("should update time range when events are added", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
      });
      act(() => {
        result.current.registerEvent({
          type: "network",
          timestamp: 500,
          data: {},
        });
      });

      expect(result.current.timeRange).toEqual({ start: 100, end: 500 });
    });

    it("should respect maxEvents limit", () => {
      const { result } = renderHook(() =>
        useDevToolsTimeline({ maxEvents: 3 }),
      );

      for (let i = 0; i < 5; i++) {
        act(() => {
          result.current.registerEvent({
            type: "console",
            timestamp: i * 100,
            data: { index: i },
          });
        });
      }

      expect(result.current.events).toHaveLength(3);
      // Should keep most recent events
      expect(result.current.events[0].data).toEqual({ index: 2 });
      expect(result.current.events[2].data).toEqual({ index: 4 });
    });
  });

  // ===========================================================================
  // CALLBACKS
  // ===========================================================================

  describe("callbacks", () => {
    it("should call onTimeChange when time changes", () => {
      const onTimeChange = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsTimeline({ onTimeChange }),
      );

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.setCurrentTime(100);
      });

      expect(onTimeChange).toHaveBeenCalledWith(100);
    });

    it("should call onEventRegistered when event is added", () => {
      const onEventRegistered = vi.fn();
      const { result } = renderHook(() =>
        useDevToolsTimeline({ onEventRegistered }),
      );

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { test: true },
        });
      });

      expect(onEventRegistered).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "console",
          timestamp: 100,
        }),
      );
    });
  });
});
