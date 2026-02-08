/**
 * BudgetForecastChart Tests
 *
 * TDD tests for budget forecast visualization component.
 * Tests written FIRST (RED phase).
 */

import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { BudgetForecastChart, type CostForecast } from "./BudgetForecastChart";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("BudgetForecastChart", () => {
  const defaultForecast: CostForecast = {
    projectedTotal: "300.00",
    confidenceLow: "250.00",
    confidenceHigh: "350.00",
    trend: "stable",
    daysAnalyzed: 10,
    message: "Based on 10 days of data, projecting $300.00 by end of month",
    monthlyLimit: "1000.00",
  };

  describe("Core Rendering", () => {
    it("renders the component", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      expect(screen.getByTestId("budget-forecast-chart")).toBeInTheDocument();
    });

    it("displays projected total", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      // Projected total appears multiple times (in display and message)
      expect(screen.getAllByText(/\$300\.00/).length).toBeGreaterThan(0);
    });

    it("displays confidence range", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/\$250\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$350\.00/)).toBeInTheDocument();
    });

    it("displays days analyzed", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      // Days info appears in the component
      expect(screen.getAllByText(/10 days/i).length).toBeGreaterThan(0);
    });

    it("displays monthly limit", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/\$1,?000\.00/)).toBeInTheDocument();
    });
  });

  describe("Trend Indicators", () => {
    it("shows stable indicator for stable trend", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/stable/i)).toBeInTheDocument();
    });

    it("shows increasing indicator for increasing trend", () => {
      const forecast = { ...defaultForecast, trend: "increasing" as const };
      render(
        <TestProvider>
          <BudgetForecastChart forecast={forecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/increasing/i)).toBeInTheDocument();
    });

    it("shows decreasing indicator for decreasing trend", () => {
      const forecast = { ...defaultForecast, trend: "decreasing" as const };
      render(
        <TestProvider>
          <BudgetForecastChart forecast={forecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/decreasing/i)).toBeInTheDocument();
    });
  });

  describe("Progress Visualization", () => {
    it("shows progress towards limit", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toBeInTheDocument();
    });

    it("progress bar reflects projected percentage", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      const progressBar = screen.getByRole("progressbar");
      // 300/1000 = 30%
      expect(progressBar.getAttribute("aria-valuenow")).toBe("30");
    });

    it("shows warning when projection exceeds limit", () => {
      const forecast = {
        ...defaultForecast,
        projectedTotal: "1200.00",
      };
      render(
        <TestProvider>
          <BudgetForecastChart forecast={forecast} />
        </TestProvider>,
      );
      expect(screen.getByTestId("over-budget-warning")).toBeInTheDocument();
    });
  });

  describe("Confidence Range Visualization", () => {
    it("shows confidence range band", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      expect(screen.getByTestId("confidence-range")).toBeInTheDocument();
    });

    it("displays low and high bounds", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={defaultForecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/\$250\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$350\.00/)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading skeleton when loading", () => {
      render(
        <TestProvider>
          <BudgetForecastChart forecast={null} loading={true} />
        </TestProvider>,
      );
      expect(
        screen.getByTestId("budget-forecast-skeleton"),
      ).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("shows message when no data available", () => {
      const emptyForecast = {
        ...defaultForecast,
        daysAnalyzed: 0,
        projectedTotal: "0.00",
      };
      render(
        <TestProvider>
          <BudgetForecastChart forecast={emptyForecast} />
        </TestProvider>,
      );
      expect(screen.getByText(/no data/i)).toBeInTheDocument();
    });
  });
});
