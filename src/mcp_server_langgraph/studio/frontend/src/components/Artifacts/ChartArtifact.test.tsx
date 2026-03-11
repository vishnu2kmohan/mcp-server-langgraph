/**
 * ChartArtifact Tests
 *
 * Tests for the ChartArtifact component that renders interactive charts.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { ChartArtifact, ChartArtifactProps } from "./ChartArtifact";

import { TestProvider } from "@/test-utils";

const barChartData: ChartArtifactProps = {
  title: "Sales by Region",
  type: "bar",
  data: [
    { label: "West", value: 450000 },
    { label: "North", value: 380000 },
    { label: "South", value: 320000 },
    { label: "East", value: 280000 },
  ],
};

const lineChartData: ChartArtifactProps = {
  title: "Monthly Trend",
  type: "line",
  data: [
    { label: "Jan", value: 100 },
    { label: "Feb", value: 120 },
    { label: "Mar", value: 115 },
    { label: "Apr", value: 140 },
  ],
};

const pieChartData: ChartArtifactProps = {
  title: "Market Share",
  type: "pie",
  data: [
    { label: "Product A", value: 45 },
    { label: "Product B", value: 30 },
    { label: "Product C", value: 25 },
  ],
};

describe("ChartArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render chart title", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      expect(screen.getByText("Sales by Region")).toBeInTheDocument();
    });

    it("should render bar chart", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chart-artifact")).toBeInTheDocument();
      expect(screen.getByTestId("chart-container")).toBeInTheDocument();
    });

    it("should render line chart", () => {
      render(
        <TestProvider>
          <ChartArtifact {...lineChartData} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chart-artifact")).toBeInTheDocument();
    });

    it("should render pie chart", () => {
      render(
        <TestProvider>
          <ChartArtifact {...pieChartData} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chart-artifact")).toBeInTheDocument();
    });

    it("should show empty state when no data", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} data={[]} />
        </TestProvider>,
      );
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });

    it("should show data labels", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      expect(screen.getByText("West")).toBeInTheDocument();
      expect(screen.getByText("North")).toBeInTheDocument();
      expect(screen.getByText("South")).toBeInTheDocument();
      expect(screen.getByText("East")).toBeInTheDocument();
    });
  });

  describe("Type Switching", () => {
    it("should render chart type buttons", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} showTypeSwitcher />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /bar/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /line/i })).toBeInTheDocument();
    });

    it("should switch chart type when button clicked", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} showTypeSwitcher />
        </TestProvider>,
      );
      const lineButton = screen.getByRole("button", { name: /line/i });
      fireEvent.click(lineButton);
      // Chart type switcher buttons use primary variant (bg-brand-primary)
      expect(lineButton).toHaveClass("bg-brand-primary");
    });
  });

  describe("Actions", () => {
    it("should render export button", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });

    /**
     * SKIPPED: Requires browser canvas/image APIs not available in jsdom.
     *
     * This functionality is tested in Playwright E2E tests:
     * @see e2e/artifact-export.spec.ts
     *   - "should trigger PNG download when export button clicked on chart"
     *   - "should create valid PNG file from chart export"
     *
     * Run with: npm run test:e2e -- --grep "Chart PNG Export"
     */
    it.skip("should call onDownload when export format selected", async () => {
      const onDownload = vi.fn();
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} onDownload={onDownload} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /export/i }));
      fireEvent.click(screen.getByRole("menuitem", { name: /png/i }));
      await waitFor(() => {
        expect(onDownload).toHaveBeenCalled();
      });
    });

    it("should call onDataPointClick when data point clicked", () => {
      const onDataPointClick = vi.fn();
      render(
        <TestProvider>
          <ChartArtifact
            {...barChartData}
            onDataPointClick={onDataPointClick}
          />
        </TestProvider>,
      );
      // Click on a bar
      const bars = screen.getAllByTestId("chart-bar");
      if (bars.length > 0) {
        fireEvent.click(bars[0]);
        expect(onDataPointClick).toHaveBeenCalledWith(barChartData.data[0]);
      }
    });
  });

  describe("Expandable", () => {
    it("should show expand button when expandable", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} expandable />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /expand/i }),
      ).toBeInTheDocument();
    });

    it("should expand when expand button clicked", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} expandable />
        </TestProvider>,
      );
      const expandButton = screen.getByRole("button", { name: /expand/i });
      fireEvent.click(expandButton);
      expect(
        screen.getByRole("button", { name: /collapse/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Layout", () => {
    it("should have proper test id", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chart-artifact")).toBeInTheDocument();
    });

    it("should apply custom className", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} className="custom-class" />
        </TestProvider>,
      );
      expect(screen.getByTestId("chart-artifact")).toHaveClass("custom-class");
    });
  });

  describe("ArtifactExporter Integration", () => {
    it("should show export menu when export button clicked", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(screen.getByTestId("export-menu")).toBeInTheDocument();
    });

    it("should show PNG option in export menu", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /png/i }),
      ).toBeInTheDocument();
    });

    it("should show SVG option in export menu", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /svg/i }),
      ).toBeInTheDocument();
    });

    it("should show PDF option in export menu", () => {
      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);
      expect(
        screen.getByRole("menuitem", { name: /pdf/i }),
      ).toBeInTheDocument();
    });

    it("should trigger export when format selected", () => {
      // Mock URL methods in JSDOM environment
      const mockUrl = "blob:test";
      const originalCreateObjectURL = URL.createObjectURL;
      const originalRevokeObjectURL = URL.revokeObjectURL;

      URL.createObjectURL = vi.fn().mockReturnValue(mockUrl);
      URL.revokeObjectURL = vi.fn();

      render(
        <TestProvider>
          <ChartArtifact {...barChartData} />
        </TestProvider>,
      );
      const exportButton = screen.getByRole("button", { name: /export/i });
      fireEvent.click(exportButton);

      const pngOption = screen.getByRole("menuitem", { name: /png/i });
      fireEvent.click(pngOption);

      expect(URL.createObjectURL).toHaveBeenCalled();

      // Restore original methods
      URL.createObjectURL = originalCreateObjectURL;
      URL.revokeObjectURL = originalRevokeObjectURL;
    });
  });
});
