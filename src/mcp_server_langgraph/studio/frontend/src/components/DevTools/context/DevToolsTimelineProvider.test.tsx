/**
 * DevToolsTimelineProvider Tests
 *
 * TDD tests for the unified timeline context provider.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import React from "react";

import {
  DevToolsTimelineProvider,
  useTimelineContext,
  type TimelineContextValue,
} from "./DevToolsTimelineProvider";

// =============================================================================
// Test Consumer Component
// =============================================================================

function TestConsumer({
  onContext,
}: {
  onContext?: (ctx: TimelineContextValue) => void;
}) {
  const timeline = useTimelineContext();
  React.useEffect(() => {
    onContext?.(timeline);
  }, [timeline, onContext]);

  return (
    <div>
      <span data-testid="event-count">{timeline.events.length}</span>
      <span data-testid="current-time">{timeline.currentTime}</span>
      <span data-testid="is-playing">
        {timeline.isPlaying ? "true" : "false"}
      </span>
      <span data-testid="is-live-mode">
        {timeline.isLiveMode ? "true" : "false"}
      </span>
      <button
        data-testid="register-event"
        onClick={() =>
          timeline.registerEvent({
            type: "console",
            timestamp: Date.now(),
            data: { message: "Test" },
          })
        }
      >
        Add Event
      </button>
      <button
        data-testid="start-playback"
        onClick={() => timeline.startPlayback()}
      >
        Play
      </button>
      <button
        data-testid="stop-playback"
        onClick={() => timeline.stopPlayback()}
      >
        Stop
      </button>
    </div>
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("DevToolsTimelineProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("context provision", () => {
    it("should provide timeline context to children", () => {
      render(
        <DevToolsTimelineProvider>
          <TestConsumer />
        </DevToolsTimelineProvider>,
      );

      expect(screen.getByTestId("event-count")).toHaveTextContent("0");
      expect(screen.getByTestId("is-live-mode")).toHaveTextContent("true");
    });

    it("should throw error when used outside provider", () => {
      // Suppress console.error for this test
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      expect(() => render(<TestConsumer />)).toThrow(
        "useTimelineContext must be used within a DevToolsTimelineProvider",
      );

      consoleSpy.mockRestore();
    });

    it("should accept initial options", () => {
      const sessionStart = Date.now();

      render(
        <DevToolsTimelineProvider sessionStartTime={sessionStart}>
          <TestConsumer />
        </DevToolsTimelineProvider>,
      );

      expect(screen.getByTestId("event-count")).toHaveTextContent("0");
    });
  });

  describe("shared state", () => {
    it("should share state between multiple consumers", () => {
      let context1: TimelineContextValue | undefined;
      let context2: TimelineContextValue | undefined;

      render(
        <DevToolsTimelineProvider>
          <TestConsumer
            onContext={(ctx) => {
              context1 = ctx;
            }}
          />
          <TestConsumer
            onContext={(ctx) => {
              context2 = ctx;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      // Register an event via the first consumer
      act(() => {
        context1?.registerEvent({
          type: "console",
          timestamp: 100,
          data: { message: "Shared event" },
        });
      });

      // Both consumers should see the event
      expect(context1?.events).toHaveLength(1);
      expect(context2?.events).toHaveLength(1);
      expect(context2?.events[0].data).toEqual({ message: "Shared event" });
    });

    it("should sync current time across consumers", () => {
      let context1: TimelineContextValue | undefined;
      let context2: TimelineContextValue | undefined;

      render(
        <DevToolsTimelineProvider>
          <TestConsumer
            onContext={(ctx) => {
              context1 = ctx;
            }}
          />
          <TestConsumer
            onContext={(ctx) => {
              context2 = ctx;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      // Register events and navigate
      act(() => {
        context1?.registerEvent({ type: "console", timestamp: 100, data: {} });
        context1?.registerEvent({ type: "console", timestamp: 500, data: {} });
      });

      act(() => {
        context1?.setCurrentTime(300);
      });

      // Both should have same current time
      expect(context1?.currentTime).toBe(300);
      expect(context2?.currentTime).toBe(300);
    });
  });

  describe("event registration", () => {
    it("should register events from any consumer", () => {
      render(
        <DevToolsTimelineProvider>
          <TestConsumer />
        </DevToolsTimelineProvider>,
      );

      act(() => {
        screen.getByTestId("register-event").click();
      });

      expect(screen.getByTestId("event-count")).toHaveTextContent("1");
    });
  });

  describe("playback controls", () => {
    it("should control playback state from context", () => {
      let ctx: TimelineContextValue | undefined;

      render(
        <DevToolsTimelineProvider>
          <TestConsumer
            onContext={(c) => {
              ctx = c;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      // Add events first
      act(() => {
        ctx?.registerEvent({ type: "console", timestamp: 100, data: {} });
        ctx?.registerEvent({ type: "console", timestamp: 500, data: {} });
      });

      expect(screen.getByTestId("is-playing")).toHaveTextContent("false");

      act(() => {
        screen.getByTestId("start-playback").click();
      });

      expect(screen.getByTestId("is-playing")).toHaveTextContent("true");

      act(() => {
        screen.getByTestId("stop-playback").click();
      });

      expect(screen.getByTestId("is-playing")).toHaveTextContent("false");
    });
  });

  describe("filtering", () => {
    it("should apply time window filter across all consumers", () => {
      let context: TimelineContextValue | undefined;

      render(
        <DevToolsTimelineProvider>
          <TestConsumer
            onContext={(ctx) => {
              context = ctx;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      act(() => {
        context?.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        context?.registerEvent({
          type: "console",
          timestamp: 200,
          data: { id: 2 },
        });
        context?.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 3 },
        });
      });

      act(() => {
        context?.setTimeWindow(150, 250);
      });

      const windowedEvents = context?.getEventsInWindow();
      expect(windowedEvents).toHaveLength(1);
      expect(windowedEvents?.[0].data).toEqual({ id: 2 });
    });

    it("should apply span selection filter", () => {
      let context: TimelineContextValue | undefined;
      const spanId = "test-span-123";

      render(
        <DevToolsTimelineProvider>
          <TestConsumer
            onContext={(ctx) => {
              context = ctx;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      act(() => {
        // Span from 100-600 (500ms duration)
        context?.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 500 },
        });
        context?.registerEvent({
          type: "console",
          timestamp: 200,
          data: { in: true },
        });
        context?.registerEvent({
          type: "console",
          timestamp: 700,
          data: { in: false },
        });
      });

      act(() => {
        context?.selectSpan(spanId);
      });

      const spanEvents = context?.getEventsInSelectedSpan();
      expect(spanEvents).toHaveLength(1);
      expect(spanEvents?.[0].data).toEqual({ in: true });
    });
  });

  describe("callbacks", () => {
    it("should call onTimeChange callback", () => {
      const onTimeChange = vi.fn();
      let context: TimelineContextValue | undefined;

      render(
        <DevToolsTimelineProvider onTimeChange={onTimeChange}>
          <TestConsumer
            onContext={(ctx) => {
              context = ctx;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      act(() => {
        context?.registerEvent({ type: "console", timestamp: 100, data: {} });
        context?.setCurrentTime(100);
      });

      expect(onTimeChange).toHaveBeenCalledWith(100);
    });

    it("should call onEventRegistered callback", () => {
      const onEventRegistered = vi.fn();

      render(
        <DevToolsTimelineProvider onEventRegistered={onEventRegistered}>
          <TestConsumer />
        </DevToolsTimelineProvider>,
      );

      act(() => {
        screen.getByTestId("register-event").click();
      });

      expect(onEventRegistered).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "console",
        }),
      );
    });
  });

  describe("reset and clear", () => {
    it("should reset all state", () => {
      let context: TimelineContextValue | undefined;

      render(
        <DevToolsTimelineProvider>
          <TestConsumer
            onContext={(ctx) => {
              context = ctx;
            }}
          />
        </DevToolsTimelineProvider>,
      );

      act(() => {
        context?.registerEvent({ type: "console", timestamp: 100, data: {} });
        context?.setTimeWindow(50, 150);
        context?.addBookmark("Test");
      });

      expect(context?.events).toHaveLength(1);
      expect(context?.timeWindow).not.toBeNull();
      expect(context?.bookmarks).toHaveLength(1);

      act(() => {
        context?.reset();
      });

      expect(context?.events).toHaveLength(0);
      expect(context?.timeWindow).toBeNull();
      expect(context?.bookmarks).toHaveLength(0);
    });
  });
});
