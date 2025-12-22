/**
 * GenerativeWidget Tests - Phase 2
 *
 * Tests for dynamic UI widget generation from AI.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { GenerativeWidget, type WidgetConfig } from "./GenerativeWidget";

// =============================================================================
// Test Data
// =============================================================================

const mockChartWidget: WidgetConfig = {
  id: "widget-1",
  type: "chart",
  title: "Sales Overview",
  data: {
    labels: ["Jan", "Feb", "Mar"],
    values: [100, 150, 200],
  },
};

const mockTableWidget: WidgetConfig = {
  id: "widget-2",
  type: "table",
  title: "User List",
  data: {
    columns: ["Name", "Email", "Status"],
    rows: [
      ["Alice", "alice@example.com", "Active"],
      ["Bob", "bob@example.com", "Inactive"],
    ],
  },
};

const mockTextWidget: WidgetConfig = {
  id: "widget-3",
  type: "text",
  title: "Summary",
  data: {
    content: "This is a generated summary from the AI.",
  },
};

// =============================================================================
// Tests
// =============================================================================

describe("GenerativeWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render widget container", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(screen.getByTestId("generative-widget")).toBeInTheDocument();
    });

    it("should display widget title", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(screen.getByText("Summary")).toBeInTheDocument();
    });

    it("should render chart widget type", () => {
      render(<GenerativeWidget config={mockChartWidget} />);
      expect(screen.getByTestId("widget-chart")).toBeInTheDocument();
    });

    it("should render table widget type", () => {
      render(<GenerativeWidget config={mockTableWidget} />);
      expect(screen.getByTestId("widget-table")).toBeInTheDocument();
    });

    it("should render text widget type", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(screen.getByTestId("widget-text")).toBeInTheDocument();
    });
  });

  describe("Chart Widget", () => {
    it("should display chart data", () => {
      render(<GenerativeWidget config={mockChartWidget} />);
      // Labels should be visible
      expect(screen.getByText("Jan")).toBeInTheDocument();
      expect(screen.getByText("Feb")).toBeInTheDocument();
      expect(screen.getByText("Mar")).toBeInTheDocument();
    });
  });

  describe("Table Widget", () => {
    it("should display table headers", () => {
      render(<GenerativeWidget config={mockTableWidget} />);
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Email")).toBeInTheDocument();
      expect(screen.getByText("Status")).toBeInTheDocument();
    });

    it("should display table rows", () => {
      render(<GenerativeWidget config={mockTableWidget} />);
      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("bob@example.com")).toBeInTheDocument();
    });
  });

  describe("Text Widget", () => {
    it("should display text content", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(
        screen.getByText("This is a generated summary from the AI."),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeleton when isLoading", () => {
      render(<GenerativeWidget config={mockTextWidget} isLoading />);
      expect(screen.getByTestId("widget-skeleton")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when error prop is set", () => {
      render(
        <GenerativeWidget
          config={mockTextWidget}
          error="Failed to load widget"
        />,
      );
      expect(screen.getByText("Failed to load widget")).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      render(
        <GenerativeWidget
          config={mockTextWidget}
          error="Failed to load widget"
        />,
      );
      expect(screen.getByTestId("retry-button")).toBeInTheDocument();
    });

    it("should call onRetry when retry button clicked", () => {
      const onRetry = vi.fn();
      render(
        <GenerativeWidget
          config={mockTextWidget}
          error="Failed to load widget"
          onRetry={onRetry}
        />,
      );
      fireEvent.click(screen.getByTestId("retry-button"));
      expect(onRetry).toHaveBeenCalled();
    });
  });

  describe("Actions", () => {
    it("should show refresh button", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(screen.getByTestId("refresh-button")).toBeInTheDocument();
    });

    it("should call onRefresh when refresh clicked", () => {
      const onRefresh = vi.fn();
      render(
        <GenerativeWidget config={mockTextWidget} onRefresh={onRefresh} />,
      );
      fireEvent.click(screen.getByTestId("refresh-button"));
      expect(onRefresh).toHaveBeenCalledWith(mockTextWidget.id);
    });
  });

  describe("Accessibility", () => {
    it("should have accessible widget role", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(screen.getByRole("region")).toBeInTheDocument();
    });

    it("should have aria-label for widget", () => {
      render(<GenerativeWidget config={mockTextWidget} />);
      expect(
        screen.getByRole("region", { name: /Summary/i }),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <GenerativeWidget config={mockTextWidget} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
