/**
 * ArtifactExporter Component Tests
 *
 * Tests for the unified artifact export functionality.
 * Supports exporting artifacts to different formats based on type.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ArtifactExporter } from "./ArtifactExporter";

// Mock the download functionality
const mockCreateObjectURL = vi.fn(() => "blob:mock-url");
const mockRevokeObjectURL = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  global.URL.createObjectURL = mockCreateObjectURL;
  global.URL.revokeObjectURL = mockRevokeObjectURL;
});

describe("ArtifactExporter", () => {
  describe("rendering", () => {
    it("should render export button", () => {
      render(
        <ArtifactExporter artifactType="table" data={[]} onExport={vi.fn()} />,
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("should show export menu when button is clicked", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ name: "test", value: 1 }]}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByTestId("export-menu")).toBeInTheDocument();
    });

    it("should close menu when clicking outside", async () => {
      render(
        <div>
          <div data-testid="outside">Outside</div>
          <ArtifactExporter
            artifactType="table"
            data={[{ name: "test" }]}
            onExport={vi.fn()}
          />
        </div>,
      );

      // Open menu
      fireEvent.click(screen.getByRole("button"));
      expect(screen.getByTestId("export-menu")).toBeInTheDocument();

      // Click outside
      fireEvent.mouseDown(screen.getByTestId("outside"));

      await waitFor(() => {
        expect(screen.queryByTestId("export-menu")).not.toBeInTheDocument();
      });
    });
  });

  describe("table exports", () => {
    const tableData = [
      { name: "Alice", age: 30 },
      { name: "Bob", age: 25 },
    ];

    it("should show CSV and Excel options for table", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={tableData}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/csv/i)).toBeInTheDocument();
      expect(screen.getByText(/excel/i)).toBeInTheDocument();
    });

    it("should call onExport with CSV format when selected", async () => {
      const mockOnExport = vi.fn();
      render(
        <ArtifactExporter
          artifactType="table"
          data={tableData}
          onExport={mockOnExport}
        />,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/csv/i));

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalledWith("csv", expect.any(Blob));
      });
    });

    it("should call onExport with Excel format when selected", async () => {
      const mockOnExport = vi.fn();
      render(
        <ArtifactExporter
          artifactType="table"
          data={tableData}
          onExport={mockOnExport}
        />,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/excel/i));

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalledWith("excel", expect.any(Blob));
      });
    });
  });

  describe("chart exports", () => {
    const chartElement = document.createElement("svg");

    it("should show PNG, SVG, and PDF options for chart", () => {
      render(
        <ArtifactExporter
          artifactType="chart"
          elementRef={{ current: chartElement }}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/png/i)).toBeInTheDocument();
      expect(screen.getByText(/svg/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
    });

    it("should call onExport with PNG format when selected", async () => {
      const mockOnExport = vi.fn();
      render(
        <ArtifactExporter
          artifactType="chart"
          elementRef={{ current: chartElement }}
          onExport={mockOnExport}
        />,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/png/i));

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalledWith("png", expect.anything());
      });
    });
  });

  describe("mermaid exports", () => {
    const mermaidCode = "graph TD\n  A --> B";

    it("should show PNG, SVG, and PDF options for mermaid", () => {
      render(
        <ArtifactExporter
          artifactType="mermaid"
          data={mermaidCode}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/png/i)).toBeInTheDocument();
      expect(screen.getByText(/svg/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
    });

    it("should also show code option for mermaid", () => {
      render(
        <ArtifactExporter
          artifactType="mermaid"
          data={mermaidCode}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/code/i)).toBeInTheDocument();
    });
  });

  describe("svg exports", () => {
    const svgData = "<svg><rect width='100' height='100'/></svg>";

    it("should show PNG, SVG, and PDF options for svg", () => {
      render(
        <ArtifactExporter
          artifactType="svg"
          data={svgData}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/png/i)).toBeInTheDocument();
      expect(screen.getByText(/svg/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
    });
  });

  describe("disabled state", () => {
    it("should be disabled when no data", () => {
      render(
        <ArtifactExporter artifactType="table" data={[]} onExport={vi.fn()} />,
      );

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("should be disabled when explicitly disabled", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={vi.fn()}
          disabled
        />,
      );

      expect(screen.getByRole("button")).toBeDisabled();
    });
  });

  describe("loading state", () => {
    it("should show loading indicator during export", async () => {
      const slowExport = vi.fn(
        () => new Promise((resolve) => setTimeout(resolve, 100)),
      );

      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={slowExport}
        />,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/csv/i));

      // Should show loading state
      expect(screen.getByTestId("export-loading")).toBeInTheDocument();
    });
  });

  describe("custom filename", () => {
    it("should use custom filename when provided", async () => {
      const mockOnExport = vi.fn();
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={mockOnExport}
          filename="my-data"
        />,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/csv/i));

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalled();
      });
    });
  });

  describe("accessibility", () => {
    it("should have aria-label on button", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={vi.fn()}
        />,
      );

      expect(screen.getByRole("button")).toHaveAttribute("aria-label");
    });

    it("should have role menu for dropdown", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("should have role menuitem for each option", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getAllByRole("menuitem").length).toBeGreaterThan(0);
    });
  });

  describe("compact mode", () => {
    it("should render smaller in compact mode", () => {
      render(
        <ArtifactExporter
          artifactType="table"
          data={[{ test: 1 }]}
          onExport={vi.fn()}
          compact
        />,
      );

      const button = screen.getByRole("button");
      expect(button).toHaveClass("p-1");
    });
  });
});
