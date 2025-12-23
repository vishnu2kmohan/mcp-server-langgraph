/**
 * NetworkTab Tests
 *
 * TDD tests for the Network tab in DevTools.
 * Displays API requests, WebSocket messages, and MCP tool calls.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import { NetworkTab } from "./NetworkTab";
import type { NetworkEntry } from "../types";

// =============================================================================
// Mock Data
// =============================================================================

const mockNetworkEntries: NetworkEntry[] = [
  {
    id: "req-1",
    method: "GET",
    url: "/api/v1/sessions",
    statusCode: 200,
    statusText: "OK",
    status: "completed",
    duration: 150,
    requestSize: 0,
    responseSize: 1024,
    startTime: 1703000000000,
    endTime: 1703000000150,
    source: "api",
  },
  {
    id: "req-2",
    method: "POST",
    url: "/api/v1/messages",
    statusCode: 201,
    statusText: "Created",
    status: "completed",
    duration: 250,
    requestSize: 512,
    responseSize: 256,
    startTime: 1703000000200,
    endTime: 1703000000450,
    source: "api",
  },
  {
    id: "req-3",
    method: "POST",
    url: "mcp://server/tool/call",
    statusCode: 200,
    statusText: "OK",
    status: "completed",
    duration: 100,
    requestSize: 128,
    responseSize: 512,
    startTime: 1703000000500,
    endTime: 1703000000600,
    source: "mcp-server",
  },
  {
    id: "req-4",
    method: "GET",
    url: "/api/v1/status",
    status: "pending",
    startTime: 1703000000700,
    source: "api",
  },
  {
    id: "req-5",
    method: "GET",
    url: "/api/v1/error",
    statusCode: 500,
    statusText: "Internal Server Error",
    status: "error",
    duration: 50,
    startTime: 1703000000800,
    endTime: 1703000000850,
    source: "api",
  },
];

// =============================================================================
// Mock Hook
// =============================================================================

const mockUseNetworkEntries = vi.fn().mockReturnValue({
  entries: mockNetworkEntries,
  isRecording: true,
  toggleRecording: vi.fn(),
  clearEntries: vi.fn(),
});

vi.mock("../hooks/useNetworkEntries", () => ({
  useNetworkEntries: () => mockUseNetworkEntries(),
}));

// =============================================================================
// Tests
// =============================================================================

describe("NetworkTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseNetworkEntries.mockReturnValue({
      entries: mockNetworkEntries,
      isRecording: true,
      toggleRecording: vi.fn(),
      clearEntries: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("network-tab")).toBeInTheDocument();
    });

    it("should display network entries", () => {
      render(<NetworkTab />);

      expect(screen.getByText("/api/v1/sessions")).toBeInTheDocument();
      expect(screen.getByText("/api/v1/messages")).toBeInTheDocument();
    });

    it("should show empty state when no entries", () => {
      mockUseNetworkEntries.mockReturnValue({
        entries: [],
        isRecording: true,
        toggleRecording: vi.fn(),
        clearEntries: vi.fn(),
      });

      render(<NetworkTab />);

      expect(screen.getByTestId("network-empty")).toBeInTheDocument();
      expect(screen.getByText(/no network activity/i)).toBeInTheDocument();
    });
  });

  describe("entry display", () => {
    it("should show HTTP method", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("method-req-1")).toHaveTextContent("GET");
      expect(screen.getByTestId("method-req-2")).toHaveTextContent("POST");
    });

    it("should show status code with color", () => {
      render(<NetworkTab />);

      // 2xx should be green
      const successStatus = screen.getByTestId("status-req-1");
      expect(successStatus).toHaveTextContent("200");
      expect(successStatus).toHaveClass("text-green-600");

      // 5xx should be red
      const errorStatus = screen.getByTestId("status-req-5");
      expect(errorStatus).toHaveTextContent("500");
      expect(errorStatus).toHaveClass("text-red-600");
    });

    it("should show duration for completed requests", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("duration-req-1")).toHaveTextContent("150ms");
      expect(screen.getByTestId("duration-req-2")).toHaveTextContent("250ms");
    });

    it("should show pending indicator for in-flight requests", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("pending-req-4")).toBeInTheDocument();
    });

    it("should show source badge for MCP calls", () => {
      render(<NetworkTab showMCPCalls />);

      const mcpEntry = screen.getByTestId("network-entry-req-3");
      expect(within(mcpEntry).getByText("mcp-server")).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    it("should show filter options", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("filter-all")).toBeInTheDocument();
      expect(screen.getByTestId("filter-api")).toBeInTheDocument();
      expect(screen.getByTestId("filter-mcp")).toBeInTheDocument();
    });

    it("should filter to API only", async () => {
      const user = userEvent.setup();

      render(<NetworkTab />);

      await user.click(screen.getByTestId("filter-api"));

      // MCP entry should be hidden
      expect(
        screen.queryByTestId("network-entry-req-3"),
      ).not.toBeInTheDocument();
    });

    it("should filter to MCP only", async () => {
      const user = userEvent.setup();

      render(<NetworkTab showMCPCalls />);

      await user.click(screen.getByTestId("filter-mcp"));

      // API entries should be hidden
      expect(
        screen.queryByTestId("network-entry-req-1"),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId("network-entry-req-3")).toBeInTheDocument();
    });

    it("should hide MCP calls when showMCPCalls is false", () => {
      render(<NetworkTab showMCPCalls={false} />);

      expect(
        screen.queryByTestId("network-entry-req-3"),
      ).not.toBeInTheDocument();
    });
  });

  describe("expand details", () => {
    it("should expand request details on click", async () => {
      const user = userEvent.setup();

      render(<NetworkTab />);

      const entry = screen.getByTestId("network-entry-req-1");
      await user.click(entry);

      expect(screen.getByTestId("request-details-req-1")).toBeInTheDocument();
    });

    it("should show headers when expanded", async () => {
      const user = userEvent.setup();

      // Add mock entry with headers
      mockUseNetworkEntries.mockReturnValue({
        entries: [
          {
            ...mockNetworkEntries[0],
            requestHeaders: { "Content-Type": "application/json" },
            responseHeaders: { "X-Request-Id": "abc-123" },
          },
        ],
        isRecording: true,
        toggleRecording: vi.fn(),
        clearEntries: vi.fn(),
      });

      render(<NetworkTab />);

      const entry = screen.getByTestId("network-entry-req-1");
      await user.click(entry);

      // Header keys show with colon
      expect(screen.getByText(/Content-Type/)).toBeInTheDocument();
      expect(screen.getByText(/X-Request-Id/)).toBeInTheDocument();
    });
  });

  describe("recording control", () => {
    it("should show recording indicator", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("recording-indicator")).toBeInTheDocument();
    });

    it("should toggle recording when clicked", async () => {
      const user = userEvent.setup();
      const mockToggle = vi.fn();

      mockUseNetworkEntries.mockReturnValue({
        entries: mockNetworkEntries,
        isRecording: true,
        toggleRecording: mockToggle,
        clearEntries: vi.fn(),
      });

      render(<NetworkTab />);

      await user.click(screen.getByTestId("recording-toggle"));

      expect(mockToggle).toHaveBeenCalled();
    });
  });

  describe("clear", () => {
    it("should have clear button", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("clear-network-button")).toBeInTheDocument();
    });

    it("should call clearEntries when clicked", async () => {
      const user = userEvent.setup();
      const mockClear = vi.fn();

      mockUseNetworkEntries.mockReturnValue({
        entries: mockNetworkEntries,
        isRecording: true,
        toggleRecording: vi.fn(),
        clearEntries: mockClear,
      });

      render(<NetworkTab />);

      await user.click(screen.getByTestId("clear-network-button"));

      expect(mockClear).toHaveBeenCalled();
    });
  });

  describe("search", () => {
    it("should have search input", () => {
      render(<NetworkTab />);

      expect(screen.getByTestId("network-search")).toBeInTheDocument();
    });

    it("should filter entries by URL", async () => {
      const user = userEvent.setup();

      render(<NetworkTab />);

      const searchInput = screen.getByTestId("network-search");
      await user.type(searchInput, "messages");

      // Only message entry should be visible
      expect(screen.getByTestId("network-entry-req-2")).toBeInTheDocument();
      expect(
        screen.queryByTestId("network-entry-req-1"),
      ).not.toBeInTheDocument();
    });
  });

  describe("size display", () => {
    it("should show request and response size", () => {
      render(<NetworkTab />);

      // Format KB
      expect(screen.getByTestId("size-req-1")).toHaveTextContent("1 KB");
    });
  });

  describe("accessibility", () => {
    it("should have accessible table structure", () => {
      render(<NetworkTab />);

      expect(screen.getByRole("table")).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(<NetworkTab />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
