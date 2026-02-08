/**
 * HumanTimestamp Component Tests
 *
 * TDD: Enhanced tests for relative time format support.
 */
import { cleanup, render, screen, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HumanTimestamp } from "./HumanTimestamp";

import { TestProvider } from "@/test-utils";

// Fixed "now" for testing relative times
const MOCK_NOW = new Date("2026-01-15T14:30:00.000Z").getTime();

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(MOCK_NOW);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("HumanTimestamp", () => {
  // ===========================================================================
  // Existing Tests (Updated for new default behavior)
  // ===========================================================================

  describe("time format (explicit)", () => {
    it("renders formatted time and tooltip", () => {
      const ts = Date.UTC(2024, 0, 1, 12, 34, 56, 789);
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="time" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el).toBeInTheDocument();
      expect(el).toHaveAttribute("title", "2024-01-01T12:34:56.789Z");
      // Time format shows HH:MM:SS.mmm - timezone independent check
      expect(el.textContent).toMatch(/\d{2}:\d{2}:56\.789/);
    });
  });

  describe("invalid timestamps", () => {
    it("returns null for invalid timestamp", () => {
      const { container } = render(
        <TestProvider>
          <HumanTimestamp timestamp={"not-a-date"} />
        </TestProvider>,
      );
      expect(container.textContent).toBe("");
    });
  });

  // ===========================================================================
  // Relative Time Format Tests (New)
  // ===========================================================================

  describe("relative format", () => {
    it("should show 'just now' for timestamps less than 1 minute ago", () => {
      const ts = MOCK_NOW - 30 * 1000; // 30 seconds ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el.textContent).toMatch(/just now|<1m|now/i);
    });

    it("should show '5m ago' for timestamps 5 minutes ago", () => {
      const ts = MOCK_NOW - 5 * 60 * 1000; // 5 minutes ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el.textContent).toMatch(/5\s?m(\s?ago)?/i);
    });

    it("should show '2h ago' for timestamps 2 hours ago", () => {
      const ts = MOCK_NOW - 2 * 60 * 60 * 1000; // 2 hours ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el.textContent).toMatch(/2\s?h(\s?ago)?/i);
    });

    it("should show '1d ago' for timestamps 1 day ago", () => {
      const ts = MOCK_NOW - 24 * 60 * 60 * 1000; // 1 day ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el.textContent).toMatch(/1\s?d(\s?ago)?/i);
    });

    it("should show full absolute timestamp in tooltip", () => {
      const ts = MOCK_NOW - 5 * 60 * 1000; // 5 minutes ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el).toHaveAttribute("title");
      expect(el.getAttribute("title")).toContain("2026-01-15");
    });

    it("should handle future timestamps gracefully", () => {
      const ts = MOCK_NOW + 60 * 60 * 1000; // 1 hour in future
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      // Should show something like "in 1h" or fallback to absolute time
      expect(el.textContent).toBeTruthy();
    });
  });

  // ===========================================================================
  // Default Format Tests
  // ===========================================================================

  describe("default format", () => {
    it("should default to relative format when no format specified", () => {
      const ts = MOCK_NOW - 10 * 60 * 1000; // 10 minutes ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      // Default should now be relative
      expect(el.textContent).toMatch(/10\s?m(\s?ago)?/i);
    });
  });

  // ===========================================================================
  // Auto-Update Tests
  // ===========================================================================

  describe("auto-update", () => {
    it("should update relative time display after 30 seconds", async () => {
      const ts = MOCK_NOW - 29 * 1000; // 29 seconds ago - "just now"
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="relative" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      const initialText = el.textContent;

      // Advance time by 35 seconds (now 64 seconds ago - "1m ago")
      await act(async () => {
        await vi.advanceTimersByTimeAsync(35000);
      });

      // Text should have updated
      const updatedText = el.textContent;
      expect(updatedText).not.toBe(initialText);
    });
  });

  // ===========================================================================
  // Both Format Tests
  // ===========================================================================

  describe("both format", () => {
    it("should show relative and absolute time when format is 'both'", () => {
      const ts = MOCK_NOW - 5 * 60 * 1000; // 5 minutes ago
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="both" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      // Should contain both relative and absolute
      expect(el.textContent).toMatch(/5\s?m/i);
      // Tooltip still shows full ISO
      expect(el).toHaveAttribute("title");
    });
  });

  // ===========================================================================
  // Datetime Format Tests (Existing)
  // ===========================================================================

  describe("datetime format", () => {
    it("should show full datetime with timezone", () => {
      const ts = Date.UTC(2024, 0, 1, 12, 34, 56, 789);
      render(
        <TestProvider>
          <HumanTimestamp timestamp={ts} format="datetime" />
        </TestProvider>,
      );

      const el = screen.getByTestId("human-timestamp");
      expect(el.textContent).toMatch(/2024/);
    });
  });
});
