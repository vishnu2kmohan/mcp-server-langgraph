/**
 * ObservabilityDocument Component Tests
 *
 * TDD tests for the observability document component used in MainDock tabs.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { ObservabilityDocument } from "./ObservabilityDocument";
import uiReducer from "../../store/slices/uiSlice";

// Mock RTK Query hooks
vi.mock("../../api", () => ({
  useListTracesQuery: () => ({
    data: {
      items: [
        {
          trace_id: "trace-1",
          name: "Test Trace",
          duration_ms: 150,
          status: "success",
          start_time: new Date().toISOString(),
          span_count: 3,
        },
      ],
      total: 1,
    },
    isLoading: false,
    isError: false,
    error: undefined,
    refetch: vi.fn(),
  }),
  useListLogsQuery: () => ({
    data: {
      items: [
        {
          id: "log-1",
          level: "info",
          message: "Test log message",
          timestamp: new Date().toISOString(),
          service: "test-service",
        },
      ],
    },
    isLoading: false,
    refetch: vi.fn(),
  }),
  useGetMetricsQuery: () => ({
    data: {
      requests_total: 1000,
      errors_total: 5,
      avg_latency_ms: 120,
      p99_latency_ms: 450,
      tokens_used: 50000,
      active_sessions: 10,
    },
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

describe("ObservabilityDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<ObservabilityDocument />);
      expect(screen.getByTestId("observability-document")).toBeInTheDocument();
    });

    it("should display observability heading", () => {
      renderWithProviders(<ObservabilityDocument />);
      expect(
        screen.getByRole("heading", { name: /Observability/i }),
      ).toBeInTheDocument();
    });

    it("should apply compact mode styling when compact prop is true", () => {
      renderWithProviders(<ObservabilityDocument compact />);
      const doc = screen.getByTestId("observability-document");
      expect(doc).toHaveClass("text-sm");
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<ObservabilityDocument className="custom-class" />);
      const doc = screen.getByTestId("observability-document");
      expect(doc).toHaveClass("custom-class");
    });
  });
});
