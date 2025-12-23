/**
 * TimelineBar Component Tests
 *
 * TDD tests for the unified timeline scrubber component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import React from "react";

import { TimelineBar } from "./TimelineBar";
import { DevToolsTimelineProvider } from "./context/DevToolsTimelineProvider";

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

describe("TimelineBar", () => {
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

  describe("rendering", () => {
    it("should render without crashing", () => {
      renderWithProvider(<TimelineBar />);
      expect(screen.getByTestId("timeline-bar")).toBeInTheDocument();
    });

    it("should display playback controls", () => {
      renderWithProvider(<TimelineBar />);
      expect(
        screen.getByRole("button", { name: /jump to start/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /play/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /jump to end/i }),
      ).toBeInTheDocument();
    });

    it("should display time information", () => {
      renderWithProvider(<TimelineBar />);
      expect(screen.getByTestId("current-time-display")).toBeInTheDocument();
      expect(screen.getByTestId("total-time-display")).toBeInTheDocument();
    });

    it("should display live mode toggle", () => {
      renderWithProvider(<TimelineBar />);
      expect(screen.getByRole("button", { name: /live/i })).toBeInTheDocument();
    });

    it("should display scrubber/slider", () => {
      renderWithProvider(<TimelineBar />);
      expect(screen.getByRole("slider")).toBeInTheDocument();
    });
  });

  describe("disabled state", () => {
    it("should disable controls when no events exist", () => {
      renderWithProvider(<TimelineBar />);
      expect(screen.getByRole("button", { name: /play/i })).toBeDisabled();
      expect(screen.getByRole("slider")).toBeDisabled();
    });
  });

  describe("optional features", () => {
    it("should display bookmark button when showBookmarkButton is true", () => {
      renderWithProvider(<TimelineBar showBookmarkButton />);
      expect(
        screen.getByRole("button", { name: /add bookmark/i }),
      ).toBeInTheDocument();
    });

    it("should display export button when showExport is true", () => {
      renderWithProvider(<TimelineBar showExport />);
      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });

    it("should display time range selector when showTimeRangeSelector is true", () => {
      renderWithProvider(<TimelineBar showTimeRangeSelector />);
      expect(screen.getByRole("button", { name: /15m/i })).toBeInTheDocument();
    });

    it("should call onExport when export button clicked", () => {
      const onExport = vi.fn();
      renderWithProvider(<TimelineBar showExport onExport={onExport} />);

      fireEvent.click(screen.getByRole("button", { name: /export/i }));
      expect(onExport).toHaveBeenCalled();
    });
  });

  describe("compact mode", () => {
    it("should render in compact mode when compact prop is true", () => {
      renderWithProvider(<TimelineBar compact />);
      const bar = screen.getByTestId("timeline-bar");
      expect(bar).toHaveClass("compact");
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA labels on controls", () => {
      renderWithProvider(<TimelineBar />);
      const slider = screen.getByRole("slider");
      expect(slider).toHaveAttribute("aria-label", "Timeline position");
    });
  });
});
