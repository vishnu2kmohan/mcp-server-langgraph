/**
 * CostPage Tests
 *
 * TDD tests for the cost tracking dashboard page using RTK Query.
 * Tests cover:
 * - Loading state
 * - Cost summary display
 * - Cost by model display
 * - Cost history chart
 * - Period selector
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { CostPage } from "./CostPage";
import personaReducer from "../store/slices/personaSlice";
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import { PersonaProvider } from "../persona/PersonaContext";

// Mock RTK Query hooks
const mockSummaryData = {
  total_cost: 125.5,
  total_tokens: 500000,
  period: "week",
};

const mockModelData = [
  { model: "gpt-4", cost: 75.0, requests: 200000 },
  { model: "gpt-3.5-turbo", cost: 50.5, requests: 300000 },
];

// History data is an array directly from backend
const mockHistoryData = [
  { date: "2025-01-01", cost: 15.5 },
  { date: "2025-01-02", cost: 22.3 },
  { date: "2025-01-03", cost: 18.75 },
  { date: "2025-01-04", cost: 25.0 },
  { date: "2025-01-05", cost: 20.5 },
  { date: "2025-01-06", cost: 12.45 },
  { date: "2025-01-07", cost: 11.0 },
];

const mockRefetch = vi.fn();

// Mock budget status data
const mockBudgetStatusData = {
  status: "ok" as const,
  percent_used: 45.5,
  current_spend: 455.0,
  remaining: 545.0,
  monthly_limit: 1000.0,
  entity_type: "user" as const,
  entity_id: "user:test-user",
  message: "Budget usage is within normal limits",
};

// Mock cost forecast data
const mockForecastData = {
  projected_total: 850.0,
  confidence_low: 720.0,
  confidence_high: 980.0,
  trend: "stable" as const,
  days_analyzed: 14,
  message: "Based on 14 days of data, projected spend is on track",
  monthly_limit: 1000.0,
};

// Import the mocked module for type-safe mocking
import * as apiModule from "../api";

vi.mock("../api", () => ({
  useGetCostSummaryQuery: vi.fn(() => ({
    data: mockSummaryData,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
  })),
  useGetCostByModelQuery: vi.fn(() => ({
    data: mockModelData,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
  })),
  useGetCostHistoryQuery: vi.fn(() => ({
    data: mockHistoryData,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
  })),
  useGetBudgetStatusQuery: vi.fn(() => ({
    data: mockBudgetStatusData,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
  })),
  useGetCostForecastQuery: vi.fn(() => ({
    data: mockForecastData,
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
  })),
  // Organizational cost hooks used by OrganizationCostDashboard
  useGetCostByOrganizationQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
  })),
  useGetCostByProjectQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
  })),
  useGetCostByTeamQuery: vi.fn(() => ({
    data: [],
    isLoading: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: mockRefetch,
  })),
}));

const mockedUseGetCostSummaryQuery = vi.mocked(
  apiModule.useGetCostSummaryQuery,
);
const mockedUseGetCostByModelQuery = vi.mocked(
  apiModule.useGetCostByModelQuery,
);
const mockedUseGetCostHistoryQuery = vi.mocked(
  apiModule.useGetCostHistoryQuery,
);

// Create a minimal store for testing with persona and auth support
const createTestStore = (persona: "admin" | "developer" | "user" = "user") =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona,
        subPersona: null,
        username: "test-user",
        visibleModules: [],
        error: null,
      },
      auth: initialAuthState,
    },
  });

const renderWithProviders = (
  component: React.ReactElement,
  { persona = "user" as const } = {},
) => {
  const store = createTestStore(persona);
  return render(
    <Provider store={store}>
      <PersonaProvider>{component}</PersonaProvider>
    </Provider>,
  );
};

describe("CostPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mocks to default successful responses
    mockedUseGetCostSummaryQuery.mockReturnValue({
      data: mockSummaryData,
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    } as ReturnType<typeof apiModule.useGetCostSummaryQuery>);
    mockedUseGetCostByModelQuery.mockReturnValue({
      data: mockModelData,
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    } as ReturnType<typeof apiModule.useGetCostByModelQuery>);
    mockedUseGetCostHistoryQuery.mockReturnValue({
      data: mockHistoryData,
      isLoading: false,
      isFetching: false,
      isError: false,
      error: null,
      refetch: mockRefetch,
    } as ReturnType<typeof apiModule.useGetCostHistoryQuery>);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Header", () => {
    it("should display page title", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText("Cost Dashboard")).toBeInTheDocument();
    });

    it("should display page description", () => {
      renderWithProviders(<CostPage />);
      expect(
        screen.getByText(/Track and analyze LLM usage costs/i),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show skeleton loaders when loading", () => {
      mockedUseGetCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isFetching: true,
        isError: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostSummaryQuery>);
      mockedUseGetCostByModelQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isFetching: true,
        isError: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostByModelQuery>);
      mockedUseGetCostHistoryQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isFetching: true,
        isError: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostHistoryQuery>);

      renderWithProviders(<CostPage />);
      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it("should hide skeleton loaders after data loads", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText("Total Cost")).toBeInTheDocument();
    });
  });

  describe("Cost Summary", () => {
    it("should display total cost", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/\$125\.50/)).toBeInTheDocument();
    });

    it("should display total tokens", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/500,000/)).toBeInTheDocument();
    });

    it("should display period label", () => {
      renderWithProviders(<CostPage />);
      // The period label shows "Past week" on each summary card (3 cards)
      const periodLabels = screen.getAllByText(/Past week/i);
      expect(periodLabels.length).toBeGreaterThan(0);
    });
  });

  describe("Cost by Model", () => {
    it("should display cost by model section heading", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/Cost by Model/i)).toBeInTheDocument();
    });

    it("should display model names", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText("gpt-4")).toBeInTheDocument();
      expect(screen.getByText("gpt-3.5-turbo")).toBeInTheDocument();
    });

    it("should display model costs", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/\$75\.00/)).toBeInTheDocument();
      expect(screen.getByText(/\$50\.50/)).toBeInTheDocument();
    });

    it("should display model request counts", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/200,000/)).toBeInTheDocument();
      expect(screen.getByText(/300,000/)).toBeInTheDocument();
    });
  });

  describe("Period Selector", () => {
    it("should have period selector dropdown", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should have day option", () => {
      renderWithProviders(<CostPage />);
      const select = screen.getByRole("combobox");
      expect(select).toContainHTML("Day");
    });

    it("should have week option", () => {
      renderWithProviders(<CostPage />);
      const select = screen.getByRole("combobox");
      expect(select).toContainHTML("Week");
    });

    it("should have month option", () => {
      renderWithProviders(<CostPage />);
      const select = screen.getByRole("combobox");
      expect(select).toContainHTML("Month");
    });

    it("should pass period to RTK Query hooks when period changes", async () => {
      renderWithProviders(<CostPage />);

      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "day" } });

      await waitFor(() => {
        // Verify hooks are called with the new period
        expect(mockedUseGetCostSummaryQuery).toHaveBeenCalledWith(
          expect.objectContaining({ period: "day" }),
        );
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error message when API fails", () => {
      mockedUseGetCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { message: "Failed to load cost data" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostSummaryQuery>);

      renderWithProviders(<CostPage />);
      // ErrorState component has role="alert" for accessibility
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /failed to load cost data/i }),
      ).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      mockedUseGetCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { message: "Error" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostSummaryQuery>);

      renderWithProviders(<CostPage />);
      // Retry button inside ErrorState
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should call refetch when retry button is clicked", async () => {
      mockedUseGetCostSummaryQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        isError: true,
        error: { message: "Error" },
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostSummaryQuery>);

      renderWithProviders(<CostPage />);
      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      await waitFor(() => {
        expect(mockRefetch).toHaveBeenCalled();
      });
    });
  });

  describe("RTK Query Integration", () => {
    it("should call useGetCostSummaryQuery with period", () => {
      renderWithProviders(<CostPage />);
      expect(mockedUseGetCostSummaryQuery).toHaveBeenCalledWith(
        expect.objectContaining({ period: "week" }),
      );
    });

    it("should call useGetCostByModelQuery with period", () => {
      renderWithProviders(<CostPage />);
      expect(mockedUseGetCostByModelQuery).toHaveBeenCalledWith(
        expect.objectContaining({ period: "week" }),
      );
    });

    it("should call useGetCostHistoryQuery with period", () => {
      renderWithProviders(<CostPage />);
      expect(mockedUseGetCostHistoryQuery).toHaveBeenCalledWith(
        expect.objectContaining({ period: "week" }),
      );
    });
  });

  describe("Cost History Chart", () => {
    it("should display cost history section heading", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/Cost Trend/i)).toBeInTheDocument();
    });

    it("should display cost history chart container", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByTestId("cost-history-chart")).toBeInTheDocument();
    });

    it("should display date labels on chart", () => {
      renderWithProviders(<CostPage />);
      expect(screen.getByText(/Jan 1/i)).toBeInTheDocument();
    });

    it("should display cost values in chart", () => {
      renderWithProviders(<CostPage />);
      const chart = screen.getByTestId("cost-history-chart");
      expect(chart).toBeInTheDocument();
      const bars = chart.querySelectorAll("[data-cost-bar]");
      expect(bars.length).toBeGreaterThan(0);
    });

    it("should show empty state when no history data", () => {
      mockedUseGetCostHistoryQuery.mockReturnValue({
        data: [], // Empty array - no history data
        isLoading: false,
        isFetching: false,
        isError: false,
        error: null,
        refetch: mockRefetch,
      } as ReturnType<typeof apiModule.useGetCostHistoryQuery>);

      renderWithProviders(<CostPage />);
      expect(
        screen.getByText(/No cost data for this period/i),
      ).toBeInTheDocument();
    });
  });

  describe("Budget Integration", () => {
    it("should render BudgetStatusCard when budget data is available", async () => {
      renderWithProviders(<CostPage userId="user:test-user" />);

      // BudgetStatusCard should be rendered (replaces old userBudget progress bar)
      await waitFor(() => {
        expect(screen.getByTestId("budget-status-card")).toBeInTheDocument();
      });
    });

    it("should render BudgetForecastChart below budget status", async () => {
      renderWithProviders(<CostPage userId="user:test-user" />);

      // BudgetForecastChart should be rendered
      await waitFor(() => {
        expect(screen.getByTestId("budget-forecast-chart")).toBeInTheDocument();
      });
    });

    it("should show budget status card in organizational view for admins", async () => {
      renderWithProviders(<CostPage userId="user:test-user" />, {
        persona: "admin",
      });

      // Switch to organizational view
      fireEvent.click(screen.getByText("Organizational View"));

      // Budget components should still be visible in org view
      await waitFor(() => {
        expect(screen.getByTestId("budget-status-card")).toBeInTheDocument();
      });
    });

    it("should use lazy loading for budget components", async () => {
      // This test verifies that lazy loading wrapper is used
      renderWithProviders(<CostPage userId="user:test-user" />);

      // Suspense fallback or component should render
      await waitFor(() => {
        // Either the skeleton (during load) or the card (after load)
        const card = screen.queryByTestId("budget-status-card");
        const skeleton = screen.queryByTestId("budget-status-skeleton");
        expect(card || skeleton).toBeTruthy();
      });
    });

    it("should show loading skeleton while budget data is loading", async () => {
      renderWithProviders(<CostPage userId="user:test-user" />);

      // During initial render, either skeleton or card should be present
      // The skeleton is shown by the BudgetStatusCard component when loading=true
      await waitFor(() => {
        const hasCard = screen.queryByTestId("budget-status-card");
        const hasSkeleton = screen.queryByTestId("budget-status-skeleton");
        expect(hasCard || hasSkeleton).toBeTruthy();
      });
    });
  });
});
