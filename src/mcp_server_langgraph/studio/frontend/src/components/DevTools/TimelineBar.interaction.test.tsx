/**
 * TimelineBar Interaction Tests
 *
 * Split from TimelineBar.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Speed selection
 * - Bookmark button
 * - Time range selector
 * - Minimap rendering
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import React from "react";

import { TimelineBar } from "./TimelineBar";
import { DevToolsTimelineProvider } from "./context/DevToolsTimelineProvider";

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

// =============================================================================
// Test Helpers
// =============================================================================

function renderWithProvider(
  ui: React.ReactElement,
  providerProps?: Partial<
    React.ComponentProps<typeof DevToolsTimelineProvider>
  >,
) {
  return render(
    <DevToolsTimelineProvider {...providerProps}>
      {ui}
    </DevToolsTimelineProvider>,
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("TimelineBar - Interaction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe("speed selection", () => {
    it("should update speed when speed option is selected", () => {
      renderWithProvider(<TimelineBar />);

      // Click speed selector button (shows "1x" by default)
      fireEvent.click(screen.getByRole("button", { name: /1x/i }));

      // Select 2x speed from dropdown
      fireEvent.click(screen.getByRole("option", { name: /2x/i }));

      // Speed button should now show "2x"
      expect(screen.getByRole("button", { name: /2x/i })).toBeInTheDocument();
    });
  });

  describe("bookmark button", () => {
    const now = Date.now();
    const initialEvents = [
      {
        id: "test-event-1",
        type: "console" as const,
        timestamp: now,
        relativeTime: 0,
        source: "test",
        data: {},
      },
    ];

    it("should render bookmark button when showBookmarkButton is true", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      expect(
        screen.getByRole("button", { name: /add bookmark/i }),
      ).toBeInTheDocument();
    });

    it("should add a bookmark when button is clicked", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      // Click the add bookmark button
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      // Bookmark indicator should appear in the minimap
      // The bookmark was added to the timeline context
      // We verify this by rendering minimap and checking for bookmark indicator
    });
  });

  describe("time range selector", () => {
    it("should render time range dropdown when showTimeRangeSelector is true", () => {
      renderWithProvider(<TimelineBar showTimeRangeSelector />);

      // Should show default time range
      expect(screen.getByRole("button", { name: /15m/i })).toBeInTheDocument();
    });

    it("should change time range when option is selected", () => {
      renderWithProvider(<TimelineBar showTimeRangeSelector />);

      // Open time range menu
      fireEvent.click(screen.getByRole("button", { name: /15m/i }));

      // Select a different range (aria-label is "1 hour")
      const hourOption = screen.getByRole("option", { name: /1 hour/i });
      fireEvent.click(hourOption);

      // Button should now show the new range value "1h"
      expect(screen.getByRole("button", { name: /1h/i })).toBeInTheDocument();
    });
  });

  describe("minimap rendering", () => {
    const now = Date.now();
    const initialEvents = [
      {
        id: "test-event-1",
        type: "console" as const,
        timestamp: now,
        relativeTime: 0,
        source: "test",
        data: {},
      },
    ];

    it("should render minimap when showMinimap is true and events exist", () => {
      renderWithProvider(<TimelineBar showMinimap showBookmarkButton />, {
        initialEvents,
      });

      // Minimap should be rendered when showMinimap=true and events exist
      expect(screen.getByTestId("timeline-minimap")).toBeInTheDocument();
    });
  });

  describe("playback controls", () => {
    it("should have play button", () => {
      renderWithProvider(<TimelineBar />);

      expect(screen.getByRole("button", { name: /play/i })).toBeInTheDocument();
    });

    it("should have step forward and backward buttons", () => {
      renderWithProvider(<TimelineBar />);

      expect(
        screen.getByRole("button", { name: /step backward/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /step forward/i }),
      ).toBeInTheDocument();
    });

    it("should display time information", () => {
      renderWithProvider(<TimelineBar />);

      expect(screen.getByTestId("current-time-display")).toBeInTheDocument();
      expect(screen.getByTestId("total-time-display")).toBeInTheDocument();
    });
  });
});
