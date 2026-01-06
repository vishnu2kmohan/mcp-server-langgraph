/**
 * ObservabilityPage Core Tests
 *
 * Tests for page header, tab navigation, URL sync, and global loading/error states.
 * Split from ObservabilityPage.test.tsx for memory optimization.
 *
 * @see ObservabilityPage.setup.ts for shared mocks and utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ObservabilityPage } from "../ObservabilityPage";
import { TestProvider } from "../../test-utils";
import observabilityReducer from "../../store/slices/observabilitySlice";

// Import shared setup
import {
  resetAllMocks,
  setupDefaultMocks,
  mockRefetchSessions,
} from "./ObservabilityPage.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    useListTracesQuery: vi.fn(),
    useListLogsQuery: vi.fn(),
    useGetMetricsQuery: vi.fn(),
    useGetTraceQuery: vi.fn(),
    useListAlertsQuery: vi.fn(),
    useListSessionsQuery: vi.fn(),
    useListWorkflowsQuery: vi.fn(),
  };
});

vi.mock("../../hooks/useTraceIntelligence", () => ({
  useTraceSummary: vi.fn(() => ({
    summary: null,
    totalDurationMs: null,
    stepCount: null,
    toolCallCount: null,
    success: null,
    keyActions: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useTraceAnomaly: vi.fn(() => ({
    anomalies: [],
    bottlenecks: [],
    healthScore: null,
    optimizationSuggestions: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: vi.fn(() => false),
}));

// Import mocked hooks
import {
  useListTracesQuery,
  useListLogsQuery,
  useGetMetricsQuery,
  useGetTraceQuery,
  useListAlertsQuery,
  useListSessionsQuery,
  useListWorkflowsQuery,
} from "../../api";

// Cast for type safety
const mockUseListTracesQuery = useListTracesQuery as ReturnType<typeof vi.fn>;
const mockUseListLogsQuery = useListLogsQuery as ReturnType<typeof vi.fn>;
const mockUseGetMetricsQuery = useGetMetricsQuery as ReturnType<typeof vi.fn>;
const mockUseGetTraceQuery = useGetTraceQuery as ReturnType<typeof vi.fn>;
const mockUseListAlertsQuery = useListAlertsQuery as ReturnType<typeof vi.fn>;
const mockUseListSessionsQuery = useListSessionsQuery as ReturnType<
  typeof vi.fn
>;
const mockUseListWorkflowsQuery = useListWorkflowsQuery as ReturnType<
  typeof vi.fn
>;

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("ObservabilityPage - Core", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
    setupDefaultMocks({
      useListTracesQuery: mockUseListTracesQuery,
      useListLogsQuery: mockUseListLogsQuery,
      useGetMetricsQuery: mockUseGetMetricsQuery,
      useGetTraceQuery: mockUseGetTraceQuery,
      useListAlertsQuery: mockUseListAlertsQuery,
      useListSessionsQuery: mockUseListSessionsQuery,
      useListWorkflowsQuery: mockUseListWorkflowsQuery,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // HEADER TESTS
  // ===========================================================================

  describe("Header", () => {
    it("should display page title", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Observability")).toBeInTheDocument();
    });

    it("should display page description", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(
        screen.getByText(/Monitor traces, logs, and metrics/),
      ).toBeInTheDocument();
    });

    it("should have refresh button", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Refresh")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // TAB NAVIGATION TESTS
  // ===========================================================================

  describe("Tabs", () => {
    it("should have Agent Sessions tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Agent Sessions")).toBeInTheDocument();
    });

    it("should have Workflow Runs tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Workflow Runs")).toBeInTheDocument();
    });

    it("should have Distributed Traces tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Distributed Traces")).toBeInTheDocument();
    });

    it("should have Logs tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Logs")).toBeInTheDocument();
    });

    it("should have Metrics tab", () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(screen.getByText("Metrics")).toBeInTheDocument();
    });

    it("should default to Agent Sessions tab", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });
    });

    it("should switch to Distributed Traces tab when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Distributed Traces"));

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });
    });

    it("should switch to Logs tab when clicked", async () => {
      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Logs"));

      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // LOADING STATE TESTS
  // ===========================================================================

  describe("Loading State", () => {
    it("should show loading skeletons initially for sessions", () => {
      mockUseListSessionsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchSessions,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      expect(document.querySelector(".animate-pulse")).toBeInTheDocument();
    });

    it("should show multiple skeleton items while loading", () => {
      mockUseListSessionsQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetchSessions,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      const skeletons = document.querySelectorAll(".animate-pulse");
      expect(skeletons.length).toBeGreaterThan(1);
    });
  });

  // ===========================================================================
  // ERROR HANDLING TESTS
  // ===========================================================================

  describe("Error Handling", () => {
    it("should display error message when fetch fails", async () => {
      mockUseListSessionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500, message: "Internal Server Error" },
        refetch: mockRefetchSessions,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
      });
    });

    it("should show retry button on error", async () => {
      mockUseListSessionsQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isFetching: false,
        error: { status: 500 },
        refetch: mockRefetchSessions,
      });

      render(
        <TestProvider>
          <ObservabilityPage />
        </TestProvider>,
      );

      await waitFor(() => {
        expect(screen.getByText("Retry")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // URL TAB SYNC TESTS
  // ===========================================================================

  describe("URL Tab Sync", () => {
    const personaReducer = (
      state = {
        persona: "user" as const,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
    ) => state;

    const renderWithRoute = (initialPath: string) => {
      const store = configureStore({
        reducer: {
          observability: observabilityReducer,
          persona: personaReducer,
        },
      });

      return render(
        <Provider store={store}>
          <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
              <Route path="/observability" element={<ObservabilityPage />} />
              <Route
                path="/observability/agent-sessions"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/workflow-runs"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/traces"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/logs"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/metrics"
                element={<ObservabilityPage />}
              />
              <Route
                path="/observability/alerts"
                element={<ObservabilityPage />}
              />
            </Routes>
          </MemoryRouter>
        </Provider>,
      );
    };

    it("should show agent sessions tab when URL path is /observability/agent-sessions", async () => {
      renderWithRoute("/observability/agent-sessions");

      await waitFor(() => {
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });
    });

    it("should show workflow runs tab when URL path is /observability/workflow-runs", async () => {
      renderWithRoute("/observability/workflow-runs");

      await waitFor(() => {
        expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
      });
    });

    it("should show traces tab when URL path is /observability/traces", async () => {
      renderWithRoute("/observability/traces");

      await waitFor(() => {
        expect(screen.getByText("chat/completion")).toBeInTheDocument();
      });
    });

    it("should show logs tab when URL path is /observability/logs", async () => {
      renderWithRoute("/observability/logs");

      await waitFor(() => {
        expect(screen.getByText("Processing request")).toBeInTheDocument();
      });
    });

    it("should show metrics tab when URL path is /observability/metrics", async () => {
      renderWithRoute("/observability/metrics");

      await waitFor(() => {
        expect(screen.getByText("Total Requests")).toBeInTheDocument();
      });
    });

    it("should show alerts tab when URL path is /observability/alerts", async () => {
      renderWithRoute("/observability/alerts");

      await waitFor(() => {
        expect(screen.getByText("High Memory Usage")).toBeInTheDocument();
      });
    });

    it("should default to agent sessions tab when URL path is /observability", async () => {
      renderWithRoute("/observability");

      await waitFor(() => {
        expect(screen.getByText("Agent Chat Session")).toBeInTheDocument();
      });
    });
  });
});
