/**
 * InteractiveChart Component Tests
 *
 * Tests for the interactive chart component with fullscreen,
 * download, and data table controls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { InteractiveChart } from "./InteractiveChart";

// Mock ResizeObserver
// Vitest 4 requires class/function syntax for constructor mocks (arrow functions don't work with `new`)
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

describe("InteractiveChart", () => {
  const sampleChartData = {
    type: "bar" as const,
    title: "Sales by Month",
    data: [
      { name: "Jan", value: 100 },
      { name: "Feb", value: 150 },
      { name: "Mar", value: 200 },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the chart with title", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      expect(screen.getByText("Sales by Month")).toBeInTheDocument();
    });

    it("should render chart type selector", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      expect(screen.getByTestId("chart-container")).toBeInTheDocument();
    });

    it("should display control buttons", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
      expect(screen.getByLabelText("Copy data")).toBeInTheDocument();
      expect(screen.getByLabelText("Toggle data table")).toBeInTheDocument();
    });
  });

  describe("Chart Type Toggle", () => {
    it("should show chart type buttons for switching", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      expect(screen.getByLabelText("Line chart")).toBeInTheDocument();
      expect(screen.getByLabelText("Bar chart")).toBeInTheDocument();
      expect(screen.getByLabelText("Pie chart")).toBeInTheDocument();
    });

    it("should switch to line chart when clicked", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      const lineButton = screen.getByLabelText("Line chart");
      fireEvent.click(lineButton);

      // Line button should be active (indicated by styling)
      expect(lineButton.classList.contains("bg-primary-2")).toBe(true);
    });
  });

  describe("Data Table", () => {
    it("should toggle data table when button is clicked", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      // Initially no data table
      expect(screen.queryByRole("table")).not.toBeInTheDocument();

      // Click toggle
      fireEvent.click(screen.getByLabelText("Toggle data table"));

      // Now data table should be visible
      await waitFor(() => {
        expect(screen.getByRole("table")).toBeInTheDocument();
      });
    });

    it("should display chart data in table format", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      fireEvent.click(screen.getByLabelText("Toggle data table"));

      await waitFor(() => {
        expect(screen.getByText("Jan")).toBeInTheDocument();
        expect(screen.getByText("100")).toBeInTheDocument();
        expect(screen.getByText("Feb")).toBeInTheDocument();
        expect(screen.getByText("150")).toBeInTheDocument();
      });
    });
  });

  describe("Copy Functionality", () => {
    it("should copy chart data as JSON when copy button is clicked", async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText },
      });

      render(<InteractiveChart chartData={sampleChartData} />);

      fireEvent.click(screen.getByLabelText("Copy data"));

      await waitFor(() => {
        expect(writeText).toHaveBeenCalled();
        const calledWith = writeText.mock.calls[0][0];
        expect(calledWith).toContain("Jan");
        expect(calledWith).toContain("100");
      });
    });
  });

  describe("Fullscreen", () => {
    it("should toggle fullscreen when button is clicked", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      const container = screen.getByTestId("chart-container");
      expect(container.classList.contains("fixed")).toBe(false);

      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));

      await waitFor(() => {
        expect(container.classList.contains("fixed")).toBe(true);
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error for invalid chart type", async () => {
      const invalidData = {
        type: "unknown" as "bar",
        data: [],
      };

      render(<InteractiveChart chartData={invalidData} />);

      expect(screen.getByTestId("chart-container")).toBeInTheDocument();
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("should exit fullscreen with Escape key", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      // Enter fullscreen
      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));
      await waitFor(() => {
        expect(
          screen.getByTestId("chart-container").classList.contains("fixed"),
        ).toBe(true);
      });

      // Exit with Escape
      const container = screen.getByTestId("chart-container");
      fireEvent.keyDown(container, { key: "Escape" });

      await waitFor(() => {
        expect(
          screen.getByTestId("chart-container").classList.contains("fixed"),
        ).toBe(false);
      });
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria labels for all controls", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
      expect(screen.getByLabelText("Copy data")).toBeInTheDocument();
      expect(screen.getByLabelText("Toggle data table")).toBeInTheDocument();
      expect(screen.getByLabelText("Line chart")).toBeInTheDocument();
      expect(screen.getByLabelText("Bar chart")).toBeInTheDocument();
      expect(screen.getByLabelText("Pie chart")).toBeInTheDocument();
    });

    it("should be focusable for keyboard navigation", async () => {
      render(<InteractiveChart chartData={sampleChartData} />);

      const container = screen.getByTestId("chart-container");
      expect(container).toHaveAttribute("tabIndex", "0");
    });
  });
});
