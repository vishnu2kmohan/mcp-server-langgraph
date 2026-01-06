/**
 * useDevToolsTimeline Playback Tests
 *
 * Tests for time navigation and playback controls:
 * - Time navigation (set time, clamp, jump to start/end, step forward/backward)
 * - Playback (start, stop, advance, speed)
 * - Bookmarks (add, remove, jump to)
 * - Clear and reset
 * - isAtEnd state
 * - Live mode
 * - Cross-source time travel
 *
 * @see useDevToolsTimeline.fixtures.ts for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useDevToolsTimeline } from "../useDevToolsTimeline";
import {
  generateTraceId,
  generateSpanId,
} from "./useDevToolsTimeline.fixtures";

describe("useDevToolsTimeline - Playback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ===========================================================================
  // TIME NAVIGATION
  // ===========================================================================

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

  // ===========================================================================
  // PLAYBACK
  // ===========================================================================

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

  // ===========================================================================
  // BOOKMARKS
  // ===========================================================================

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

  // ===========================================================================
  // CLEAR AND RESET
  // ===========================================================================

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

  // ===========================================================================
  // IS AT END STATE
  // ===========================================================================

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

  // ===========================================================================
  // LIVE MODE
  // ===========================================================================

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
  // CROSS-SOURCE TIME TRAVEL
  // ===========================================================================

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
