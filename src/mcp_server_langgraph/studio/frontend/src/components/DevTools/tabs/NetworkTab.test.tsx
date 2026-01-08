/**
 * NetworkTab Tests - react-table + auto-tail
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

import { NetworkTab } from "./NetworkTab";
import type { NetworkEntry } from "../types";

expect.extend(toHaveNoViolations);

// =============================================================================
// Mocks
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
];

const mockUseNetworkEntries = vi.fn().mockReturnValue({
  entries: mockNetworkEntries,
  isRecording: true,
  toggleRecording: vi.fn(),
  clearEntries: vi.fn(),
});

vi.mock("../hooks/useNetworkEntries", () => ({
  useNetworkEntries: () => mockUseNetworkEntries(),
}));

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

describe("NetworkTab (react-table)", () => {
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
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders requests with human-friendly timestamps", () => {
    render(<NetworkTab />);
    expect(screen.getByTestId("network-tab")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^network-entry-/)).toHaveLength(4);
    expect(screen.getAllByTestId("human-timestamp").length).toBeGreaterThan(0);
  });

  it("shows empty state when there are no entries", () => {
    mockUseNetworkEntries.mockReturnValue({
      entries: [],
      isRecording: true,
      toggleRecording: vi.fn(),
      clearEntries: vi.fn(),
    });
    render(<NetworkTab />);
    expect(screen.getByTestId("network-empty")).toBeInTheDocument();
  });

  it("filters between API and MCP entries", async () => {
    const user = userEvent.setup();
    render(<NetworkTab showMCPCalls />);

    await user.click(screen.getByTestId("filter-mcp"));
    expect(screen.getAllByTestId(/^network-entry-/)).toHaveLength(1);
    expect(screen.getByTestId("network-entry-req-3")).toBeInTheDocument();
  });

  it("opens request details when a row is selected", async () => {
    const user = userEvent.setup();
    render(<NetworkTab />);

    await user.click(screen.getByTestId("network-entry-req-1"));
    expect(screen.getByTestId("request-details-req-1")).toBeInTheDocument();
  });

  it("searches by URL with debounce", async () => {
    const user = userEvent.setup();
    render(<NetworkTab />);

    await user.type(screen.getByTestId("network-search"), "messages");
    await waitFor(() => {
      expect(screen.getByTestId("network-entry-req-2")).toBeInTheDocument();
      expect(
        screen.queryByTestId("network-entry-req-1"),
      ).not.toBeInTheDocument();
    });
  });

  it("toggles auto-tail via the down arrow control", async () => {
    const user = userEvent.setup();
    render(<NetworkTab />);

    const toggle = screen.getByTestId("network-auto-tail");
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "false");
  });

  it("invokes recording toggle and clear controls", async () => {
    const user = userEvent.setup();
    const mockToggle = vi.fn();
    const mockClear = vi.fn();
    mockUseNetworkEntries.mockReturnValue({
      entries: mockNetworkEntries,
      isRecording: true,
      toggleRecording: mockToggle,
      clearEntries: mockClear,
    });

    render(<NetworkTab />);

    await user.click(screen.getByTestId("recording-toggle"));
    await user.click(screen.getByTestId("clear-network-button"));

    expect(mockToggle).toHaveBeenCalled();
    expect(mockClear).toHaveBeenCalled();
  });

  it("has no obvious accessibility violations", async () => {
    const { container } = render(<NetworkTab />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
