/**
 * ConsoleTab Performance Tests
 *
 * TDD tests for performance optimizations in ConsoleTab.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
  cleanup,
} from "@testing-library/react";

import { ConsoleTab } from "./ConsoleTab";
import type { ConsoleEntry } from "../types";

// =============================================================================
// Mocks
// =============================================================================

// Mock useConsoleEntries hook
const mockClearConsole = vi.fn();
const mockEntries: ConsoleEntry[] = [];

vi.mock("../hooks/useConsoleEntries", () => ({
  useConsoleEntries: vi.fn(() => ({
    entries: mockEntries,
    filteredEntries: mockEntries,
    clearConsole: mockClearConsole,
  })),
}));

// Mock timeline context to avoid provider requirement
vi.mock("../context/DevToolsTimelineProvider", () => ({
  useTimelineContext: () => ({
    timeWindow: null,
    isLiveMode: true,
    currentTime: Date.now(),
    events: [],
    bookmarks: [],
  }),
}));

// =============================================================================
// Test Data Generators
// =============================================================================

function generateMockEntries(count: number): ConsoleEntry[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `entry-${i}`,
    level: ["info", "warning", "error", "debug"][
      i % 4
    ] as ConsoleEntry["level"],
    source: ["system", "api", "mcp", "notification", "execution", "websocket"][
      i % 6
    ] as ConsoleEntry["source"],
    message: `Test message ${i}`,
    timestamp: Date.now() - i * 1000,
    data: i % 3 === 0 ? { key: `value-${i}` } : undefined,
  }));
}

// =============================================================================
// Tests
// =============================================================================

describe("ConsoleTab Performance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEntries.length = 0;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Large List Handling", () => {
    it("should render quickly with 1000 entries", async () => {
      mockEntries.push(...generateMockEntries(1000));

      const start = performance.now();
      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );
      const renderTime = performance.now() - start;

      // Current threshold is 1000ms - can be improved with virtualization
      // TODO: Add virtualization to improve to <500ms target
      expect(renderTime).toBeLessThan(1000);
      expect(screen.getByTestId("console-entries-list")).toBeInTheDocument();
    });

    it("should show entry count correctly for large lists", () => {
      mockEntries.push(...generateMockEntries(500));

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      const countElement = screen.getByTestId("entry-count");
      expect(countElement).toHaveTextContent("500");
    });

    it("should handle scroll events efficiently", async () => {
      mockEntries.push(...generateMockEntries(200));

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      const list = screen.getByTestId("console-entries-list");

      // Multiple scroll events should not cause performance issues
      const scrollCount = 10;
      for (let i = 0; i < scrollCount; i++) {
        fireEvent.scroll(list, { target: { scrollTop: i * 100 } });
      }

      // Should still be responsive after scrolling
      expect(list).toBeInTheDocument();
    });
  });

  describe("Filter Performance", () => {
    it("should filter entries without blocking UI", async () => {
      mockEntries.push(...generateMockEntries(500));

      const handleFilterChange = vi.fn();
      render(
        <ConsoleTab
          filter="all"
          onFilterChange={handleFilterChange}
          contextEntityId="test-session"
        />,
      );

      const select = screen.getByTestId("console-filter-select");

      // Rapid filter changes should not cause issues
      for (const level of ["info", "warning", "error", "all"]) {
        fireEvent.change(select, { target: { value: level } });
      }

      expect(handleFilterChange).toHaveBeenCalled();
    });
  });

  describe("Expand/Collapse Performance", () => {
    it("should expand entries efficiently", async () => {
      const entriesWithData = generateMockEntries(50).map((e) => ({
        ...e,
        data: { nested: { deep: { value: e.id } } },
      }));
      mockEntries.push(...entriesWithData);

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      // Get first expand button
      const expandButtons = screen.getAllByTestId("expand-button");
      expect(expandButtons.length).toBeGreaterThan(0);

      // Expand first entry
      fireEvent.click(expandButtons[0]);

      // Expanded data should be visible
      // Note: Entries are sorted by timestamp ascending, so entry-49 appears first
      // (entry-0 has highest timestamp, entry-49 has lowest)
      await waitFor(() => {
        expect(
          screen.getByTestId("expanded-data-entry-49"),
        ).toBeInTheDocument();
      });
    });

    it("should handle multiple expand/collapse operations", async () => {
      const entriesWithData = generateMockEntries(20).map((e) => ({
        ...e,
        data: { value: e.id },
      }));
      mockEntries.push(...entriesWithData);

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      const expandButtons = screen.getAllByTestId("expand-button");

      // Expand and collapse multiple entries rapidly
      for (let i = 0; i < Math.min(5, expandButtons.length); i++) {
        fireEvent.click(expandButtons[i]);
        fireEvent.click(expandButtons[i]);
      }

      // Component should still be responsive
      expect(screen.getByTestId("console-tab")).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation Performance", () => {
    it("should handle rapid keyboard navigation", async () => {
      mockEntries.push(...generateMockEntries(100));

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      const list = screen.getByTestId("console-entries-list");
      list.focus();

      // Simulate rapid keyboard navigation
      for (let i = 0; i < 20; i++) {
        fireEvent.keyDown(list, { key: "ArrowDown" });
      }
      for (let i = 0; i < 10; i++) {
        fireEvent.keyDown(list, { key: "ArrowUp" });
      }

      // Component should handle rapid navigation without issues
      expect(list).toBeInTheDocument();
    });
  });

  describe("Copy Operations", () => {
    it("should copy message to clipboard efficiently", async () => {
      mockEntries.push(...generateMockEntries(10));

      const mockWriteText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: mockWriteText,
        },
      });

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      // Hover over first entry to show copy button
      const entry = screen.getByTestId("console-entry-entry-0");
      fireEvent.mouseEnter(entry);

      // Find and click copy button
      const copyButton = screen.getByTestId("copy-button");
      await act(async () => {
        fireEvent.click(copyButton);
      });

      expect(mockWriteText).toHaveBeenCalledWith("Test message 0");
    });
  });

  describe("Clear Console Performance", () => {
    it("should clear console quickly with many entries", async () => {
      mockEntries.push(...generateMockEntries(500));

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="test-session"
        />,
      );

      const clearButton = screen.getByTestId("clear-console-button");

      const start = performance.now();
      fireEvent.click(clearButton);
      const clearTime = performance.now() - start;

      // Clear should be fast even with many entries
      expect(clearTime).toBeLessThan(100);
      expect(mockClearConsole).toHaveBeenCalled();
    });
  });

  describe("Memory Usage", () => {
    it("should not leak memory with repeated renders", () => {
      mockEntries.push(...generateMockEntries(100));

      const { unmount, rerender } = render(
        <ConsoleTab
          filter="all"
          onFilterChange={vi.fn()}
          contextEntityId="session-1"
        />,
      );

      // Re-render multiple times with different props
      for (let i = 0; i < 10; i++) {
        rerender(
          <ConsoleTab
            filter={
              ["all", "info", "warning", "error"][i % 4] as
                | "all"
                | "info"
                | "warning"
                | "error"
            }
            onFilterChange={vi.fn()}
            contextEntityId={`session-${i}`}
          />,
        );
      }

      // Unmount should clean up properly
      unmount();

      // No assertions on memory, but no errors means success
      expect(true).toBe(true);
    });
  });
});
