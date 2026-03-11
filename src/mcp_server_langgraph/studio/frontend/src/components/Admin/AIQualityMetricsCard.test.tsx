/**
 * AIQualityMetricsCard Component Tests
 *
 * TDD tests for the AI quality metrics card displaying hallucination reports
 * and category breakdowns in the admin dashboard.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AIQualityMetricsCard } from "./AIQualityMetricsCard";

// Mock RTK Query hook
const mockUseGetFeedbackSummaryQuery = vi.fn();

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetFeedbackSummaryQuery: () => mockUseGetFeedbackSummaryQuery(),
  };
});
// Create minimal store for Provider
function createTestStore() {
  return configureStore({
    reducer: {
      api: (state = {}) => state,
    },
  });
}

// Render helper
function renderWithProviders(ui: React.ReactElement) {
  const store = createTestStore();
  const user = userEvent.setup();
  return { ...render(<Provider store={store}>{ui}</Provider>), user };
}

// Mock data
const mockFeedbackSummary = {
  timeframe: "7d",
  totalFeedback: 150,
  positiveCount: 120,
  negativeCount: 30,
  positiveRate: 0.8,
  hallucinationReports: 12,
  hallucinationCategories: {
    factualError: 5,
    outdatedInfo: 3,
    madeUpSource: 2,
    other: 2,
  },
};

describe("AIQualityMetricsCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseGetFeedbackSummaryQuery.mockReturnValue({
      data: mockFeedbackSummary,
      isLoading: false,
      isError: false,
      error: null,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the card with title", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByText(/AI Quality/i)).toBeInTheDocument();
    });

    it("should display hallucination report count", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText(/hallucination reports/i)).toBeInTheDocument();
    });

    it("should display positive rate as percentage", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      // 80% positive rate
      expect(screen.getByText(/80%/)).toBeInTheDocument();
    });

    it("should display category breakdown", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByText(/factual error/i)).toBeInTheDocument();
      expect(screen.getByText(/outdated info/i)).toBeInTheDocument();
      expect(screen.getByText(/made up source/i)).toBeInTheDocument();
      expect(screen.getByText(/other/i)).toBeInTheDocument();
    });

    it("should display category counts", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      // Find elements containing the counts
      expect(screen.getByText("5")).toBeInTheDocument(); // factualError
      expect(screen.getByText("3")).toBeInTheDocument(); // outdatedInfo
    });
  });

  describe("Loading State", () => {
    it("should show skeleton loader when loading", () => {
      mockUseGetFeedbackSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        error: null,
      });

      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByTestId("ai-quality-loading")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when API fails", () => {
      mockUseGetFeedbackSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Failed to fetch" },
      });

      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no data", () => {
      mockUseGetFeedbackSummaryQuery.mockReturnValue({
        data: {
          ...mockFeedbackSummary,
          hallucinationReports: 0,
          hallucinationCategories: undefined,
        },
        isLoading: false,
        isError: false,
        error: null,
      });

      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByText(/no reports/i)).toBeInTheDocument();
    });
  });

  describe("Timeframe", () => {
    it("should display the timeframe from API", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(screen.getByText(/7d/i)).toBeInTheDocument();
    });

    it("should accept custom timeframe prop", () => {
      mockUseGetFeedbackSummaryQuery.mockReturnValue({
        data: { ...mockFeedbackSummary, timeframe: "30d" },
        isLoading: false,
        isError: false,
        error: null,
      });

      renderWithProviders(<AIQualityMetricsCard timeframe="30d" />);
      expect(screen.getByText(/30d/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible heading structure", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      const heading = screen.getByRole("heading", { name: /AI Quality/i });
      expect(heading).toBeInTheDocument();
    });

    it("should have aria-label on the card container", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(
        screen.getByRole("region", { name: /AI quality metrics/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("should render compact variant when compact prop is true", () => {
      renderWithProviders(<AIQualityMetricsCard compact />);
      expect(screen.getByTestId("ai-quality-card")).toHaveClass("p-3");
    });

    it("should hide category breakdown in compact mode", () => {
      renderWithProviders(<AIQualityMetricsCard compact />);
      expect(screen.queryByText(/factual error/i)).not.toBeInTheDocument();
    });
  });

  describe("Visualization Toggle", () => {
    it("should render toggle button when showToggle prop is true", () => {
      renderWithProviders(<AIQualityMetricsCard showToggle />);
      expect(
        screen.getByRole("button", { name: /switch to pie/i }),
      ).toBeInTheDocument();
    });

    it("should not render toggle button by default", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(
        screen.queryByRole("button", { name: /switch to/i }),
      ).not.toBeInTheDocument();
    });

    it("should switch from grid to pie when toggle is clicked", async () => {
      const { user } = renderWithProviders(<AIQualityMetricsCard showToggle />);

      // Initially shows grid (no pie chart)
      expect(
        screen.queryByTestId("ai-quality-pie-chart"),
      ).not.toBeInTheDocument();
      expect(screen.getByText(/factual error/i)).toBeInTheDocument();

      // Click toggle
      await user.click(screen.getByRole("button", { name: /switch to pie/i }));

      // Now shows pie chart
      expect(screen.getByTestId("ai-quality-pie-chart")).toBeInTheDocument();
    });

    it("should switch from pie to grid when toggle is clicked", async () => {
      const { user } = renderWithProviders(
        <AIQualityMetricsCard showToggle visualization="pie" />,
      );

      // Initially shows pie chart
      expect(screen.getByTestId("ai-quality-pie-chart")).toBeInTheDocument();

      // Click toggle
      await user.click(screen.getByRole("button", { name: /switch to grid/i }));

      // Now shows grid
      expect(
        screen.queryByTestId("ai-quality-pie-chart"),
      ).not.toBeInTheDocument();
      expect(screen.getByText(/factual error/i)).toBeInTheDocument();
    });

    it("should not show toggle in compact mode", () => {
      renderWithProviders(<AIQualityMetricsCard showToggle compact />);
      expect(
        screen.queryByRole("button", { name: /switch to/i }),
      ).not.toBeInTheDocument();
    });

    it("should not show toggle when no reports", () => {
      mockUseGetFeedbackSummaryQuery.mockReturnValue({
        data: {
          ...mockFeedbackSummary,
          hallucinationReports: 0,
          hallucinationCategories: undefined,
        },
        isLoading: false,
        isError: false,
        error: null,
      });

      renderWithProviders(<AIQualityMetricsCard showToggle />);
      expect(
        screen.queryByRole("button", { name: /switch to/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Pie Chart Visualization", () => {
    it("should render pie chart when visualization='pie' prop is set", () => {
      renderWithProviders(<AIQualityMetricsCard visualization="pie" />);
      expect(screen.getByTestId("ai-quality-pie-chart")).toBeInTheDocument();
    });

    it("should render grid layout by default (no visualization prop)", () => {
      renderWithProviders(<AIQualityMetricsCard />);
      expect(
        screen.queryByTestId("ai-quality-pie-chart"),
      ).not.toBeInTheDocument();
      // Grid should still show category labels
      expect(screen.getByText(/factual error/i)).toBeInTheDocument();
    });

    it("should hide pie chart in compact mode even when visualization='pie'", () => {
      renderWithProviders(<AIQualityMetricsCard compact visualization="pie" />);
      expect(
        screen.queryByTestId("ai-quality-pie-chart"),
      ).not.toBeInTheDocument();
    });

    it("should not render pie chart when there are no reports", () => {
      mockUseGetFeedbackSummaryQuery.mockReturnValue({
        data: {
          ...mockFeedbackSummary,
          hallucinationReports: 0,
          hallucinationCategories: undefined,
        },
        isLoading: false,
        isError: false,
        error: null,
      });

      renderWithProviders(<AIQualityMetricsCard visualization="pie" />);
      expect(
        screen.queryByTestId("ai-quality-pie-chart"),
      ).not.toBeInTheDocument();
    });

    it("should have accessible label on pie chart", () => {
      renderWithProviders(<AIQualityMetricsCard visualization="pie" />);
      const pieChart = screen.getByTestId("ai-quality-pie-chart");
      expect(pieChart).toHaveAttribute(
        "aria-label",
        expect.stringContaining("category breakdown"),
      );
    });

    it("should render pie chart container with proper structure", () => {
      renderWithProviders(<AIQualityMetricsCard visualization="pie" />);
      // Pie chart container should exist with proper height
      const pieChart = screen.getByTestId("ai-quality-pie-chart");
      expect(pieChart).toHaveClass("h-48");
      // Recharts doesn't fully render SVG in JSDOM, but container should be present
      expect(
        pieChart.querySelector(".recharts-responsive-container"),
      ).toBeInTheDocument();
    });
  });
});
