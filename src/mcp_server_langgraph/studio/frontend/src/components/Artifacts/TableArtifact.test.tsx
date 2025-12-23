/**
 * TableArtifact Tests
 *
 * Tests for the TableArtifact component that renders data tables
 * with sorting and filtering capabilities.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { TableArtifact, TableArtifactProps } from "./TableArtifact";

const sampleData: TableArtifactProps = {
  title: "Sales Data",
  columns: [
    { key: "name", label: "Name", sortable: true },
    { key: "region", label: "Region", sortable: true },
    { key: "amount", label: "Amount", sortable: true, type: "number" },
    { key: "date", label: "Date", sortable: true, type: "date" },
  ],
  data: [
    { name: "Product A", region: "West", amount: 1500, date: "2024-01-15" },
    { name: "Product B", region: "East", amount: 2300, date: "2024-02-20" },
    { name: "Product C", region: "North", amount: 1800, date: "2024-01-25" },
  ],
};

describe("TableArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render table title", () => {
      render(<TableArtifact {...sampleData} />);
      expect(screen.getByText("Sales Data")).toBeInTheDocument();
    });

    it("should render all column headers", () => {
      render(<TableArtifact {...sampleData} />);
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Region")).toBeInTheDocument();
      expect(screen.getByText("Amount")).toBeInTheDocument();
      expect(screen.getByText("Date")).toBeInTheDocument();
    });

    it("should render all data rows", () => {
      render(<TableArtifact {...sampleData} />);
      expect(screen.getByText("Product A")).toBeInTheDocument();
      expect(screen.getByText("Product B")).toBeInTheDocument();
      expect(screen.getByText("Product C")).toBeInTheDocument();
    });

    it("should render all cell values", () => {
      render(<TableArtifact {...sampleData} />);
      expect(screen.getByText("West")).toBeInTheDocument();
      expect(screen.getByText("East")).toBeInTheDocument();
      expect(screen.getByText("1500")).toBeInTheDocument();
      expect(screen.getByText("2300")).toBeInTheDocument();
    });

    it("should show empty state when no data", () => {
      render(<TableArtifact {...sampleData} data={[]} />);
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });
  });

  describe("Sorting", () => {
    it("should sort by column when header clicked", () => {
      render(<TableArtifact {...sampleData} />);
      const nameHeader = screen.getByText("Name");
      fireEvent.click(nameHeader);
      // First click should sort ascending
      const rows = screen.getAllByRole("row");
      expect(rows[1]).toHaveTextContent("Product A");
    });

    it("should toggle sort direction on second click", () => {
      render(<TableArtifact {...sampleData} />);
      const nameHeader = screen.getByText("Name");
      fireEvent.click(nameHeader);
      fireEvent.click(nameHeader);
      // Second click should sort descending
      const rows = screen.getAllByRole("row");
      expect(rows[1]).toHaveTextContent("Product C");
    });

    it("should sort numbers correctly", () => {
      render(<TableArtifact {...sampleData} />);
      const amountHeader = screen.getByText("Amount");
      fireEvent.click(amountHeader);
      const rows = screen.getAllByRole("row");
      // Ascending order: 1500, 1800, 2300
      expect(rows[1]).toHaveTextContent("1500");
    });
  });

  describe("Actions", () => {
    it("should render export button", () => {
      render(<TableArtifact {...sampleData} />);
      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });

    it("should call onExport when export format selected", () => {
      const onExport = vi.fn();
      render(<TableArtifact {...sampleData} onExport={onExport} />);
      // Click the export button to open menu
      fireEvent.click(screen.getByRole("button", { name: /export/i }));
      // Click CSV option in the menu
      fireEvent.click(screen.getByRole("menuitem", { name: /csv/i }));
      expect(onExport).toHaveBeenCalled();
    });

    it("should call onRowClick when row clicked", () => {
      const onRowClick = vi.fn();
      render(<TableArtifact {...sampleData} onRowClick={onRowClick} />);
      const firstRow = screen.getAllByRole("row")[1];
      fireEvent.click(firstRow);
      expect(onRowClick).toHaveBeenCalledWith(sampleData.data[0]);
    });
  });

  describe("Expandable", () => {
    it("should show expand button when expandable", () => {
      render(<TableArtifact {...sampleData} expandable />);
      expect(
        screen.getByRole("button", { name: /expand/i }),
      ).toBeInTheDocument();
    });

    it("should collapse when collapse button clicked", () => {
      render(<TableArtifact {...sampleData} expandable />);
      const expandButton = screen.getByRole("button", { name: /expand/i });
      fireEvent.click(expandButton);
      // After expanding, should show collapse button
      expect(
        screen.getByRole("button", { name: /collapse/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Layout", () => {
    it("should have proper test id", () => {
      render(<TableArtifact {...sampleData} />);
      expect(screen.getByTestId("table-artifact")).toBeInTheDocument();
    });

    it("should apply custom className", () => {
      render(<TableArtifact {...sampleData} className="custom-class" />);
      expect(screen.getByTestId("table-artifact")).toHaveClass("custom-class");
    });
  });

  describe("ArtifactExporter Integration", () => {
    it("should show export menu when export button clicked", () => {
      render(<TableArtifact {...sampleData} />);
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(screen.getByTestId("export-menu")).toBeInTheDocument();
    });

    it("should show CSV option in export menu", () => {
      render(<TableArtifact {...sampleData} />);
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /csv/i }),
      ).toBeInTheDocument();
    });

    it("should show Excel option in export menu", () => {
      render(<TableArtifact {...sampleData} />);
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /excel/i }),
      ).toBeInTheDocument();
    });

    it("should trigger export when format selected", () => {
      // Mock URL methods in JSDOM environment
      const mockUrl = "blob:test";
      const originalCreateObjectURL = URL.createObjectURL;
      const originalRevokeObjectURL = URL.revokeObjectURL;

      URL.createObjectURL = vi.fn().mockReturnValue(mockUrl);
      URL.revokeObjectURL = vi.fn();

      render(<TableArtifact {...sampleData} />);
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);

      const csvOption = screen.getByRole("menuitem", { name: /csv/i });
      fireEvent.click(csvOption);

      expect(URL.createObjectURL).toHaveBeenCalled();

      // Restore original methods
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    });
  });
});
