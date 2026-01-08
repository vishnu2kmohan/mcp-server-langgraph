/**
 * ConsoleTab Tests - react-table layout + auto-tail
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  render,
  screen,
  within,
  cleanup,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

import { ConsoleTab } from "./ConsoleTab";
import type { ConsoleEntry } from "../types";

expect.extend(toHaveNoViolations);

// =============================================================================
// Mocks
// =============================================================================

const mockEntries: ConsoleEntry[] = [
  {
    id: "entry-1",
    level: "info",
    source: "system",
    message: "Application started",
    timestamp: 1703000000000,
  },
  {
    id: "entry-2",
    level: "warning",
    source: "mcp",
    message: "Connection retry in 5s",
    timestamp: 1703000001000,
  },
  {
    id: "entry-3",
    level: "error",
    source: "api",
    message: "Failed to fetch data",
    timestamp: 1703000002000,
    data: { statusCode: 500, endpoint: "/api/sessions" },
    stackTrace: "Error: Failed to fetch\n  at fetchData (/src/api.ts:42)",
  },
  {
    id: "entry-4",
    level: "debug",
    source: "execution",
    message: "Agent step completed",
    timestamp: 1703000003000,
    data: { nodeId: "node-1", duration: 150 },
  },
  {
    id: "entry-5",
    level: "info",
    source: "notification",
    message: "Task completed successfully",
    timestamp: 1703000004000,
  },
];

const mockClearConsole = vi.fn();

let mockReturnValue = {
  entries: mockEntries,
  filteredEntries: mockEntries,
  clearConsole: mockClearConsole,
  isLoading: false,
  addEntry: vi.fn(),
  counts: { info: 2, warning: 1, error: 1, debug: 1, total: 5 },
};

vi.mock("../hooks/useConsoleEntries", () => ({
  useConsoleEntries: () => mockReturnValue,
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

describe("ConsoleTab (react-table)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReturnValue = {
      entries: mockEntries,
      filteredEntries: mockEntries,
      clearConsole: mockClearConsole,
      isLoading: false,
      addEntry: vi.fn(),
      counts: { info: 2, warning: 1, error: 1, debug: 1, total: 5 },
    };
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders entries in a tabular layout with timestamps", () => {
    render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

    expect(screen.getByTestId("console-tab")).toBeInTheDocument();
    expect(screen.getByText("Level")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^console-entry-/)).toHaveLength(5);
    expect(screen.getAllByTestId("human-timestamp").length).toBeGreaterThan(0);
  });

  it("filters by level and shows empty state when no matches", () => {
    // Filter to info → only info rows remain
    render(<ConsoleTab filter="info" onFilterChange={() => {}} />);
    expect(screen.getAllByTestId(/^console-entry-/)).toHaveLength(2);
    expect(
      screen.queryByText("Connection retry in 5s"),
    ).not.toBeInTheDocument();

    // No matches should render empty state
    mockReturnValue = {
      ...mockReturnValue,
      entries: mockEntries.filter((e) => e.level === "warning"),
    };
    cleanup();
    render(<ConsoleTab filter="error" onFilterChange={() => {}} />);
    expect(screen.getByTestId("console-empty-state")).toBeInTheDocument();
  });

  it("expands structured payloads and stack traces", async () => {
    const user = userEvent.setup();
    render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

    const errorRow = screen.getByTestId("console-entry-entry-3");
    await user.click(within(errorRow).getByTestId("expand-button"));

    expect(screen.getByTestId("expanded-data-entry-3")).toBeInTheDocument();
    expect(screen.getByTestId("stack-trace-entry-3")).toBeInTheDocument();
  });

  it("supports search filtering", async () => {
    const user = userEvent.setup();
    render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

    await user.type(screen.getByTestId("console-search-input"), "fetch");

    await waitFor(() => {
      expect(screen.getByText("Failed to fetch data")).toBeInTheDocument();
      expect(
        screen.queryByText("Connection retry in 5s"),
      ).not.toBeInTheDocument();
    });
  });

  it("toggles auto-tail via the down arrow control", async () => {
    const user = userEvent.setup();
    render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

    const toggle = screen.getByTestId("scroll-to-bottom");
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "false");
  });

  it("shows copy control on hover", async () => {
    const user = userEvent.setup();
    render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

    const firstRow = screen.getByTestId("console-entry-entry-1");
    await user.hover(firstRow);
    expect(within(firstRow).getByTestId("copy-button")).toBeInTheDocument();
  });

  it("has no obvious accessibility violations", async () => {
    const { container } = render(
      <ConsoleTab filter="all" onFilterChange={() => {}} />,
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
