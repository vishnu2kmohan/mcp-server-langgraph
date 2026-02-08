/**
 * ArtifactExporter Component Tests
 *
 * Tests for the unified artifact export functionality.
 * Supports exporting artifacts to different formats based on type.
 *
 * TDD RED Phase: Write failing tests first.
 */

import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ArtifactExporter } from "./ArtifactExporter";

import { TestProvider } from "@/test-utils";

// Mock the download functionality
const mockCreateObjectURL = vi.fn(() => "blob:mock-url");
const mockRevokeObjectURL = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  global.URL.createObjectURL = mockCreateObjectURL;
  global.URL.revokeObjectURL = mockRevokeObjectURL;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ArtifactExporter", () => {
  describe("rendering", () => {
    it("should render export button", () => {
      render(
        <TestProvider>
          <ArtifactExporter artifactType="table" data={[]} onExport={vi.fn()} />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("should show export menu when button is clicked", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ name: "test", value: 1 }]}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByTestId("export-menu")).toBeInTheDocument();
    });

    it("should close menu when clicking outside", async () => {
      render(
        <TestProvider>
          <div>
            <div data-testid="outside">Outside</div>
            <ArtifactExporter
              artifactType="table"
              data={[{ name: "test" }]}
              onExport={vi.fn()}
            />
          </div>
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={tableData}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/csv/i)).toBeInTheDocument();
      expect(screen.getByText(/excel/i)).toBeInTheDocument();
    });

    it("should call onExport with CSV format when selected", async () => {
      const mockOnExport = vi.fn();
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={tableData}
            onExport={mockOnExport}
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={tableData}
            onExport={mockOnExport}
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="chart"
            elementRef={{ current: chartElement }}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/png/i)).toBeInTheDocument();
      expect(screen.getByText(/svg/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
    });

    /**
     * SKIPPED: Requires browser canvas/image APIs not available in jsdom.
     *
     * This functionality is tested in Playwright E2E tests:
     * @see e2e/artifact-export.spec.ts
     *   - "should trigger PNG download when export button clicked on chart"
     *   - "should show PNG, SVG, and PDF export options for charts"
     *
     * Run with: npm run test:e2e -- --grep "Artifact Export"
     */
    it.skip("should call onExport with PNG format when selected", async () => {
      const mockOnExport = vi.fn();
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="chart"
            elementRef={{ current: chartElement }}
            onExport={mockOnExport}
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="mermaid"
            data={mermaidCode}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/png/i)).toBeInTheDocument();
      expect(screen.getByText(/svg/i)).toBeInTheDocument();
      expect(screen.getByText(/pdf/i)).toBeInTheDocument();
    });

    it("should also show code option for mermaid", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="mermaid"
            data={mermaidCode}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByText(/code/i)).toBeInTheDocument();
    });
  });

  describe("svg exports", () => {
    const svgData = "<svg><rect width='100' height='100'/></svg>";

    it("should show PNG, SVG, and PDF options for svg", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="svg"
            data={svgData}
            onExport={vi.fn()}
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter artifactType="table" data={[]} onExport={vi.fn()} />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toBeDisabled();
    });

    it("should be disabled when explicitly disabled", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={vi.fn()}
            disabled
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={slowExport}
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={mockOnExport}
            filename="my-data"
          />
        </TestProvider>,
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
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button")).toHaveAttribute("aria-label");
    });

    it("should have role menu for dropdown", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getByRole("menu")).toBeInTheDocument();
    });

    it("should have role menuitem for each option", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={vi.fn()}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));

      expect(screen.getAllByRole("menuitem").length).toBeGreaterThan(0);
    });
  });

  describe("compact mode", () => {
    it("should render smaller in compact mode", () => {
      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="table"
            data={[{ test: 1 }]}
            onExport={vi.fn()}
            compact
          />
        </TestProvider>,
      );

      const button = screen.getByRole("button");
      expect(button).toHaveClass("p-1");
    });
  });

  /**
   * PNG Export Conversion Tests
   *
   * SKIPPED: These tests require browser canvas/image APIs not available in jsdom.
   * They verify the SVG-to-PNG conversion flow which uses canvas.toBlob().
   *
   * This functionality is tested in Playwright E2E tests:
   * @see e2e/artifact-export.spec.ts
   *   - "should convert SVG artifact to PNG on export"
   *   - "should create valid PNG file from chart export"
   *
   * Run with: npm run test:e2e -- --grep "SVG to PNG Export"
   */
  describe("PNG export conversion", () => {
    it.skip("should call onExport with PNG blob for SVG data", async () => {
      const mockOnExport = vi.fn();
      const svgData =
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>';

      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="svg"
            data={svgData}
            onExport={mockOnExport}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/png/i));

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalledWith("png", expect.any(Blob));
      });

      // Verify the blob type is PNG
      const [, blob] = mockOnExport.mock.calls[0];
      expect(blob.type).toBe("image/png");
    });

    it.skip("should export PNG from SVG element reference", async () => {
      const mockOnExport = vi.fn();
      const svgElement = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "svg",
      );
      svgElement.setAttribute("width", "100");
      svgElement.setAttribute("height", "100");
      svgElement.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      const rect = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "svg",
      );
      rect.setAttribute("width", "100");
      rect.setAttribute("height", "100");
      rect.setAttribute("fill", "blue");
      svgElement.appendChild(rect);

      render(
        <TestProvider>
          <ArtifactExporter
            artifactType="chart"
            elementRef={{ current: svgElement }}
            onExport={mockOnExport}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button"));
      fireEvent.click(screen.getByText(/png/i));

      await waitFor(() => {
        expect(mockOnExport).toHaveBeenCalledWith("png", expect.any(Blob));
      });

      // Verify the blob type is PNG
      const [, blob] = mockOnExport.mock.calls[0];
      expect(blob.type).toBe("image/png");
    });
  });
});
