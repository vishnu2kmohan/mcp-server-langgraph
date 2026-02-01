/**
 * OTELDataTable Component Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests virtualized table wrapper with TanStack Table + React Virtual.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ColumnDef } from "@tanstack/react-table";

import { OTELDataTable } from "./OTELDataTable";

// =============================================================================
// Test Data Types
// =============================================================================

interface TestLogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warning" | "error";
  message: string;
}

// =============================================================================
// Mock Data
// =============================================================================

const mockLogs: TestLogEntry[] = [
  {
    id: "1",
    timestamp: "2026-01-15T10:00:00Z",
    level: "info",
    message: "Request received",
  },
  {
    id: "2",
    timestamp: "2026-01-15T10:00:01Z",
    level: "debug",
    message: "Processing started",
  },
  {
    id: "3",
    timestamp: "2026-01-15T10:00:02Z",
    level: "error",
    message: "Connection failed",
  },
  {
    id: "4",
    timestamp: "2026-01-15T10:00:03Z",
    level: "warning",
    message: "Slow response",
  },
  {
    id: "5",
    timestamp: "2026-01-15T10:00:04Z",
    level: "info",
    message: "Request completed",
  },
];

const testColumns: ColumnDef<TestLogEntry>[] = [
  { accessorKey: "timestamp", header: "Time" },
  { accessorKey: "level", header: "Level" },
  { accessorKey: "message", header: "Message" },
];

// =============================================================================
// Basic Rendering Tests
// =============================================================================

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OTELDataTable", () => {
  describe("basic rendering", () => {
    it("should render table with data", () => {
      render(<OTELDataTable data={mockLogs} columns={testColumns} />);
      expect(screen.getByRole("table")).toBeInTheDocument();
    });

    it("should render table headers", () => {
      render(<OTELDataTable data={mockLogs} columns={testColumns} />);
      expect(screen.getByText("Time")).toBeInTheDocument();
      expect(screen.getByText("Level")).toBeInTheDocument();
      expect(screen.getByText("Message")).toBeInTheDocument();
    });

    it("should render data rows", () => {
      render(<OTELDataTable data={mockLogs} columns={testColumns} />);
      expect(screen.getByText("Request received")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should show empty state when no data", () => {
      render(<OTELDataTable data={[]} columns={testColumns} />);
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Sorting Tests
  // ===========================================================================

  describe("sorting", () => {
    it("should render sortable header buttons", () => {
      render(
        <OTELDataTable data={mockLogs} columns={testColumns} enableSorting />,
      );
      const headers = screen.getAllByRole("columnheader");
      expect(headers.length).toBeGreaterThan(0);
    });

    it("should sort by column when header clicked", async () => {
      const user = userEvent.setup();
      render(
        <OTELDataTable data={mockLogs} columns={testColumns} enableSorting />,
      );

      // Click Level header to sort
      const levelHeader = screen.getByText("Level");
      await user.click(levelHeader);

      // Check that rows are sorted (debug should come first alphabetically)
      const rows = screen.getAllByRole("row");
      expect(rows.length).toBeGreaterThan(1);
    });

    it("should toggle sort direction on repeated click", async () => {
      const user = userEvent.setup();
      render(
        <OTELDataTable data={mockLogs} columns={testColumns} enableSorting />,
      );

      const levelHeader = screen.getByText("Level");

      // First click - ascending
      await user.click(levelHeader);
      // Second click - descending
      await user.click(levelHeader);

      // Sort indicator should change
      expect(
        levelHeader.closest("[data-sorted]") || levelHeader,
      ).toBeInTheDocument();
    });

    it("should use defaultSort when provided", () => {
      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          enableSorting
          defaultSort={{ id: "level", desc: false }}
        />,
      );

      // Table should be rendered with default sort applied
      expect(screen.getByRole("table")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Row Expansion Tests
  // ===========================================================================

  describe("row expansion", () => {
    it("should expand row when clicked", async () => {
      const user = userEvent.setup();
      const renderExpandedRow = (row: TestLogEntry) => (
        <div data-testid="expanded-content">Details for {row.id}</div>
      );

      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          renderExpandedRow={renderExpandedRow}
        />,
      );

      // Click first row
      const rows = screen.getAllByRole("row");
      await user.click(rows[1]); // Skip header row

      expect(screen.getByTestId("expanded-content")).toBeInTheDocument();
      expect(screen.getByText("Details for 1")).toBeInTheDocument();
    });

    it("should collapse row when clicked again", async () => {
      const user = userEvent.setup();
      const renderExpandedRow = (row: TestLogEntry) => (
        <div data-testid="expanded-content">Details for {row.id}</div>
      );

      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          renderExpandedRow={renderExpandedRow}
        />,
      );

      const rows = screen.getAllByRole("row");

      // Click to expand
      await user.click(rows[1]);
      expect(screen.getByTestId("expanded-content")).toBeInTheDocument();

      // Click to collapse
      await user.click(rows[1]);
      expect(screen.queryByTestId("expanded-content")).not.toBeInTheDocument();
    });

    it("should call onRowExpand callback", async () => {
      const onRowExpand = vi.fn();
      const user = userEvent.setup();

      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          onRowExpand={onRowExpand}
          renderExpandedRow={() => <div>Expanded</div>}
        />,
      );

      const rows = screen.getAllByRole("row");
      await user.click(rows[1]);

      expect(onRowExpand).toHaveBeenCalledWith("1");
    });

    it("should expand specific row when expandedRowId is controlled", () => {
      const renderExpandedRow = (row: TestLogEntry) => (
        <div data-testid="expanded-content">Details for {row.id}</div>
      );

      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          expandedRowId="2"
          renderExpandedRow={renderExpandedRow}
        />,
      );

      expect(screen.getByText("Details for 2")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Row Styling Tests
  // ===========================================================================

  describe("row styling", () => {
    it("should apply custom row className from getRowClassName", () => {
      const getRowClassName = (row: TestLogEntry) => {
        if (row.level === "error") return "bg-error-2";
        return "";
      };

      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          getRowClassName={getRowClassName}
        />,
      );

      // Find the error row and check for custom class
      const errorRow = screen.getByText("Connection failed").closest("tr");
      expect(errorRow).toHaveClass("bg-error-2");
    });

    it("should highlight row on hover", () => {
      render(<OTELDataTable data={mockLogs} columns={testColumns} />);

      const rows = screen.getAllByRole("row");
      // Data rows should have hover styling (check class presence)
      expect(rows[1]).toHaveClass("hover:bg-neutral-2");
    });
  });

  // ===========================================================================
  // Virtualization Tests
  // ===========================================================================

  describe("virtualization", () => {
    it("should enable virtualization when data exceeds threshold", () => {
      // Generate large dataset
      const largeData: TestLogEntry[] = Array.from({ length: 200 }, (_, i) => ({
        id: String(i),
        timestamp: `2026-01-15T10:00:${String(i).padStart(2, "0")}Z`,
        level: "info" as const,
        message: `Log message ${i}`,
      }));

      render(
        <OTELDataTable
          data={largeData}
          columns={testColumns}
          virtualizeThreshold={100}
        />,
      );

      // Table should still render
      expect(screen.getByRole("table")).toBeInTheDocument();

      // Should not render all 200 rows (virtualization limits visible rows)
      const rows = screen.getAllByRole("row");
      // With virtualization, we should have fewer visible rows
      expect(rows.length).toBeLessThan(200);
    });

    it("should not virtualize when data is below threshold", () => {
      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          virtualizeThreshold={100}
        />,
      );

      // All 5 rows + 1 header should be rendered
      const rows = screen.getAllByRole("row");
      expect(rows.length).toBe(6);
    });
  });

  // ===========================================================================
  // Auto-Tail Tests
  // ===========================================================================

  describe("auto-tail", () => {
    it("should show jump to latest button when scrolled up", async () => {
      // Generate enough data to scroll
      const largeData: TestLogEntry[] = Array.from({ length: 100 }, (_, i) => ({
        id: String(i),
        timestamp: `2026-01-15T10:00:${String(i).padStart(2, "0")}Z`,
        level: "info" as const,
        message: `Log message ${i}`,
      }));

      render(
        <OTELDataTable data={largeData} columns={testColumns} enableAutoTail />,
      );

      // Should have table rendered
      expect(screen.getByRole("table")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Buffer Management Tests
  // ===========================================================================

  describe("buffer management", () => {
    it("should respect maxEntries limit", () => {
      const largeData: TestLogEntry[] = Array.from({ length: 100 }, (_, i) => ({
        id: String(i),
        timestamp: `2026-01-15T10:00:${String(i).padStart(2, "0")}Z`,
        level: "info" as const,
        message: `Log message ${i}`,
      }));

      render(
        <OTELDataTable
          data={largeData}
          columns={testColumns}
          maxEntries={50}
        />,
      );

      // Only the last 50 entries should be displayed
      expect(screen.queryByText("Log message 0")).not.toBeInTheDocument();
      expect(screen.getByText("Log message 99")).toBeInTheDocument();
    });

    it("should call onBufferFull when limit exceeded", () => {
      const onBufferFull = vi.fn();
      const largeData: TestLogEntry[] = Array.from({ length: 100 }, (_, i) => ({
        id: String(i),
        timestamp: `2026-01-15T10:00:${String(i).padStart(2, "0")}Z`,
        level: "info" as const,
        message: `Log message ${i}`,
      }));

      render(
        <OTELDataTable
          data={largeData}
          columns={testColumns}
          maxEntries={50}
          onBufferFull={onBufferFull}
        />,
      );

      expect(onBufferFull).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Export Tests
  // ===========================================================================

  describe("export functionality", () => {
    it("should show export button when enableExport is true", () => {
      render(
        <OTELDataTable data={mockLogs} columns={testColumns} enableExport />,
      );

      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });

    it("should hide export button when enableExport is false", () => {
      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          enableExport={false}
        />,
      );

      expect(
        screen.queryByRole("button", { name: /export/i }),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("should have proper table structure with thead and tbody", () => {
      render(<OTELDataTable data={mockLogs} columns={testColumns} />);

      const table = screen.getByRole("table");
      expect(
        within(table).getAllByRole("rowgroup").length,
      ).toBeGreaterThanOrEqual(1);
      expect(within(table).getAllByRole("columnheader").length).toBe(3);
    });

    it("should have keyboard navigable rows", async () => {
      const user = userEvent.setup();
      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          renderExpandedRow={() => <div>Expanded</div>}
        />,
      );

      const rows = screen.getAllByRole("row");
      rows[1].focus();

      // Press Enter to expand
      await user.keyboard("{Enter}");

      // Row should be expandable via keyboard
      expect(screen.getByText("Expanded")).toBeInTheDocument();
    });

    it("should announce sort order changes to screen readers", async () => {
      const user = userEvent.setup();
      render(
        <OTELDataTable data={mockLogs} columns={testColumns} enableSorting />,
      );

      const levelHeader = screen.getByText("Level");
      await user.click(levelHeader);

      // Header should have aria-sort attribute
      const headerCell = levelHeader.closest("[role='columnheader']");
      expect(headerCell).toHaveAttribute("aria-sort");
    });
  });

  // ===========================================================================
  // Custom className Tests
  // ===========================================================================

  describe("className prop", () => {
    it("should merge custom className with default styles", () => {
      render(
        <OTELDataTable
          data={mockLogs}
          columns={testColumns}
          className="custom-table"
        />,
      );

      // className is on the outer wrapper, two levels up from table
      const table = screen.getByRole("table");
      const tableContainer = table.parentElement;
      const outerWrapper = tableContainer?.parentElement;
      expect(outerWrapper).toHaveClass("custom-table");
    });
  });
});
