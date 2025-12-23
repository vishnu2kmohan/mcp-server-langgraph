/**
 * CostDocument Component Tests
 *
 * TDD tests for the cost dashboard document component used in MainDock tabs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { CostDocument } from "./CostDocument";
import uiReducer from "../../store/slices/uiSlice";

// Mock RTK Query hooks
vi.mock("../../api", () => ({
  useGetCostSummaryQuery: () => ({
    data: {
      total_cost: 125.5,
      total_tokens: 50000,
      request_count: 250,
    },
    isLoading: false,
    isError: false,
    error: undefined,
    refetch: vi.fn(),
  }),
  useGetCostByModelQuery: () => ({
    data: [
      { model: "gpt-4", cost: 100.0, requests: 200 },
      { model: "gpt-3.5-turbo", cost: 25.5, requests: 50 },
    ],
    isLoading: false,
    refetch: vi.fn(),
  }),
  useGetCostHistoryQuery: () => ({
    data: [
      { date: "2024-01-01", cost: 10.5 },
      { date: "2024-01-02", cost: 15.0 },
      { date: "2024-01-03", cost: 20.0 },
    ],
    isLoading: false,
    refetch: vi.fn(),
  }),
}));

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: uiReducer,
    },
  });
};

const renderWithProviders = (ui: React.ReactElement) => {
  const store = createTestStore();
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>,
    ),
  };
};

describe("CostDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<CostDocument />);
      expect(screen.getByTestId("cost-document")).toBeInTheDocument();
    });

    it("should display cost dashboard heading", () => {
      renderWithProviders(<CostDocument />);
      expect(
        screen.getByRole("heading", { name: /Cost Dashboard/i }),
      ).toBeInTheDocument();
    });

    it("should apply compact mode styling when compact prop is true", () => {
      renderWithProviders(<CostDocument compact />);
      const doc = screen.getByTestId("cost-document");
      expect(doc).toHaveClass("text-sm");
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<CostDocument className="custom-class" />);
      const doc = screen.getByTestId("cost-document");
      expect(doc).toHaveClass("custom-class");
    });
  });
});
