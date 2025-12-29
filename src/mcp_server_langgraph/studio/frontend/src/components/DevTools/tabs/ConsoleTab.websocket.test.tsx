/**
 * ConsoleTab WebSocket Integration Tests (TDD)
 *
 * Tests for Console tab receiving entries from DevTools WebSocket.
 * This verifies the integration between useDevToolsWebSocket and ConsoleTab.
 *
 * Following TDD: RED phase - write failing tests first
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

import { ConsoleTab } from "./ConsoleTab";
import type { ConsoleEntry } from "../types";

// =============================================================================
// Test Data
// =============================================================================

const mockWebSocketEntries: ConsoleEntry[] = [
  {
    id: "ws-entry-1",
    level: "info",
    source: "websocket",
    message: "WebSocket message received",
    timestamp: Date.now(),
  },
  {
    id: "ws-entry-2",
    level: "error",
    source: "websocket",
    message: "Connection error",
    timestamp: Date.now() + 1000,
  },
];

// =============================================================================
// Mock Hooks
// =============================================================================

const mockAddEntry = vi.fn();
const mockClearConsole = vi.fn();

let mockConsoleEntriesReturn = {
  entries: [] as ConsoleEntry[],
  filteredEntries: [] as ConsoleEntry[],
  clearConsole: mockClearConsole,
  isLoading: false,
  addEntry: mockAddEntry,
  counts: { info: 0, warning: 0, error: 0, debug: 0, total: 0 },
};

vi.mock("../hooks/useConsoleEntries", () => ({
  useConsoleEntries: () => mockConsoleEntriesReturn,
}));

// Mock timeline context
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
// Tests
// =============================================================================

describe("ConsoleTab WebSocket Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConsoleEntriesReturn = {
      entries: [],
      filteredEntries: [],
      clearConsole: mockClearConsole,
      isLoading: false,
      addEntry: mockAddEntry,
      counts: { info: 0, warning: 0, error: 0, debug: 0, total: 0 },
    };
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("external entries prop", () => {
    it("should accept and display external entries prop", () => {
      // The ConsoleTab should be able to receive entries from parent
      // (from useDevToolsWebSocket) via externalEntries prop
      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
        />,
      );

      expect(screen.getByTestId("console-tab")).toBeInTheDocument();
      expect(
        screen.getByText("WebSocket message received"),
      ).toBeInTheDocument();
      expect(screen.getByText("Connection error")).toBeInTheDocument();
    });

    it("should merge external entries with local entries", () => {
      const localEntries: ConsoleEntry[] = [
        {
          id: "local-1",
          level: "info",
          source: "system",
          message: "Local system message",
          timestamp: Date.now() - 1000,
        },
      ];

      mockConsoleEntriesReturn = {
        ...mockConsoleEntriesReturn,
        entries: localEntries,
        filteredEntries: localEntries,
        counts: { info: 1, warning: 0, error: 0, debug: 0, total: 1 },
      };

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
        />,
      );

      // Should show both local and external entries
      expect(screen.getByText("Local system message")).toBeInTheDocument();
      expect(
        screen.getByText("WebSocket message received"),
      ).toBeInTheDocument();
    });

    it("should sort entries by timestamp when merging", () => {
      const localEntry: ConsoleEntry = {
        id: "local-middle",
        level: "info",
        source: "system",
        message: "Middle message",
        timestamp: mockWebSocketEntries[0].timestamp + 500, // Between WS entries
      };

      mockConsoleEntriesReturn = {
        ...mockConsoleEntriesReturn,
        entries: [localEntry],
        filteredEntries: [localEntry],
        counts: { info: 1, warning: 0, error: 0, debug: 0, total: 1 },
      };

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
        />,
      );

      // Check order by finding all entries and verifying sequence
      const entries = screen.getAllByTestId(/^console-entry-/);
      expect(entries).toHaveLength(3);

      // First: ws-entry-1 (earliest timestamp)
      expect(entries[0]).toHaveAttribute(
        "data-testid",
        "console-entry-ws-entry-1",
      );
      // Second: local-middle (middle timestamp)
      expect(entries[1]).toHaveAttribute(
        "data-testid",
        "console-entry-local-middle",
      );
      // Third: ws-entry-2 (latest timestamp)
      expect(entries[2]).toHaveAttribute(
        "data-testid",
        "console-entry-ws-entry-2",
      );
    });

    it("should update count to include external entries", () => {
      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
        />,
      );

      // Count should include external entries
      expect(screen.getByTestId("entry-count")).toHaveTextContent("2");
    });

    it("should filter external entries by level", () => {
      render(
        <ConsoleTab
          filter="error"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
        />,
      );

      // Only error entries should show
      expect(screen.getByText("Connection error")).toBeInTheDocument();
      expect(
        screen.queryByText("WebSocket message received"),
      ).not.toBeInTheDocument();
    });

    it("should deduplicate entries with same id", () => {
      const duplicateEntry: ConsoleEntry = {
        id: "ws-entry-1", // Same ID as first WebSocket entry
        level: "info",
        source: "system",
        message: "Duplicate message",
        timestamp: Date.now(),
      };

      mockConsoleEntriesReturn = {
        ...mockConsoleEntriesReturn,
        entries: [duplicateEntry],
        filteredEntries: [duplicateEntry],
      };

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
        />,
      );

      // Should show only 2 entries (deduplicated by ID)
      const entries = screen.getAllByTestId(/^console-entry-/);
      expect(entries).toHaveLength(2);
    });

    it("should handle empty external entries", () => {
      mockConsoleEntriesReturn = {
        ...mockConsoleEntriesReturn,
        entries: [mockWebSocketEntries[0]],
        filteredEntries: [mockWebSocketEntries[0]],
        counts: { info: 1, warning: 0, error: 0, debug: 0, total: 1 },
      };

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={[]}
        />,
      );

      // Should still show local entries
      expect(
        screen.getByText("WebSocket message received"),
      ).toBeInTheDocument();
    });

    it("should handle undefined external entries gracefully", () => {
      mockConsoleEntriesReturn = {
        ...mockConsoleEntriesReturn,
        entries: [mockWebSocketEntries[0]],
        filteredEntries: [mockWebSocketEntries[0]],
        counts: { info: 1, warning: 0, error: 0, debug: 0, total: 1 },
      };

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          // externalEntries not provided (undefined)
        />,
      );

      // Should show local entries without error
      expect(
        screen.getByText("WebSocket message received"),
      ).toBeInTheDocument();
    });
  });

  describe("onClearExternal callback", () => {
    it("should call onClearExternal when clearing console", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const handleClearExternal = vi.fn();

      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          externalEntries={mockWebSocketEntries}
          onClearExternal={handleClearExternal}
        />,
      );

      const clearButton = screen.getByTestId("clear-console-button");
      await user.click(clearButton);

      expect(handleClearExternal).toHaveBeenCalled();
      expect(mockClearConsole).toHaveBeenCalled();
    });
  });
});
