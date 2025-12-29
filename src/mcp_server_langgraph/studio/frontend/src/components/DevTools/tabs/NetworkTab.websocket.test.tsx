/**
 * NetworkTab WebSocket Integration Tests (TDD)
 *
 * Tests for Network tab receiving entries from DevTools WebSocket.
 * This verifies the integration between useDevToolsWebSocket and NetworkTab.
 *
 * Following TDD: RED phase - write failing tests first
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

import { NetworkTab } from "./NetworkTab";
import type { NetworkEntry } from "../types";

// =============================================================================
// Test Data
// =============================================================================

const mockWebSocketNetworkEntries: NetworkEntry[] = [
  {
    id: "ws-net-1",
    method: "GET",
    url: "/api/v1/sessions",
    status: "completed",
    statusCode: 200,
    startTime: Date.now(),
    endTime: Date.now() + 150,
    duration: 150,
    responseSize: 1024,
    source: "api",
  },
  {
    id: "ws-net-2",
    method: "POST",
    url: "/api/v1/chat",
    status: "pending",
    startTime: Date.now() + 1000,
    source: "api",
  },
  {
    id: "ws-net-3",
    method: "GET",
    url: "mcp://tool/execute",
    status: "completed",
    statusCode: 200,
    startTime: Date.now() + 2000,
    duration: 50,
    source: "mcp",
  },
];

// =============================================================================
// Mock Hooks
// =============================================================================

const mockAddEntry = vi.fn();
const mockUpdateEntry = vi.fn();
const mockClearEntries = vi.fn();
const mockToggleRecording = vi.fn();

let mockNetworkEntriesReturn = {
  entries: [] as NetworkEntry[],
  isRecording: true,
  toggleRecording: mockToggleRecording,
  clearEntries: mockClearEntries,
  addEntry: mockAddEntry,
  updateEntry: mockUpdateEntry,
};

vi.mock("../hooks/useNetworkEntries", () => ({
  useNetworkEntries: () => mockNetworkEntriesReturn,
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

describe("NetworkTab WebSocket Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNetworkEntriesReturn = {
      entries: [],
      isRecording: true,
      toggleRecording: mockToggleRecording,
      clearEntries: mockClearEntries,
      addEntry: mockAddEntry,
      updateEntry: mockUpdateEntry,
    };
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("external entries prop", () => {
    it("should accept and display external entries prop", () => {
      // The NetworkTab should be able to receive entries from parent
      // (from useDevToolsWebSocket) via externalEntries prop
      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      expect(screen.getByTestId("network-tab")).toBeInTheDocument();
      expect(screen.getByTestId("network-entry-ws-net-1")).toBeInTheDocument();
      expect(screen.getByTestId("network-entry-ws-net-2")).toBeInTheDocument();
    });

    it("should merge external entries with local entries", () => {
      const localEntries: NetworkEntry[] = [
        {
          id: "local-net-1",
          method: "DELETE",
          url: "/api/v1/sessions/123",
          status: "completed",
          statusCode: 204,
          startTime: Date.now() - 1000,
          duration: 100,
          source: "api",
        },
      ];

      mockNetworkEntriesReturn = {
        ...mockNetworkEntriesReturn,
        entries: localEntries,
      };

      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      // Should show both local and external entries
      expect(
        screen.getByTestId("network-entry-local-net-1"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("network-entry-ws-net-1")).toBeInTheDocument();
    });

    it("should sort entries by startTime when merging", () => {
      const localEntry: NetworkEntry = {
        id: "local-middle",
        method: "PUT",
        url: "/api/v1/users",
        status: "completed",
        statusCode: 200,
        startTime: mockWebSocketNetworkEntries[0].startTime + 500,
        duration: 75,
        source: "api",
      };

      mockNetworkEntriesReturn = {
        ...mockNetworkEntriesReturn,
        entries: [localEntry],
      };

      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      // Check order
      const rows = screen.getAllByTestId(/^network-entry-/);
      expect(rows).toHaveLength(4);

      // Verify order by startTime
      expect(rows[0]).toHaveAttribute("data-testid", "network-entry-ws-net-1");
      expect(rows[1]).toHaveAttribute(
        "data-testid",
        "network-entry-local-middle",
      );
      expect(rows[2]).toHaveAttribute("data-testid", "network-entry-ws-net-2");
      expect(rows[3]).toHaveAttribute("data-testid", "network-entry-ws-net-3");
    });

    it("should filter external entries by type filter", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();

      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      // Click MCP filter
      const mcpFilter = screen.getByTestId("filter-mcp");
      await user.click(mcpFilter);

      // Only MCP entries should show
      expect(screen.getByTestId("network-entry-ws-net-3")).toBeInTheDocument();
      expect(
        screen.queryByTestId("network-entry-ws-net-1"),
      ).not.toBeInTheDocument();
    });

    it("should apply search filter to external entries", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();

      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      const searchInput = screen.getByTestId("network-search");
      await user.type(searchInput, "chat");

      // Wait for debounced search
      await new Promise((r) => setTimeout(r, 200));

      // Only chat endpoint should show
      expect(screen.getByTestId("network-entry-ws-net-2")).toBeInTheDocument();
      expect(
        screen.queryByTestId("network-entry-ws-net-1"),
      ).not.toBeInTheDocument();
    });

    it("should show correct request count with external entries", () => {
      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      expect(screen.getByText("3 requests")).toBeInTheDocument();
    });

    it("should handle external entry updates", () => {
      const updatedEntries: NetworkEntry[] = [
        {
          ...mockWebSocketNetworkEntries[1],
          status: "completed",
          statusCode: 200,
          endTime: Date.now() + 1500,
          duration: 500,
        },
      ];

      const { rerender } = render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      // Verify pending status
      expect(screen.getByTestId("pending-ws-net-2")).toBeInTheDocument();

      // Update with completed entry
      rerender(
        <NetworkTab
          contextEntityId={null}
          externalEntries={[
            mockWebSocketNetworkEntries[0],
            ...updatedEntries,
            mockWebSocketNetworkEntries[2],
          ]}
        />,
      );

      // Should show completed status
      expect(screen.getByTestId("status-ws-net-2")).toBeInTheDocument();
      expect(screen.queryByTestId("pending-ws-net-2")).not.toBeInTheDocument();
    });

    it("should deduplicate entries with same id", () => {
      const duplicateEntry: NetworkEntry = {
        id: "ws-net-1", // Same ID as first WebSocket entry
        method: "GET",
        url: "/api/v1/duplicate",
        status: "completed",
        statusCode: 200,
        startTime: Date.now(),
        source: "api",
      };

      mockNetworkEntriesReturn = {
        ...mockNetworkEntriesReturn,
        entries: [duplicateEntry],
      };

      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
        />,
      );

      // Should show only 3 entries (deduplicated by ID)
      const rows = screen.getAllByTestId(/^network-entry-/);
      expect(rows).toHaveLength(3);
    });

    it("should handle empty external entries", () => {
      mockNetworkEntriesReturn = {
        ...mockNetworkEntriesReturn,
        entries: [mockWebSocketNetworkEntries[0]],
      };

      render(<NetworkTab contextEntityId={null} externalEntries={[]} />);

      // Should still show local entries
      expect(screen.getByTestId("network-entry-ws-net-1")).toBeInTheDocument();
    });

    it("should handle undefined external entries gracefully", () => {
      mockNetworkEntriesReturn = {
        ...mockNetworkEntriesReturn,
        entries: [mockWebSocketNetworkEntries[0]],
      };

      render(
        <NetworkTab
          contextEntityId={null}
          // externalEntries not provided (undefined)
        />,
      );

      // Should show local entries without error
      expect(screen.getByTestId("network-entry-ws-net-1")).toBeInTheDocument();
    });
  });

  describe("onClearExternal callback", () => {
    it("should call onClearExternal when clearing network log", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const handleClearExternal = vi.fn();

      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
          onClearExternal={handleClearExternal}
        />,
      );

      const clearButton = screen.getByTestId("clear-network-button");
      await user.click(clearButton);

      expect(handleClearExternal).toHaveBeenCalled();
      expect(mockClearEntries).toHaveBeenCalled();
    });
  });

  describe("showMCPCalls with external entries", () => {
    it("should hide MCP entries when showMCPCalls is false", () => {
      render(
        <NetworkTab
          contextEntityId={null}
          externalEntries={mockWebSocketNetworkEntries}
          showMCPCalls={false}
        />,
      );

      // MCP entries should be hidden
      expect(
        screen.queryByTestId("network-entry-ws-net-3"),
      ).not.toBeInTheDocument();
      // API entries should still show
      expect(screen.getByTestId("network-entry-ws-net-1")).toBeInTheDocument();
    });
  });
});
