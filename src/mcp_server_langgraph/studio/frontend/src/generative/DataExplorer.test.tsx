/**
 * DataExplorer Tests - Phase 2
 *
 * Tests for dynamic data exploration dashboard.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { DataExplorer, type DataExplorerConfig } from "./DataExplorer";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const mockConfig: DataExplorerConfig = {
  id: "explorer-1",
  title: "Sales Analytics",
  dataSource: "api/sales",
  columns: [
    { id: "date", label: "Date", type: "date", sortable: true },
    { id: "product", label: "Product", type: "string", sortable: true },
    { id: "amount", label: "Amount", type: "number", sortable: true },
    { id: "status", label: "Status", type: "string", filterable: true },
  ],
  data: [
    {
      date: "2024-01-01",
      product: "Widget A",
      amount: 100,
      status: "Completed",
    },
    { date: "2024-01-02", product: "Widget B", amount: 150, status: "Pending" },
    {
      date: "2024-01-03",
      product: "Widget C",
      amount: 200,
      status: "Completed",
    },
  ],
};

// =============================================================================
// Tests
// =============================================================================

describe("DataExplorer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render explorer container", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByTestId("data-explorer")).toBeInTheDocument();
    });

    it("should display explorer title", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByText("Sales Analytics")).toBeInTheDocument();
    });

    it("should render column headers", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByText("Date")).toBeInTheDocument();
      expect(screen.getByText("Product")).toBeInTheDocument();
      expect(screen.getByText("Amount")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
    });

    it("should render data rows", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByText("Widget A")).toBeInTheDocument();
      expect(screen.getByText("Widget B")).toBeInTheDocument();
      expect(screen.getByText("Widget C")).toBeInTheDocument();
    });
  });

  describe("Sorting", () => {
    it("should show sort indicator on sortable columns", () => {
      render(<DataExplorer config={mockConfig} />);
      const dateHeader = screen.getByText("Date").closest("th");
      expect(dateHeader).toHaveAttribute("data-sortable", "true");
    });

    it("should call onSort when sortable column clicked", () => {
      const onSort = vi.fn();
      render(<DataExplorer config={mockConfig} onSort={onSort} />);
      fireEvent.click(screen.getByText("Date"));
      expect(onSort).toHaveBeenCalledWith("date", "asc");
    });

    it("should toggle sort direction on second click", () => {
      const onSort = vi.fn();
      render(<DataExplorer config={mockConfig} onSort={onSort} />);
      const dateHeader = screen.getByText("Date");
      fireEvent.click(dateHeader);
      fireEvent.click(dateHeader);
      expect(onSort).toHaveBeenLastCalledWith("date", "desc");
    });
  });

  describe("Filtering", () => {
    it("should show filter input for filterable columns", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByTestId("filter-status")).toBeInTheDocument();
    });

    it("should call onFilter when filter input changes", () => {
      const onFilter = vi.fn();
      render(<DataExplorer config={mockConfig} onFilter={onFilter} />);
      const filterInput = screen.getByTestId("filter-status");
      fireEvent.change(filterInput, { target: { value: "Completed" } });
      expect(onFilter).toHaveBeenCalledWith("status", "Completed");
    });
  });

  describe("Search", () => {
    it("should show search input", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByTestId("search-input")).toBeInTheDocument();
    });

    it("should call onSearch when search input changes", () => {
      const onSearch = vi.fn();
      render(<DataExplorer config={mockConfig} onSearch={onSearch} />);
      const searchInput = screen.getByTestId("search-input");
      fireEvent.change(searchInput, { target: { value: "Widget" } });
      expect(onSearch).toHaveBeenCalledWith("Widget");
    });
  });

  describe("Pagination", () => {
    it("should show pagination controls when pageSize is set", () => {
      render(<DataExplorer config={{ ...mockConfig, pageSize: 2 }} />);
      expect(screen.getByTestId("pagination")).toBeInTheDocument();
    });

    it("should show page info", () => {
      render(<DataExplorer config={{ ...mockConfig, pageSize: 2 }} />);
      expect(screen.getByText(/Page 1/)).toBeInTheDocument();
    });

    it("should call onPageChange when next page clicked", () => {
      const onPageChange = vi.fn();
      render(
        <DataExplorer
          config={{ ...mockConfig, pageSize: 2 }}
          onPageChange={onPageChange}
        />,
      );
      fireEvent.click(screen.getByTestId("next-page"));
      expect(onPageChange).toHaveBeenCalledWith(2);
    });
  });

  describe("Loading State", () => {
    it("should show loading overlay when isLoading", () => {
      render(<DataExplorer config={mockConfig} isLoading />);
      expect(screen.getByTestId("loading-overlay")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty message when no data", () => {
      render(<DataExplorer config={{ ...mockConfig, data: [] }} />);
      expect(screen.getByText(/No data available/i)).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should show export button", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByTestId("export-button")).toBeInTheDocument();
    });

    it("should call onExport when export clicked", () => {
      const onExport = vi.fn();
      render(<DataExplorer config={mockConfig} onExport={onExport} />);
      fireEvent.click(screen.getByTestId("export-button"));
      expect(onExport).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<DataExplorer config={mockConfig} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when empty", async () => {
      const { container } = render(
        <DataExplorer config={{ ...mockConfig, data: [] }} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when loading", async () => {
      const { container } = render(
        <DataExplorer config={mockConfig} isLoading />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have table role", () => {
      render(<DataExplorer config={mockConfig} />);
      expect(screen.getByRole("table")).toBeInTheDocument();
    });

    it("should have scope on headers", () => {
      render(<DataExplorer config={mockConfig} />);
      const headers = screen.getAllByRole("columnheader");
      headers.forEach((header) => {
        expect(header).toHaveAttribute("scope", "col");
      });
    });
  });
});
