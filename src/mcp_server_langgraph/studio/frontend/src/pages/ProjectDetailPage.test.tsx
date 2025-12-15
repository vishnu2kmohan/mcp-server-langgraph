/**
 * ProjectDetailPage Tests
 *
 * TDD tests for the unified project workspace page.
 * Tests cover:
 * - Loading state
 * - Error state
 * - Project details display
 * - Tab navigation (Sessions, Workflows, Connections, Observability, Cost, Members)
 * - Back navigation
 * - Session/Workflow click navigation
 * - Empty state messages
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ProjectDetailPage } from "./ProjectDetailPage";
import { api } from "../api";

// Default mock refetch function
const mockRefetch = vi.fn();

// Mock RTK Query
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useGetFeatureFlagsQuery: vi.fn(() => ({
      data: {
        enable_workflows_feature: true,
        enable_observability_ui: true,
        enable_cost_dashboard: true,
      },
      isLoading: false,
      error: null,
    })),
    useGetProjectQuery: vi.fn(),
    // Project-scoped observability hooks
    useGetProjectObservabilityQuery: vi.fn(() => ({
      data: {
        traceCount: 100,
        requestsTotal: 500,
        errorsTotal: 10,
        avgLatencyMs: 150,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })),
    useGetProjectLogsQuery: vi.fn(() => ({
      data: { logs: [], total: 0 },
      isLoading: false,
      error: null,
    })),
    useGetProjectAlertsQuery: vi.fn(() => ({
      data: { alerts: [], total: 0 },
      isLoading: false,
      error: null,
    })),
    // Project-scoped cost hooks
    useGetProjectCostSummaryQuery: vi.fn(() => ({
      data: {
        total_cost: 25.5,
        prompt_tokens: 10000,
        completion_tokens: 5000,
        session_count: 15,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })),
    useGetProjectCostByModelQuery: vi.fn(() => ({
      data: [
        { model: "gpt-4", cost: 20.0, tokens: 12000 },
        { model: "gpt-3.5-turbo", cost: 5.5, tokens: 8000 },
      ],
      isLoading: false,
      error: null,
    })),
    // Project members mutations
    useAddProjectMemberMutation: vi.fn(() => [
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve() }),
      { isLoading: false },
    ]),
    useRemoveProjectMemberMutation: vi.fn(() => [
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve() }),
      { isLoading: false },
    ]),
    // Project connections mutation
    useAddProjectConnectionMutation: vi.fn(() => [
      vi.fn().mockReturnValue({ unwrap: () => Promise.resolve() }),
      { isLoading: false },
    ]),
  };
});

// Mock data
const mockProject = {
  id: "project-123",
  name: "Test Project",
  description: "A test project for testing",
  organization_id: "org-1",
  owner_id: "user-1",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-02T00:00:00Z",
  workflow_count: 2,
  session_count: 3,
  connection_count: 1,
  status: "active",
  workflows: [
    { id: "wf-1", name: "Workflow One", created_at: "2025-01-01T00:00:00Z" },
    { id: "wf-2", name: "Workflow Two", created_at: null },
  ],
  sessions: [
    {
      id: "sess-1",
      name: "Session One",
      message_count: 10,
      created_at: "2025-01-01T00:00:00Z",
    },
    { id: "sess-2", name: "Session Two", message_count: 5, created_at: null },
    { id: "sess-3", name: "Session Three", message_count: 0, created_at: null },
  ],
  connections: [
    { id: "conn-1", name: "MCP Server", type: "mcp", status: "active" },
  ],
  members: [
    { user_id: "user-1", role: "owner", added_at: "2025-01-01T00:00:00Z" },
    { user_id: "user-2", role: "editor", added_at: "2025-01-02T00:00:00Z" },
    { user_id: "user-3", role: "viewer", added_at: "2025-01-03T00:00:00Z" },
  ],
};

const mockEmptyProject = {
  ...mockProject,
  workflow_count: 0,
  session_count: 0,
  connection_count: 0,
  workflows: [],
  sessions: [],
  connections: [],
  members: [],
};

// Create a wrapper with Redux provider (for RTK Query) and router
interface FeatureFlagsState {
  enable_workflows_feature?: boolean;
  enable_observability_ui?: boolean;
  enable_cost_dashboard?: boolean;
}

// Import the mocked function for test manipulation
import {
  useGetFeatureFlagsQuery,
  useGetProjectQuery,
  useGetProjectObservabilityQuery,
  useGetProjectLogsQuery,
  useGetProjectAlertsQuery,
  useGetProjectCostSummaryQuery,
  useGetProjectCostByModelQuery,
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
  useAddProjectConnectionMutation,
} from "../api";

const createStore = () => {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
};

// Helper to render with router and Redux
const renderWithRouter = (
  projectId = "project-123",
  featureFlags: FeatureFlagsState = {},
) => {
  // Update the mock return value for this specific test
  (useGetFeatureFlagsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
    data: {
      enable_workflows_feature: featureFlags.enable_workflows_feature ?? true,
      enable_observability_ui: featureFlags.enable_observability_ui ?? true,
      enable_cost_dashboard: featureFlags.enable_cost_dashboard ?? true,
    },
    isLoading: false,
    error: null,
  });

  const store = createStore();
  return render(
    <Provider store={store}>
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={[`/studio/projects/${projectId}`]}
      >
        <Routes>
          <Route
            path="/studio/projects/:projectId"
            element={<ProjectDetailPage />}
          />
          <Route path="/studio/projects" element={<div>Projects List</div>} />
          <Route path="/studio/chat" element={<div>Chat Page</div>} />
          <Route path="/studio/workflows" element={<div>Workflows Page</div>} />
        </Routes>
      </MemoryRouter>
    </Provider>,
  );
};

describe("ProjectDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRefetch.mockReset();
    // Default: return loaded project data
    (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockProject,
      isLoading: false,
      isFetching: false,
      error: null,
      refetch: mockRefetch,
    });
    // Keep fetch mock for child tab operations (observability, cost)
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        }),
      ),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Loading State", () => {
    it("should show loading spinner while fetching project", async () => {
      // Override mock to return loading state
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: true,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter();

      expect(screen.getByText("Loading project...")).toBeInTheDocument();
      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when fetch fails", async () => {
      // Override mock to return error state
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Internal Server Error" },
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText("Back to Projects")).toBeInTheDocument();
      });
    });

    it("should show error message when fetch throws", async () => {
      // Override mock to return error state
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { message: "Network error" },
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });

    it("should navigate back to projects on error button click", async () => {
      // Override mock to return error state
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Internal Server Error" },
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Back to Projects")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Back to Projects"));

      await waitFor(() => {
        expect(screen.getByText("Projects List")).toBeInTheDocument();
      });
    });
  });

  describe("Project Details Display", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should display project name", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });
    });

    it("should display project description", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(
          screen.getByText("A test project for testing"),
        ).toBeInTheDocument();
      });
    });

    it("should display all tabs with correct counts", async () => {
      renderWithRouter();

      await waitFor(() => {
        // Use getAllByText since tabs and content both show these labels
        expect(screen.getAllByText("Sessions").length).toBeGreaterThanOrEqual(
          1,
        );
        expect(screen.getAllByText("Workflows").length).toBeGreaterThanOrEqual(
          1,
        );
        expect(
          screen.getAllByText("Connections").length,
        ).toBeGreaterThanOrEqual(1);
        expect(screen.getByText("Observability")).toBeInTheDocument();
        expect(screen.getByText("Cost")).toBeInTheDocument();
        expect(screen.getByText("Members")).toBeInTheDocument();
      });

      // Check counts are displayed (may appear multiple times for sessions/members)
      expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1); // session_count & members count
      expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1); // workflow_count
      expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1); // connection_count
    });

    it("should have refresh button", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByTitle("Refresh")).toBeInTheDocument();
      });
    });

    it("should have settings button", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByTitle("Settings")).toBeInTheDocument();
      });
    });
  });

  describe("Tab Navigation", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should default to Sessions tab", async () => {
      renderWithRouter();

      await waitFor(() => {
        // Sessions tab content should be visible
        expect(
          screen.getByRole("heading", { name: "Sessions" }),
        ).toBeInTheDocument();
      });
    });

    it("should switch to Workflows tab on click", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Click Workflows tab
      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: "Workflows" }),
        ).toBeInTheDocument();
      });
    });

    it("should switch to Connections tab on click", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: "Connections" }),
        ).toBeInTheDocument();
      });
    });

    it("should switch to Observability tab on click", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Traces")).toBeInTheDocument();
        expect(screen.getByText("Metrics")).toBeInTheDocument();
        expect(screen.getByText("Logs")).toBeInTheDocument();
        expect(screen.getByText("Alerts")).toBeInTheDocument();
      });
    });

    it("should switch to Cost tab on click", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("Total Cost")).toBeInTheDocument();
        expect(screen.getByText("Total Tokens")).toBeInTheDocument();
        // Mock returns total_cost: 25.50
        expect(screen.getByText("$25.50")).toBeInTheDocument();
      });
    });

    it("should switch to Members tab on click", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("heading", { name: "Members" }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Sessions Tab", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should display session list", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
        expect(screen.getByText("Session Two")).toBeInTheDocument();
        expect(screen.getByText("Session Three")).toBeInTheDocument();
      });
    });

    it("should display message counts", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("10 messages")).toBeInTheDocument();
        expect(screen.getByText("5 messages")).toBeInTheDocument();
        expect(screen.getByText("0 messages")).toBeInTheDocument();
      });
    });

    it("should have New Session button", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });
    });
  });

  describe("Workflows Tab", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should display workflow list", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
        expect(screen.getByText("Workflow Two")).toBeInTheDocument();
      });
    });

    it("should have New Workflow button", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("New Workflow")).toBeInTheDocument();
      });
    });
  });

  describe("Connections Tab", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should display connection list with status", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("MCP Server")).toBeInTheDocument();
        expect(screen.getByText("mcp")).toBeInTheDocument();
        expect(screen.getByText("active")).toBeInTheDocument();
      });
    });

    it("should have Add Connection button", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Connection")).toBeInTheDocument();
      });
    });
  });

  describe("Members Tab", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should display member list with roles", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-1")).toBeInTheDocument();
        expect(screen.getByText("user-2")).toBeInTheDocument();
        expect(screen.getByText("user-3")).toBeInTheDocument();
        expect(screen.getByText("owner")).toBeInTheDocument();
        expect(screen.getByText("editor")).toBeInTheDocument();
        expect(screen.getByText("viewer")).toBeInTheDocument();
      });
    });

    it("should have Add Member button", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });
    });
  });

  describe("Empty States", () => {
    beforeEach(() => {
      // Override with empty project data
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: mockEmptyProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });
    });

    it("should show empty state for sessions", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText(/No sessions yet/)).toBeInTheDocument();
      });
    });

    it("should show empty state for workflows", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText(/No workflows yet/)).toBeInTheDocument();
      });
    });

    it("should show empty state for connections", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText(/No connections yet/)).toBeInTheDocument();
      });
    });

    it("should show empty state for members", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText(/No members added yet/)).toBeInTheDocument();
      });
    });
  });

  describe("Back Navigation", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should navigate back to projects list on back button click", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Find and click the back button (ArrowLeft icon button)
      const backButton = document.querySelector("button");
      if (backButton) {
        fireEvent.click(backButton);
      }

      await waitFor(() => {
        expect(screen.getByText("Projects List")).toBeInTheDocument();
      });
    });
  });

  describe("Observability Tab Links", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should have correct observability links", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        const tracesLink = screen.getByText("View traces →");
        expect(tracesLink).toHaveAttribute(
          "href",
          "/studio/observability?project=project-123",
        );

        const metricsLink = screen.getByText("View metrics →");
        expect(metricsLink).toHaveAttribute(
          "href",
          "/studio/observability?project=project-123&tab=metrics",
        );

        const logsLink = screen.getByText("View logs →");
        expect(logsLink).toHaveAttribute(
          "href",
          "/studio/observability?project=project-123&tab=logs",
        );

        const alertsLink = screen.getByText("View alerts →");
        expect(alertsLink).toHaveAttribute(
          "href",
          "/studio/observability?project=project-123&tab=alerts",
        );
      });
    });
  });

  describe("Cost Tab Links", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should have correct cost link", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        const costLink = screen.getByText("View detailed cost breakdown →");
        expect(costLink).toHaveAttribute(
          "href",
          "/studio/cost?project=project-123",
        );
      });
    });
  });

  // =========================================================================
  // Phase 3: Real Data Fetching Tests
  // =========================================================================

  describe("ObservabilityTab Real Data", () => {
    it("should display trace count from RTK Query", async () => {
      // Mock RTK Query hooks with custom data
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          traceCount: 42,
          requestsTotal: 100,
          errorsTotal: 5,
          avgLatencyMs: 250,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("42")).toBeInTheDocument(); // Total traces
        expect(screen.getByText("100")).toBeInTheDocument(); // Total requests
        expect(screen.getByText("5")).toBeInTheDocument(); // Total errors
      });
    });

    it("should show loading state while fetching observability data", async () => {
      // Mock RTK Query hooks with loading state
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });
      (useGetProjectLogsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      (useGetProjectAlertsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Loading...")).toBeInTheDocument();
      });
    });
  });

  describe("CostTab Real Data", () => {
    it("should display real cost data from RTK Query", async () => {
      // Mock RTK Query hooks with custom cost data
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          total_cost: 12.34,
          prompt_tokens: 50000,
          completion_tokens: 25000,
          session_count: 15,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (
        useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("$12.34")).toBeInTheDocument(); // Total cost
        expect(screen.getByText("75,000")).toBeInTheDocument(); // Total tokens (50000 + 25000)
        expect(screen.getByText("15")).toBeInTheDocument(); // Sessions
      });
    });

    it("should show loading state while fetching cost data", async () => {
      // Mock RTK Query hooks with loading state
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });
      (
        useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("Loading...")).toBeInTheDocument();
      });
    });

    it("should display cost by model section", async () => {
      // Mock RTK Query hooks with model data
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          total_cost: 12.34,
          prompt_tokens: 50000,
          completion_tokens: 25000,
          session_count: 15,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (
        useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: [
          { model: "gpt-4", cost: 8.5, tokens: 40000 },
          { model: "claude-3-opus", cost: 3.84, tokens: 35000 },
        ],
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("Cost by Model")).toBeInTheDocument();
      });
    });

    it("should display model names in cost breakdown", async () => {
      // Mock RTK Query hooks with model data
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          total_cost: 12.34,
          prompt_tokens: 50000,
          completion_tokens: 25000,
          session_count: 15,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (
        useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: [
          { model: "gpt-4", cost: 8.5, tokens: 40000 },
          { model: "claude-3-opus", cost: 3.84, tokens: 35000 },
        ],
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("gpt-4")).toBeInTheDocument();
        expect(screen.getByText("claude-3-opus")).toBeInTheDocument();
      });
    });

    it("should display model costs in cost breakdown", async () => {
      // Mock RTK Query hooks with model data
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          total_cost: 12.34,
          prompt_tokens: 50000,
          completion_tokens: 25000,
          session_count: 15,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (
        useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: [
          { model: "gpt-4", cost: 8.5, tokens: 40000 },
          { model: "claude-3-opus", cost: 3.84, tokens: 35000 },
        ],
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("$8.50")).toBeInTheDocument();
        expect(screen.getByText("$3.84")).toBeInTheDocument();
      });
    });

    it("should show empty state when no model costs", async () => {
      // Mock RTK Query hooks with empty data
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          total_cost: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
          session_count: 0,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (
        useGetProjectCostByModelQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText("Cost by Model")).toBeInTheDocument();
        expect(screen.getByText(/No model data/i)).toBeInTheDocument();
      });
    });
  });

  describe("ObservabilityTab Logs", () => {
    it("should call useGetProjectLogsQuery hook", async () => {
      // RTK Query hook is automatically called when ObservabilityTab mounts
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        // Verify hook was called (via UI presence)
        expect(screen.getByText("Recent Logs")).toBeInTheDocument();
      });

      // Verify the hook was called with the project ID
      expect(useGetProjectLogsQuery).toHaveBeenCalledWith("project-123");
    });

    it("should display recent logs section", async () => {
      // Mock RTK Query hook with log data
      (useGetProjectLogsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          logs: [
            {
              id: "log-1",
              timestamp: "2025-01-01T12:00:00Z",
              level: "info",
              message: "Session started",
            },
          ],
          total: 1,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Recent Logs")).toBeInTheDocument();
      });
    });

    it("should display log messages", async () => {
      // Mock RTK Query hook with log data
      (useGetProjectLogsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          logs: [
            {
              id: "log-1",
              timestamp: "2025-01-01T12:00:00Z",
              level: "info",
              message: "Session started",
            },
            {
              id: "log-2",
              timestamp: "2025-01-01T12:01:00Z",
              level: "error",
              message: "Tool execution failed",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Session started")).toBeInTheDocument();
        expect(screen.getByText("Tool execution failed")).toBeInTheDocument();
      });
    });

    it("should display log levels with appropriate styling", async () => {
      // Mock RTK Query hook with log data
      (useGetProjectLogsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          logs: [
            {
              id: "log-1",
              timestamp: "2025-01-01T12:00:00Z",
              level: "info",
              message: "Info log",
            },
            {
              id: "log-2",
              timestamp: "2025-01-01T12:01:00Z",
              level: "error",
              message: "Error log",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("info")).toBeInTheDocument();
        expect(screen.getByText("error")).toBeInTheDocument();
      });
    });

    it("should show empty state when no logs", async () => {
      // Mock RTK Query hooks with empty data
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          traceCount: 0,
          requestsTotal: 0,
          errorsTotal: 0,
          avgLatencyMs: 0,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (useGetProjectLogsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: { logs: [], total: 0 },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Recent Logs")).toBeInTheDocument();
        expect(screen.getByText(/No logs/i)).toBeInTheDocument();
      });
    });
  });

  describe("ObservabilityTab Alerts", () => {
    it("should call useGetProjectAlertsQuery hook", async () => {
      // RTK Query hook is automatically called when ObservabilityTab mounts
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        // Verify hook was called (via UI presence)
        expect(screen.getByText("Active Alerts")).toBeInTheDocument();
      });

      // Verify the hook was called with the project ID
      expect(useGetProjectAlertsQuery).toHaveBeenCalledWith("project-123");
    });

    it("should display active alerts section", async () => {
      // Mock RTK Query hook with alert data
      (useGetProjectAlertsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          alerts: [
            {
              id: "alert-1",
              severity: "warning",
              message: "High latency",
              created_at: "2025-01-01T12:00:00Z",
            },
          ],
          total: 1,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Active Alerts")).toBeInTheDocument();
      });
    });

    it("should display alert messages", async () => {
      // Mock RTK Query hook with alert data
      (useGetProjectAlertsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          alerts: [
            {
              id: "alert-1",
              severity: "warning",
              message: "High latency detected",
              created_at: "2025-01-01T12:00:00Z",
            },
            {
              id: "alert-2",
              severity: "critical",
              message: "Error rate exceeded",
              created_at: "2025-01-01T12:01:00Z",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("High latency detected")).toBeInTheDocument();
        expect(screen.getByText("Error rate exceeded")).toBeInTheDocument();
      });
    });

    it("should display alert severity levels", async () => {
      // Mock RTK Query hook with alert data
      (useGetProjectAlertsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: {
          alerts: [
            {
              id: "alert-1",
              severity: "warning",
              message: "Warning alert",
              created_at: "2025-01-01T12:00:00Z",
            },
            {
              id: "alert-2",
              severity: "critical",
              message: "Critical alert",
              created_at: "2025-01-01T12:01:00Z",
            },
          ],
          total: 2,
        },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("warning")).toBeInTheDocument();
        expect(screen.getByText("critical")).toBeInTheDocument();
      });
    });

    it("should show empty state when no alerts", async () => {
      // Mock RTK Query hooks with empty data
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: {
          traceCount: 0,
          requestsTotal: 0,
          errorsTotal: 0,
          avgLatencyMs: 0,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });
      (useGetProjectLogsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: { logs: [], total: 0 },
        isLoading: false,
        error: null,
      });
      (useGetProjectAlertsQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: { alerts: [], total: 0 },
        isLoading: false,
        error: null,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText("Active Alerts")).toBeInTheDocument();
        expect(screen.getByText(/No active alerts/i)).toBeInTheDocument();
      });
    });
  });

  describe("Refresh Functionality", () => {
    // Uses default RTK Query mock from parent beforeEach

    it("should call refetch when refresh button is clicked", async () => {
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Reset mock to track new calls
      mockRefetch.mockClear();

      // Click refresh
      fireEvent.click(screen.getByTitle("Refresh"));

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Action Button Tests (Phase 1: Wire up action buttons)
  // =========================================================================

  describe("New Session Button", () => {
    it("should open dialog when clicked", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Session"));

      await waitFor(() => {
        expect(screen.getByText("Create New Session")).toBeInTheDocument();
        expect(screen.getByLabelText("Session Name")).toBeInTheDocument();
      });
    });

    it("should create session when dialog is submitted", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "POST" && url.includes("/sessions")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                session_count: 4,
                sessions: [
                  ...mockProject.sessions,
                  {
                    id: "sess-new",
                    name: "New Test Session",
                    message_count: 0,
                    created_at: null,
                  },
                ],
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByText("New Session"));

      await waitFor(() => {
        expect(screen.getByLabelText("Session Name")).toBeInTheDocument();
      });

      // Fill form and submit
      fireEvent.change(screen.getByLabelText("Session Name"), {
        target: { value: "New Test Session" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        // Should call POST to create session
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/projects/project-123/sessions"),
          expect.objectContaining({
            method: "POST",
          }),
        );
      });
    });

    it("should close dialog when cancel is clicked", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("New Session")).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByText("New Session"));

      await waitFor(() => {
        expect(screen.getByText("Create New Session")).toBeInTheDocument();
      });

      // Click cancel
      fireEvent.click(screen.getByText("Cancel"));

      await waitFor(() => {
        expect(
          screen.queryByText("Create New Session"),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("New Workflow Button", () => {
    it("should open dialog when clicked", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Workflows tab
      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("New Workflow")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("New Workflow"));

      await waitFor(() => {
        expect(screen.getByText("Create New Workflow")).toBeInTheDocument();
        expect(screen.getByLabelText("Workflow Name")).toBeInTheDocument();
      });
    });

    it("should create workflow when dialog is submitted", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "POST" && url.includes("/workflows")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                workflow_count: 3,
                workflows: [
                  ...mockProject.workflows,
                  { id: "wf-new", name: "New Test Workflow", created_at: null },
                ],
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Workflows tab
      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("New Workflow")).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByText("New Workflow"));

      await waitFor(() => {
        expect(screen.getByLabelText("Workflow Name")).toBeInTheDocument();
      });

      // Fill form and submit
      fireEvent.change(screen.getByLabelText("Workflow Name"), {
        target: { value: "New Test Workflow" },
      });
      fireEvent.click(screen.getByText("Create"));

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/projects/project-123/workflows"),
          expect.objectContaining({
            method: "POST",
          }),
        );
      });
    });
  });

  describe("Add Connection Button", () => {
    it("should open dialog when clicked", async () => {
      // Uses default RTK Query mocks - no fetch mock needed
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Connections tab
      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Connection")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Connection"));

      await waitFor(() => {
        expect(screen.getByText("Add New Connection")).toBeInTheDocument();
        expect(screen.getByLabelText("Connection Name")).toBeInTheDocument();
        expect(screen.getByLabelText("Connection Type")).toBeInTheDocument();
      });
    });

    it("should create connection when dialog is submitted", async () => {
      // Mock the RTK Query mutation
      const mockAddConnection = vi
        .fn()
        .mockReturnValue({ unwrap: () => Promise.resolve() });
      (
        useAddProjectConnectionMutation as ReturnType<typeof vi.fn>
      ).mockReturnValue([mockAddConnection, { isLoading: false }]);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Connections tab
      fireEvent.click(screen.getByRole("button", { name: /Connections/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Connection")).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByText("Add Connection"));

      await waitFor(() => {
        expect(screen.getByLabelText("Connection Name")).toBeInTheDocument();
      });

      // Fill form and submit
      fireEvent.change(screen.getByLabelText("Connection Name"), {
        target: { value: "New MCP" },
      });
      fireEvent.change(screen.getByLabelText("Connection Type"), {
        target: { value: "mcp_server" },
      });
      fireEvent.click(screen.getByText("Add"));

      await waitFor(() => {
        // Verify RTK Query mutation was called with correct parameters
        expect(mockAddConnection).toHaveBeenCalledWith(
          expect.objectContaining({
            project_id: "project-123",
            connection_type: "mcp_server",
            connection_name: "New MCP",
          }),
        );
      });
    });
  });

  describe("Add Member Button", () => {
    it("should open dialog when clicked", async () => {
      // Uses default RTK Query mocks - no fetch mock needed
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Members tab
      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Add Member"));

      await waitFor(() => {
        expect(screen.getByText("Add Team Member")).toBeInTheDocument();
        expect(screen.getByLabelText("User ID")).toBeInTheDocument();
        expect(screen.getByLabelText("Role")).toBeInTheDocument();
      });
    });

    it("should add member when dialog is submitted", async () => {
      // Mock the RTK Query mutation
      const mockAddMember = vi
        .fn()
        .mockReturnValue({ unwrap: () => Promise.resolve() });
      (useAddProjectMemberMutation as ReturnType<typeof vi.fn>).mockReturnValue(
        [mockAddMember, { isLoading: false }],
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Members tab
      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByText("Add Member"));

      await waitFor(() => {
        expect(screen.getByLabelText("User ID")).toBeInTheDocument();
      });

      // Fill form and submit
      fireEvent.change(screen.getByLabelText("User ID"), {
        target: { value: "user-new" },
      });
      fireEvent.change(screen.getByLabelText("Role"), {
        target: { value: "editor" },
      });
      fireEvent.click(screen.getByText("Add"));

      await waitFor(() => {
        // Verify RTK Query mutation was called with correct parameters
        expect(mockAddMember).toHaveBeenCalledWith(
          expect.objectContaining({
            project_id: "project-123",
            user_id: "user-new",
            role: "editor",
          }),
        );
      });
    });

    it("should show role options: editor, viewer, executor", async () => {
      // Uses default RTK Query mocks - no fetch mock needed
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Members tab
      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("Add Member")).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByText("Add Member"));

      await waitFor(() => {
        const roleSelect = screen.getByLabelText("Role");
        expect(roleSelect).toBeInTheDocument();
        // Check options exist
        expect(
          screen.getByRole("option", { name: "Editor" }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("option", { name: "Viewer" }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("option", { name: "Executor" }),
        ).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // Remove Resource Tests (Critical Gap - DELETE operations)
  // =========================================================================

  describe("Remove Session", () => {
    it("should have remove button on each session", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
      });

      // Should have remove buttons for each session
      const removeButtons = screen.getAllByLabelText(/remove session/i);
      expect(removeButtons.length).toBe(3);
    });

    it("should call DELETE API when remove button is clicked", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "DELETE" && url.includes("/sessions/sess-1")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                session_count: 2,
                sessions: mockProject.sessions.filter((s) => s.id !== "sess-1"),
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Session One")).toBeInTheDocument();
      });

      // Click remove button for first session
      const removeButtons = screen.getAllByLabelText(/remove session/i);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining(
            "/api/v1/projects/project-123/sessions/sess-1",
          ),
          expect.objectContaining({
            method: "DELETE",
          }),
        );
      });
    });
  });

  describe("Remove Workflow", () => {
    it("should have remove button on each workflow", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockProject),
          }),
        ),
      );

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Switch to Workflows tab
      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
      });

      // Should have remove buttons for each workflow
      const removeButtons = screen.getAllByLabelText(/remove workflow/i);
      expect(removeButtons.length).toBe(2);
    });

    it("should call DELETE API when remove button is clicked", async () => {
      const fetchMock = vi.fn((url: string, options?: RequestInit) => {
        if (options?.method === "DELETE" && url.includes("/workflows/wf-1")) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                ...mockProject,
                workflow_count: 1,
                workflows: mockProject.workflows.filter((w) => w.id !== "wf-1"),
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProject),
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Workflows/i }));

      await waitFor(() => {
        expect(screen.getByText("Workflow One")).toBeInTheDocument();
      });

      // Click remove button for first workflow
      const removeButtons = screen.getAllByLabelText(/remove workflow/i);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining(
            "/api/v1/projects/project-123/workflows/wf-1",
          ),
          expect.objectContaining({
            method: "DELETE",
          }),
        );
      });
    });
  });

  describe("Remove Member", () => {
    it("should have remove button on non-owner members", async () => {
      // Uses default RTK Query mocks - no fetch mock needed
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-1")).toBeInTheDocument();
      });

      // Should have remove buttons for non-owner members (2 out of 3)
      const removeButtons = screen.getAllByLabelText(/remove member/i);
      expect(removeButtons.length).toBe(2);
    });

    it("should call RTK Query mutation when remove button is clicked", async () => {
      // Mock the RTK Query mutation
      const mockRemoveMember = vi
        .fn()
        .mockReturnValue({ unwrap: () => Promise.resolve() });
      (
        useRemoveProjectMemberMutation as ReturnType<typeof vi.fn>
      ).mockReturnValue([mockRemoveMember, { isLoading: false }]);

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-2")).toBeInTheDocument();
      });

      // Click remove button (first non-owner member)
      const removeButtons = screen.getAllByLabelText(/remove member/i);
      fireEvent.click(removeButtons[0]);

      await waitFor(() => {
        // Verify RTK Query mutation was called with correct parameters
        expect(mockRemoveMember).toHaveBeenCalledWith(
          expect.objectContaining({
            project_id: "project-123",
            user_id: "user-2",
          }),
        );
      });
    });

    it("should not show remove button for owner", async () => {
      // Uses default RTK Query mocks - no fetch mock needed
      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Members/i }));

      await waitFor(() => {
        expect(screen.getByText("user-1")).toBeInTheDocument();
        expect(screen.getByText("owner")).toBeInTheDocument();
      });

      // Owner row should not have remove button
      const ownerRow = screen
        .getByText("user-1")
        .closest('div[class*="rounded-lg"]');
      expect(ownerRow?.querySelector('[aria-label*="remove"]')).toBeNull();
    });
  });

  // =========================================================================
  // Feature Flag Integration Tests
  // =========================================================================

  describe("Feature Flag Integration", () => {
    // Uses default RTK Query mock from parent beforeEach

    describe("All Features Enabled", () => {
      it("should show all tabs when all features are enabled", async () => {
        renderWithRouter("project-123", {
          enable_workflows_feature: true,
          enable_observability_ui: true,
          enable_cost_dashboard: true,
        });

        await waitFor(() => {
          expect(screen.getByText("Test Project")).toBeInTheDocument();
        });

        // All tabs should be visible
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Workflows/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Observability/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Cost/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();
      });
    });

    describe("Workflows Feature Disabled", () => {
      it("should hide Workflows tab when enable_workflows_feature is false", async () => {
        renderWithRouter("project-123", {
          enable_workflows_feature: false,
          enable_observability_ui: true,
          enable_cost_dashboard: true,
        });

        await waitFor(() => {
          expect(screen.getByText("Test Project")).toBeInTheDocument();
        });

        // Sessions tab should still be visible
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();

        // Workflows tab should be hidden
        expect(
          screen.queryByRole("button", { name: /Workflows/i }),
        ).not.toBeInTheDocument();

        // Other tabs should still be visible
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Observability/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Cost/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();
      });
    });

    describe("Observability Feature Disabled", () => {
      it("should hide Observability tab when enable_observability_ui is false", async () => {
        renderWithRouter("project-123", {
          enable_workflows_feature: true,
          enable_observability_ui: false,
          enable_cost_dashboard: true,
        });

        await waitFor(() => {
          expect(screen.getByText("Test Project")).toBeInTheDocument();
        });

        // Sessions tab should still be visible
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Workflows/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();

        // Observability tab should be hidden
        expect(
          screen.queryByRole("button", { name: /Observability/i }),
        ).not.toBeInTheDocument();

        // Other tabs should still be visible
        expect(
          screen.getByRole("button", { name: /Cost/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();
      });
    });

    describe("Cost Dashboard Disabled", () => {
      it("should hide Cost tab when enable_cost_dashboard is false", async () => {
        renderWithRouter("project-123", {
          enable_workflows_feature: true,
          enable_observability_ui: true,
          enable_cost_dashboard: false,
        });

        await waitFor(() => {
          expect(screen.getByText("Test Project")).toBeInTheDocument();
        });

        // Sessions tab should still be visible
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Workflows/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Observability/i }),
        ).toBeInTheDocument();

        // Cost tab should be hidden
        expect(
          screen.queryByRole("button", { name: /Cost/i }),
        ).not.toBeInTheDocument();

        // Members tab should still be visible
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();
      });
    });

    describe("Multiple Features Disabled", () => {
      it("should hide multiple tabs when multiple features are disabled", async () => {
        renderWithRouter("project-123", {
          enable_workflows_feature: false,
          enable_observability_ui: false,
          enable_cost_dashboard: false,
        });

        await waitFor(() => {
          expect(screen.getByText("Test Project")).toBeInTheDocument();
        });

        // Essential tabs should always be visible
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();

        // Feature-gated tabs should be hidden
        expect(
          screen.queryByRole("button", { name: /Workflows/i }),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByRole("button", { name: /Observability/i }),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByRole("button", { name: /Cost/i }),
        ).not.toBeInTheDocument();
      });
    });

    describe("Default Behavior", () => {
      it("should show all tabs by default (all features enabled)", async () => {
        // No feature flags passed - should default to all enabled
        renderWithRouter("project-123");

        await waitFor(() => {
          expect(screen.getByText("Test Project")).toBeInTheDocument();
        });

        // All tabs should be visible
        expect(
          screen.getByRole("button", { name: /Sessions/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Workflows/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Connections/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Observability/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Cost/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /Members/i }),
        ).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // Error UI with Retry Tests
  // =========================================================================

  describe("ObservabilityTab Error Handling", () => {
    it("should show error message when RTK Query returns error", async () => {
      // Mock RTK Query hooks with error state
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it("should show retry button when RTK Query returns error", async () => {
      // Mock RTK Query hooks with error state
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });
    });

    it("should refetch when retry button is clicked", async () => {
      const mockRefetch = vi.fn();

      // Start with error state
      (
        useGetProjectObservabilityQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Observability/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });

      // Click retry
      fireEvent.click(screen.getByRole("button", { name: /Retry/i }));

      // Verify refetch was called
      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe("CostTab Error Handling", () => {
    it("should show error message when RTK Query returns error", async () => {
      // Mock RTK Query hooks with error state
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(screen.getByText(/Error:/i)).toBeInTheDocument();
      });
    });

    it("should show retry button when RTK Query returns error", async () => {
      // Mock RTK Query hooks with error state
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: vi.fn(),
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });
    });

    it("should refetch when retry button is clicked", async () => {
      const mockRefetch = vi.fn();

      // Start with error state
      (
        useGetProjectCostSummaryQuery as ReturnType<typeof vi.fn>
      ).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: { status: 500, data: "Server error" },
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Cost/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /Retry/i }),
        ).toBeInTheDocument();
      });

      // Click retry
      fireEvent.click(screen.getByRole("button", { name: /Retry/i }));

      // Verify refetch was called
      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  // =========================================================================
  // RTK Query Integration Tests (Phase: Migration to RTK Query)
  // =========================================================================

  describe("RTK Query Integration", () => {
    // Uses global mockRefetch and default beforeEach setup

    it("should call useGetProjectQuery with project ID", async () => {
      renderWithRouter("project-123");

      await waitFor(() => {
        expect(useGetProjectQuery).toHaveBeenCalledWith(
          "project-123",
          expect.any(Object),
        );
      });
    });

    it("should show loading state from RTK Query", async () => {
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: true,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter();

      expect(screen.getByText("Loading project...")).toBeInTheDocument();
    });

    it("should show error state from RTK Query", async () => {
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: null,
        isLoading: false,
        isFetching: false,
        error: { status: 500, data: "Internal Server Error" },
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText(/Error:/)).toBeInTheDocument();
        expect(screen.getByText("Back to Projects")).toBeInTheDocument();
      });
    });

    it("should call refetch when refresh button is clicked", async () => {
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: mockProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTitle("Refresh"));

      expect(mockRefetch).toHaveBeenCalled();
    });

    it("should show loading indicator when refetching", async () => {
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: mockProject,
        isLoading: false,
        isFetching: true,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
      });

      // Refresh button should show spinning indicator
      const refreshButton = screen.getByTitle("Refresh");
      expect(refreshButton.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should display project data from RTK Query", async () => {
      (useGetProjectQuery as ReturnType<typeof vi.fn>).mockReturnValue({
        data: mockProject,
        isLoading: false,
        isFetching: false,
        error: null,
        refetch: mockRefetch,
      });

      renderWithRouter();

      await waitFor(() => {
        expect(screen.getByText("Test Project")).toBeInTheDocument();
        expect(
          screen.getByText("A test project for testing"),
        ).toBeInTheDocument();
      });
    });
  });
});
