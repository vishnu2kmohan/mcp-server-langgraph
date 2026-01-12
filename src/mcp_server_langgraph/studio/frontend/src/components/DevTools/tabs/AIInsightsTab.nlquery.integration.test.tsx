/**
 * AIInsightsTab NL Query API Integration Tests (TDD)
 *
 * Tests that NL Query submits to the real studioAnalyze API endpoint
 * instead of using mock setTimeout responses.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

import { AIInsightsTab } from "./AIInsightsTab";
import { api } from "../../../api";
import type { AIInsight } from "../types";

// =============================================================================
// Mock Data
// =============================================================================

const mockInsights: AIInsight[] = [
  {
    id: "insight-1",
    type: "anomaly",
    severity: "high",
    title: "High latency detected",
    description: "Node 3 took 500ms longer than average",
    timestamp: 1703000000000,
    confidence: 0.9,
    entityId: "session-123",
    suggestedAction: "Check network connectivity",
  },
];

const mockObservabilityInsights = {
  traceAnomalies: {
    slowSpans: [],
    errorPatterns: [],
    percentiles: { p50: 150, p95: 800, p99: 1500 },
  },
  alertCorrelations: [],
  costPrediction: {
    trend: "stable" as const,
    projectedDaily: 12.5,
    anomalies: [],
  },
  rootCauseAnalysis: {
    hypothesis: "No issues detected",
    confidence: 0.9,
    rootCauses: [],
    suggestedActions: [],
  },
};

// =============================================================================
// Mock Setup
// =============================================================================

// Track studioAnalyze mutation calls
const mockStudioAnalyzeMutation = vi.fn();

vi.mock("../../../api", async () => {
  const actual =
    await vi.importActual<typeof import("../../../api")>("../../../api");
  return {
    ...actual,
    useStudioAnalyzeMutation: () => [
      mockStudioAnalyzeMutation,
      { isLoading: false, data: null, error: null },
    ],
  };
});

// Mock hooks
const mockUseDevToolsAI = vi.fn().mockReturnValue({
  insights: mockInsights,
  suggestedLayout: null,
  confidence: 0,
  isLoading: false,
  error: null,
  dismissInsight: vi.fn(),
  applyLayout: vi.fn(),
  fetchSuggestions: vi.fn(),
});

const mockUseObservabilityAI = vi.fn().mockReturnValue({
  insights: mockObservabilityInsights,
  suggestedActions: [],
  isAnalyzing: false,
  refresh: vi.fn(),
});

vi.mock("../hooks/useDevToolsAI", () => ({
  useDevToolsAI: (options: unknown) => mockUseDevToolsAI(options),
}));

vi.mock("../hooks/useObservabilityAI", () => ({
  useObservabilityAI: (options: unknown) => mockUseObservabilityAI(options),
}));

// Mock Redux store hooks
const mockUser = { id: "test-user-id", username: "testuser" };

vi.mock("../../../store/hooks", () => ({
  useAppSelector: vi.fn(() => mockUser),
  useAppDispatch: vi.fn(() => vi.fn()),
}));

vi.mock("../../../store/slices/authSlice", () => ({
  selectUser: vi.fn(),
}));

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

// =============================================================================
// Tests: NL Query API Integration
// =============================================================================

describe("AIInsightsTab - NL Query API Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // RTK Query mutations return an object with unwrap() method
    mockStudioAnalyzeMutation.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          user_id: "test-user-id",
          session_id: "session-123",
          analyses: {
            trace_nl_query: {
              response:
                "Based on the analysis, the API errors are caused by database connection timeouts.",
              suggestions: ["Check connection pool", "Review timeout settings"],
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.002",
        }),
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("API integration", () => {
    it("should call studioAnalyze API when query is submitted", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(
        <Provider store={store}>
          <AIInsightsTab
            context="session"
            contextEntityId="session-123"
            enableNLQuery={true}
          />
        </Provider>,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "What caused the API errors?{Enter}");

      // Verify studioAnalyze mutation was called with correct parameters
      await waitFor(() => {
        expect(mockStudioAnalyzeMutation).toHaveBeenCalledWith(
          expect.objectContaining({
            user_id: "test-user-id",
            session_id: "session-123",
            tasks: expect.arrayContaining([
              expect.objectContaining({
                category: "TRACE",
                type: "nl_query",
                data: expect.objectContaining({
                  query: "What caused the API errors?",
                }),
              }),
            ]),
          }),
        );
      });
    });

    it("should display API response in the UI", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(
        <Provider store={store}>
          <AIInsightsTab
            context="session"
            contextEntityId="session-123"
            enableNLQuery={true}
          />
        </Provider>,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "What caused the API errors?{Enter}");

      // Verify response is displayed
      await waitFor(() => {
        expect(screen.getByTestId("nl-query-response")).toHaveTextContent(
          /database connection timeouts/i,
        );
      });
    });

    it("should show error state when API call fails", async () => {
      // Mock unwrap() to reject with an error
      mockStudioAnalyzeMutation.mockReturnValue({
        unwrap: () => Promise.reject(new Error("API Error")),
      });

      const user = userEvent.setup();
      const store = createTestStore();

      render(
        <Provider store={store}>
          <AIInsightsTab
            context="session"
            contextEntityId="session-123"
            enableNLQuery={true}
          />
        </Provider>,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "What caused the API errors?{Enter}");

      // Verify error is displayed
      await waitFor(() => {
        expect(screen.getByTestId("nl-query-error")).toBeInTheDocument();
      });
    });

    it("should include observability context in API call", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(
        <Provider store={store}>
          <AIInsightsTab
            context="session"
            contextEntityId="session-123"
            enableNLQuery={true}
            enableObservability={true}
          />
        </Provider>,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "Why are there slow spans?{Enter}");

      // Verify context is included
      await waitFor(() => {
        expect(mockStudioAnalyzeMutation).toHaveBeenCalledWith(
          expect.objectContaining({
            context: expect.objectContaining({
              observability: expect.any(Object),
            }),
          }),
        );
      });
    });
  });

  describe("query history", () => {
    it("should add successful query to history", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(
        <Provider store={store}>
          <AIInsightsTab
            context="session"
            contextEntityId="session-123"
            enableNLQuery={true}
          />
        </Provider>,
      );

      const input = screen.getByTestId("nl-query-input");
      await user.type(input, "First query{Enter}");

      // Wait for response
      await waitFor(() => {
        expect(screen.getByTestId("nl-query-response")).toBeInTheDocument();
      });

      // Submit second query
      await user.clear(input);
      await user.type(input, "Second query{Enter}");

      // Verify history shows first query
      await waitFor(() => {
        expect(screen.getByTestId("nl-query-history")).toHaveTextContent(
          /First query/i,
        );
      });
    });
  });
});
