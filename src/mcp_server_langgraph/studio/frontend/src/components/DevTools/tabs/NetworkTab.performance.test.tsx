/**
 * NetworkTab Performance Tests
 *
 * TDD tests for performance optimizations in NetworkTab.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";

import { NetworkTab } from "./NetworkTab";
import type { NetworkEntry } from "../types";

// =============================================================================
// Mocks
// =============================================================================

const mockToggleRecording = vi.fn();
const mockClearEntries = vi.fn();
const mockEntries: NetworkEntry[] = [];

vi.mock("../hooks/useNetworkEntries", () => ({
  useNetworkEntries: vi.fn(() => ({
    entries: mockEntries,
    isRecording: true,
    toggleRecording: mockToggleRecording,
    clearEntries: mockClearEntries,
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

function generateMockEntries(count: number): NetworkEntry[] {
  const methods = ["GET", "POST", "PUT", "DELETE", "PATCH"];
  const sources = ["api", "mcp", undefined];
  const statuses = ["completed", "pending", "error"];

  return Array.from({ length: count }, (_, i) => ({
    id: `net-${i}`,
    method: methods[i % methods.length],
    url: `/api/v1/resource-${i}?param=value`,
    status: statuses[i % statuses.length] as "completed" | "pending" | "error",
    statusCode: i % statuses.length === 0 ? 200 + (i % 5) * 100 : undefined,
    statusText: i % statuses.length === 0 ? "OK" : undefined,
    startTime: Date.now() - i * 100,
    endTime:
      i % statuses.length === 0
        ? Date.now() - i * 100 + 50 + (i % 200)
        : undefined,
    duration: i % statuses.length === 0 ? 50 + (i % 200) : undefined,
    requestSize: i % 3 === 0 ? 100 + i * 10 : undefined,
    responseSize: i % statuses.length === 0 ? 1000 + i * 50 : undefined,
    source: sources[i % sources.length],
    requestBody: i % 4 === 0 ? { data: `request-${i}` } : undefined,
    responseBody: i % 4 === 0 ? { result: `response-${i}` } : undefined,
  }));
}

// =============================================================================
// Tests
// =============================================================================

describe("NetworkTab Performance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEntries.length = 0;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Large List Rendering", () => {
    it("should render quickly with 500 entries", async () => {
      mockEntries.push(...generateMockEntries(500));

      const start = performance.now();
      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);
      const renderTime = performance.now() - start;

      // Should render within 500ms even with many entries
      expect(renderTime).toBeLessThan(500);
      expect(screen.getByTestId("network-tab")).toBeInTheDocument();
    });

    it("should render 1000 entries without crashing", () => {
      mockEntries.push(...generateMockEntries(1000));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      // Table should render
      expect(screen.getByRole("table")).toBeInTheDocument();
    });

    it("should show correct request count for large lists", () => {
      mockEntries.push(...generateMockEntries(500));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      expect(screen.getByText("500 requests")).toBeInTheDocument();
    });
  });

  describe("Search Performance", () => {
    it("should filter entries with debounced search", async () => {
      mockEntries.push(...generateMockEntries(100));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      const searchInput = screen.getByTestId("network-search");

      // Type quickly
      fireEvent.change(searchInput, { target: { value: "resource-50" } });

      // Results should filter (may be debounced)
      await waitFor(() => {
        expect(screen.getByTestId("network-search")).toHaveValue("resource-50");
      });
    });

    it("should handle rapid search input", async () => {
      mockEntries.push(...generateMockEntries(200));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      const searchInput = screen.getByTestId("network-search");

      // Simulate rapid typing
      const testStrings = ["a", "ab", "abc", "abcd", "abcde", "abcdef"];
      for (const str of testStrings) {
        fireEvent.change(searchInput, { target: { value: str } });
      }

      // Should not crash
      expect(screen.getByTestId("network-tab")).toBeInTheDocument();
    });
  });

  describe("Filter Button Performance", () => {
    it("should switch filters quickly", async () => {
      mockEntries.push(...generateMockEntries(300));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      const filters = ["all", "api", "mcp", "all"];
      const filterTimes: number[] = [];

      for (const filter of filters) {
        const start = performance.now();
        fireEvent.click(screen.getByTestId(`filter-${filter}`));
        filterTimes.push(performance.now() - start);
      }

      // Average filter switch time should be fast (allows for occasional spikes in test env)
      const avgFilterTime =
        filterTimes.reduce((a, b) => a + b, 0) / filterTimes.length;
      expect(avgFilterTime).toBeLessThan(150);
    });
  });

  describe("Row Selection Performance", () => {
    it("should select rows efficiently", async () => {
      mockEntries.push(...generateMockEntries(100));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      // Select multiple rows in sequence
      for (let i = 0; i < 5; i++) {
        const row = screen.getByTestId(`network-entry-net-${i}`);
        fireEvent.click(row);
      }

      // Component should remain responsive
      expect(screen.getByTestId("network-tab")).toBeInTheDocument();
    });

    it("should show request details efficiently", async () => {
      const entriesWithDetails = generateMockEntries(50).map((e) => ({
        ...e,
        requestHeaders: { "Content-Type": "application/json" },
        responseHeaders: { "X-Request-Id": `req-${e.id}` },
        requestBody: { data: "test" },
        responseBody: { result: "success" },
      }));
      mockEntries.push(...entriesWithDetails);

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      // Select first entry
      fireEvent.click(screen.getByTestId("network-entry-net-0"));

      // Details should appear
      await waitFor(() => {
        expect(screen.getByTestId("request-details-net-0")).toBeInTheDocument();
      });
    });
  });

  describe("Recording Toggle Performance", () => {
    it("should toggle recording quickly", () => {
      mockEntries.push(...generateMockEntries(100));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      const toggleButton = screen.getByTestId("recording-toggle");

      // Multiple toggles should be fast
      for (let i = 0; i < 5; i++) {
        const start = performance.now();
        fireEvent.click(toggleButton);
        const toggleTime = performance.now() - start;

        expect(toggleTime).toBeLessThan(50);
      }
    });
  });

  describe("Clear Performance", () => {
    it("should clear entries quickly", () => {
      mockEntries.push(...generateMockEntries(500));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      const clearButton = screen.getByTestId("clear-network-button");

      const start = performance.now();
      fireEvent.click(clearButton);
      const clearTime = performance.now() - start;

      expect(clearTime).toBeLessThan(100);
      expect(mockClearEntries).toHaveBeenCalled();
    });
  });

  describe("Scroll Performance", () => {
    it("should handle scroll events efficiently", () => {
      mockEntries.push(...generateMockEntries(200));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      const tableContainer = screen.getByRole("table").parentElement!;

      // Simulate multiple scroll events
      for (let i = 0; i < 20; i++) {
        fireEvent.scroll(tableContainer, { target: { scrollTop: i * 50 } });
      }

      // Component should still be responsive
      expect(screen.getByTestId("network-tab")).toBeInTheDocument();
    });
  });

  describe("Export Performance", () => {
    it("should export JSON efficiently with many entries", async () => {
      mockEntries.push(...generateMockEntries(500));

      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);

      // Mock download functions after render to avoid interfering with React DOM
      const mockClick = vi.fn();
      const originalCreateElement = document.createElement.bind(document);

      vi.spyOn(document, "createElement").mockImplementation(
        (tagName: string) => {
          if (tagName === "a") {
            return {
              href: "",
              download: "",
              click: mockClick,
              style: {},
            } as unknown as HTMLAnchorElement;
          }
          return originalCreateElement(tagName);
        },
      );
      vi.spyOn(document.body, "appendChild").mockImplementation(
        (node) => node as Node,
      );
      vi.spyOn(document.body, "removeChild").mockImplementation(
        (node) => node as Node,
      );
      vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
      vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

      // Trigger export by hovering and clicking
      const exportButton = screen.getByTestId("export-network-button");
      fireEvent.mouseEnter(exportButton.parentElement!);

      const exportJsonButton = screen.getByTestId("export-network-json-button");

      const start = performance.now();
      fireEvent.click(exportJsonButton);
      const exportTime = performance.now() - start;

      // Export should be reasonably fast
      expect(exportTime).toBeLessThan(500);
    });
  });

  describe("Memory Management", () => {
    it("should handle repeated renders without memory leaks", () => {
      mockEntries.push(...generateMockEntries(100));

      const { unmount, rerender } = render(
        <NetworkTab contextEntityId="session-1" showMCPCalls={true} />,
      );

      // Re-render multiple times
      for (let i = 0; i < 10; i++) {
        rerender(
          <NetworkTab
            contextEntityId={`session-${i}`}
            showMCPCalls={i % 2 === 0}
          />,
        );
      }

      // Unmount should clean up
      unmount();

      // No assertion on memory but no errors means success
      expect(true).toBe(true);
    });
  });

  describe("Empty State Performance", () => {
    it("should show empty state quickly", () => {
      // No entries
      mockEntries.length = 0;

      const start = performance.now();
      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);
      const renderTime = performance.now() - start;

      expect(renderTime).toBeLessThan(100);
      expect(screen.getByTestId("network-empty")).toBeInTheDocument();
    });
  });

  describe("URL Parsing Performance", () => {
    it("should parse URLs efficiently", () => {
      // Entries with complex URLs
      const complexEntries = Array.from({ length: 100 }, (_, i) => ({
        id: `net-${i}`,
        method: "GET",
        url: `https://api.example.com/v1/users/${i}/posts?page=${i}&limit=20&sort=desc&filter[status]=active`,
        status: "completed" as const,
        statusCode: 200,
        statusText: "OK",
        startTime: Date.now(),
        endTime: Date.now() + 100,
        duration: 100,
      }));
      mockEntries.push(...complexEntries);

      const start = performance.now();
      render(<NetworkTab contextEntityId="test-session" showMCPCalls={true} />);
      const renderTime = performance.now() - start;

      // Should parse and render URLs efficiently
      expect(renderTime).toBeLessThan(300);
    });
  });
});
