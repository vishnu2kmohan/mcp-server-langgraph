/**
 * TimelineBar Interaction Tests
 *
 * Split from TimelineBar.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Persistence callbacks
 * - Bookmark management
 * - Motion animations
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

  describe("persistence callbacks", () => {
    it("should call onPlaybackSpeedChange when speed is selected", () => {
      const onPlaybackSpeedChange = vi.fn();
      renderWithProvider(
        <TimelineBar onPlaybackSpeedChange={onPlaybackSpeedChange} />,
      );

      // Click speed selector button (shows "1x" by default)
      fireEvent.click(screen.getByRole("button", { name: /1x/i }));

      // Select 2x speed from dropdown
      fireEvent.click(screen.getByRole("option", { name: /2x/i }));

      expect(onPlaybackSpeedChange).toHaveBeenCalledWith(2);
    });

    it("should call onBookmarkAdd when bookmark is added via menu", () => {
      const onBookmarkAdd = vi.fn();
      const now = Date.now();
      // Provide initial events so the bookmark button is enabled
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
      renderWithProvider(
        <TimelineBar showBookmarkButton onBookmarkAdd={onBookmarkAdd} />,
        { initialEvents },
      );

      // Open bookmark menu
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      // Click add bookmark in menu
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      expect(onBookmarkAdd).toHaveBeenCalledWith(
        expect.objectContaining({
          id: expect.any(String),
          time: expect.any(Number),
          label: expect.stringMatching(/Bookmark \d+/),
        }),
      );
    });
  });

  describe("bookmark management", () => {
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

    it("should open bookmark menu when clicked", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      expect(screen.getByTestId("bookmark-menu")).toBeInTheDocument();
    });

    it("should show 'No bookmarks yet' when empty", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      expect(screen.getByText(/no bookmarks yet/i)).toBeInTheDocument();
    });

    it("should display bookmark count in button", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      // Add a bookmark first
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Re-open menu and check count
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      // Button should show "1" as bookmark count
      const button = screen.getByRole("button", { name: /add bookmark/i });
      expect(button).toHaveTextContent("1");
    });

    it("should display bookmark items in menu", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      // Add a bookmark
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Re-open menu
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      expect(screen.getByTestId("bookmark-item")).toBeInTheDocument();
      expect(screen.getByText(/Bookmark 1/)).toBeInTheDocument();
    });

    it("should call onBookmarkRemove when bookmark is deleted", () => {
      const onBookmarkRemove = vi.fn();
      renderWithProvider(
        <TimelineBar showBookmarkButton onBookmarkRemove={onBookmarkRemove} />,
        { initialEvents },
      );

      // Add a bookmark first
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Re-open menu
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      // Click remove button on bookmark
      fireEvent.click(
        screen.getByRole("button", { name: /remove bookmark 1/i }),
      );

      expect(onBookmarkRemove).toHaveBeenCalledWith(expect.any(String));
    });

    it("should jump to bookmark when clicked", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      // Add a bookmark
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Re-open menu
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      // Click on bookmark to jump
      fireEvent.click(
        screen.getByRole("button", { name: /jump to bookmark 1/i }),
      );

      // Menu should close after jumping
      expect(screen.queryByTestId("bookmark-menu")).not.toBeInTheDocument();
    });

    it("should have proper ARIA attributes on bookmark button", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      const button = screen.getByRole("button", { name: /add bookmark/i });
      expect(button).toHaveAttribute("aria-haspopup", "menu");
      expect(button).toHaveAttribute("aria-expanded", "false");

      fireEvent.click(button);
      expect(button).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("Motion animations", () => {
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

    it("should render speed dropdown with motion wrapper", () => {
      renderWithProvider(<TimelineBar />);

      // Open speed menu
      fireEvent.click(screen.getByRole("button", { name: /1x/i }));

      // Dropdown should be wrapped in motion component
      const dropdown = screen.getByTestId("speed-dropdown");
      expect(dropdown).toBeInTheDocument();
    });

    it("should render time range dropdown with motion wrapper", () => {
      renderWithProvider(<TimelineBar showTimeRangeSelector />);

      // Open time range menu
      fireEvent.click(screen.getByRole("button", { name: /15m/i }));

      // Dropdown should be wrapped in motion component
      const dropdown = screen.getByTestId("time-range-dropdown");
      expect(dropdown).toBeInTheDocument();
    });

    it("should render bookmark dropdown with motion wrapper", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      // Open bookmark menu
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      // Menu should be wrapped in motion component
      const menu = screen.getByTestId("bookmark-menu");
      expect(menu).toBeInTheDocument();
    });

    it("should render minimap when showMinimap is true and events exist", () => {
      renderWithProvider(<TimelineBar showMinimap showBookmarkButton />, {
        initialEvents,
      });

      // Minimap should be rendered when showMinimap=true and events exist
      expect(screen.getByTestId("timeline-minimap")).toBeInTheDocument();
    });

    it("should animate bookmark items with stagger effect", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />, { initialEvents });

      // Add two bookmarks
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));
      fireEvent.click(
        screen.getByRole("menuitem", { name: /add bookmark at current time/i }),
      );

      // Re-open menu
      fireEvent.click(screen.getByRole("button", { name: /add bookmark/i }));

      // Bookmark items should be wrapped with motion
      const items = screen.getAllByTestId("bookmark-item");
      expect(items.length).toBe(2);
    });
  });
});
