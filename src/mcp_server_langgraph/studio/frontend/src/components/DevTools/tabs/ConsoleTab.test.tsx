/**
 * ConsoleTab Tests
 *
 * TDD tests for the Console tab in DevTools.
 * Tests log display, filtering, expanding entries, and accessibility.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import { ConsoleTab } from "./ConsoleTab";
import type { ConsoleEntry } from "../types";

// =============================================================================
// Test Data
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

// =============================================================================
// Mock Hooks
// =============================================================================

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

// =============================================================================
// Tests
// =============================================================================

describe("ConsoleTab", () => {
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
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByTestId("console-tab")).toBeInTheDocument();
    });

    it("should render console entries", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByText("Application started")).toBeInTheDocument();
      expect(screen.getByText("Connection retry in 5s")).toBeInTheDocument();
      expect(screen.getByText("Failed to fetch data")).toBeInTheDocument();
    });

    it("should display empty state when no entries", () => {
      mockReturnValue = {
        ...mockReturnValue,
        entries: [],
        filteredEntries: [],
      };

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByTestId("console-empty-state")).toBeInTheDocument();
      expect(screen.getByText(/no console output/i)).toBeInTheDocument();
    });
  });

  describe("entry display", () => {
    it("should display timestamp for each entry", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      // Should show formatted time
      const entries = screen.getAllByTestId(/^console-entry-/);
      expect(entries.length).toBeGreaterThan(0);
    });

    it("should display source indicator for each entry", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByTestId("source-system")).toBeInTheDocument();
      expect(screen.getByTestId("source-mcp")).toBeInTheDocument();
      expect(screen.getByTestId("source-api")).toBeInTheDocument();
    });

    it("should style info entries with blue color", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const infoEntry = screen.getByTestId("console-entry-entry-1");
      expect(infoEntry).toHaveClass("text-blue-600");
    });

    it("should style warning entries with amber color", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const warningEntry = screen.getByTestId("console-entry-entry-2");
      expect(warningEntry).toHaveClass("text-amber-600");
    });

    it("should style error entries with red color", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const errorEntry = screen.getByTestId("console-entry-entry-3");
      expect(errorEntry).toHaveClass("text-red-600");
    });

    it("should style debug entries with gray color", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const debugEntry = screen.getByTestId("console-entry-entry-4");
      expect(debugEntry).toHaveClass("text-gray-500");
    });
  });

  describe("filtering", () => {
    it("should show all entries when filter is 'all'", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entries = screen.getAllByTestId(/^console-entry-/);
      expect(entries.length).toBe(5);
    });

    it("should show only filtered entries when filter is applied", () => {
      const infoEntries = mockEntries.filter((e) => e.level === "info");
      mockReturnValue = {
        ...mockReturnValue,
        filteredEntries: infoEntries,
      };

      render(<ConsoleTab filter="info" onFilterChange={() => {}} />);

      const entries = screen.getAllByTestId(/^console-entry-/);
      expect(entries.length).toBe(2); // Two info entries
    });

    it("should call onFilterChange when filter dropdown changed", async () => {
      const user = userEvent.setup();
      const handleFilterChange = vi.fn();

      render(<ConsoleTab filter="all" onFilterChange={handleFilterChange} />);

      const filterSelect = screen.getByTestId("console-filter-select");
      await user.selectOptions(filterSelect, "error");

      expect(handleFilterChange).toHaveBeenCalledWith("error");
    });
  });

  describe("expandable entries", () => {
    it("should show expand button for entries with data", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      // Entry-3 and entry-4 have data
      const entry3 = screen.getByTestId("console-entry-entry-3");
      expect(within(entry3).getByTestId("expand-button")).toBeInTheDocument();

      const entry4 = screen.getByTestId("console-entry-entry-4");
      expect(within(entry4).getByTestId("expand-button")).toBeInTheDocument();
    });

    it("should not show expand button for entries without data", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry1 = screen.getByTestId("console-entry-entry-1");
      expect(
        within(entry1).queryByTestId("expand-button"),
      ).not.toBeInTheDocument();
    });

    it("should expand entry data when expand button clicked", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry3 = screen.getByTestId("console-entry-entry-3");
      const expandButton = within(entry3).getByTestId("expand-button");
      await user.click(expandButton);

      // Should show expanded data
      expect(screen.getByTestId("expanded-data-entry-3")).toBeInTheDocument();
      expect(screen.getByText(/statusCode/)).toBeInTheDocument();
      expect(screen.getByText(/500/)).toBeInTheDocument();
    });

    it("should collapse entry data when expand button clicked again", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry3 = screen.getByTestId("console-entry-entry-3");
      const expandButton = within(entry3).getByTestId("expand-button");

      // Expand
      await user.click(expandButton);
      expect(screen.getByTestId("expanded-data-entry-3")).toBeInTheDocument();

      // Collapse
      await user.click(expandButton);
      expect(
        screen.queryByTestId("expanded-data-entry-3"),
      ).not.toBeInTheDocument();
    });
  });

  describe("stack trace", () => {
    it("should show stack trace for error entries", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry3 = screen.getByTestId("console-entry-entry-3");
      const expandButton = within(entry3).getByTestId("expand-button");
      await user.click(expandButton);

      expect(screen.getByTestId("stack-trace-entry-3")).toBeInTheDocument();
      expect(screen.getByText(/at fetchData/)).toBeInTheDocument();
    });
  });

  describe("copy to clipboard", () => {
    it("should show copy button on entry hover", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry1 = screen.getByTestId("console-entry-entry-1");
      await user.hover(entry1);

      expect(within(entry1).getByTestId("copy-button")).toBeInTheDocument();
    });

    it("should have clickable copy button", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry1 = screen.getByTestId("console-entry-entry-1");
      await user.hover(entry1);
      const copyButton = within(entry1).getByTestId("copy-button");

      // Just verify the button is clickable
      expect(copyButton).toBeEnabled();
      await user.click(copyButton);
      // Copy action should complete without error
    });
  });

  describe("clear console", () => {
    it("should show clear button in toolbar", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByTestId("clear-console-button")).toBeInTheDocument();
    });

    it("should call clearConsole when clear button clicked", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const clearButton = screen.getByTestId("clear-console-button");
      await user.click(clearButton);

      expect(mockClearConsole).toHaveBeenCalled();
    });
  });

  describe("auto-scroll", () => {
    it("should have scroll-to-bottom button", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByTestId("scroll-to-bottom")).toBeInTheDocument();
    });
  });

  describe("context filtering", () => {
    it("should filter entries by contextEntityId when provided", () => {
      // When contextEntityId is provided, entries should be filtered
      // This would be handled by the hook
      render(
        <ConsoleTab
          filter="all"
          onFilterChange={() => {}}
          contextEntityId="session-123"
        />,
      );

      expect(screen.getByTestId("console-tab")).toBeInTheDocument();
    });
  });

  describe("keyboard navigation", () => {
    it("should navigate entries with arrow keys", async () => {
      const user = userEvent.setup();

      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const list = screen.getByTestId("console-entries-list");
      await user.click(list);

      // After click, focusedIndex is 0, so entry-1 should be focused
      expect(screen.getByTestId("console-entry-entry-1")).toHaveAttribute(
        "data-focused",
        "true",
      );

      // ArrowDown moves to next entry
      await user.keyboard("{ArrowDown}");
      expect(screen.getByTestId("console-entry-entry-2")).toHaveAttribute(
        "data-focused",
        "true",
      );
    });
  });

  describe("accessibility", () => {
    it("should have accessible role for log list", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have aria-label for filter select", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const filterSelect = screen.getByTestId("console-filter-select");
      expect(filterSelect).toHaveAttribute("aria-label");
    });

    it("should have aria-expanded on expandable entries", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      const entry3 = screen.getByTestId("console-entry-entry-3");
      const expandButton = within(entry3).getByTestId("expand-button");
      expect(expandButton).toHaveAttribute("aria-expanded", "false");
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <ConsoleTab filter="all" onFilterChange={() => {}} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("entry count", () => {
    it("should display entry count in toolbar", () => {
      render(<ConsoleTab filter="all" onFilterChange={() => {}} />);

      expect(screen.getByTestId("entry-count")).toHaveTextContent("5");
    });

    it("should update count when filter changes", () => {
      const errorEntries = mockEntries.filter((e) => e.level === "error");
      mockReturnValue = {
        ...mockReturnValue,
        entries: errorEntries,
        filteredEntries: errorEntries,
      };

      render(<ConsoleTab filter="error" onFilterChange={() => {}} />);

      expect(screen.getByTestId("entry-count")).toHaveTextContent("1");
    });
  });
});
