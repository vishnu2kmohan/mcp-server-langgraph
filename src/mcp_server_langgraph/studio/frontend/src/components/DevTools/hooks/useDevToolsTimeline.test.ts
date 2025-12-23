/**
 * useDevToolsTimeline Hook Tests
 *
 * TDD tests for unified time-travel debugging across all DevTools tabs.
 * Synchronizes logs, metrics, alerts, traces, and state snapshots.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import {
  useDevToolsTimeline,
  type TimelineEvent,
  type TimelineEventType,
} from "./useDevToolsTimeline";

// =============================================================================
// Test Helpers
// =============================================================================

function createEvent(
  type: TimelineEventType,
  timestamp: number,
  data: Record<string, unknown> = {},
): TimelineEvent {
  return {
    id: `${type}-${timestamp}`,
    type,
    timestamp,
    relativeTime: timestamp,
    source: type,
    data,
  };
}

// OTEL trace/span ID generators for testing
function generateTraceId(): string {
  return Array.from({ length: 32 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join("");
}

function generateSpanId(): string {
  return Array.from({ length: 16 }, () =>
    Math.floor(Math.random() * 16).toString(16),
  ).join("");
}

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

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

  describe("time navigation", () => {
    it("should set current time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.setCurrentTime(300);
      });

      expect(result.current.currentTime).toBe(300);
    });

    it("should clamp current time to valid range", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.setCurrentTime(1000);
      });

      expect(result.current.currentTime).toBe(500);

      act(() => {
        result.current.setCurrentTime(-50);
      });

      expect(result.current.currentTime).toBe(100);
    });

    it("should jump to start", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
        result.current.setCurrentTime(300);
      });

      act(() => {
        result.current.jumpToStart();
      });

      expect(result.current.currentTime).toBe(100);
    });

    it("should jump to end", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.jumpToEnd();
      });

      expect(result.current.currentTime).toBe(500);
      expect(result.current.isAtEnd).toBe(true);
    });

    it("should step forward to next event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: {},
        });
        result.current.setCurrentTime(100);
      });

      act(() => {
        result.current.stepForward();
      });

      expect(result.current.currentTime).toBe(200);
    });

    it("should step backward to previous event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: {},
        });
        result.current.setCurrentTime(300);
      });

      act(() => {
        result.current.stepBackward();
      });

      expect(result.current.currentTime).toBe(200);
    });
  });

  describe("playback", () => {
    it("should start playback", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.startPlayback();
      });

      expect(result.current.isPlaying).toBe(true);
    });

    it("should stop playback", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.startPlayback();
      });

      act(() => {
        result.current.stopPlayback();
      });

      expect(result.current.isPlaying).toBe(false);
    });

    it("should advance time during playback", () => {
      const { result } = renderHook(() =>
        useDevToolsTimeline({ playbackInterval: 100 }),
      );

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 0,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 1000,
          data: {},
        });
      });

      act(() => {
        result.current.startPlayback();
      });

      // Allow effect to set up interval
      act(() => {
        vi.advanceTimersByTime(0);
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(result.current.currentTime).toBeGreaterThan(0);
    });

    it("should stop playback at end", () => {
      const { result } = renderHook(() =>
        useDevToolsTimeline({ playbackInterval: 50, playbackSpeed: 100 }),
      );

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 0,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
      });

      act(() => {
        result.current.startPlayback();
      });

      // Advance enough to reach end (multiple ticks at 100x speed)
      act(() => {
        vi.advanceTimersByTime(50);
      });
      act(() => {
        vi.advanceTimersByTime(50);
      });

      expect(result.current.isPlaying).toBe(false);
      expect(result.current.isAtEnd).toBe(true);
    });

    it("should support playback speed multiplier", () => {
      const { result } = renderHook(() =>
        useDevToolsTimeline({ playbackInterval: 100, playbackSpeed: 2 }),
      );

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 0,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 1000,
          data: {},
        });
      });

      act(() => {
        result.current.startPlayback();
      });

      const initialTime = result.current.currentTime;

      // Allow effect to set up interval, then advance
      act(() => {
        vi.advanceTimersByTime(0);
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });

      // At 2x speed, should advance 200ms of timeline time per 100ms real time
      expect(result.current.currentTime - initialTime).toBeGreaterThanOrEqual(
        200,
      );
    });

    it("should change playback speed", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      expect(result.current.playbackSpeed).toBe(1);

      act(() => {
        result.current.setPlaybackSpeed(4);
      });

      expect(result.current.playbackSpeed).toBe(4);
    });
  });

  describe("event filtering", () => {
    it("should get events at current time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: { id: 3 },
        });
        result.current.setCurrentTime(200);
      });

      const eventsAtTime = result.current.getEventsAtCurrentTime();

      // Should return events up to and including current time
      expect(eventsAtTime).toHaveLength(2);
      expect(eventsAtTime[0].data).toEqual({ id: 1 });
      expect(eventsAtTime[1].data).toEqual({ id: 2 });
    });

    it("should filter events by type", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 400,
          data: {},
        });
      });

      const consoleEvents = result.current.getEventsByType("console");

      expect(consoleEvents).toHaveLength(2);
      expect(consoleEvents.every((e) => e.type === "console")).toBe(true);
    });

    it("should filter events by time range", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 3 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 400,
          data: { id: 4 },
        });
      });

      const rangeEvents = result.current.getEventsInRange(150, 350);

      expect(rangeEvents).toHaveLength(2);
      expect(rangeEvents[0].data).toEqual({ id: 2 });
      expect(rangeEvents[1].data).toEqual({ id: 3 });
    });

    it("should get visible events based on current time and filter", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 150,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 250,
          data: {},
        });
        result.current.setCurrentTime(200);
        result.current.setTypeFilter(["console"]);
      });

      const visible = result.current.getVisibleEvents();

      expect(visible).toHaveLength(2);
      expect(visible.every((e) => e.type === "console")).toBe(true);
    });
  });

  describe("event correlation", () => {
    it("should find events near a timestamp", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 105,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 110,
          data: { id: 3 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: { id: 4 },
        });
      });

      const nearEvents = result.current.getEventsNear(105, 20);

      expect(nearEvents).toHaveLength(3);
    });

    it("should find correlated events by ID", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      const correlationId = "request-123";

      act(() => {
        result.current.registerEvent({
          type: "network",
          timestamp: 100,
          data: { correlationId, status: "pending" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: { correlationId, message: "Processing request" },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: { correlationId, status: "completed" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { message: "Unrelated log" },
        });
      });

      const correlated = result.current.getCorrelatedEvents(correlationId);

      expect(correlated).toHaveLength(3);
    });

    it("should get previous event of same type", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "state",
          timestamp: 100,
          data: { value: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 200,
          data: { value: 2 },
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: { value: 3 },
        });
      });

      const event = result.current.events.find((e) => e.timestamp === 300);
      const previous = result.current.getPreviousEventOfType(
        event!.id,
        "state",
      );

      expect(previous?.data).toEqual({ value: 2 });
    });
  });

  describe("bookmarks", () => {
    it("should add a bookmark at current time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
      });

      act(() => {
        result.current.setCurrentTime(100);
      });

      act(() => {
        result.current.addBookmark("Important moment");
      });

      expect(result.current.bookmarks).toHaveLength(1);
      expect(result.current.bookmarks[0].label).toBe("Important moment");
      expect(result.current.bookmarks[0].timestamp).toBe(100);
    });

    it("should remove a bookmark", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
      });

      act(() => {
        result.current.setCurrentTime(100);
      });

      act(() => {
        result.current.addBookmark("Test");
      });

      const bookmarkId = result.current.bookmarks[0].id;

      act(() => {
        result.current.removeBookmark(bookmarkId);
      });

      expect(result.current.bookmarks).toHaveLength(0);
    });

    it("should jump to bookmark", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.setCurrentTime(500);
      });

      act(() => {
        result.current.addBookmark("Start");
      });

      act(() => {
        result.current.setCurrentTime(100);
      });

      const bookmark = result.current.bookmarks[0];

      act(() => {
        result.current.jumpToBookmark(bookmark.id);
      });

      expect(result.current.currentTime).toBe(500);
    });
  });

  describe("clear and reset", () => {
    it("should clear all events", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
      });

      act(() => {
        result.current.clearEvents();
      });

      expect(result.current.events).toHaveLength(0);
      expect(result.current.currentTime).toBe(0);
    });

    it("should clear events by type", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: {},
        });
      });

      act(() => {
        result.current.clearEventsByType("console");
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("network");
    });

    it("should reset timeline to initial state", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.setCurrentTime(100);
        result.current.addBookmark("Test");
        result.current.startPlayback();
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.events).toHaveLength(0);
      expect(result.current.bookmarks).toHaveLength(0);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.isPlaying).toBe(false);
    });
  });

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

  describe("isAtEnd state", () => {
    it("should be true when at the latest event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
        result.current.setCurrentTime(500);
      });

      expect(result.current.isAtEnd).toBe(true);
    });

    it("should be false when not at the latest event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
        result.current.setCurrentTime(300);
      });

      expect(result.current.isAtEnd).toBe(false);
    });
  });

  describe("live mode", () => {
    it("should enable live mode by default", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      expect(result.current.isLiveMode).toBe(true);
    });

    it("should auto-advance to new events in live mode", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
      });

      expect(result.current.currentTime).toBe(100);

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: {},
        });
      });

      expect(result.current.currentTime).toBe(200);
    });

    it("should disable live mode when manually navigating", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: {},
        });
      });

      act(() => {
        result.current.setCurrentTime(100);
      });

      expect(result.current.isLiveMode).toBe(false);
    });

    it("should re-enable live mode when jumping to end", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: {},
        });
        result.current.setCurrentTime(100);
      });

      expect(result.current.isLiveMode).toBe(false);

      act(() => {
        result.current.jumpToEnd();
      });

      expect(result.current.isLiveMode).toBe(true);
    });
  });

  // ===========================================================================
  // OTEL Distributed Trace Support
  // ===========================================================================

  describe("OTEL distributed traces", () => {
    it("should register an OTEL span event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId,
            operationName: "HTTP GET /api/users",
            serviceName: "mcp-server",
            duration: 150,
            status: "OK",
          },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("otel_span");
      expect(result.current.events[0].data.traceId).toBe(traceId);
    });

    it("should register nested OTEL spans with parent-child relationship", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const parentSpanId = generateSpanId();
      const childSpanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: parentSpanId,
            operationName: "agent.execute",
            serviceName: "mcp-server",
            duration: 500,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1050,
          data: {
            traceId,
            spanId: childSpanId,
            parentSpanId,
            operationName: "llm.invoke",
            serviceName: "mcp-server",
            duration: 300,
          },
        });
      });

      expect(result.current.events).toHaveLength(2);

      // Verify parent-child relationship
      const childSpan = result.current.events.find(
        (e) => e.data.spanId === childSpanId,
      );
      expect(childSpan?.data.parentSpanId).toBe(parentSpanId);
    });

    it("should get all spans for a distributed trace by traceId", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId1 = generateTraceId();
      const traceId2 = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId: traceId1,
            spanId: generateSpanId(),
            operationName: "op1",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1100,
          data: {
            traceId: traceId1,
            spanId: generateSpanId(),
            operationName: "op2",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1200,
          data: {
            traceId: traceId2,
            spanId: generateSpanId(),
            operationName: "op3",
          },
        });
      });

      const trace1Spans = result.current.getSpansByTraceId(traceId1);

      expect(trace1Spans).toHaveLength(2);
      expect(trace1Spans.every((s) => s.data.traceId === traceId1)).toBe(true);
    });

    it("should get span hierarchy for a trace", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const rootSpanId = generateSpanId();
      const childSpanId1 = generateSpanId();
      const childSpanId2 = generateSpanId();
      const grandchildSpanId = generateSpanId();

      act(() => {
        // Root span
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: { traceId, spanId: rootSpanId, operationName: "root" },
        });
        // Child spans
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1010,
          data: {
            traceId,
            spanId: childSpanId1,
            parentSpanId: rootSpanId,
            operationName: "child1",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1020,
          data: {
            traceId,
            spanId: childSpanId2,
            parentSpanId: rootSpanId,
            operationName: "child2",
          },
        });
        // Grandchild span
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1030,
          data: {
            traceId,
            spanId: grandchildSpanId,
            parentSpanId: childSpanId1,
            operationName: "grandchild",
          },
        });
      });

      const hierarchy = result.current.getSpanHierarchy(traceId);

      expect(hierarchy.root?.data.spanId).toBe(rootSpanId);
      expect(hierarchy.children).toHaveLength(2);
      expect(hierarchy.depth).toBe(3);
    });

    it("should correlate OTEL spans with console logs by traceId", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: { traceId, spanId: generateSpanId(), operationName: "process" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 1050,
          data: { traceId, message: "Processing request" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 1100,
          data: { message: "Unrelated log" },
        });
      });

      const correlated = result.current.getEventsByTraceId(traceId);

      expect(correlated).toHaveLength(2);
      expect(correlated.some((e) => e.type === "otel_span")).toBe(true);
      expect(correlated.some((e) => e.type === "console")).toBe(true);
    });

    it("should correlate OTEL spans with network requests", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "HTTP POST",
          },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 1000,
          data: { traceId, url: "/api/submit", method: "POST" },
        });
      });

      const correlated = result.current.getEventsByTraceId(traceId);

      expect(correlated).toHaveLength(2);
    });

    it("should get span duration statistics", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "op1",
            duration: 100,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1100,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "op2",
            duration: 200,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1300,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "op3",
            duration: 300,
          },
        });
      });

      const stats = result.current.getSpanStats(traceId);

      expect(stats.totalSpans).toBe(3);
      expect(stats.totalDuration).toBe(600);
      expect(stats.averageDuration).toBe(200);
    });

    it("should identify slow spans", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "fast",
            duration: 50,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1050,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "slow",
            duration: 5000,
          },
        });
      });

      const slowSpans = result.current.getSlowSpans(1000); // threshold 1000ms

      expect(slowSpans).toHaveLength(1);
      expect(slowSpans[0].data.operationName).toBe("slow");
    });

    it("should identify error spans", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "success",
            status: "OK",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1100,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "failed",
            status: "ERROR",
            errorMessage: "Connection refused",
          },
        });
      });

      const errorSpans = result.current.getErrorSpans();

      expect(errorSpans).toHaveLength(1);
      expect(errorSpans[0].data.status).toBe("ERROR");
    });
  });

  describe("LangGraph execution trace", () => {
    it("should register a LangGraph node execution event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1000,
          data: {
            nodeId: "agent",
            nodeName: "Agent",
            nodeType: "agent",
            status: "running",
            input: { query: "Hello" },
          },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("langgraph_node");
    });

    it("should track LangGraph node state transitions", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const nodeId = "agent-1";

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1000,
          data: { nodeId, status: "pending" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1100,
          data: { nodeId, status: "running" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1500,
          data: { nodeId, status: "completed", output: { response: "Hi" } },
        });
      });

      const nodeEvents = result.current.getLangGraphNodeEvents(nodeId);

      expect(nodeEvents).toHaveLength(3);
      expect(nodeEvents[0].data.status).toBe("pending");
      expect(nodeEvents[2].data.status).toBe("completed");
    });

    it("should correlate LangGraph nodes with OTEL spans", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const nodeId = "agent-1";

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1000,
          data: { nodeId, traceId, status: "running" },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "langgraph.node.agent",
          },
        });
      });

      const correlated = result.current.getEventsByTraceId(traceId);

      expect(correlated).toHaveLength(2);
      expect(correlated.some((e) => e.type === "langgraph_node")).toBe(true);
      expect(correlated.some((e) => e.type === "otel_span")).toBe(true);
    });

    it("should get LangGraph execution graph at current time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 100,
          data: { nodeId: "start", status: "completed" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 200,
          data: { nodeId: "agent", status: "running" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 300,
          data: { nodeId: "agent", status: "completed" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 400,
          data: { nodeId: "tool", status: "running" },
        });
        result.current.setCurrentTime(250);
      });

      const graphState = result.current.getLangGraphStateAtCurrentTime();

      // At time 250: start=completed, agent=running, tool=not started
      expect(graphState.start).toBe("completed");
      expect(graphState.agent).toBe("running");
      expect(graphState.tool).toBeUndefined();
    });
  });

  describe("time window and span selection", () => {
    it("should set and get time window selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.setTimeWindow(150, 400);
      });

      expect(result.current.timeWindow).toEqual({ start: 150, end: 400 });
    });

    it("should filter events within time window", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 3 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 400,
          data: { id: 4 },
        });
      });

      act(() => {
        result.current.setTimeWindow(150, 350);
      });

      const windowedEvents = result.current.getEventsInWindow();

      expect(windowedEvents).toHaveLength(2);
      expect(windowedEvents[0].data).toEqual({ id: 2 });
      expect(windowedEvents[1].data).toEqual({ id: 3 });
    });

    it("should clear time window selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.setTimeWindow(100, 200);
      });

      act(() => {
        result.current.clearTimeWindow();
      });

      expect(result.current.timeWindow).toBeNull();
    });

    it("should select a span for filtering", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { traceId, spanId, operationName: "root", duration: 500 },
        });
      });

      act(() => {
        result.current.selectSpan(spanId);
      });

      expect(result.current.selectedSpanId).toBe(spanId);
    });

    it("should filter events that occurred during selected span", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const spanId = generateSpanId();

      act(() => {
        // Span runs from 100 to 600 (duration 500ms)
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { traceId, spanId, operationName: "root", duration: 500 },
        });
        // Events during the span
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: { message: "During span 1" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 400,
          data: { message: "During span 2" },
        });
        // Event after the span
        result.current.registerEvent({
          type: "console",
          timestamp: 700,
          data: { message: "After span" },
        });
      });

      act(() => {
        result.current.selectSpan(spanId);
      });

      const spanEvents = result.current.getEventsInSelectedSpan();

      expect(spanEvents).toHaveLength(2);
      expect(spanEvents[0].data.message).toBe("During span 1");
      expect(spanEvents[1].data.message).toBe("During span 2");
    });

    it("should clear span selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 100 },
        });
        result.current.selectSpan(spanId);
      });

      act(() => {
        result.current.clearSpanSelection();
      });

      expect(result.current.selectedSpanId).toBeNull();
    });

    it("should get active filters summary", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 100 },
        });
      });

      act(() => {
        result.current.setTimeWindow(50, 250);
        result.current.selectSpan(spanId);
        result.current.setTypeFilter(["console", "network"]);
      });

      const filters = result.current.getActiveFilters();

      expect(filters.hasTimeWindow).toBe(true);
      expect(filters.hasSpanSelection).toBe(true);
      expect(filters.hasTypeFilter).toBe(true);
      expect(filters.typeFilter).toEqual(["console", "network"]);
    });

    it("should combine time window and span selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const spanId = generateSpanId();

      act(() => {
        // Span from 100-600
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 500 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: { id: 3 },
        });
      });

      act(() => {
        result.current.selectSpan(spanId);
        // Further constrain to 200-400
        result.current.setTimeWindow(200, 400);
      });

      // Should only include console event at 300 (within span AND within time window)
      const filtered = result.current.getFilteredEvents();

      // The span itself is at 100, so excluded. Console at 300 is within both.
      expect(filtered.filter((e) => e.type === "console")).toHaveLength(1);
      expect(filtered.find((e) => e.type === "console")?.data).toEqual({
        id: 2,
      });
    });
  });

  describe("cross-source time travel", () => {
    it("should show unified view of all event types at a point in time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        // Console log
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { message: "Starting request", traceId },
        });
        // Network request starts
        result.current.registerEvent({
          type: "network",
          timestamp: 100,
          data: { url: "/api/process", status: "pending", traceId },
        });
        // OTEL span
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { traceId, spanId: generateSpanId(), operationName: "process" },
        });
        // LangGraph node
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 100,
          data: { nodeId: "agent", status: "running", traceId },
        });
        // State change
        result.current.registerEvent({
          type: "state",
          timestamp: 100,
          data: { isProcessing: true },
        });
        // Alert
        result.current.registerEvent({
          type: "alert",
          timestamp: 150,
          data: { severity: "warning", message: "High latency" },
        });
        // Metric
        result.current.registerEvent({
          type: "metric",
          timestamp: 150,
          data: { name: "request.latency", value: 500 },
        });

        result.current.setCurrentTime(125);
      });

      const eventsAtTime = result.current.getEventsAtCurrentTime();

      // Should include events at or before time 125
      expect(eventsAtTime).toHaveLength(5);
      expect(eventsAtTime.some((e) => e.type === "console")).toBe(true);
      expect(eventsAtTime.some((e) => e.type === "network")).toBe(true);
      expect(eventsAtTime.some((e) => e.type === "otel_span")).toBe(true);
      expect(eventsAtTime.some((e) => e.type === "langgraph_node")).toBe(true);
      expect(eventsAtTime.some((e) => e.type === "state")).toBe(true);
      // Alert and metric at 150 should NOT be included
      expect(eventsAtTime.some((e) => e.type === "alert")).toBe(false);
    });

    it("should scrub through time and update all event visibility", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: {},
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 400,
          data: {},
        });
      });

      // Scrub to different times and verify visible events
      act(() => {
        result.current.setCurrentTime(150);
      });
      expect(result.current.getEventsAtCurrentTime()).toHaveLength(1);

      act(() => {
        result.current.setCurrentTime(250);
      });
      expect(result.current.getEventsAtCurrentTime()).toHaveLength(2);

      act(() => {
        result.current.setCurrentTime(350);
      });
      expect(result.current.getEventsAtCurrentTime()).toHaveLength(3);

      act(() => {
        result.current.setCurrentTime(450);
      });
      expect(result.current.getEventsAtCurrentTime()).toHaveLength(4);
    });
  });
});
